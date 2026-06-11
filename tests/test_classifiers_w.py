"""Tests for lab/classifiers_w.py — W-sweep taxonomies T-D…T-H.

Registered spec: docs/plans/2026-06-10-widening-preregistration.md §4
(taxonomies, canonical label orders, cuts, NaN policy) and §2 (coverage
floor: < 90 distinct UTC calendar days each with >= 1 non-NaN observation
of a non-funding Feature => every bar of the fold carries the axis's na
label; funding axes exempt).

Hand-constructed frames with hand-computed expected labels. Never lab CSVs.

NaN semantics: funding keeps FREEZE-ADDENDUM D4.3 (NaN clause FALSE — pos
requires f >= 0, so NaN funding -> neg branch; NaN extremity -> mid). A NaN
non-funding Feature bar maps to the taxonomy's explicit na label.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.classifiers_w import (  # noqa: E402
    AXIS_FEATURE_W,
    COVERAGE_FLOOR_DAYS,
    LABELS_W,
    NA_LABEL_W,
    RSI_OB,
    RSI_OS,
    TAXONOMIES_W,
    derive_thresholds_w,
    label_w,
)

# Shared hand-picked absolute thresholds for label tests (cut derivation is
# tested separately; label_w only consumes absolute numbers, R1).
TD_T = {"c_hi": 0.001, "c_x": 0.002}
TE_T = {"axis_na": False}
TF_T = {"fg_lo": 20.0, "fg_hi": 80.0, "axis_na": False}
TG_T = {"axis_na": False}
TH_T = {"rsi_os": 30.0, "rsi_ob": 70.0, "axis_na": False}


def _frame(index=None, **cols):
    return pd.DataFrame(cols, index=index)


def _coverage_frame(col, n_days, bars_per_day=6, total_days=91):
    """4h-grid frame spanning total_days UTC days; the first bar of each of
    the first n_days days holds a non-NaN observation of col, all else NaN."""
    idx = pd.date_range(
        "2024-01-01", periods=total_days * bars_per_day, freq="4h", tz="UTC"
    )
    vals = np.full(len(idx), np.nan)
    for d in range(n_days):
        vals[d * bars_per_day] = 1.0
    return pd.DataFrame({col: vals}, index=idx)


# ------------------------------------------------------ registered constants


def test_taxonomies_w_canonical_order():
    # §7 RNG map: taxonomy_index T-D=0 / T-E=1 / T-F=2 / T-G=3 / T-H=4.
    assert TAXONOMIES_W == ["TD", "TE", "TF", "TG", "TH"]


def test_labels_w_match_registration_table():
    # §4 table, canonical order verbatim (feeds §5 action-map zipping: the
    # non-na prefix of each list is exactly the §5 direction-vector order).
    assert LABELS_W == {
        "TD": ["pos-mid", "pos-hi", "pos-x", "neg-mid", "neg-hi", "neg-x"],
        "TE": ["pos-build", "pos-unwind", "neg-build", "neg-unwind", "oi-na"],
        "TF": ["pos-fear", "pos-greed", "neg-fear", "neg-greed",
               "fg-mid", "fg-na"],
        "TG": ["pos-above", "neg-above", "pos-below", "neg-below", "sma-na"],
        "TH": ["pos-os", "pos-mid", "pos-ob", "neg-os", "neg-mid", "neg-ob",
               "rsi-na"],
    }


def test_na_label_and_axis_feature_maps():
    # Funding-only T-D has no na label and no non-funding axis (§2 exemption).
    assert NA_LABEL_W == {
        "TD": None, "TE": "oi-na", "TF": "fg-na", "TG": "sma-na",
        "TH": "rsi-na",
    }
    assert AXIS_FEATURE_W == {
        "TD": None,
        "TE": "oi_chg_24h_daily",
        "TF": "fg",
        "TG": "close_vs_sma200_1d",
        "TH": "rsi14_1d",
    }


def test_registered_scalar_constants():
    assert COVERAGE_FLOOR_DAYS == 90
    assert RSI_OS == 30.0
    assert RSI_OB == 70.0


# -------------------------------------------------------- derive_thresholds_w


def test_derive_td_cuts_hand_computed():
    # |funding| = 0..10 -> q60 = 6.0, q90 = 9.0 (linear interpolation on 11
    # points). Alternating signs pin that cuts use |funding_rate_8h|.
    funding = [0.0, -1.0, 2.0, -3.0, 4.0, -5.0, 6.0, -7.0, 8.0, -9.0, 10.0]
    out = derive_thresholds_w(_frame(funding_rate_8h=funding), "TD")
    assert set(out) == {"c_hi", "c_x"}
    assert isinstance(out["c_hi"], float)
    assert isinstance(out["c_x"], float)
    assert out["c_hi"] == pytest.approx(6.0)
    assert out["c_x"] == pytest.approx(9.0)


def test_derive_td_nans_excluded():
    funding = [0.0, -1.0, 2.0, -3.0, 4.0, -5.0, 6.0, -7.0, 8.0, -9.0, 10.0,
               np.nan, np.nan]
    out = derive_thresholds_w(_frame(funding_rate_8h=funding), "TD")
    assert out["c_hi"] == pytest.approx(6.0)
    assert out["c_x"] == pytest.approx(9.0)


def test_derive_td_funding_axis_exempt_from_coverage_floor():
    # Only 3 covered days, but funding axes are exempt (§2): no sentinel.
    df = _coverage_frame("funding_rate_8h", 3)
    out = derive_thresholds_w(df, "TD")
    assert set(out) == {"c_hi", "c_x"}


def test_derive_tf_cuts_hand_computed():
    # fg = 0..10 -> q20 = 2.0, q80 = 8.0. Frame spans < 90 days, so the
    # coverage sentinel is True; cuts are still derived (the sentinel, not
    # the cuts, governs labeling on a floored fold).
    idx = pd.date_range("2024-01-01", periods=11, freq="4h", tz="UTC")
    out = derive_thresholds_w(_frame(index=idx, fg=list(range(11))), "TF")
    assert set(out) == {"fg_lo", "fg_hi", "axis_na"}
    assert out["fg_lo"] == pytest.approx(2.0)
    assert out["fg_hi"] == pytest.approx(8.0)
    assert out["axis_na"] is True


def test_derive_tf_all_nan_fg_is_floored():
    idx = pd.date_range("2024-01-01", periods=12, freq="4h", tz="UTC")
    out = derive_thresholds_w(_frame(index=idx, fg=[np.nan] * 12), "TF")
    assert out["axis_na"] is True
    assert np.isnan(out["fg_lo"])
    assert np.isnan(out["fg_hi"])


def test_derive_te_tg_no_train_cuts():
    # §4: T-E and T-G have no train-derived cuts — sentinel only.
    te = derive_thresholds_w(_coverage_frame("oi_chg_24h_daily", 90), "TE")
    tg = derive_thresholds_w(_coverage_frame("close_vs_sma200_1d", 90), "TG")
    assert set(te) == {"axis_na"}
    assert set(tg) == {"axis_na"}
    assert te["axis_na"] is False
    assert tg["axis_na"] is False


def test_derive_th_fixed_constants_returned_as_is():
    # §4: os/ob bands are canonical constants 30/70, never data-derived —
    # extreme rsi values must not move them.
    idx = pd.date_range("2024-01-01", periods=4, freq="4h", tz="UTC")
    df = _frame(index=idx, rsi14_1d=[0.0, 1.0, 99.0, 100.0])
    out = derive_thresholds_w(df, "TH")
    assert set(out) == {"rsi_os", "rsi_ob", "axis_na"}
    assert out["rsi_os"] == 30.0
    assert out["rsi_ob"] == 70.0


@pytest.mark.parametrize(
    "tax,col",
    [
        ("TE", "oi_chg_24h_daily"),
        ("TF", "fg"),
        ("TG", "close_vs_sma200_1d"),
        ("TH", "rsi14_1d"),
    ],
)
def test_coverage_floor_flips_at_90_days(tax, col):
    # §2: < 90 distinct covered UTC days -> floored; exactly 90 -> not.
    floored = derive_thresholds_w(_coverage_frame(col, 89), tax)
    ok = derive_thresholds_w(_coverage_frame(col, 90), tax)
    assert floored["axis_na"] is True
    assert ok["axis_na"] is False


def test_coverage_floor_counts_days_not_observations():
    # 89 fully-populated days = 534 observations but only 89 distinct UTC
    # calendar days -> still floored.
    df = _coverage_frame("oi_chg_24h_daily", 0)
    df.iloc[: 89 * 6, df.columns.get_loc("oi_chg_24h_daily")] = 1.0
    out = derive_thresholds_w(df, "TE")
    assert out["axis_na"] is True


def test_derive_unknown_taxonomy_raises():
    with pytest.raises(ValueError):
        derive_thresholds_w(_frame(funding_rate_8h=[0.0]), "TX")


# ------------------------------------------------------------------ T-D label


def test_td_labels_every_branch():
    df = _frame(
        funding_rate_8h=[0.0005, 0.0015, 0.0025, -0.0005, -0.0015, -0.0025],
    )
    out = label_w(df, "TD", TD_T)
    assert out.tolist() == [
        "pos-mid", "pos-hi", "pos-x", "neg-mid", "neg-hi", "neg-x",
    ]


def test_td_boundaries():
    # pos <=> f >= 0 (0.0 -> pos); bands inclusive: |f| >= c_hi -> hi,
    # |f| >= c_x -> x (frozen T-C convention, §6 reference labeling).
    df = _frame(funding_rate_8h=[0.0, 0.001, 0.002, -0.001, -0.002])
    out = label_w(df, "TD", TD_T)
    assert out.tolist() == ["pos-mid", "pos-hi", "pos-x", "neg-hi", "neg-x"]


def test_td_nan_funding_is_neg_mid():
    # D4.3: (NaN >= 0) FALSE -> neg branch; (|NaN| >= cut) FALSE -> mid.
    df = _frame(funding_rate_8h=[np.nan])
    assert label_w(df, "TD", TD_T).tolist() == ["neg-mid"]


def test_td_derive_then_label_integration():
    # cuts from the same synthetic train: c_hi = 6.0, c_x = 9.0.
    funding = [0.0, -1.0, 2.0, -3.0, 4.0, -5.0, 6.0, -7.0, 8.0, -9.0, 10.0]
    df = _frame(funding_rate_8h=funding)
    cuts = derive_thresholds_w(df, "TD")
    out = label_w(df, "TD", cuts)
    assert out.tolist() == [
        "pos-mid", "neg-mid", "pos-mid", "neg-mid", "pos-mid", "neg-mid",
        "pos-hi", "neg-hi", "pos-hi", "neg-x", "pos-x",
    ]


# ------------------------------------------------------------------ T-E label


def test_te_labels_every_branch():
    # build <=> oi_chg_24h_daily >= 0 (0.0 -> build); pos <=> f >= 0.
    df = _frame(
        funding_rate_8h=[0.0001, 0.0001, -0.0001, -0.0001, 0.0, 0.0001],
        oi_chg_24h_daily=[0.05, -0.05, 0.05, -0.05, 0.05, 0.0],
    )
    out = label_w(df, "TE", TE_T)
    assert out.tolist() == [
        "pos-build", "pos-unwind", "neg-build", "neg-unwind",
        "pos-build", "pos-build",
    ]


def test_te_nan_routing():
    # NaN oi -> oi-na (even with funding fine, and when both are NaN);
    # NaN funding with oi present -> D4.3 neg branch.
    df = _frame(
        funding_rate_8h=[0.0001, np.nan, np.nan, np.nan],
        oi_chg_24h_daily=[np.nan, 0.05, -0.05, np.nan],
    )
    out = label_w(df, "TE", TE_T)
    assert out.tolist() == ["oi-na", "neg-build", "neg-unwind", "oi-na"]


# ------------------------------------------------------------------ T-F label


def test_tf_labels_every_branch():
    # fear <=> fg <= fg_lo, greed <=> fg >= fg_hi (inclusive); fg-mid is a
    # single funding-free label (acts 0 in every direction map, §5).
    df = _frame(
        funding_rate_8h=[0.0001, 0.0001, -0.0001, -0.0001, 0.0001, -0.0001,
                         0.0001, -0.0001],
        fg=[10.0, 90.0, 10.0, 90.0, 50.0, 50.0, 20.0, 80.0],
    )
    out = label_w(df, "TF", TF_T)
    assert out.tolist() == [
        "pos-fear", "pos-greed", "neg-fear", "neg-greed",
        "fg-mid", "fg-mid", "pos-fear", "neg-greed",
    ]


def test_tf_nan_routing():
    # NaN fg -> fg-na; NaN funding -> neg branch in the corners; fg-mid is
    # reached regardless of funding NaN.
    df = _frame(
        funding_rate_8h=[0.0001, np.nan, np.nan, np.nan],
        fg=[np.nan, 10.0, 90.0, 50.0],
    )
    out = label_w(df, "TF", TF_T)
    assert out.tolist() == ["fg-na", "neg-fear", "neg-greed", "fg-mid"]


# ------------------------------------------------------------------ T-G label


def test_tg_labels_every_branch():
    # above <=> close_vs_sma200_1d > 0 (strict: 0.0 -> below).
    df = _frame(
        funding_rate_8h=[0.0001, -0.0001, 0.0001, -0.0001, 0.0001, 0.0],
        close_vs_sma200_1d=[0.5, 0.5, -0.5, -0.5, 0.0, 1.0],
    )
    out = label_w(df, "TG", TG_T)
    assert out.tolist() == [
        "pos-above", "neg-above", "pos-below", "neg-below",
        "pos-below", "pos-above",
    ]


def test_tg_nan_routing():
    # NaN sma -> sma-na (explicit na label, NOT the D4.3 below branch);
    # NaN funding with sma present -> neg branch.
    df = _frame(
        funding_rate_8h=[0.0001, np.nan, np.nan, np.nan],
        close_vs_sma200_1d=[np.nan, 0.5, -0.5, np.nan],
    )
    out = label_w(df, "TG", TG_T)
    assert out.tolist() == ["sma-na", "neg-above", "neg-below", "sma-na"]


# ------------------------------------------------------------------ T-H label


def test_th_labels_every_branch():
    # os <=> rsi <= 30, ob <=> rsi >= 70 (inclusive, fixed constants).
    df = _frame(
        funding_rate_8h=[0.0001, 0.0001, 0.0001, -0.0001, -0.0001, -0.0001,
                         0.0001, -0.0001],
        rsi14_1d=[20.0, 50.0, 80.0, 20.0, 50.0, 80.0, 30.0, 70.0],
    )
    out = label_w(df, "TH", TH_T)
    assert out.tolist() == [
        "pos-os", "pos-mid", "pos-ob", "neg-os", "neg-mid", "neg-ob",
        "pos-os", "neg-ob",
    ]


def test_th_nan_routing():
    # NaN rsi -> rsi-na; NaN funding with rsi present -> neg branch.
    df = _frame(
        funding_rate_8h=[0.0001, np.nan, np.nan],
        rsi14_1d=[np.nan, 20.0, 50.0],
    )
    out = label_w(df, "TH", TH_T)
    assert out.tolist() == ["rsi-na", "neg-os", "neg-mid"]


# ----------------------------------------------------- axis-floored labeling


@pytest.mark.parametrize(
    "tax,cols,thresholds",
    [
        ("TE", {"oi_chg_24h_daily": [0.05, -0.05]}, {"axis_na": True}),
        ("TF", {"fg": [10.0, 90.0]},
         {"fg_lo": 20.0, "fg_hi": 80.0, "axis_na": True}),
        ("TG", {"close_vs_sma200_1d": [0.5, -0.5]}, {"axis_na": True}),
        ("TH", {"rsi14_1d": [20.0, 80.0]},
         {"rsi_os": 30.0, "rsi_ob": 70.0, "axis_na": True}),
    ],
)
def test_axis_floored_fold_every_bar_is_na(tax, cols, thresholds):
    # §2: a floored axis forces the na label on EVERY bar of the fold, even
    # bars whose Features are present and would otherwise label cleanly.
    df = _frame(funding_rate_8h=[0.0001, -0.0001], **cols)
    out = label_w(df, tax, thresholds)
    assert out.tolist() == [NA_LABEL_W[tax]] * 2
    assert out.index.equals(df.index)


# ----------------------------------------------------------------- plumbing


def test_label_index_preserved():
    idx = pd.date_range("2025-04-03", periods=3, freq="4h", tz="UTC")
    df = _frame(index=idx, funding_rate_8h=[0.0005, -0.0015, 0.0025])
    out = label_w(df, "TD", TD_T)
    assert out.index.equals(idx)
    assert out.tolist() == ["pos-mid", "neg-hi", "pos-x"]


def test_label_unknown_taxonomy_raises():
    with pytest.raises(ValueError):
        label_w(_frame(funding_rate_8h=[0.0]), "TX", {})


def test_every_emitted_label_is_registered():
    # Each taxonomy's labeler can only emit labels from §4's table.
    frames = {
        "TD": _frame(funding_rate_8h=[0.0005, -0.0025, np.nan]),
        "TE": _frame(funding_rate_8h=[0.0001, np.nan],
                     oi_chg_24h_daily=[0.05, np.nan]),
        "TF": _frame(funding_rate_8h=[0.0001, -0.0001, np.nan],
                     fg=[10.0, 50.0, np.nan]),
        "TG": _frame(funding_rate_8h=[0.0001, np.nan],
                     close_vs_sma200_1d=[0.5, np.nan]),
        "TH": _frame(funding_rate_8h=[0.0001, np.nan],
                     rsi14_1d=[20.0, np.nan]),
    }
    thresholds = {"TD": TD_T, "TE": TE_T, "TF": TF_T, "TG": TG_T, "TH": TH_T}
    for tax in TAXONOMIES_W:
        out = label_w(frames[tax], tax, thresholds[tax])
        assert set(out) <= set(LABELS_W[tax]), tax
