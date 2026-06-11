"""Tests for lab/gate_w.py — the 8-clause W-gate (widening registration §7).

Hand-constructed pooled-OOS evidence. Never touches data/. The frozen
clause-1-5 mechanics are pinned by AGREEMENT with lab.gate.shipping_gate on
identical inputs; the three added clauses are pinned here
(docs/plans/2026-06-10-widening-preregistration.md §7):

  null_p99          sharpe(strat) > np.quantile(null_sharpes, 0.99)
                    (the same numpy quantile call as the frozen p95)
  min_active_sample OOS trades >= 60  AND  nonzero-position OOS bars >= 200
                    AND nonzero trades in >= 60% of feature-covered folds
                    AND fold-concentration: per-fold compounded nets r_i,
                    pooled R = prod(1+r_i) - 1, evaluated only when R > 0,
                    contribution_i = ln(1+r_i)/ln(1+R), FAIL iff max > 0.5
  topk_pass         net after removing the K best OOS trades > 0,
                    K = max(5, ceil(0.02 * OOS trade count))

Registered implication structure (so NOT testable as single-clause
failures): q99 >= q95 means null_pass can never fail alone in the 8-clause
gate, and removing the top K >= 5 trades removes at least the top-5 gain,
so top5_pass can never fail alone either. Both are pinned below as exact
failure SETS instead.
"""

import dataclasses
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.gate import GateVerdict, shipping_gate  # noqa: E402
from lab.gate_w import GateVerdictW, shipping_gate_w  # noqa: E402
from lab.hooks import top_n_removal  # noqa: E402
from lab.metrics import sharpe  # noqa: E402

CLAUSES_W = {"beats_flat", "beats_hodl", "null_pass", "top5_pass",
             "ladder_pass", "null_p99", "min_active_sample", "topk_pass"}
FROZEN_CLAUSES = {"beats_flat", "beats_hodl", "null_pass", "top5_pass",
                  "ladder_pass"}

# 600 bars: 100 pre-OOS, then 5 folds x 100 OOS bars each.
IDX = pd.date_range("2026-01-01 00:00", periods=600, freq="4h")
OOS_IDX = IDX[100:]
FOLDS = {f"F0{i + 1}": IDX[100 + 100 * i: 200 + 100 * i] for i in range(5)}

# Five equal fold nets compounding to pooled R = +30%.
FOLD_NET_BASE = 1.3 ** 0.2 - 1.0


def make_trades(entries, pnl) -> pd.DataFrame:
    """Duck-typed frozen trades frame (engine TRADE_COLUMNS schema)."""
    entries = list(entries)
    if np.isscalar(pnl):
        pnl = [pnl] * len(entries)
    return pd.DataFrame({
        "entry_ts": entries,
        "exit_ts": entries,
        "w": 1.0,
        "pnl_pct": list(pnl),
    })


def spread_entries(n_per_fold) -> list:
    """First n_per_fold[i] OOS bars of each fold as trade entry stamps."""
    out = []
    for n, idx in zip(n_per_fold, FOLDS.values()):
        out.extend(idx[:n])
    return out


def base_inputs() -> dict:
    """Inputs that pass every one of the 8 clauses."""
    # One nonzero bar per fold -> fold nets all FOLD_NET_BASE, R ~ +30%,
    # contributions ~0.2 each; pooled sharpe strongly positive.
    strat = pd.Series(0.0, index=OOS_IDX)
    for idx in FOLDS.values():
        strat.loc[idx[0]] = FOLD_NET_BASE
    hodl = pd.Series(np.tile([-0.001, -0.002], 250), index=OOS_IDX)
    # q95 ~0.90, q99 ~0.98 -- both far below the strat sharpe (~4.7).
    null_sharpes = np.linspace(-1.0, 1.0, 200)
    # 80 OOS trades, 16 per fold, small positive pnl.
    trades = make_trades(spread_entries([16] * 5), 0.002)
    # 100 pre-OOS nonzero bars (must NOT count) + 300 OOS nonzero bars.
    w = pd.Series(0.0, index=IDX)
    w.iloc[:400] = 1.0
    ladder = {
        5: {"net_return_oos": 0.35, "sharpe_oos": 2.0},
        10: {"net_return_oos": 0.30, "sharpe_oos": 1.5},
        20: {"net_return_oos": 0.10, "sharpe_oos": 1.0},
    }
    return {
        "strat_oos_returns": strat,
        "hodl_oos_returns": hodl,
        "null_sharpes": null_sharpes,
        "ladder": ladder,
        "trades": trades,
        "w": w,
        "oos_idx": OOS_IDX,
        "fold_oos_idx": dict(FOLDS),
        "covered_folds": list(FOLDS),
    }


def assert_single_clause_failure(verdict: GateVerdictW, clause: str):
    assert isinstance(verdict, GateVerdictW)
    assert verdict.passed is False
    assert set(verdict.reasons) == CLAUSES_W
    assert verdict.reasons[clause] is False
    for other in CLAUSES_W - {clause}:
        assert verdict.reasons[other] is True, other


def assert_exact_failures(verdict: GateVerdictW, failing: set):
    assert verdict.passed is False
    assert set(verdict.reasons) == CLAUSES_W
    assert {k for k, ok in verdict.reasons.items() if not ok} == failing


# ---------------------------------------------------------------- pass case


def test_crafted_pass_case_all_eight_clauses():
    verdict = shipping_gate_w(**base_inputs())
    assert isinstance(verdict, GateVerdictW)
    assert verdict.passed is True
    assert set(verdict.reasons) == CLAUSES_W
    assert all(verdict.reasons.values())


def test_gate_verdict_w_mirrors_gate_verdict_fields():
    assert [f.name for f in dataclasses.fields(GateVerdictW)] == \
        [f.name for f in dataclasses.fields(GateVerdict)]


def test_stats_carry_every_compared_number():
    inputs = base_inputs()
    verdict = shipping_gate_w(**inputs)
    s = verdict.stats

    # frozen six (clauses 1-5), passed through unchanged
    assert s["strat_sharpe_oos"] == pytest.approx(
        sharpe(inputs["strat_oos_returns"]))
    assert s["hodl_sharpe_oos"] == pytest.approx(
        sharpe(inputs["hodl_oos_returns"]))
    assert s["null_p95"] == pytest.approx(
        float(np.quantile(inputs["null_sharpes"], 0.95)))
    assert s["net_return_oos_10bps"] == pytest.approx(0.30)
    assert s["net_return_oos_20bps"] == pytest.approx(0.10)

    # clause 6: the same numpy quantile call at 0.99
    assert s["null_p99"] == pytest.approx(
        float(np.quantile(inputs["null_sharpes"], 0.99)))

    # clause 7 numbers
    assert s["oos_trade_count"] == 80
    assert s["nonzero_oos_bars"] == 300          # pre-OOS bars excluded
    assert s["covered_fold_count"] == 5
    assert s["folds_with_trades"] == 5
    assert s["pooled_fold_net"] == pytest.approx(0.30)
    assert set(s["fold_nets"]) == set(FOLDS)
    assert set(s["fold_contributions"]) == set(FOLDS)
    for name in FOLDS:
        assert s["fold_nets"][name] == pytest.approx(FOLD_NET_BASE)
        assert s["fold_contributions"][name] == pytest.approx(0.2)
    assert s["max_fold_contribution"] == pytest.approx(0.2)
    assert s["concentration_evaluated"] is True
    assert s["min_active_sample_parts"] == {
        "trades_ok": True, "bars_ok": True,
        "folds_ok": True, "concentration_ok": True}

    # clause 8 numbers: 80 trades -> K = max(5, ceil(1.6)) = 5, so the
    # top-K computation is the top-5 computation
    assert s["topk_k"] == 5
    assert s["topk_net_return"] == pytest.approx(s["top5_net_return"])
    assert s["top5_net_return"] > 0


# ----------------------------------- clauses 1-5 byte-identical to frozen


def test_clauses_1_to_5_agree_with_frozen_gate():
    """Frozen reasons AND frozen stats match lab.gate.shipping_gate when its
    inputs are built with the frozen primitives on identical evidence."""
    flat_fail = base_inputs()
    flat_fail["ladder"][10]["net_return_oos"] = -0.01
    hodl_fail = base_inputs()
    hodl_fail["hodl_oos_returns"] = hodl_fail["strat_oos_returns"] + 0.01
    null_fail = base_inputs()
    null_fail["null_sharpes"] = np.full(200, 10.0)

    for inputs in (base_inputs(), flat_fail, hodl_fail, null_fail):
        w_verdict = shipping_gate_w(**inputs)
        null_p95 = float(np.quantile(inputs["null_sharpes"], 0.95))
        top5 = top_n_removal(inputs["trades"], inputs["strat_oos_returns"],
                             inputs["oos_idx"], 5)
        frozen = shipping_gate(inputs["strat_oos_returns"],
                               inputs["hodl_oos_returns"], null_p95, top5,
                               inputs["ladder"])
        for clause in FROZEN_CLAUSES:
            assert w_verdict.reasons[clause] == frozen.reasons[clause], clause
        for key, value in frozen.stats.items():
            assert w_verdict.stats[key] == value, key


# ------------------------------------------- one failure per clause, exactly


def test_fails_only_beats_flat():
    inputs = base_inputs()
    inputs["ladder"][10]["net_return_oos"] = -0.01
    assert_single_clause_failure(shipping_gate_w(**inputs), "beats_flat")


def test_fails_only_beats_hodl():
    inputs = base_inputs()
    # same dispersion as strat, mean shifted up -> strictly higher sharpe
    inputs["hodl_oos_returns"] = inputs["strat_oos_returns"] + 0.01
    assert_single_clause_failure(shipping_gate_w(**inputs), "beats_hodl")


def test_fails_only_ladder_pass():
    inputs = base_inputs()
    inputs["ladder"][20]["net_return_oos"] = -0.05
    assert_single_clause_failure(shipping_gate_w(**inputs), "ladder_pass")


def test_fails_only_null_p99():
    # q95 below the strat sharpe, q99 above it: 195 draws at 0, 5 at 10
    # -> p95 = 0.0 (clause 3 passes), p99 = 10.0 (clause 6 fails).
    inputs = base_inputs()
    inputs["null_sharpes"] = np.array([0.0] * 195 + [10.0] * 5)
    verdict = shipping_gate_w(**inputs)
    assert_single_clause_failure(verdict, "null_p99")
    assert verdict.stats["null_p95"] == pytest.approx(0.0)
    assert verdict.stats["null_p99"] == pytest.approx(10.0)


def test_sharpe_below_p95_fails_both_null_clauses():
    # q99 >= q95 always, so failing clause 3 implies failing clause 6:
    # null_pass can never fail alone in the 8-clause gate.
    inputs = base_inputs()
    inputs["null_sharpes"] = np.full(200, 10.0)
    assert_exact_failures(shipping_gate_w(**inputs),
                          {"null_pass", "null_p99"})


def test_top5_flip_fails_both_top_clauses():
    # Removing the top K >= 5 trades removes at least the top-5 gain, so
    # top5_pass can never fail alone. Five 10% trades vs +30% total: top-5
    # removal flips negative -> with K = 5 (80 trades) topk fails too.
    inputs = base_inputs()
    inputs["trades"]["pnl_pct"] = [0.10] * 5 + [0.002] * 75
    assert_exact_failures(shipping_gate_w(**inputs),
                          {"top5_pass", "topk_pass"})


def test_fails_only_topk_pass():
    # 300 OOS trades -> K = max(5, ceil(6.0)) = 6. Total +30%; top five at
    # 5% leave +1.86% (top5 passes), the sixth at 4% drags the K-removal to
    # -2.06% (topk fails). Every other clause still passes.
    inputs = base_inputs()
    inputs["trades"] = make_trades(
        spread_entries([60] * 5), [0.05] * 5 + [0.04] + [0.0] * 294)
    verdict = shipping_gate_w(**inputs)
    assert_single_clause_failure(verdict, "topk_pass")
    assert verdict.stats["topk_k"] == 6
    assert verdict.stats["oos_trade_count"] == 300
    assert verdict.stats["top5_net_return"] > 0
    assert verdict.stats["topk_net_return"] < 0


# --------------------------------------- clause 7: min_active_sample bounds


def test_exactly_60_oos_trades_passes():
    inputs = base_inputs()
    inputs["trades"] = make_trades(spread_entries([12] * 5), 0.002)
    verdict = shipping_gate_w(**inputs)
    assert verdict.passed is True
    assert verdict.stats["oos_trade_count"] == 60


def test_59_oos_trades_fails_min_active_sample_only():
    inputs = base_inputs()
    inputs["trades"] = make_trades(spread_entries([12, 12, 12, 12, 11]),
                                   0.002)
    verdict = shipping_gate_w(**inputs)
    assert_single_clause_failure(verdict, "min_active_sample")
    assert verdict.stats["oos_trade_count"] == 59
    assert verdict.stats["min_active_sample_parts"]["trades_ok"] is False
    assert verdict.stats["min_active_sample_parts"]["bars_ok"] is True
    assert verdict.stats["min_active_sample_parts"]["folds_ok"] is True


def test_exactly_200_nonzero_oos_bars_passes():
    inputs = base_inputs()
    w = pd.Series(0.0, index=IDX)
    w.iloc[100:300] = 1.0                       # exactly 200 OOS nonzero
    inputs["w"] = w
    verdict = shipping_gate_w(**inputs)
    assert verdict.passed is True
    assert verdict.stats["nonzero_oos_bars"] == 200


def test_199_nonzero_oos_bars_fails_min_active_sample_only():
    inputs = base_inputs()
    w = pd.Series(0.0, index=IDX)
    w.iloc[100:299] = 1.0
    # pre-OOS nonzero bars must not rescue the count
    w.iloc[:100] = 1.0
    inputs["w"] = w
    verdict = shipping_gate_w(**inputs)
    assert_single_clause_failure(verdict, "min_active_sample")
    assert verdict.stats["nonzero_oos_bars"] == 199
    assert verdict.stats["min_active_sample_parts"]["bars_ok"] is False


def test_trades_in_exactly_60pct_of_covered_folds_passes():
    # 3 of 5 covered folds hold trades: 3/5 = 60% exactly -> >= 60% passes.
    inputs = base_inputs()
    inputs["trades"] = make_trades(spread_entries([27, 27, 26, 0, 0]), 0.002)
    verdict = shipping_gate_w(**inputs)
    assert verdict.passed is True
    assert verdict.stats["folds_with_trades"] == 3


def test_trades_in_40pct_of_covered_folds_fails_min_active_sample_only():
    inputs = base_inputs()
    inputs["trades"] = make_trades(spread_entries([40, 40, 0, 0, 0]), 0.002)
    verdict = shipping_gate_w(**inputs)
    assert_single_clause_failure(verdict, "min_active_sample")
    assert verdict.stats["folds_with_trades"] == 2
    assert verdict.stats["min_active_sample_parts"]["folds_ok"] is False


# ------------------------------- clause 7: fold-concentration (§7, pinned)


def test_fold_concentration_worked_example():
    """The §7 worked example: fold nets {+60%, -20%, +10%} (others 0).

    R = 1.6 * 0.8 * 1.1 - 1 = 0.408. Registered ln-reading:
      contribution_1 = ln(1.6)/ln(1.408) ~ +1.3736  (> 1, and that FAILS)
      contribution_2 = ln(0.8)/ln(1.408) ~ -0.6521  (negative fold)
      contribution_3 = ln(1.1)/ln(1.408) ~ +0.2786
    The naive arithmetic-share reading of fold 1 would be 0.6/0.5 = 1.2 —
    the readings disagree, and the ln values are the registered ones.
    """
    inputs = base_inputs()
    strat = pd.Series(0.0, index=OOS_IDX)
    strat.loc[FOLDS["F01"][0]] = 0.6
    strat.loc[FOLDS["F02"][0]] = -0.2
    strat.loc[FOLDS["F03"][0]] = 0.1
    inputs["strat_oos_returns"] = strat

    verdict = shipping_gate_w(**inputs)
    assert_single_clause_failure(verdict, "min_active_sample")
    s = verdict.stats
    assert s["min_active_sample_parts"]["concentration_ok"] is False
    assert s["min_active_sample_parts"]["trades_ok"] is True
    assert s["min_active_sample_parts"]["bars_ok"] is True
    assert s["min_active_sample_parts"]["folds_ok"] is True

    assert s["concentration_evaluated"] is True
    assert s["pooled_fold_net"] == pytest.approx(0.408)
    ln_r = math.log(1.408)
    assert s["fold_contributions"]["F01"] == pytest.approx(
        math.log(1.6) / ln_r, rel=1e-9)
    assert s["fold_contributions"]["F02"] == pytest.approx(
        math.log(0.8) / ln_r, rel=1e-9)
    assert s["fold_contributions"]["F03"] == pytest.approx(
        math.log(1.1) / ln_r, rel=1e-9)
    assert s["fold_contributions"]["F04"] == pytest.approx(0.0)
    assert s["fold_contributions"]["F05"] == pytest.approx(0.0)
    # disagreement with the arithmetic-share reading is the point
    assert s["fold_contributions"]["F01"] != pytest.approx(0.6 / 0.5)
    # a contribution may exceed 1 — that fails
    assert s["fold_contributions"]["F01"] > 1.0
    assert s["max_fold_contribution"] == pytest.approx(
        math.log(1.6) / ln_r, rel=1e-9)
    assert s["max_fold_contribution"] > 0.5


def test_concentration_skipped_when_pooled_net_negative():
    # fold nets {-50%, +40%}: R = 0.5 * 1.4 - 1 = -0.3 <= 0 -> the
    # concentration sub-clause is NOT evaluated; min_active_sample passes
    # even though one fold dominates (other clauses fail on the loss).
    inputs = base_inputs()
    strat = pd.Series(0.0, index=OOS_IDX)
    strat.loc[FOLDS["F01"][0]] = -0.5
    strat.loc[FOLDS["F02"][0]] = 0.4
    inputs["strat_oos_returns"] = strat
    verdict = shipping_gate_w(**inputs)
    assert verdict.reasons["min_active_sample"] is True
    assert verdict.stats["concentration_evaluated"] is False
    assert verdict.stats["fold_contributions"] == {}
    assert verdict.stats["max_fold_contribution"] is None
    assert verdict.stats["pooled_fold_net"] == pytest.approx(-0.3)
    assert verdict.stats["min_active_sample_parts"]["concentration_ok"] \
        is True


def test_concentration_skipped_when_pooled_net_exactly_zero():
    # fold nets {+100%, -50%}: R = 2.0 * 0.5 - 1 = 0.0 exactly (both nets
    # are exact binary floats) -> "evaluated only when R > 0" skips it.
    inputs = base_inputs()
    strat = pd.Series(0.0, index=OOS_IDX)
    strat.loc[FOLDS["F01"][0]] = 1.0
    strat.loc[FOLDS["F02"][0]] = -0.5
    inputs["strat_oos_returns"] = strat
    verdict = shipping_gate_w(**inputs)
    assert verdict.stats["pooled_fold_net"] == 0.0
    assert verdict.stats["concentration_evaluated"] is False
    assert verdict.reasons["min_active_sample"] is True


# ----------------------------------------------- clause 8: the K formula


def test_k_formula_250_oos_trades_gives_5_and_ignores_pre_oos_trades():
    inputs = base_inputs()
    trades = make_trades(spread_entries([50] * 5), 0.0)
    # three pre-OOS trades with huge pnl: excluded from the count AND from
    # the removal pool (else top-5 removal would flip the verdict).
    pre = make_trades([IDX[0], IDX[1], IDX[2]], 5.0)
    inputs["trades"] = pd.concat([pre, trades], ignore_index=True)
    verdict = shipping_gate_w(**inputs)
    assert verdict.passed is True
    assert verdict.stats["oos_trade_count"] == 250
    assert verdict.stats["topk_k"] == 5          # max(5, ceil(5.0)) = 5


def test_k_formula_251_oos_trades_gives_6():
    inputs = base_inputs()
    inputs["trades"] = make_trades(spread_entries([51, 50, 50, 50, 50]), 0.0)
    verdict = shipping_gate_w(**inputs)
    assert verdict.stats["oos_trade_count"] == 251
    assert verdict.stats["topk_k"] == 6          # ceil(5.02) = 6


def test_k_formula_400_oos_trades_gives_8():
    inputs = base_inputs()
    inputs["trades"] = make_trades(spread_entries([80] * 5), 0.0)
    verdict = shipping_gate_w(**inputs)
    assert verdict.passed is True
    assert verdict.stats["oos_trade_count"] == 400
    assert verdict.stats["topk_k"] == 8          # max(5, ceil(8.0)) = 8
