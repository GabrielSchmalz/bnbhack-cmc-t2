"""Shipping gate (plan Task 1.9, PR-7, ADR-001) + R3 disclosure helper.

The gate is a binary predicate over pooled-OOS evidence; ALL clauses must
hold (reasons keys are canonical):

  beats_flat  = ladder[10]["net_return_oos"] > 0   (net of 10 bps RT)
  beats_hodl  = sharpe(strat_oos_returns) > sharpe(hodl_oos_returns)
  null_pass   = sharpe(strat_oos_returns) > null_p95 (episode-shuffle null)
  top5_pass   = top5_net_return > 0                 (after top-5 removal)
  ladder_pass = ladder[20]["net_return_oos"] > 0    (still beats flat @20bps)

Inputs come from lab.hooks (shuffle_null, top_n_removal, cost_ladder) and the
pooled-OOS bar-return series of the variant and the HODL benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lab.metrics import sharpe


@dataclass
class GateVerdict:
    passed: bool
    reasons: dict[str, bool]   # per-clause outcome, canonical keys
    stats: dict                # the numbers the clauses compared (R3/report)


def shipping_gate(strat_oos_returns: pd.Series, hodl_oos_returns: pd.Series,
                  null_p95: float, top5_net_return: float,
                  ladder: dict[int, dict]) -> GateVerdict:
    """Evaluate the PR-7 shipping gate on pooled-OOS evidence."""
    strat_sharpe = sharpe(strat_oos_returns)
    hodl_sharpe = sharpe(hodl_oos_returns)
    net_10 = float(ladder[10]["net_return_oos"])
    net_20 = float(ladder[20]["net_return_oos"])

    reasons = {
        "beats_flat": bool(net_10 > 0.0),
        "beats_hodl": bool(strat_sharpe > hodl_sharpe),
        "null_pass": bool(strat_sharpe > null_p95),
        "top5_pass": bool(top5_net_return > 0.0),
        "ladder_pass": bool(net_20 > 0.0),
    }
    stats = {
        "strat_sharpe_oos": strat_sharpe,
        "hodl_sharpe_oos": hodl_sharpe,
        "null_p95": float(null_p95),
        "top5_net_return": float(top5_net_return),
        "net_return_oos_10bps": net_10,
        "net_return_oos_20bps": net_20,
    }
    return GateVerdict(passed=all(reasons.values()), reasons=reasons,
                       stats=stats)


def null_pass_rate(verdict_fn_results: list[bool]) -> float:
    """Fraction of True outcomes — R3 expected gate-pass-rate disclosure.

    Empty input -> 0.0 (no draws, no passes).
    """
    if not verdict_fn_results:
        return 0.0
    return sum(bool(v) for v in verdict_fn_results) / len(verdict_fn_results)
