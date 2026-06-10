"""Tests for lab/gate.py — shipping gate (plan Task 1.9, PR-7, ADR-001).

Hand-constructed return series + crafted hook outputs. Never touches data/.

Clauses (ALL must hold):
  beats_flat  = ladder[10]["net_return_oos"] > 0
  beats_hodl  = sharpe(strat_oos_returns) > sharpe(hodl_oos_returns)
  null_pass   = sharpe(strat_oos_returns) > null_p95
  top5_pass   = top5_net_return > 0
  ladder_pass = ladder[20]["net_return_oos"] > 0

One crafted pass case, then one case per clause failing EXACTLY that clause.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.gate import GateVerdict, null_pass_rate, shipping_gate  # noqa: E402
from lab.metrics import sharpe  # noqa: E402

CLAUSES = {"beats_flat", "beats_hodl", "null_pass", "top5_pass", "ladder_pass"}

IDX = pd.date_range("2026-01-01 00:00", periods=4, freq="4h")


def base_inputs() -> dict:
    """Inputs that pass every clause."""
    strat = pd.Series([0.01, -0.005, 0.02, 0.01], index=IDX)  # sharpe > 0
    hodl = pd.Series([-0.01, 0.005, -0.02, -0.01], index=IDX)  # sharpe < 0
    return {
        "strat_oos_returns": strat,
        "hodl_oos_returns": hodl,
        "null_p95": sharpe(strat) - 1.0,   # strictly below strat sharpe
        "top5_net_return": 0.05,
        "ladder": {
            5: {"net_return_oos": 0.30, "sharpe_oos": 2.0},
            10: {"net_return_oos": 0.20, "sharpe_oos": 1.5},
            20: {"net_return_oos": 0.10, "sharpe_oos": 1.0},
        },
    }


def assert_single_clause_failure(verdict: GateVerdict, clause: str):
    assert isinstance(verdict, GateVerdict)
    assert verdict.passed is False
    assert set(verdict.reasons) == CLAUSES
    assert verdict.reasons[clause] is False
    for other in CLAUSES - {clause}:
        assert verdict.reasons[other] is True, other


# ---------------------------------------------------------------- pass case


def test_crafted_pass_case():
    inputs = base_inputs()
    verdict = shipping_gate(**inputs)

    assert isinstance(verdict, GateVerdict)
    assert verdict.passed is True
    assert set(verdict.reasons) == CLAUSES
    assert all(verdict.reasons.values())

    # stats expose the numbers the clauses compared (R3/report evidence)
    assert verdict.stats["strat_sharpe_oos"] == pytest.approx(
        sharpe(inputs["strat_oos_returns"]))
    assert verdict.stats["hodl_sharpe_oos"] == pytest.approx(
        sharpe(inputs["hodl_oos_returns"]))
    assert verdict.stats["null_p95"] == pytest.approx(inputs["null_p95"])
    assert verdict.stats["top5_net_return"] == pytest.approx(0.05)
    assert verdict.stats["net_return_oos_10bps"] == pytest.approx(0.20)
    assert verdict.stats["net_return_oos_20bps"] == pytest.approx(0.10)


# ------------------------------------------- one failure per clause, exactly


def test_fails_only_beats_flat():
    inputs = base_inputs()
    inputs["ladder"][10]["net_return_oos"] = -0.01
    assert_single_clause_failure(shipping_gate(**inputs), "beats_flat")


def test_fails_only_beats_hodl():
    inputs = base_inputs()
    # same dispersion as strat, mean shifted up -> strictly higher sharpe
    inputs["hodl_oos_returns"] = (
        inputs["strat_oos_returns"] + 0.01)
    assert_single_clause_failure(shipping_gate(**inputs), "beats_hodl")


def test_fails_only_null_pass():
    inputs = base_inputs()
    inputs["null_p95"] = sharpe(inputs["strat_oos_returns"]) + 1.0
    assert_single_clause_failure(shipping_gate(**inputs), "null_pass")


def test_fails_only_top5_pass():
    inputs = base_inputs()
    inputs["top5_net_return"] = -0.02
    assert_single_clause_failure(shipping_gate(**inputs), "top5_pass")


def test_fails_only_ladder_pass():
    inputs = base_inputs()
    inputs["ladder"][20]["net_return_oos"] = -0.05
    assert_single_clause_failure(shipping_gate(**inputs), "ladder_pass")


# ------------------------------------------------------------ null_pass_rate


def test_null_pass_rate_fraction_true():
    assert null_pass_rate([True, False, False, True]) == pytest.approx(0.5)
    assert null_pass_rate([True, True, True, False]) == pytest.approx(0.75)
    assert null_pass_rate([False]) == 0.0


def test_null_pass_rate_empty_is_zero():
    assert null_pass_rate([]) == 0.0
