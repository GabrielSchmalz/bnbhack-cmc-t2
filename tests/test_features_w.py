"""W-sweep tests — lab/features_w.py (widening registration §2 + §3).

All tests drive add_features_w / q_hi_abs with small hand-constructed
frames and hand-computed expectations. The committed data/ CSVs are NEVER
read here.

Pinned behavior (docs/plans/2026-06-10-widening-preregistration.md §2, §3):
  - close_vs_sma200_1d: daily-close series, SMA-200 (min_periods=200), value
    is daily_close - SMA200 (sign basis, same convention as the frozen
    SMA30 Feature); a value computed from days up to and including D-1
    becomes available to bars from D 00:00 onward (the D-1 close IS the
    D 00:00 boundary) — peeking at day D's own close is engineered to FLIP
    the value, so a leak fails loudly; NaN until 200 daily closes exist
  - pc_24h: close / close.shift(6) - 1 (exactly 6 bars = 24h on the 4h
    grid); first six bars NaN
  - q_hi_abs: pure quantile of |series| over EXACTLY the series handed in
    (R1: callers pass fold-train rows only), NaNs excluded, plain float,
    default q = 0.8 — the registered q80(|pc_24h|, fold-train) vol-band cut
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.features_w import add_features_w, q_hi_abs  # noqa: E402


# ---------------------------------------------------------------- helpers

def make_panel(n: int = 6, *, start: str = "2025-05-01 00:00",
               closes=None, funding=None, oi=None, fg=None) -> pd.DataFrame:
    """Minimal panel-shaped frame on a 4h grid (dataset.load_panel schema)."""
    idx = pd.date_range(start, periods=n, freq="4h")
    closes = list(closes) if closes is not None else [100.0 + i for i in range(n)]
    df = pd.DataFrame({
        "open": closes,
        "high": [c + 1.0 for c in closes],
        "low": [c - 1.0 for c in closes],
        "close": closes,
        "volume": 1.0,
        "funding_rate": funding if funding is not None else 0.0,
        "oi": oi if oi is not None else 100.0,
        "ls_ratio": 1.0,
        "dvol": 50.0,
        "fg": fg if fg is not None else 50.0,
        "band": np.nan,
    }, index=idx)
    df.index.name = "open_time"
    return df


def daily_panel(daily_closes, *, start: str = "2025-01-01 00:00",
                extra_bar_closes=None) -> pd.DataFrame:
    """Panel where every bar of day d closes at daily_closes[d] (6 bars/day);
    extra_bar_closes appends bars of the following day starting at 00:00."""
    closes = list(np.repeat([float(c) for c in daily_closes], 6))
    if extra_bar_closes is not None:
        closes += [float(c) for c in extra_bar_closes]
    return make_panel(len(closes), start=start, closes=closes)


# ------------------------------------------ add_features_w general contract

def test_add_features_w_returns_copy_and_preserves_originals():
    panel = make_panel(8)
    snapshot = panel.copy(deep=True)
    out = add_features_w(panel)
    pd.testing.assert_frame_equal(panel, snapshot)      # input not mutated
    assert out is not panel
    for col in snapshot.columns:                        # originals untouched
        pd.testing.assert_series_equal(out[col], snapshot[col])
    for col in ["close_vs_sma200_1d", "pc_24h"]:
        assert col in out.columns


# ------------------------------------------------------------------ pc_24h

def test_pc_24h_uses_exactly_six_bars_back():
    closes = [100.0 + i * i for i in range(10)]  # nonlinear: shift(5/7) differ
    panel = make_panel(10, closes=closes)
    panel["open"] = 999.0    # pc_24h must come from close, never open
    out = add_features_w(panel)
    assert out["pc_24h"].iloc[:6].isna().all()
    assert out["pc_24h"].iloc[6] == pytest.approx(136.0 / 100.0 - 1.0)
    assert out["pc_24h"].iloc[9] == pytest.approx(181.0 / 109.0 - 1.0)
    # a 5-bar (20h) shift would have produced a different number at iloc[6]
    assert out["pc_24h"].iloc[6] != pytest.approx(136.0 / 101.0 - 1.0)


def test_pc_24h_hand_computed_on_flat_then_jump():
    # 7 bars: six at 100, seventh at 110 -> pc_24h = 110/100 - 1 = +0.10
    panel = make_panel(7, closes=[100.0] * 6 + [110.0])
    out = add_features_w(panel)
    assert out["pc_24h"].iloc[:6].isna().all()
    assert out["pc_24h"].iloc[6] == pytest.approx(0.10)


# ------------------------------------------------------ close_vs_sma200_1d

def test_close_vs_sma200_nan_until_200_daily_closes():
    daily = [100.0 + d for d in range(200)] + [10.0]
    panel = daily_panel(daily, extra_bar_closes=[10.0])
    out = add_features_w(panel)
    day = out.index.normalize()
    d0 = out.index[0].normalize()
    # first defined value is "through day 199" (closes 0..199, exactly 200
    # of them, min_periods=200), available on day-200 bars
    assert out.loc[day <= d0 + pd.Timedelta(days=199),
                   "close_vs_sma200_1d"].isna().all()
    assert out.loc[day >= d0 + pd.Timedelta(days=200),
                   "close_vs_sma200_1d"].notna().all()


def test_close_vs_sma200_never_peeks_at_same_day_close():
    # days 0..199 close 100..299 (steady uptrend), then day 200 crashes to 10.
    # Through day 199: close_vs_sma200 = 299 - mean(100..299) = +99.5
    # Including day 200 (the PEEK):
    #   close_vs_sma200 = 10 - (sum(101..299) + 10)/200
    #                   = 10 - 39810/200 = 10 - 199.05 = -189.05
    # The value flips violently, so any same-day leak fails the sign assert.
    daily = [100.0 + d for d in range(200)] + [10.0]
    panel = daily_panel(daily, extra_bar_closes=[10.0])  # day-201 00:00 bar
    out = add_features_w(panel)
    day = out.index.normalize()
    d0 = out.index[0].normalize()

    on_d200 = out.loc[day == d0 + pd.Timedelta(days=200)]
    assert len(on_d200) == 6
    assert on_d200["close_vs_sma200_1d"].to_numpy() == pytest.approx(99.5)
    assert (on_d200["close_vs_sma200_1d"] > 0).all()     # peek would be < 0

    # the D-1 close IS the D 00:00 boundary: at day-201 00:00 the day-200
    # crash close (close-time = day-201 00:00) is exactly usable
    at_d201 = out.loc[day == d0 + pd.Timedelta(days=201)]
    assert len(at_d201) == 1
    assert at_d201["close_vs_sma200_1d"].iloc[0] == pytest.approx(-189.05)


# ---------------------------------------------------------------- q_hi_abs

TRAIN_PC = [-0.10, -0.05, 0.00, 0.05, 0.20]
# q80 of |TRAIN_PC| = q80 of sorted [0, 0.05, 0.05, 0.10, 0.20]:
# linear-interpolation pos 3.2 -> 0.10 + 0.2 * (0.20 - 0.10) = 0.12
EXPECTED_TRAIN_CUT = 0.12


def test_q_hi_abs_hand_computed_default_is_registered_q80():
    cut = q_hi_abs(pd.Series(TRAIN_PC))
    assert cut == pytest.approx(EXPECTED_TRAIN_CUT)
    assert type(cut) is float
    # the default IS the registered q80 cut (§3)
    assert cut == q_hi_abs(pd.Series(TRAIN_PC), 0.8)


def test_q_hi_abs_excludes_nans():
    s = pd.Series(TRAIN_PC + [np.nan, np.nan, np.nan])
    assert q_hi_abs(s) == pytest.approx(EXPECTED_TRAIN_CUT)


def test_q_hi_abs_r1_train_slice_ignores_oos_rows():
    # OOS rows are engineered to shift the quantile if they leaked in —
    # proves the cut is over exactly the (train) series the caller passes
    train = pd.Series(TRAIN_PC)
    full = pd.Series(TRAIN_PC + [5.0, -8.0, 9.0])
    assert q_hi_abs(train) == pytest.approx(EXPECTED_TRAIN_CUT)
    assert q_hi_abs(full) != pytest.approx(EXPECTED_TRAIN_CUT)


def test_q_hi_abs_custom_q():
    # q50 of sorted |TRAIN_PC| [0, 0.05, 0.05, 0.10, 0.20] -> 0.05
    assert q_hi_abs(pd.Series(TRAIN_PC), q=0.5) == pytest.approx(0.05)


def test_vol_band_cut_from_add_features_w_output_is_plain_float():
    # end-to-end shape check: add_features_w output slices straight into
    # q_hi_abs (the §3 vol-band cut path)
    closes = [100.0 + ((i * 7) % 13) for i in range(20)]
    panel = make_panel(20, closes=closes)
    cut = q_hi_abs(add_features_w(panel)["pc_24h"])
    assert type(cut) is float
    assert cut >= 0.0
