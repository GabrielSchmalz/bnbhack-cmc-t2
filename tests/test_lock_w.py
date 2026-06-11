"""Tests for lab/lock_w.py — §6 hypothesis-family quarantine (lock layers).

Registered spec: docs/plans/2026-06-10-widening-preregistration.md §6:
reference extremity labeling (per-fold train cuts c_hi = q60(|f|),
c_x = q90(|f|), identical to T-D §4; extremity bar iff f >= 0 and
|f| >= c_hi), lock layer 1 (pure-map predicate — catches A1/A2 and the
every-positive-label-short case, NOT the registered symmetric maps),
lock layer 2 (extremity-neutralized twin w' on synthetic series: short
leg neutralized, long-only de-risk re-risked, fallback-0 fold), lock
layer 3 (share backstop, majority rule > 0.5, arithmetic worked example).

Hand-constructed series with hand-computed expectations. Never lab CSVs.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.classifiers_w import derive_thresholds_w  # noqa: E402
from lab.lock_w import (  # noqa: E402
    layer1_pure_map_locked,
    layer2_twin,
    layer3_share,
    reference_cuts,
    reference_extremity_mask,
    reference_mild_mask,
)
from lab.variants_w import VariantW, enumerate_all_w  # noqa: E402

# 11 train values: sorted |f| = .001 .002 .002 .003 .004 .005 .006 .007
# .008 .009 .010 -> with linear interpolation h = (n-1)q lands on integer
# positions: q60 -> index 6 exactly (0.006), q90 -> index 9 exactly (0.009).
TRAIN_FUNDING = pd.Series(
    [0.001, -0.002, 0.002, 0.003, -0.004, 0.005,
     0.006, -0.007, 0.008, 0.009, 0.010],
    index=pd.date_range("2024-01-01", periods=11, freq="4h", tz="UTC"),
)
C_HI = 0.006
C_X = 0.009


def _variant(taxonomy, actions, vid="SYN"):
    """Synthetic VariantW for layer-1 predicate tests."""
    return VariantW(
        id=vid, panel="P-BTC", family="direction", taxonomy=taxonomy,
        action_map=tuple(actions.items()),
    )


# ----------------------------------------------- reference extremity labeling


def test_reference_cuts_hand_computed():
    cuts = reference_cuts(TRAIN_FUNDING)
    assert cuts["c_hi"] == pytest.approx(C_HI)
    assert cuts["c_x"] == pytest.approx(C_X)


def test_reference_cuts_identical_to_td_thresholds():
    # §6: "identical to T-D §4" — same numbers as derive_thresholds_w(TD).
    td = derive_thresholds_w(
        pd.DataFrame({"funding_rate_8h": TRAIN_FUNDING}), "TD")
    cuts = reference_cuts(TRAIN_FUNDING)
    assert cuts["c_hi"] == td["c_hi"]
    assert cuts["c_x"] == td["c_x"]


def test_reference_extremity_mask_hand_computed():
    idx = pd.date_range("2025-01-01", periods=6, freq="4h", tz="UTC")
    oos = pd.Series([0.007, 0.006, 0.0059, -0.009, 0.0, np.nan], index=idx)
    mask = reference_extremity_mask(oos, TRAIN_FUNDING)
    # f >= 0 AND |f| >= c_hi (inclusive); negative funding never qualifies
    # however extreme; NaN funding -> clause FALSE (D4.3).
    assert mask.tolist() == [True, True, False, False, False, False]
    assert mask.index.equals(idx)
    assert mask.dtype == bool


def test_reference_mild_mask_hand_computed_and_disjoint():
    idx = pd.date_range("2025-01-01", periods=6, freq="4h", tz="UTC")
    oos = pd.Series([0.007, 0.006, 0.0059, -0.009, 0.0, np.nan], index=idx)
    mild = reference_mild_mask(oos, TRAIN_FUNDING)
    # f >= 0 AND |f| < c_hi (strict); NaN -> FALSE.
    assert mild.tolist() == [False, False, True, False, True, False]
    ext = reference_extremity_mask(oos, TRAIN_FUNDING)
    assert not (mild & ext).any()  # disjoint by construction
    # union = every non-NaN positive-funding bar
    assert (mild | ext).tolist() == [True, True, True, False, True, False]


# ----------------------------------------------------- layer 1: pure-map lock


def test_layer1_locks_exactly_the_annex_across_the_registration():
    # §6: "(A1/A2 satisfy it; the registered symmetric maps do not.)"
    for v in enumerate_all_w():
        assert layer1_pure_map_locked(v) is v.annex, v.id


def test_layer1_named_cases_from_registration():
    by_id = {v.id: v for v in enumerate_all_w()}
    locked = [
        "P-BTC-DIR-TD-A1-fade_pos_x_only-1.0",
        "P-BTC-DIR-TD-A1-fade_pos_x_only-0.5-ts6",
        "P-BTC-DIR-TD-A2-fade_pos_graded-1.0",
        "P-BTC-DIR-TD-A2-fade_pos_graded-0.5",
    ]
    unlocked = [
        "P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0",  # acts in neg bands
        "P-BTC-DIR-TD-D2-fade_x_only_sym-1.0",           # long in neg-x
        "P-BTC-DIR-TE-E3-fade_pos_long_neg-1.0",         # long in neg labels
    ]
    for vid in locked:
        assert layer1_pure_map_locked(by_id[vid]) is True, vid
    for vid in unlocked:
        assert layer1_pure_map_locked(by_id[vid]) is False, vid


def test_layer1_every_positive_label_short_te_like_map_locked():
    # Taxonomy without extremity bands: short on EVERY positive-funding
    # label, silent on negative labels, long nowhere -> locked.
    v = _variant("TE", {
        "pos-build": -1.0, "pos-unwind": -1.0,
        "neg-build": 0.0, "neg-unwind": 0.0, "oi-na": 0.0,
    })
    assert layer1_pure_map_locked(v) is True


def test_layer1_partial_positive_short_without_band_not_locked():
    # Short on only ONE positive label of a no-extremity-band taxonomy.
    v = _variant("TE", {
        "pos-build": -1.0, "pos-unwind": 0.0,
        "neg-build": 0.0, "neg-unwind": 0.0, "oi-na": 0.0,
    })
    assert layer1_pure_map_locked(v) is False


def test_layer1_td_short_only_in_mild_not_locked():
    # T-D HAS extremity bands (pos-hi, pos-x): a pos-mid-only short fails
    # clause (i).
    v = _variant("TD", {
        "pos-mid": -1.0, "pos-hi": 0.0, "pos-x": 0.0,
        "neg-mid": 0.0, "neg-hi": 0.0, "neg-x": 0.0,
    })
    assert layer1_pure_map_locked(v) is False


def test_layer1_long_in_na_label_blocks():
    # Clause (iii): long NOWHERE — a long na label breaks the predicate.
    v = _variant("TE", {
        "pos-build": -1.0, "pos-unwind": -1.0,
        "neg-build": 0.0, "neg-unwind": 0.0, "oi-na": 0.5,
    })
    assert layer1_pure_map_locked(v) is False


def test_layer1_nonzero_negative_label_blocks_even_when_short():
    # Clause (ii): NO nonzero action in any negative-funding label — a
    # short there also breaks the predicate.
    v = _variant("TE", {
        "pos-build": -1.0, "pos-unwind": -1.0,
        "neg-build": -0.5, "neg-unwind": 0.0, "oi-na": 0.0,
    })
    assert layer1_pure_map_locked(v) is False


def test_layer1_unknown_taxonomy_raises():
    v = _variant("TC", {"pos-extreme": -1.0})
    with pytest.raises(ValueError):
        layer1_pure_map_locked(v)


# ------------------------------------------------ layer 2: neutralized twin


def _twin_fixture():
    """8 bars, two folds F1/F2 (4 bars each).

    F1: mild bars 0,1 (w = 1.0, 0.5 -> mean 0.75); masked bars 2 (short
    leg, w = -1.0) and 3 (de-risked long, w = 0.25).
    F2: NO mild bars (fallback 0); masked bar 5 (w = -0.5).
    """
    idx = pd.date_range("2025-01-01", periods=8, freq="4h", tz="UTC")
    w = pd.Series([1.0, 0.5, -1.0, 0.25, 0.8, -0.5, 0.0, 1.0], index=idx)
    mask = pd.Series(
        [False, False, True, True, False, True, False, False], index=idx)
    mild = pd.Series(
        [True, True, False, False, False, False, False, False], index=idx)
    folds = pd.Series(["F1"] * 4 + ["F2"] * 4, index=idx)
    return w, mask, mild, folds


def test_layer2_twin_worked_example():
    w, mask, mild, folds = _twin_fixture()
    twin = layer2_twin(w, mask, folds, mild_mask=mild)
    # F1 mild mean = (1.0 + 0.5) / 2 = 0.75:
    #   bar 2: short leg -1.0  -> 0.75 (short leg neutralized AND re-risked)
    #   bar 3: de-risk   0.25  -> 0.75 (long-only de-risk coat re-risked)
    # F2 has no mild bars -> fallback 0: bar 5 -0.5 -> 0.0.
    # All unmasked bars keep w.
    expected = [1.0, 0.5, 0.75, 0.75, 0.8, 0.0, 0.0, 1.0]
    assert twin.tolist() == expected
    assert twin.index.equals(w.index)


def test_layer2_twin_does_not_mutate_inputs():
    w, mask, mild, folds = _twin_fixture()
    w_orig = w.copy()
    twin = layer2_twin(w, mask, folds, mild_mask=mild)
    assert w.equals(w_orig)
    assert twin is not w


def test_layer2_mild_mean_includes_zero_w_bars():
    # Mean signed w over ALL mild bars of the fold, zeros included.
    idx = pd.date_range("2025-01-01", periods=3, freq="4h", tz="UTC")
    w = pd.Series([1.0, 0.0, -1.0], index=idx)
    mild = pd.Series([True, True, False], index=idx)
    mask = pd.Series([False, False, True], index=idx)
    folds = pd.Series(["F1"] * 3, index=idx)
    twin = layer2_twin(w, mask, folds, mild_mask=mild)
    assert twin.tolist() == [1.0, 0.0, 0.5]  # mean(1.0, 0.0) = 0.5


def test_layer2_mild_mean_is_signed():
    # A net-short mild profile fills masked bars with a NEGATIVE mean.
    idx = pd.date_range("2025-01-01", periods=4, freq="4h", tz="UTC")
    w = pd.Series([-0.5, -1.0, 1.0, 0.0], index=idx)
    mild = pd.Series([True, True, False, False], index=idx)
    mask = pd.Series([False, False, True, False], index=idx)
    folds = pd.Series(["F1"] * 4, index=idx)
    twin = layer2_twin(w, mask, folds, mild_mask=mild)
    assert twin.tolist() == [-0.5, -1.0, -0.75, 0.0]


def test_layer2_per_fold_means_are_independent():
    # Two folds with different mild means; each fold's masked bars take
    # ONLY their own fold's mean.
    idx = pd.date_range("2025-01-01", periods=4, freq="4h", tz="UTC")
    w = pd.Series([1.0, -1.0, 0.5, -1.0], index=idx)
    mild = pd.Series([True, False, True, False], index=idx)
    mask = pd.Series([False, True, False, True], index=idx)
    folds = pd.Series(["F1", "F1", "F2", "F2"], index=idx)
    twin = layer2_twin(w, mask, folds, mild_mask=mild)
    assert twin.tolist() == [1.0, 1.0, 0.5, 0.5]


# --------------------------------------------------- layer 3: share backstop


def test_layer3_worked_example_minority_share_not_locked():
    idx = pd.date_range("2025-01-01", periods=5, freq="4h", tz="UTC")
    contrib = pd.Series([0.04, -0.01, 0.03, 0.02, -0.02], index=idx)
    mask = pd.Series([False, True, True, True, False], index=idx)
    w = pd.Series([1.0, -1.0, -0.5, 0.5, -1.0], index=idx)
    out = layer3_share(contrib, mask, w)
    # Locked-leg bars = mask & w < 0 -> bars 1, 2 (bar 3 is masked but
    # LONG, bar 4 is short but unmasked — both excluded).
    # leg_sum = -0.01 + 0.03 = 0.02; total = 0.06; share = 1/3 <= 0.5.
    assert out["evaluated"] is True
    assert out["total"] == pytest.approx(0.06)
    assert out["leg_sum"] == pytest.approx(0.02)
    assert out["share"] == pytest.approx(1.0 / 3.0)
    assert out["locked"] is False


def test_layer3_majority_share_locked():
    idx = pd.date_range("2025-01-01", periods=4, freq="4h", tz="UTC")
    contrib = pd.Series([0.01, 0.04, 0.02, -0.01], index=idx)
    mask = pd.Series([False, True, True, False], index=idx)
    w = pd.Series([1.0, -1.0, -1.0, 1.0], index=idx)
    out = layer3_share(contrib, mask, w)
    # leg_sum = 0.04 + 0.02 = 0.06; total = 0.06; share = 1.0 > 0.5.
    assert out["evaluated"] is True
    assert out["share"] == pytest.approx(1.0)
    assert out["locked"] is True


def test_layer3_total_nonpositive_not_evaluated():
    idx = pd.date_range("2025-01-01", periods=3, freq="4h", tz="UTC")
    contrib = pd.Series([0.01, -0.03, 0.01], index=idx)  # total = -0.01
    mask = pd.Series([False, True, False], index=idx)
    w = pd.Series([1.0, -1.0, 1.0], index=idx)
    out = layer3_share(contrib, mask, w)
    assert out["evaluated"] is False
    assert out["locked"] is False
    assert np.isnan(out["share"])
    assert out["total"] == pytest.approx(-0.01)


def test_layer3_share_exactly_half_not_locked():
    # Majority rule is STRICT: share == 0.5 does not lock. Binary-exact
    # values so the boundary is float-round-off-free.
    idx = pd.date_range("2025-01-01", periods=2, freq="4h", tz="UTC")
    contrib = pd.Series([0.25, 0.25], index=idx)
    mask = pd.Series([True, False], index=idx)
    w = pd.Series([-1.0, 1.0], index=idx)
    out = layer3_share(contrib, mask, w)
    assert out["evaluated"] is True
    assert out["share"] == 0.5
    assert out["locked"] is False


def test_layer3_zero_or_positive_w_masked_bars_never_in_leg():
    # w == 0 and w > 0 masked bars are not locked-leg bars.
    idx = pd.date_range("2025-01-01", periods=3, freq="4h", tz="UTC")
    contrib = pd.Series([0.05, 0.05, 0.05], index=idx)
    mask = pd.Series([True, True, True], index=idx)
    w = pd.Series([0.0, 1.0, -1.0], index=idx)
    out = layer3_share(contrib, mask, w)
    assert out["leg_sum"] == pytest.approx(0.05)
    assert out["share"] == pytest.approx(1.0 / 3.0)
    assert out["locked"] is False
