"""Tests for lab/rules.py — Task 2.3.

rules.apply(labels, action_map) maps a regime-label series to a position
series w. The 1-bar lag LIVES HERE: the engine expects pre-lagged w, so
regime known at close of bar t may only affect w from bar t+1 on.

Hand-constructed synthetic series only — never lab CSVs.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.rules import apply  # noqa: E402

ACTION_MAP = {"calm": 1.0, "stressed": -0.5, "extreme": 0.0}


def _labels(values, index=None):
    return pd.Series(values, index=index, dtype=object)


# ------------------------------------------------------------------- 1-bar lag


def test_lag_regime_at_bar_t_affects_w_at_t_plus_1_only():
    # Single-bar regime blip at t=2: it must show up in w ONLY at t=3.
    idx = pd.date_range("2025-04-03", periods=5, freq="4h", tz="UTC")
    labels = _labels(["calm", "calm", "stressed", "calm", "calm"], index=idx)
    w = apply(labels, ACTION_MAP)
    assert w.tolist() == [0.0, 1.0, 1.0, -0.5, 1.0]
    # explicit pin: bar 2's regime is visible at bar 3 and NOWHERE else
    assert w.iloc[2] == 1.0  # not yet -0.5
    assert w.iloc[3] == -0.5  # exactly one bar later
    assert w.iloc[4] == 1.0  # gone again


def test_first_bar_is_flat():
    # No prior regime exists at bar 0 -> w[0] = 0.0, whatever the label.
    labels = _labels(["extreme", "calm"])
    w = apply(labels, {"extreme": -1.0, "calm": 1.0})
    assert w.iloc[0] == 0.0
    assert w.iloc[1] == -1.0


def test_constant_regime_series():
    labels = _labels(["calm"] * 4)
    w = apply(labels, ACTION_MAP)
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0]


# -------------------------------------------------- unknown / NaN labels -> 0


def test_unknown_label_maps_to_zero():
    # "mystery" is not in the action map -> contributes 0.0 (one bar later).
    labels = _labels(["calm", "mystery", "calm", "calm"])
    w = apply(labels, ACTION_MAP)
    assert w.tolist() == [0.0, 1.0, 0.0, 1.0]


def test_nan_label_maps_to_zero():
    labels = _labels(["calm", np.nan, "stressed", "calm"])
    w = apply(labels, ACTION_MAP)
    assert w.tolist() == [0.0, 1.0, 0.0, -0.5]


def test_all_unknown_gives_all_flat():
    labels = _labels(["x", "y", np.nan])
    w = apply(labels, ACTION_MAP)
    assert w.tolist() == [0.0, 0.0, 0.0]


# -------------------------------------------------------------- output shape


def test_index_preserved_and_float_dtype():
    idx = pd.date_range("2025-04-03", periods=3, freq="4h", tz="UTC")
    labels = _labels(["calm", "stressed", "calm"], index=idx)
    w = apply(labels, ACTION_MAP)
    assert w.index.equals(idx)
    assert w.dtype == float


def test_fractional_sizes_pass_through():
    labels = _labels(["a", "b", "c", "d"])
    w = apply(labels, {"a": 0.25, "b": -0.25, "c": 0.5, "d": -1.0})
    assert w.tolist() == [0.0, 0.25, -0.25, 0.5]


def test_empty_series():
    w = apply(_labels([]), ACTION_MAP)
    assert len(w) == 0
    assert w.dtype == float


def test_input_labels_not_mutated():
    labels = _labels(["calm", "stressed"])
    before = labels.copy()
    apply(labels, ACTION_MAP)
    pd.testing.assert_series_equal(labels, before)
