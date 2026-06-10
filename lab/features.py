"""Canonical Feature columns + train-only threshold derivation (R1).

Plan Task 2.1, amended by FREEZE-ADDENDUM D2 (trend Feature is
close_vs_sma30_1d, W=30 — the TA tool serves only {7, 30, 200}-day SMAs).

Every Feature is Gate-0-frozen (docs/gate0/GATE0-FREEZE.md §7 table):
  funding_rate_8h    F1  docs/gate0/get_global_crypto_derivatives_metrics.json
                         / docs/gate0/get_global_metrics_latest.json (D1)
  oi_chg_24h         F2  docs/gate0/get_global_crypto_derivatives_metrics.json
  fg                 F3  docs/gate0/get_global_metrics_latest.json
  rsi14_1d           F4  docs/gate0/get_crypto_technical_analysis.json
  close_vs_sma30_1d  F5  docs/gate0/get_crypto_technical_analysis.json (D2)

add_features(panel) adds the canonical columns and leaves the originals:
  - funding_rate_8h: last-known 8h rate forward-filled onto every bar from
    the stamp-only ``funding_rate`` column (stamps = 00/08/16 UTC bar opens;
    filler 0.0 on non-stamp bars is ignored, a TRUE 0.0 rate at a stamp is
    carried). ffill only, no staleness cap — funding is dense; never
    backfilled, so bars before the first stamp are NaN.
  - oi_chg_24h: oi / oi.shift(6) - 1 (6 bars = 24h on the 4h grid). The
    panel's oi is the D4.2 daily snapshot, so this is day-over-day change;
    NaN propagates through holes.
  - fg: passthrough (already a panel column).
  - rsi14_1d / close_vs_sma30_1d: bars resampled to 1d UTC closes (the close
    of day D's last bar; with full data that bar closes exactly at D+1
    00:00). RSI(14, Wilder smoothing) and daily_close − SMA30 (sign basis;
    column value is the float difference). CAUSALITY: a daily value computed
    from days up to and including D−1 becomes available to bars from D 00:00
    onward — the D−1 close IS the D 00:00 boundary; at any bar t only daily
    closes with close-time <= t contribute (pinned by a peek-flips-the-value
    test).

derive_thresholds(df_train, q=(0.2, 0.8)) maps the train slice — and ONLY
the frame it is handed (R1: callers pass fold-train rows exclusively) — to
the absolute threshold dict consumed by lab/classifier.py:
  funding_hi = q_hi(funding_rate_8h)      funding_lo = q_lo(funding_rate_8h)
  funding_hi_abs = q_hi(|funding_rate_8h|)
  oi_surge = q_hi(|oi_chg_24h|)
  fg_lo = q_lo(fg)                        fg_hi = q_hi(fg)
NaNs are excluded; values are plain Python floats — these are the numbers
that freeze (G7).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RSI_PERIOD = 14
SMA_WINDOW = 30
OI_CHG_BARS = 6           # 24h / 4h bars
FUNDING_STAMP_HOURS = 8   # Binance funding stamps: 00/08/16 UTC

FEATURE_COLUMNS = [
    "funding_rate_8h", "oi_chg_24h", "fg", "rsi14_1d", "close_vs_sma30_1d",
]


def _wilder_rsi(closes: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """RSI with Wilder smoothing on a (daily) close series.

    Seed at index `period`: simple mean of the first `period` gains/losses;
    then avg = (prev_avg * (period-1) + current) / period. RSI is computed
    as 100 * avg_gain / (avg_gain + avg_loss) (identical to the 100−100/(1+RS)
    form, well-defined when avg_loss == 0); a fully flat seed window (both
    averages 0) maps to neutral 50.0. NaN before `period` changes exist.
    """
    vals = closes.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    if len(vals) <= period:
        return pd.Series(out, index=closes.index)
    delta = np.diff(vals)
    gains = np.clip(delta, 0.0, None)
    losses = np.clip(-delta, 0.0, None)

    def rsi(avg_gain: float, avg_loss: float) -> float:
        denom = avg_gain + avg_loss
        if denom == 0.0:
            return 50.0
        return 100.0 * avg_gain / denom

    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    out[period] = rsi(avg_gain, avg_loss)
    for i in range(period + 1, len(vals)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = rsi(avg_gain, avg_loss)
    return pd.Series(out, index=closes.index)


def _daily_to_bars(daily: pd.Series, bar_index: pd.DatetimeIndex) -> pd.Series:
    """Causal as-of join of a daily-indexed value series onto the bar grid.

    The value indexed at day D was computed from daily closes through D, the
    last of which has close-time at most D+1 00:00 — so it becomes available
    at D+1 00:00 sharp. Each bar takes the last value whose availability
    stamp is <= its open_time; earlier bars get NaN (no backfill).
    """
    if daily.empty:
        return pd.Series(np.nan, index=bar_index)
    avail = pd.DatetimeIndex(daily.index) + pd.Timedelta(days=1)
    pos = avail.searchsorted(bar_index, side="right") - 1
    safe = np.clip(pos, 0, None)
    vals = daily.to_numpy(dtype=float)[safe]
    return pd.Series(np.where(pos >= 0, vals, np.nan), index=bar_index)


def add_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the panel with the canonical Feature columns added."""
    out = panel.copy()
    idx = out.index

    # F1: stamp-only rates (00/08/16 UTC bar opens) ffilled; filler zeros on
    # non-stamp bars are masked out so a true 0.0 stamp still overrides
    is_stamp = (idx.hour % FUNDING_STAMP_HOURS == 0) & (idx.minute == 0)
    out["funding_rate_8h"] = out["funding_rate"].where(is_stamp).ffill()

    # F2: day-over-day change of the D4.2 daily snapshot; NaN through holes
    out["oi_chg_24h"] = out["oi"] / out["oi"].shift(OI_CHG_BARS) - 1.0

    # F3 fg: passthrough — already a panel column.

    # F4/F5: daily UTC closes -> RSI(14, Wilder) and close − SMA30, then a
    # causal D-1 -> D 00:00 availability join back onto the bar grid
    daily_close = out["close"].resample("1D").last().dropna()
    rsi_daily = _wilder_rsi(daily_close)
    sma = daily_close.rolling(SMA_WINDOW, min_periods=SMA_WINDOW).mean()
    out["rsi14_1d"] = _daily_to_bars(rsi_daily, idx)
    out["close_vs_sma30_1d"] = _daily_to_bars(daily_close - sma, idx)
    return out


def derive_thresholds(df_train: pd.DataFrame,
                      q: tuple[float, float] = (0.2, 0.8)) -> dict[str, float]:
    """Train-only absolute thresholds (R1) for lab/classifier.py.

    Quantiles are computed over the rows of df_train and nothing else — the
    caller is responsible for passing exactly the fold-train slice. NaNs are
    excluded (pandas quantile semantics); returns plain floats.
    """
    q_lo, q_hi = q
    funding = df_train["funding_rate_8h"]
    oi_chg = df_train["oi_chg_24h"]
    fg = df_train["fg"]
    return {
        "funding_hi": float(funding.quantile(q_hi)),
        "funding_lo": float(funding.quantile(q_lo)),
        "funding_hi_abs": float(funding.abs().quantile(q_hi)),
        "oi_surge": float(oi_chg.abs().quantile(q_hi)),
        "fg_lo": float(fg.quantile(q_lo)),
        "fg_hi": float(fg.quantile(q_hi)),
    }
