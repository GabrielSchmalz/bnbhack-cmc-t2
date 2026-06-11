"""W-panel assembly + fold geometry (widening pre-registration §1, §2).

Registered spec: docs/plans/2026-06-10-widening-preregistration.md.

Panels (§1, ADR-002 gating domains):
  P-BTC  data/lab/bars_4h.csv      2020-04-01 00:00 -> 2026-06-09 20:00
  P-ETH  data/lab/bars_4h_eth.csv  2020-04-01 00:00 -> 2026-06-09 20:00
  P-SOL  data/lab/bars_4h_sol.csv  2020-10-01 00:00 -> 2026-06-09 20:00

Assembly (§2 R-SRC, one source per Feature; frozen code paths REUSED,
never duplicated):
  - per-asset funding (data/backfill/funding_{btc,eth,sol}usdt_binance.csv)
    is stamped onto the 4h grid by lab.dataset.build_panel (D4.5
    exact-stamp join) and ffilled into ``funding_rate_8h`` by
    lab.features.add_features — the frozen convention end-to-end;
  - fg (data/backfill/fear_greed.csv) rides the same build_panel call:
    frozen D4.4 availability (day-D value live from the D 04:00 bar, no
    staleness cap);
  - ``oi_chg_24h_daily`` comes from the registered lab.oi_cg loader on
    P-BTC ONLY (the §2 source is the Binance-BTCUSDT subset); P-ETH and
    P-SOL panels OMIT the column;
  - lab.features.add_features + lab.features_w.add_features_w run on the
    warmup-EXTENDED frame, and only then is the panel trimmed to its
    registered span: rows earlier than the span start feed Feature
    construction (SMA200/RSI warmup, OI delta baseline) and are never
    train or OOS rows (§1 span-start rule). No panel has 200 daily closes
    before its start, so early-panel bars are sma-na on every panel.

Fold geometry (§1, PR-6 mechanics unchanged): expanding train = every
grid bar strictly before each quarterly calendar-UTC boundary; OOS =
[boundary + E bars .. next boundary) counted on the index grid; the final
fold's OOS runs to the panel end. Boundary lists are registered
constants — P-BTC/P-ETH 2021-04-01 .. 2026-04-01 (21 folds, F01..F21),
P-SOL 2021-10-01 .. 2026-04-01 (19 folds) — with test-pinned counts.

Embargo (§1, pinned; §13 amendment 27): E per (panel, taxonomy) =
max(42, ceil(median NON-``na`` regime-episode length in bars)), the
median computed on the panel's FIRST fold's train slice labeled with that
fold's train-derived cuts (lab.classifiers_w). ``na`` episodes (the
taxonomy's NA_LABEL_W label) are missing-feature placeholders, not regime
episodes — they are excluded from the median, consistent with honest-N's
regime-episode unit and the null's ``na``-freeze; if the slice holds no
non-``na`` episodes the 42-bar floor binds (pre-repair, T-F's 100%-fg-na
first-fold train formed ONE 2,190-bar episode and E = 2,190 structurally
voided every T-F OOS slice). compute_embargo is the formula ONLY — the
once-pre-OOS-contact computation run per (panel, taxonomy), and the
artifact print of every E, live in the sweep driver (lab/sweep_w.py). The
42-bar floor is expected to bind; any (panel, taxonomy) where it does not
is an R3 disclosure, not a special case here.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lab.classifier import episodes
from lab.classifiers_w import NA_LABEL_W, derive_thresholds_w, label_w
from lab.dataset import DATA_DIR, build_panel
from lab.features import add_features
from lab.features_w import add_features_w
from lab.oi_cg import join_to_bars, load_oi_cg_daily, oi_chg_24h_daily
from lab.walkforward import EMBARGO_FLOOR_BARS, Fold, _at

# Canonical asset order == §7 RNG panel_index map (P-BTC=0, P-ETH=1, P-SOL=2).
ASSETS_W = ("BTC", "ETH", "SOL")

SPAN_END_W = pd.Timestamp("2026-06-09 20:00")

# §1 panel spans (4h-grid bar opens, inclusive on both ends). P-ETH is
# aligned to P-BTC's start for cross-panel fold comparability (registered
# choice; its sources are live from 2019-11).
W_SPANS: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {
    "BTC": (pd.Timestamp("2020-04-01 00:00"), SPAN_END_W),
    "ETH": (pd.Timestamp("2020-04-01 00:00"), SPAN_END_W),
    "SOL": (pd.Timestamp("2020-10-01 00:00"), SPAN_END_W),
}


def _quarterly(first: str, last: str) -> list[pd.Timestamp]:
    """Inclusive quarterly calendar-UTC boundaries (Jan/Apr/Jul/Oct 1)."""
    return list(pd.date_range(first, last, freq="QS"))


# §1 registered boundary lists (test-pinned: 21 / 21 / 19 folds).
W_BOUNDARIES: dict[str, list[pd.Timestamp]] = {
    "BTC": _quarterly("2021-04-01", "2026-04-01"),
    "ETH": _quarterly("2021-04-01", "2026-04-01"),
    "SOL": _quarterly("2021-10-01", "2026-04-01"),
}

_BARS_CSV = {
    "BTC": "bars_4h.csv",
    "ETH": "bars_4h_eth.csv",
    "SOL": "bars_4h_sol.csv",
}
_FUNDING_CSV = {
    "BTC": "funding_btcusdt_binance.csv",
    "ETH": "funding_ethusdt_binance.csv",
    "SOL": "funding_solusdt_binance.csv",
}
OI_CG_CSV = DATA_DIR / "lab" / "oi_cg_daily_btc.csv"

# Final W-panel column order: bars + raw funding stamps (engine accrual) +
# the registered §2/§3 Feature set. Non-BTC panels omit oi_chg_24h_daily.
W_PANEL_COLUMNS = [
    "open", "high", "low", "close", "volume", "funding_rate",
    "funding_rate_8h", "oi_chg_24h_daily", "fg", "rsi14_1d",
    "close_vs_sma200_1d", "pc_24h",
]


def _empty_source(cols: list[str]) -> pd.DataFrame:
    """Empty source frame in a dataset.build_panel schema (no such source
    exists for W panels; the frozen join path then yields all-NaN)."""
    return pd.DataFrame({c: pd.Series(dtype=object) for c in cols})


def build_w_panel(bars: pd.DataFrame, funding: pd.DataFrame,
                  fg: pd.DataFrame, span_start, span_end,
                  oi_cg_daily: pd.Series | None = None) -> pd.DataFrame:
    """Assemble one W panel from source frames (frozen code paths reused).

    bars / funding / fg follow the committed CSV schemas consumed by
    lab.dataset.build_panel. oi_cg_daily is the deduped daily snapshot
    Series from lab.oi_cg.load_oi_cg_daily (P-BTC), or None to omit the
    column (P-ETH / P-SOL). EVERY bar row handed in before span_end
    participates in Feature construction (warmup); the returned frame is
    then trimmed to [span_start, span_end] inclusive (§1).
    """
    start, end = pd.Timestamp(span_start), pd.Timestamp(span_end)
    # no warmup clipping: every committed bar row up to the span end feeds
    # feature construction (§1 — warmup is trimmed only AFTER features)
    warmup_start = pd.to_datetime(bars["open_time"]).min()
    panel = build_panel(
        bars=bars,
        funding=funding,
        oi=_empty_source(["ts", "open_interest"]),
        ls=_empty_source(["ts", "long_short_ratio"]),
        dvol=_empty_source(["ts", "close"]),
        fg=fg,
        bands=_empty_source(["bar_ts", "region_id"]),
        window_start=warmup_start,
        window_end=end,
    )
    if oi_cg_daily is not None:
        panel["oi_chg_24h_daily"] = join_to_bars(
            oi_chg_24h_daily(oi_cg_daily), panel.index)
    out = add_features_w(add_features(panel))
    out = out[(out.index >= start) & (out.index <= end)]
    cols = [c for c in W_PANEL_COLUMNS
            if c != "oi_chg_24h_daily" or oi_cg_daily is not None]
    return out[cols]


def load_w_panel(asset: str) -> pd.DataFrame:
    """Read the committed CSVs and assemble the registered panel for an
    asset ('BTC' | 'ETH' | 'SOL'). Thin wrapper over build_w_panel so tests
    can drive hand-constructed frames through the same assembly code."""
    if asset not in W_SPANS:
        raise ValueError(
            f"unknown W asset {asset!r}; expected one of {list(ASSETS_W)}")
    start, end = W_SPANS[asset]
    lab_dir = DATA_DIR / "lab"
    backfill_dir = DATA_DIR / "backfill"
    return build_w_panel(
        bars=pd.read_csv(lab_dir / _BARS_CSV[asset]),
        funding=pd.read_csv(backfill_dir / _FUNDING_CSV[asset]),
        fg=pd.read_csv(backfill_dir / "fear_greed.csv"),
        span_start=start,
        span_end=end,
        oi_cg_daily=load_oi_cg_daily(OI_CG_CSV) if asset == "BTC" else None,
    )


def w_folds(panel_index: pd.DatetimeIndex,
            boundaries: list[pd.Timestamp],
            embargo_bars: int) -> list[Fold]:
    """§1 expanding folds over a panel's bar-grid index.

    Train = every grid bar strictly before the boundary; OOS =
    [boundary + embargo_bars .. next boundary) counted on the grid; the
    final fold's OOS runs to the panel end. Fold names F01..Fnn in
    boundary order (the §7 fold_ordinal is the panel-local 1-based index).
    """
    if not panel_index.is_monotonic_increasing:
        raise ValueError("panel_index must be sorted ascending")
    if embargo_bars < 0:
        raise ValueError("embargo_bars must be >= 0")
    positions = [
        panel_index.searchsorted(_at(pd.Timestamp(b), panel_index), side="left")
        for b in boundaries
    ]
    out: list[Fold] = []
    for i, b_pos in enumerate(positions):
        oos_stop = positions[i + 1] if i + 1 < len(positions) else len(panel_index)
        out.append(Fold(
            train_idx=panel_index[:b_pos],
            oos_idx=panel_index[b_pos + embargo_bars: oos_stop],
            name=f"F{i + 1:02d}",
        ))
    return out


def compute_embargo(panel: pd.DataFrame, taxonomy: str,
                    boundaries: list[pd.Timestamp]) -> int:
    """§1 pinned embargo formula (§13 amendment 27):
    E = max(42, ceil(median NON-na episode bars)).

    The median regime-episode length is computed on the FIRST fold's train
    slice — every panel row strictly before boundaries[0] (pass the
    panel's registered W_BOUNDARIES list) — labeled by lab.classifiers_w
    with that slice's own train-derived cuts (train-only by construction,
    R1), over non-``na`` episodes ONLY: episodes carrying the taxonomy's
    NA_LABEL_W label are missing-feature placeholders, not regime
    episodes, and are dropped before the median (amendment 27). If no
    non-``na`` episode exists (e.g. a coverage-floored axis collapsing the
    slice to one ``na`` episode), the 42-bar floor binds. Floor/ceil
    mechanics mirror the frozen lab.walkforward.embargo_bars (max(42,
    math.ceil(np.median(n_bars)))). Function only: the sweep driver runs
    this once per (panel, taxonomy) pre-OOS-contact and prints every E in
    the artifact.
    """
    first_boundary = _at(pd.Timestamp(boundaries[0]), panel.index)
    b_pos = panel.index.searchsorted(first_boundary, side="left")
    train = panel.iloc[:b_pos]
    cuts = derive_thresholds_w(train, taxonomy)
    labels = label_w(train, taxonomy, cuts)
    eps = episodes(labels)
    na_label = NA_LABEL_W[taxonomy]
    if not eps.empty and na_label is not None:
        eps = eps[eps["label"] != na_label]
    if eps.empty:
        return EMBARGO_FLOOR_BARS
    median = float(np.median(eps["n_bars"].to_numpy()))
    return max(EMBARGO_FLOOR_BARS, math.ceil(median))
