"""Registered CG daily-OI loader for BTC (widening pre-registration §2).

Source: data/lab/oi_cg_daily_btc.csv — read-only export of the CG relay's
daily OI candles (exchange=Binance, symbol=BTCUSDT, 2020-02-27 ->
2026-05-18 frozen tail), `oi` = candle open. Stamp semantics were
determined pre-OOS against the bybit daily-snapshot era and committed in
docs/gate0/OI-CG-STAMP-SEMANTICS.md: the stamp is the candle-START time,
so row D IS the day-D 00:00 snapshot (16:00 snapshot on the 13
double-stamp days of 2026-04) and the registered availability rule is
causal verbatim.

Registered semantics (§2 "Daily-OI loader", mirrors D4.2/D4.4):
  - dedupe to the LAST stamp per UTC day D (actual stamp times kept);
  - oi_chg_24h_daily(D) = snap(D)/snap(D-1) - 1, NaN when day D-1 has no
    snapshot;
  - the day-D value becomes usable at the first 4h bar opening STRICTLY
    AFTER the day-D stamp (00:00 stamp -> the D 04:00 bar; a bar opening
    exactly at the stamp must not see it);
  - staleness > 48h from the stamp -> NaN -> `oi-na` downstream (exactly
    48h is still fresh — the frozen _asof cap convention).
"""

from pathlib import Path

import numpy as np
import pandas as pd

STALENESS_OI_CG = pd.Timedelta(hours=48)


def load_oi_cg_daily(path: str | Path) -> pd.Series:
    """CSV (ts, oi) -> float Series deduped to the LAST stamp per UTC day.

    Index: the surviving rows' actual stamp times (sorted ascending) —
    NOT normalized to midnight, because availability in join_to_bars is
    measured from the stamp itself (the 16:00 stamps of 2026-04 only
    become usable at the 20:00 bar).
    """
    df = pd.read_csv(path)
    s = pd.Series(
        df["oi"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(pd.to_datetime(df["ts"])),
        name="oi",
    ).sort_index()
    day = s.index.normalize()
    return s[~day.duplicated(keep="last")]


def oi_chg_24h_daily(daily: pd.Series) -> pd.Series:
    """snap(D)/snap(D-1) - 1 on the deduped daily series (registered).

    A row whose PRECEDING UTC day carries no snapshot gets NaN (the first
    row always does) — a hole never silently widens the change window.
    Index: unchanged (the day-D stamps).
    """
    vals = daily.to_numpy(dtype=float)
    chg = np.full(len(daily), np.nan)
    if len(daily) > 1:
        day = daily.index.normalize()
        adjacent = (day[1:] - day[:-1]) == pd.Timedelta(days=1)
        chg[1:] = np.where(adjacent, vals[1:] / vals[:-1] - 1, np.nan)
    return pd.Series(chg, index=daily.index, name="oi_chg_24h_daily")


def join_to_bars(daily_chg: pd.Series, bar_index: pd.DatetimeIndex) -> pd.Series:
    """As-of join under the registered availability rule.

    Each bar sees the value of the last stamp STRICTLY BEFORE its open
    (first bar opening after the day-D stamp is the first to see day D:
    00:00 stamp -> D 04:00 bar), NaN when no stamp precedes the bar or
    when bar_open - stamp > 48h (frozen tail 2026-05-18 -> NaN from the
    2026-05-20 04:00 bar onward).
    """
    if daily_chg.empty:
        return pd.Series(np.nan, index=bar_index, name=daily_chg.name)
    pos = daily_chg.index.searchsorted(bar_index, side="left") - 1
    safe = np.clip(pos, 0, None)
    vals = daily_chg.to_numpy(dtype=float)[safe]
    age = bar_index.to_numpy() - daily_chg.index.to_numpy()[safe]
    ok = (pos >= 0) & (age <= STALENESS_OI_CG.to_timedelta64())
    return pd.Series(np.where(ok, vals, np.nan), index=bar_index,
                     name=daily_chg.name)
