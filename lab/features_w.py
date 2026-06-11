"""W-sweep Feature columns + vol-band cut helper (widening registration).

docs/plans/2026-06-10-widening-preregistration.md §2 (Feature table) and
§3 (vol-band overlay input). Both Features are computed from panel bars and
are point-in-time live-computable from Gate-0-verified CMC fields:
  close_vs_sma200_1d  daily closes, SMA-200 (min_periods=200), causal
                      D-1 -> D 00:00 availability join — the SAME mechanics
                      as the frozen SMA30 Feature (lab/features.py;
                      _daily_to_bars is imported, never duplicated). Value
                      is daily_close − SMA200 (sign basis, the frozen
                      convention; §4 T-G: above ⇔ close_vs_sma200_1d > 0).
                      Live analog F5: simple_moving_average_200_day +
                      quotes price. The D2 supersession note (§2) scopes
                      this Feature to W-panels only.
  pc_24h              close / close(6 bars back) − 1 (6 bars = 24h on the
                      4h grid); NaN on the first six bars. Live analog F6:
                      percent_change_24h.

add_features_w(panel) returns a copy of the panel with exactly those two
columns added; it composes with the frozen add_features and touches none
of its columns.

q_hi_abs(series_train, q) is the pure vol-band cut helper for §3's
q80(|pc_24h|, fold-train): the q-quantile of the series' absolute values,
NaNs excluded (pandas quantile semantics), returned as a plain float. R1:
the CALLER passes train rows exclusively — this helper quantiles exactly
the series it is handed and nothing else.
"""

from __future__ import annotations

import pandas as pd

from lab.features import _daily_to_bars

SMA200_WINDOW = 200
PC_24H_BARS = 6       # 24h / 4h bars
VOL_BAND_Q = 0.8      # §3: q80(|pc_24h|, fold-train)

FEATURE_COLUMNS_W = ["close_vs_sma200_1d", "pc_24h"]


def add_features_w(panel: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the panel with the W-sweep Feature columns added."""
    out = panel.copy()
    idx = out.index

    # F5 (W): daily UTC closes -> close − SMA200 (min_periods=200), then the
    # frozen causal D-1 -> D 00:00 availability join back onto the bar grid
    daily_close = out["close"].resample("1D").last().dropna()
    sma = daily_close.rolling(SMA200_WINDOW, min_periods=SMA200_WINDOW).mean()
    out["close_vs_sma200_1d"] = _daily_to_bars(daily_close - sma, idx)

    # F6 (W): 24h percent change from panel bars; NaN on the first six bars
    out["pc_24h"] = out["close"] / out["close"].shift(PC_24H_BARS) - 1.0
    return out


def q_hi_abs(series_train: pd.Series, q: float = VOL_BAND_Q) -> float:
    """Train-only |series| quantile cut (R1) for the §3 vol-band overlay.

    The quantile is computed over the rows of series_train and nothing
    else — the caller is responsible for passing exactly the fold-train
    slice. NaNs are excluded (pandas quantile semantics); returns a plain
    float — this is a number that freezes (G7).
    """
    return float(series_train.abs().quantile(q))
