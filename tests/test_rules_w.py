"""Tests for lab/rules_w.py — W-sweep rule surface (registration §3, W6).

apply_time_stop / apply_vol_band operate on the POST-LAG (w, lagged_labels)
pair: w = lab.rules.apply(labels, action_map) and lagged_labels =
labels.shift(1), so w[t] = action_map[lagged_labels[t]] (unknown/NaN -> 0).
Fixtures build that pair through lab.rules.apply itself so the lag
convention under test is the real one.

Every clause of the §3 pinned semantics is pinned here: run start (incl.
series start), sign-flip continuation, mid-run label change keeps the
clock, exit at the k-th bar close, blocked re-entry on same-label
persistence, re-entry on transition to a nonzero-action label, transition
to a zero-action (or unknown) label NOT re-entering, intervening
zero-action labels not blocking the later re-entry, NaN safety, and the
boundary convention (transition at the first forced-flat bar re-enters
immediately — dd_guard precedent, see lab/rules_w.py docstring).

Hand-constructed synthetic series only — never lab CSVs, never OOS data
(Phase-1 no-OOS-contact rule).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.rules import apply as rules_apply  # noqa: E402
from lab.rules_w import apply_time_stop, apply_vol_band  # noqa: E402

# A: long, B: short, H: half-long, Z: mapped-but-zero action.
ACTION_MAP = {"A": 1.0, "B": -1.0, "H": 0.5, "Z": 0.0}


def _post_lag(raw_labels, index=None):
    """(w, lagged_labels) exactly as the lab derives them (1-bar lag)."""
    labels = pd.Series(raw_labels, index=index, dtype=object)
    return rules_apply(labels, ACTION_MAP), labels.shift(1)


# ----------------------------------------------------- time-stop: run starts


def test_runs_shorter_than_k_pass_through_unchanged():
    # Two runs (2 long bars, 2 short bars), both < k=3 -> output == input.
    w, lagged = _post_lag(["A", "A", "Z", "B", "B", "Z", "A"])
    assert w.tolist() == [0.0, 1.0, 1.0, 0.0, -1.0, -1.0, 0.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=3)
    assert out.tolist() == w.tolist()


def test_run_starts_at_first_nonzero_after_flat_and_exits_at_kth_bar_close():
    # Label A persists: run = bars 1..2 (k=2 bars keep their position);
    # forced w = 0 from the close of the 2nd run bar, i.e. bar 3 onward.
    w, lagged = _post_lag(["A"] * 6)
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, 0.0]


def test_run_starting_at_series_start_counts_from_bar_0():
    # "(or panel start)": w nonzero at bar 0 starts the run there. This pair
    # cannot arise from rules.apply (bar 0 is always flat) — defensive pin
    # of the registered "or panel start" clause for mid-position slices.
    w = pd.Series([1.0, 1.0, 1.0])
    lagged = pd.Series(["A", "A", "A"], dtype=object)
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [1.0, 1.0, 0.0]


# --------------------------------------------- time-stop: run continuation


def test_sign_flip_without_flat_bar_continues_the_same_run():
    # A,A then B,B,B: w flips +1 -> -1 with no flat bar in between; the run
    # clock keeps counting, so with k=3 the flip bar is run bar 3 and the
    # stop fires at its close.
    w, lagged = _post_lag(["A", "A", "B", "B", "B", "B"])
    assert w.tolist() == [0.0, 1.0, 1.0, -1.0, -1.0, -1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=3)
    assert out.tolist() == [0.0, 1.0, 1.0, -1.0, 0.0, 0.0]


def test_same_sign_label_change_mid_run_does_not_reset_the_clock():
    # H (+0.5) -> A (+1.0): a label transition mid-run without a flat bar.
    # A run starts ONLY at a nonzero bar preceded by a flat bar, so the
    # clock keeps counting (k=3 -> stop after the 3rd run bar).
    w, lagged = _post_lag(["H", "A", "A", "A", "A"])
    assert w.tolist() == [0.0, 0.5, 1.0, 1.0, 1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=3)
    assert out.tolist() == [0.0, 0.5, 1.0, 1.0, 0.0]


def test_natural_flat_ends_run_without_stop_and_budget_is_fresh():
    # Run of 2 (< k=3) ends on a zero-action bar: no stop fired, so the next
    # nonzero bar starts a NEW run with a fresh k-bar budget (plain run-start
    # rule, no transition re-entry needed).
    w, lagged = _post_lag(["A", "A", "Z", "A", "A", "A", "A"])
    assert w.tolist() == [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=3)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0]


# ------------------------------------------------------ time-stop: re-entry


def test_blocked_reentry_on_same_label_persistence():
    # After the stop, label A persists (no transition): w stays forced 0 for
    # every persisting bar even though the mapped action is nonzero.
    w, lagged = _post_lag(["A", "A", "A", "A", "A", "A", "A"])
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]


def test_reentry_on_transition_to_nonzero_action_label_with_fresh_budget():
    # Stop after run bars 1..2; A persists (blocked at bars 3-4); lagged
    # label transitions A -> B at bar 5 -> re-entry AT bar 5; the new run
    # gets a fresh k=2 budget and stops again after bar 6.
    w, lagged = _post_lag(["A", "A", "A", "A", "B", "B", "B", "B"])
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, -1.0, -1.0, 0.0]


def test_transition_to_zero_action_label_does_not_reenter():
    # After the stop, A -> Z IS a transition, but Z's mapped action is 0 ->
    # no re-entry (w stays 0); the later Z -> B transition re-enters:
    # "regardless of intervening zero-action labels".
    w, lagged = _post_lag(["A", "A", "A", "Z", "Z", "B", "B"])
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0, 0.0, 0.0, -1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, 0.0, -1.0]


def test_transition_to_unknown_label_does_not_reenter():
    # Unknown labels map to action 0 (lab/rules.py convention) -> not a
    # re-entry; the later transition into B (nonzero) re-enters.
    w, lagged = _post_lag(["A", "A", "A", "mystery", "B", "B"])
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0, 0.0, -1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, -1.0]


def test_reentry_into_same_label_after_zero_action_gap():
    # "TRANSITION into ANY label whose mapped action is nonzero" includes a
    # return to the very label that was stopped: A (stop) -> Z -> A.
    w, lagged = _post_lag(["A", "A", "A", "Z", "A", "A", "A"])
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0]


def test_transition_at_first_forced_flat_bar_reenters_immediately():
    # Boundary convention (pinned): the stop fires at the close of run bar
    # k; a qualifying transition observed at that same close (lagged label
    # changes at run bar k+1) re-enters AT that bar — the forced exit and
    # the fresh entry share one fill, cost-identical under PR-3 per-side
    # |dw| costs to exiting to 0 and re-entering at the same open. Mirrors
    # lab/dd_guard.py re-entry mechanics. The re-entered run consumed none
    # of its budget at the boundary: it stops again k bars later.
    w, lagged = _post_lag(["A", "A", "B", "B", "B", "B"])
    assert w.tolist() == [0.0, 1.0, 1.0, -1.0, -1.0, -1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, -1.0, -1.0, 0.0]


def test_after_reentry_plain_rules_resume():
    # Re-entered run ends naturally on a zero-action bar (no stop fired);
    # the next nonzero bar starts a new run by the plain run-start rule.
    w, lagged = _post_lag(["A", "A", "A", "B", "Z", "B", "B"])
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0, -1.0, 0.0, -1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    # bars 1-2: run, stop; bar 3: lagged label still A (persistence) -> 0;
    # bar 4: A->B transition -> re-enter (run bar 1); bar 5: Z -> natural
    # flat, run over after 1 bar (no stop fired); bar 6: Z->B nonzero ->
    # new run by the plain run-start rule (last bar).
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, -1.0, 0.0, -1.0]


# ------------------------------------------------------ time-stop: NaN-safe


def test_nan_lagged_labels_are_zero_action_and_nan_to_nan_is_no_transition():
    # After the stop: A -> NaN is a transition into a zero-action "label"
    # (no re-entry); NaN -> NaN is NOT a transition (NaN-safe equality);
    # NaN -> B is a transition into a nonzero-action label -> re-entry.
    w, lagged = _post_lag(["A", "A", "A", np.nan, np.nan, "B", "B"])
    assert w.tolist() == [0.0, 1.0, 1.0, 1.0, 0.0, 0.0, -1.0]
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, 0.0, -1.0]


def test_nan_w_bar_is_treated_as_flat_and_output_has_no_nans():
    # Defensive: lab/rules.apply can never emit NaN w, but a NaN w bar is
    # treated as flat (missing => flat, §4 policy): it ends the run and the
    # output carries 0.0 there, never NaN.
    w = pd.Series([0.0, 1.0, np.nan, 1.0, 1.0, 1.0])
    lagged = pd.Series([np.nan, "A", "A", "A", "A", "A"], dtype=object)
    out = apply_time_stop(w, lagged, ACTION_MAP, k=3)
    assert out.tolist() == [0.0, 1.0, 0.0, 1.0, 1.0, 1.0]
    assert not out.isna().any()


# ------------------------------------------------- time-stop: k domain, shape


def test_k_none_returns_w_unchanged_as_a_new_series():
    # Registered rung "none": no time stop. Must not return the same object.
    w, lagged = _post_lag(["A", "A", "B", "Z", "A"])
    out = apply_time_stop(w, lagged, ACTION_MAP, k=None)
    assert out.tolist() == w.tolist()
    assert out is not w


def test_k_must_be_a_positive_integer():
    w, lagged = _post_lag(["A", "A", "A"])
    for bad in (0, -1, 2.5):
        with pytest.raises(ValueError):
            apply_time_stop(w, lagged, ACTION_MAP, k=bad)


def test_index_preserved_dtype_float_input_not_mutated():
    idx = pd.date_range("2025-04-03", periods=6, freq="4h", tz="UTC")
    w, lagged = _post_lag(["A"] * 6, index=idx)
    w_before, lagged_before = w.copy(), lagged.copy()
    out = apply_time_stop(w, lagged, ACTION_MAP, k=2)
    assert out.index.equals(idx)
    assert out.dtype == float
    pd.testing.assert_series_equal(w, w_before)
    pd.testing.assert_series_equal(lagged, lagged_before)


def test_empty_series():
    out = apply_time_stop(pd.Series([], dtype=float),
                          pd.Series([], dtype=object), ACTION_MAP, k=6)
    assert len(out) == 0
    assert out.dtype == float


# ------------------------------------------------------------------ vol-band


def test_vol_band_halves_w_on_hot_bars_only():
    w = pd.Series([1.0, -1.0, 0.5, 0.0, -0.5])
    hot = pd.Series([True, False, True, True, True], index=w.index)
    out = apply_vol_band(w, hot)
    assert out.tolist() == [0.5, -1.0, 0.25, 0.0, -0.25]


def test_vol_band_all_cold_is_identity():
    w = pd.Series([1.0, -0.5, 0.0])
    out = apply_vol_band(w, pd.Series([False] * 3, index=w.index))
    assert out.tolist() == w.tolist()


def test_vol_band_nan_mask_bars_do_not_scale():
    # D4.3: a NaN clause evaluates FALSE — a NaN/missing mask bar is cold.
    w = pd.Series([1.0, 1.0, 1.0])
    hot = pd.Series([True, np.nan, None], index=w.index, dtype=object)
    out = apply_vol_band(w, hot)
    assert out.tolist() == [0.5, 1.0, 1.0]


def test_vol_band_mask_aligned_on_w_index_missing_bars_cold():
    idx = pd.date_range("2025-04-03", periods=4, freq="4h", tz="UTC")
    w = pd.Series([1.0, 1.0, 1.0, 1.0], index=idx)
    # mask covers only bars 1-2 (plus an extraneous bar outside w's index).
    hot = pd.Series([True, False, True],
                    index=[idx[1], idx[2],
                           idx[-1] + pd.Timedelta(hours=4)])
    out = apply_vol_band(w, hot)
    assert out.tolist() == [1.0, 0.5, 1.0, 1.0]
    assert out.index.equals(idx)


def test_vol_band_index_dtype_and_no_mutation():
    idx = pd.date_range("2025-04-03", periods=3, freq="4h", tz="UTC")
    w = pd.Series([1.0, -1.0, 0.5], index=idx)
    hot = pd.Series([True, True, False], index=idx)
    w_before, hot_before = w.copy(), hot.copy()
    out = apply_vol_band(w, hot)
    assert out.index.equals(idx)
    assert out.dtype == float
    pd.testing.assert_series_equal(w, w_before)
    pd.testing.assert_series_equal(hot, hot_before)


def test_vol_band_empty():
    out = apply_vol_band(pd.Series([], dtype=float),
                         pd.Series([], dtype=bool))
    assert len(out) == 0
    assert out.dtype == float
