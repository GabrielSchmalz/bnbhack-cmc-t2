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


# ----------------- lane W-A differential pins (registered k = 6, additive)
#
# Lane W-A (docs/report/adversarial/w_lane1_reproduction.md §1) resolved the
# §3 cap-bar re-entry corner by black-box differential testing of five
# text-consistent time-stop machines against the artifact
# (~/.cache/wlane1/ts_hypo.py). The artifact matches ONLY the immediate
# cap-bar re-entry machine (M5, implemented here); the four rejected
# readings are M1 (stop first, re-entry only at a LATER transition),
# M2 (run counter resets on any mid-run label transition), M2b (counter
# resets on a sign flip), M3 (hold k+1 bars). The lane asked for the
# determination to be test-pinned; these tests encode the discriminating
# scenarios at the registered rung k = 6 on synthetic labels.


def _wa_machine(w, lagged, action_map, k, mode):
    """Port of ~/.cache/wlane1/ts_hypo.py::machine to the post-lag frame.

    Reference implementation of the five candidate §3 readings, kept
    independent of lab/rules_w.py internals. `mode` in {M1, M2, M2b, M3,
    M5}; M5 is the implemented (artifact-matching) reading.
    """
    wv = w.astype(float).to_numpy()
    labs = lagged.loc[w.index].to_numpy()

    def same(a, b):
        a_na, b_na = pd.isna(a), pd.isna(b)
        if a_na or b_na:
            return bool(a_na and b_na)
        return bool(a == b)

    out = np.zeros(len(wv))
    run_start, stopped, held = -1, False, 0
    for t in range(len(wv)):
        at = wv[t]
        trans = t > 0 and not same(labs[t], labs[t - 1])
        if stopped:
            if trans and at != 0.0:
                stopped = False
                run_start = t
                held = 0
            else:
                continue
        if at == 0.0:
            run_start = -1
            held = 0
            continue
        if run_start < 0:
            run_start = t
            held = 0
        if mode == "M2" and trans and run_start != t:
            held = 0                  # counter resets on any transition
        if mode == "M2b" and run_start != t and t > 0 and wv[t - 1] != 0 \
                and np.sign(at) != np.sign(wv[t - 1]):
            held = 0                  # counter resets on sign flip
        limit = k + 1 if mode == "M3" else k
        if held >= limit:
            if mode == "M5" and trans:
                # cap bar coincides with a transition into a nonzero-action
                # label: capped run ends at the k-th bar's close, a NEW run
                # re-enters immediately at this bar
                out[t] = at
                run_start = t
                held = 1
            else:
                out[t] = 0.0
                stopped = True
                run_start = -1
                held = 0
        else:
            out[t] = at
            held += 1
    return pd.Series(out, index=w.index)


def test_cap_bar_transition_immediate_reentry_at_registered_k6():
    # Determination (1) at the registered rung: the lagged label transitions
    # A -> B exactly on the bar after the k-th run bar (k = 6). Implemented
    # reading: re-entry is immediate AT that bar (exit and re-entry fills
    # coincide, no forced flat bar) and the new run carries a fresh k-bar
    # budget (stops again 6 bars later).
    w, lagged = _post_lag(["A"] * 6 + ["B"] * 9)
    out = apply_time_stop(w, lagged, ACTION_MAP, k=6)
    expected = [0.0] + [1.0] * 6 + [-1.0] * 6 + [0.0, 0.0]
    assert out.tolist() == expected
    assert out.tolist() == _wa_machine(w, lagged, ACTION_MAP, 6,
                                       "M5").tolist()
    # The rejected stricter reading (M1: stop first, re-entry only at a
    # LATER transition) consumes the cap-bar transition while stopped and
    # never re-enters on this series — it forces flat from bar 7 onward.
    m1 = _wa_machine(w, lagged, ACTION_MAP, 6, "M1")
    assert m1.tolist() == [0.0] + [1.0] * 6 + [0.0] * 8
    assert [t for t in range(len(w)) if out.iloc[t] != m1.iloc[t]] == \
        [7, 8, 9, 10, 11, 12]


def test_k6_differential_rejects_m1_m2_m2b_m3_and_matches_m5():
    # One 23-bar sequence discriminating the implemented machine from every
    # rejected candidate (lane W-A §1: nz 1503/1583/1515/1608 vs artifact
    # 1541 on the real panel; here pinned on synthetic labels): a sign-flip
    # mid-run transition (bar 4), same-label persistence past the cap (bars
    # 7-9), a zero-action transition while stopped (bar 10), a qualifying
    # re-entry transition (bar 11), and a cap-bar transition (bar 17).
    raw = (["A"] * 3 + ["B"] * 6 + ["Z"] + ["A"] * 6 + ["B"] * 7)
    w, lagged = _post_lag(raw)
    assert w.tolist() == ([0.0] + [1.0] * 3 + [-1.0] * 6 + [0.0]
                          + [1.0] * 6 + [-1.0] * 6)
    out = apply_time_stop(w, lagged, ACTION_MAP, k=6)
    expected = ([0.0] + [1.0] * 3 + [-1.0] * 3 + [0.0] * 4
                + [1.0] * 6 + [-1.0] * 6)
    assert out.tolist() == expected
    # implemented == M5, bar for bar
    assert out.tolist() == _wa_machine(w, lagged, ACTION_MAP, 6,
                                       "M5").tolist()
    # each rejected machine differs at exactly its discriminating bars
    rejected = {
        "M1": [17, 18, 19, 20, 21, 22],   # no cap-bar re-entry at bar 17
        "M2": [7, 8, 9],                  # bar-4 transition resets counter
        "M2b": [7, 8, 9],                 # bar-4 sign flip resets counter
        "M3": [7, 18, 19, 20, 21, 22],    # holds k+1 bars, shifted stops
    }
    for mode, diff_bars in rejected.items():
        ref = _wa_machine(w, lagged, ACTION_MAP, 6, mode)
        got = [t for t in range(len(w)) if out.iloc[t] != ref.iloc[t]]
        assert got == diff_bars, mode
