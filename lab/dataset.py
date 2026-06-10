"""Causal 4h panel assembly — committed CSVs -> aligned bar-grid DataFrame.

Plan Task 1.1 + Gate-0 freeze addendum D4. All joins are causal: a bar may
only see values stamped at-or-before its open_time.

Policies (addendum D4):
  D4.1  bars drop_duplicates on open_time (7 byte-identical dupes 2026-05-28/29)
  D4.2  OI/LS: resample to daily 00:00 snapshots FIRST (last observation
        at-or-before each midnight, valid only if observed within the 24h
        ending at that midnight — holes are never forward-filled), then as-of
        join to bars with staleness cap 36h, else NaN. One daily cadence
        across the whole window.
  D4.3  holes under the cap -> NaN (classifier NaN clauses evaluate FALSE
        downstream — that semantics lives in the classifier, not here)
  D4.4  F&G stamped day D 00:00 becomes available from the D 04:00 bar onward
  D4.5  funding: Binance REST stamps align to 00/08/16 UTC bar opens; bars
        whose open_time is not a funding stamp carry 0.0

dvol: plain as-of join, staleness cap 24h. band: exact join on bar open_time.

Public interface:
  load_panel(window: str = "full") -> pd.DataFrame   # reads data/ CSVs
  build_panel(bars, funding, oi, ls, dvol, fg, bands,
              window_start, window_end) -> pd.DataFrame
load_panel is a thin wrapper over build_panel so tests can drive tiny
hand-constructed frames through the exact same assembly code.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# bar-open windows, inclusive on both ends (PR-1)
WINDOWS: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {
    # bybit OI/LS start -> last complete 4h bar at export time
    "full": (pd.Timestamp("2025-04-03 00:00"), pd.Timestamp("2026-06-09 20:00")),
    # DVOL start -> CoinGlass freeze (all bars opening on 2026-05-18 included)
    "deep": (pd.Timestamp("2021-03-24 00:00"), pd.Timestamp("2026-05-18 20:00")),
}

STALENESS_OI_LS = pd.Timedelta(hours=36)   # D4.2 snapshot-jitter tolerance
STALENESS_DVOL = pd.Timedelta(hours=24)
FG_AVAILABILITY_LAG = pd.Timedelta(hours=4)  # D4.4: day-D value live at D 04:00
_DAY = pd.Timedelta(hours=24)

COLUMNS = ["open", "high", "low", "close", "volume",
           "funding_rate", "oi", "ls_ratio", "dvol", "fg", "band"]


def _ts_series(df: pd.DataFrame, ts_col: str, val_col: str,
               numeric: bool = True) -> pd.Series:
    """Frame -> Series indexed by parsed timestamps, sorted, deduped."""
    s = pd.Series(
        df[val_col].to_numpy(),
        index=pd.DatetimeIndex(pd.to_datetime(df[ts_col])),
        name=val_col,
    )
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if numeric:
        s = s.astype(float)
    return s


def _asof(idx: pd.DatetimeIndex, s: pd.Series,
          staleness: pd.Timedelta | None) -> pd.Series:
    """Backward as-of join: last value stamped <= each idx entry.

    Entries whose matched stamp is more than `staleness` before the bar open
    (strictly older — exactly-at-cap is still fresh) become NaN.
    """
    if s.empty:
        return pd.Series(np.nan, index=idx)
    pos = s.index.searchsorted(idx, side="right") - 1
    safe = np.clip(pos, 0, None)
    vals = s.to_numpy(dtype=float)[safe]
    ok = pos >= 0
    if staleness is not None:
        age = idx.to_numpy() - s.index.to_numpy()[safe]
        ok &= age <= staleness.to_timedelta64()
    return pd.Series(np.where(ok, vals, np.nan), index=idx)


def _daily_snapshots(s: pd.Series) -> pd.Series:
    """D4.2: collapse an observation series to daily 00:00 snapshots.

    Snapshot at midnight M = last observation with ts <= M, valid only if
    that observation falls inside (M - 24h, M]. Days with no observation in
    the trailing 24h get NO snapshot row — holes are not forward-filled, so
    the downstream 36h as-of cap sees true staleness.
    """
    if s.empty:
        return s
    first = s.index[0].normalize()
    if s.index[0] != first:
        first += _DAY
    last = s.index[-1].normalize()
    if s.index[-1] != last:
        last += _DAY
    grid = pd.date_range(first, last, freq="D")
    pos = s.index.searchsorted(grid, side="right") - 1
    safe = np.clip(pos, 0, None)
    obs_ts = s.index.to_numpy()[safe]
    fresh = (pos >= 0) & (obs_ts > (grid - _DAY).to_numpy())
    return pd.Series(s.to_numpy(dtype=float)[safe][fresh], index=grid[fresh])


def build_panel(bars: pd.DataFrame, funding: pd.DataFrame, oi: pd.DataFrame,
                ls: pd.DataFrame, dvol: pd.DataFrame, fg: pd.DataFrame,
                bands: pd.DataFrame, window_start, window_end) -> pd.DataFrame:
    """Assemble the aligned 4h panel from source frames.

    Expected frame schemas (the committed CSV headers):
      bars:    open_time, open, high, low, close, volume
      funding: funding_time_utc, funding_rate   (8h stamps, 00/08/16 UTC)
      oi:      ts, open_interest
      ls:      ts, long_short_ratio
      dvol:    ts, close
      fg:      date_utc, value                  (daily, stamped D 00:00)
      bands:   bar_ts, region_id                (4h bar grid)

    Index: bar open_time (UTC, tz-naive), clipped to
    [window_start, window_end] inclusive. Columns: COLUMNS.
    """
    start, end = pd.Timestamp(window_start), pd.Timestamp(window_end)

    b = bars.copy()
    b["open_time"] = pd.to_datetime(b["open_time"])
    b = b.drop_duplicates(subset="open_time")          # D4.1
    b = b.sort_values("open_time")
    b = b[(b["open_time"] >= start) & (b["open_time"] <= end)]
    panel = b.set_index("open_time")[
        ["open", "high", "low", "close", "volume"]].astype(float)
    idx = panel.index

    # D4.5 funding: exact-stamp join, non-stamp bars 0.0
    f = _ts_series(funding, "funding_time_utc", "funding_rate")
    panel["funding_rate"] = (f.reindex(idx).fillna(0.0)
                             if not f.empty else 0.0)

    # D4.2 OI/LS: daily 00:00 snapshots, then as-of with 36h cap
    panel["oi"] = _asof(
        idx, _daily_snapshots(_ts_series(oi, "ts", "open_interest")),
        STALENESS_OI_LS)
    panel["ls_ratio"] = _asof(
        idx, _daily_snapshots(_ts_series(ls, "ts", "long_short_ratio")),
        STALENESS_OI_LS)

    # dvol: as-of at native cadence, 24h cap
    panel["dvol"] = _asof(idx, _ts_series(dvol, "ts", "close"),
                          STALENESS_DVOL)

    # D4.4 F&G: day-D value effective from D 04:00; no cap (daily-complete)
    g = _ts_series(fg, "date_utc", "value")
    if not g.empty:
        g.index = g.index + FG_AVAILABILITY_LAG
    panel["fg"] = _asof(idx, g, None)

    # band: exact join on the 4h bar stamp (rm17 labels live on the grid)
    bd = _ts_series(bands, "bar_ts", "region_id", numeric=False)
    panel["band"] = bd.reindex(idx) if not bd.empty else np.nan

    return panel[COLUMNS]


def load_panel(window: str = "full") -> pd.DataFrame:
    """Read the committed CSVs and assemble the panel for a window.

    window: "full" (full-stack, sweep/gate domain) or "deep" (deep-history,
    robustness replay only — oi/ls_ratio/band are all-NaN there because those
    sources start 2025-04-03 / 2025-10-04, which is correct behavior).
    """
    if window not in WINDOWS:
        raise ValueError(
            f"unknown window {window!r}; expected one of {sorted(WINDOWS)}")
    start, end = WINDOWS[window]
    lab_dir = DATA_DIR / "lab"
    backfill_dir = DATA_DIR / "backfill"
    return build_panel(
        bars=pd.read_csv(lab_dir / "bars_4h.csv"),
        funding=pd.read_csv(backfill_dir / "funding_btcusdt_binance.csv"),
        oi=pd.read_csv(lab_dir / "oi_bybit.csv"),
        ls=pd.read_csv(lab_dir / "ls_bybit.csv"),
        dvol=pd.read_csv(lab_dir / "dvol.csv"),
        fg=pd.read_csv(backfill_dir / "fear_greed.csv"),
        bands=pd.read_csv(lab_dir / "bands_rm17.csv"),
        window_start=start,
        window_end=end,
    )
