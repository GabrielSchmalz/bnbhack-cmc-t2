"""Task 2.1 tests — lab/features.py canonical Features + R1 thresholds.

All tests drive add_features / derive_thresholds with small hand-constructed
frames and hand-computed expectations. The committed data/ CSVs are NEVER
read here.

Pinned behavior (plan Task 2.1, amended by FREEZE-ADDENDUM D2):
  - funding_rate_8h: last-known 8h-stamp rate ffilled onto every bar; stamp
    bars are 00/08/16 UTC; a TRUE 0.0 rate at a stamp overrides; NaN before
    the first stamp (never backfilled)
  - oi_chg_24h: oi / oi.shift(6) - 1 (exactly 6 bars = 24h); NaN propagates
    through holes
  - fg: passthrough
  - rsi14_1d / close_vs_sma30_1d: daily-close series; value computed from
    days up to and including D-1 becomes available to bars from D 00:00
    onward (the D-1 close IS the D 00:00 boundary) — peeking at day D's own
    close is engineered to FLIP the value, so a leak fails loudly
  - derive_thresholds: train-frame-only quantiles (R1), NaNs excluded,
    plain floats, canonical keys matching lab/classifier.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package and pytest
# only inserts tests/ (rootdir-wide fix belongs in shared config, not here)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.features import add_features, derive_thresholds

THRESHOLD_KEYS = {
    "funding_hi", "funding_lo", "funding_hi_abs", "oi_surge", "fg_lo", "fg_hi",
}


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


# -------------------------------------------- add_features general contract

def test_add_features_returns_copy_and_preserves_originals():
    panel = make_panel(8)
    snapshot = panel.copy(deep=True)
    out = add_features(panel)
    pd.testing.assert_frame_equal(panel, snapshot)      # input not mutated
    assert out is not panel
    for col in snapshot.columns:                        # originals untouched
        pd.testing.assert_series_equal(out[col], snapshot[col])
    for col in ["funding_rate_8h", "oi_chg_24h", "fg",
                "rsi14_1d", "close_vs_sma30_1d"]:
        assert col in out.columns


def test_fg_passthrough():
    panel = make_panel(6, fg=[10.0, 20.0, 30.0, 40.0, np.nan, 60.0])
    out = add_features(panel)
    pd.testing.assert_series_equal(out["fg"], panel["fg"])


# --------------------------------------------------------- funding_rate_8h

def test_funding_rate_8h_ffill_from_stamps():
    # grid 00,04,08,12,16,20 — dataset puts the rate on stamp bars, 0.0 filler
    panel = make_panel(6, funding=[0.0001, 0.0, 0.0002, 0.0, -0.0003, 0.0])
    out = add_features(panel)
    assert out["funding_rate_8h"].tolist() == pytest.approx(
        [0.0001, 0.0001, 0.0002, 0.0002, -0.0003, -0.0003])


def test_funding_rate_8h_true_zero_at_stamp_overrides():
    # 00:00 stamp +5e-4, 08:00 stamp TRUE 0.0 — a value-based (nonzero) fill
    # would wrongly carry 5e-4 past 08:00
    panel = make_panel(4, funding=[0.0005, 0.0, 0.0, 0.0])
    out = add_features(panel)
    assert out["funding_rate_8h"].tolist() == pytest.approx(
        [0.0005, 0.0005, 0.0, 0.0])


def test_funding_rate_8h_nan_before_first_stamp_never_backfilled():
    # grid starts 04:00 (not a stamp); first stamp is 08:00
    panel = make_panel(3, start="2025-05-01 04:00",
                       funding=[0.0, 0.0002, 0.0])
    out = add_features(panel)
    assert np.isnan(out["funding_rate_8h"].iloc[0])
    assert out["funding_rate_8h"].iloc[1:].tolist() == pytest.approx(
        [0.0002, 0.0002])


# -------------------------------------------------------------- oi_chg_24h

def test_oi_chg_24h_uses_exactly_six_bars_back():
    oi = [100.0 + i * i for i in range(10)]  # nonlinear: shift(5/7) differ
    panel = make_panel(10, oi=oi)
    out = add_features(panel)
    assert out["oi_chg_24h"].iloc[:6].isna().all()
    assert out["oi_chg_24h"].iloc[6] == pytest.approx(136.0 / 100.0 - 1.0)
    assert out["oi_chg_24h"].iloc[9] == pytest.approx(181.0 / 109.0 - 1.0)
    # a 5-bar (20h) shift would have produced a different number at iloc[6]
    assert out["oi_chg_24h"].iloc[6] != pytest.approx(136.0 / 101.0 - 1.0)


def test_oi_chg_24h_nan_propagates_through_holes():
    oi = [100.0 + i for i in range(12)]
    oi[3] = np.nan
    panel = make_panel(12, oi=oi)
    out = add_features(panel)
    assert np.isnan(out["oi_chg_24h"].iloc[3])   # NaN numerator
    assert np.isnan(out["oi_chg_24h"].iloc[9])   # NaN denominator (3 + 6)
    assert out["oi_chg_24h"].iloc[8] == pytest.approx(108.0 / 102.0 - 1.0)
    assert out["oi_chg_24h"].iloc[10] == pytest.approx(110.0 / 104.0 - 1.0)


# ---------------------------------------------------- rsi14_1d (Wilder)

def test_rsi14_hand_computed_wilder_smoothing():
    # day closes: 100, then 14 alternating +1/-1 changes, then one more gain.
    # seed (day 14): avg_gain = avg_loss = 7/14 = 0.5          -> RSI = 50
    # day 15 (gain 1): avg_gain = (0.5*13 + 1)/14 = 7.5/14
    #                  avg_loss = (0.5*13 + 0)/14 = 6.5/14
    #                  RSI = 100 * 7.5/(7.5 + 6.5) = 53.571428...
    daily = [100.0]
    for i in range(14):
        daily.append(daily[-1] + (1.0 if i % 2 == 0 else -1.0))
    daily.append(daily[-1] + 1.0)  # day 15
    panel = daily_panel(daily, extra_bar_closes=[daily[-1]])  # day-16 00:00 bar
    out = add_features(panel)
    day = out.index.normalize()
    d0 = out.index[0].normalize()
    # value through D-1: needs 15 closes (14 changes) -> first defined value
    # is "through day 14", available on day-15 bars
    assert out.loc[day <= d0 + pd.Timedelta(days=14), "rsi14_1d"].isna().all()
    on_d15 = out.loc[day == d0 + pd.Timedelta(days=15), "rsi14_1d"]
    assert len(on_d15) == 6
    assert on_d15.to_numpy() == pytest.approx(50.0)
    on_d16 = out.loc[day == d0 + pd.Timedelta(days=16), "rsi14_1d"]
    assert on_d16.to_numpy() == pytest.approx(100.0 * 7.5 / 14.0)


def test_rsi14_all_gains_is_100():
    daily = [100.0 + d for d in range(16)]              # days 0..15, all gains
    panel = daily_panel(daily, extra_bar_closes=[115.0])  # day-16 00:00 bar
    out = add_features(panel)
    day = out.index.normalize()
    d0 = out.index[0].normalize()
    assert out.loc[day == d0 + pd.Timedelta(days=15),
                   "rsi14_1d"].to_numpy() == pytest.approx(100.0)
    assert out.loc[day == d0 + pd.Timedelta(days=16),
                   "rsi14_1d"].to_numpy() == pytest.approx(100.0)


# ------------------------------- daily causality: peeking FLIPS the value

def test_daily_features_never_peek_at_same_day_close():
    # days 0..29 close 100..129 (steady uptrend), then day 30 crashes to 10.
    # Through day 29:  close_vs_sma30 = 129 - mean(100..129) = +14.5
    #                  rsi14 = 100.0 (all gains)
    # Including day 30 (the PEEK):
    #                  close_vs_sma30 = 10 - (sum(101..129)+10)/30 = -101.5
    #                  rsi14 = 100*(13/14)/((13/14)+(119/14)) = 1300/132 ≈ 9.85
    # Both values flip violently, so any same-day leak fails the sign asserts.
    daily = [100.0 + d for d in range(30)] + [10.0]
    panel = daily_panel(daily, extra_bar_closes=[10.0])  # day-31 00:00 bar
    out = add_features(panel)
    day = out.index.normalize()
    d0 = out.index[0].normalize()

    on_d30 = out.loc[day == d0 + pd.Timedelta(days=30)]
    assert len(on_d30) == 6
    assert on_d30["close_vs_sma30_1d"].to_numpy() == pytest.approx(14.5)
    assert (on_d30["close_vs_sma30_1d"] > 0).all()       # peek would be < 0
    assert on_d30["rsi14_1d"].to_numpy() == pytest.approx(100.0)  # peek ≈ 9.85

    # the D-1 close IS the D 00:00 boundary: at day-31 00:00 the day-30
    # crash close (close-time = day-31 00:00) is exactly usable
    at_d31 = out.loc[day == d0 + pd.Timedelta(days=31)]
    assert len(at_d31) == 1
    assert at_d31["close_vs_sma30_1d"].iloc[0] == pytest.approx(-101.5)
    assert at_d31["rsi14_1d"].iloc[0] == pytest.approx(1300.0 / 132.0)


def test_close_vs_sma30_nan_until_30_daily_closes():
    daily = [100.0 + d for d in range(30)] + [10.0]
    panel = daily_panel(daily, extra_bar_closes=[10.0])
    out = add_features(panel)
    day = out.index.normalize()
    d0 = out.index[0].normalize()
    # first defined value is "through day 29" (closes 0..29), on day-30 bars
    assert out.loc[day <= d0 + pd.Timedelta(days=29),
                   "close_vs_sma30_1d"].isna().all()
    assert out.loc[day >= d0 + pd.Timedelta(days=30),
                   "close_vs_sma30_1d"].notna().all()


# -------------------------------------------------------- derive_thresholds

def feature_frame(funding, oi_chg, fg, start="2025-05-01 00:00") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(funding), freq="4h")
    return pd.DataFrame({
        "funding_rate_8h": funding,
        "oi_chg_24h": oi_chg,
        "fg": fg,
    }, index=idx)


TRAIN_FUNDING = [-0.04, -0.02, 0.00, 0.02, 0.04]
TRAIN_OI_CHG = [-0.10, -0.05, 0.00, 0.05, 0.20]
TRAIN_FG = [10.0, 20.0, 50.0, 80.0, 90.0]

# hand-computed linear-interpolation quantiles of the 5-row train block
EXPECTED_TRAIN_THRESHOLDS = {
    "funding_hi": 0.024,      # q80 of TRAIN_FUNDING: pos 3.2 -> 0.02+0.2*0.02
    "funding_lo": -0.024,     # q20: pos 0.8 -> -0.04+0.8*0.02
    "funding_hi_abs": 0.04,   # q80 of [0,0.02,0.02,0.04,0.04]: 0.04+0.2*0
    "oi_surge": 0.12,         # q80 of [0,0.05,0.05,0.10,0.20]: 0.10+0.2*0.10
    "fg_lo": 18.0,            # q20 of TRAIN_FG: 10+0.8*10
    "fg_hi": 82.0,            # q80: 80+0.2*10
}


def test_derive_thresholds_hand_computed_quantiles_and_plain_floats():
    df = feature_frame(TRAIN_FUNDING, TRAIN_OI_CHG, TRAIN_FG)
    thr = derive_thresholds(df)
    assert set(thr) == THRESHOLD_KEYS
    for key, expected in EXPECTED_TRAIN_THRESHOLDS.items():
        assert thr[key] == pytest.approx(expected), key
        assert type(thr[key]) is float, key


def test_derive_thresholds_r1_train_slice_ignores_oos_rows():
    # OOS rows are engineered to shift EVERY quantile if they leaked in
    oos_funding = [10.0, 20.0, 30.0, -10.0, -20.0]
    oos_oi_chg = [5.0, -5.0, 8.0, -8.0, 9.0]
    oos_fg = [0.0, 0.0, 100.0, 100.0, 100.0]
    train = feature_frame(TRAIN_FUNDING, TRAIN_OI_CHG, TRAIN_FG,
                          start="2025-05-01 00:00")
    oos = feature_frame(oos_funding, oos_oi_chg, oos_fg,
                        start="2025-05-02 00:00")
    df = pd.concat([train, oos])
    cutoff = pd.Timestamp("2025-05-02 00:00")

    thr_train = derive_thresholds(df.loc[df.index < cutoff])
    thr_full = derive_thresholds(df)

    for key, expected in EXPECTED_TRAIN_THRESHOLDS.items():
        assert thr_train[key] == pytest.approx(expected), key
        # every quantile WOULD have shifted — proves the slice was honored
        assert thr_full[key] != pytest.approx(expected), key


def test_derive_thresholds_excludes_nans():
    base = feature_frame(TRAIN_FUNDING, TRAIN_OI_CHG, TRAIN_FG)
    nan_rows = feature_frame([np.nan] * 3, [np.nan] * 3, [np.nan] * 3,
                             start="2025-05-02 00:00")
    thr = derive_thresholds(pd.concat([base, nan_rows]))
    for key, expected in EXPECTED_TRAIN_THRESHOLDS.items():
        assert thr[key] == pytest.approx(expected), key


def test_derive_thresholds_custom_q():
    df = feature_frame(TRAIN_FUNDING, TRAIN_OI_CHG, TRAIN_FG)
    thr = derive_thresholds(df, q=(0.5, 0.5))
    assert thr["funding_lo"] == pytest.approx(0.0)
    assert thr["funding_hi"] == pytest.approx(0.0)
    assert thr["fg_lo"] == pytest.approx(50.0)
    assert thr["fg_hi"] == pytest.approx(50.0)


def test_thresholds_from_add_features_output_feed_classifier_keys():
    # end-to-end shape check: add_features output slices straight into
    # derive_thresholds, and the keys match lab/classifier.py's canon
    oi = [100.0 * (1.0 + 0.01 * i) for i in range(20)]
    funding = [(0.0001 * ((i % 3) - 1)) if i % 2 == 0 else 0.0
               for i in range(20)]
    fg = list(np.linspace(10.0, 90.0, 20))
    panel = make_panel(20, oi=oi, funding=funding, fg=fg)
    thr = derive_thresholds(add_features(panel))
    assert set(thr) == THRESHOLD_KEYS
    assert all(type(v) is float for v in thr.values())
