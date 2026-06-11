"""W-gate — the 8-clause shipping gate of the widened search.

Registered spec: docs/plans/2026-06-10-widening-preregistration.md §7
(clause table, pinned fold-concentration formula, null-mechanics paragraph)
plus REPORT.md §6.2.3 (the active-sample bar carried into clause 7).
Evaluated per panel on pooled-OOS evidence at the 10 bps gate rung; ALL
eight clauses must hold. Canonical reasons keys:

  beats_flat / beats_hodl / null_pass / top5_pass / ladder_pass   (frozen)
  null_p99 / min_active_sample / topk_pass                        (added)

Clause reuse map (§7: "clause mechanics for 1-5 are byte-identical to
lab/gate.py / lab/hooks.py"):

  1-5  DELEGATED verbatim to the frozen lab.gate.shipping_gate. Its inputs
       are built with the frozen primitives exactly as the frozen sweep
       (lab/sweep._eval_variant) builds them: null_p95 =
       np.quantile(null_sharpes, 0.95) — the same call as
       lab/hooks.shuffle_null_pooled — and top5_net_return =
       lab.hooks.top_n_removal(trades, strat_oos_returns, oos_idx, 5).
       `strat_oos_returns` plays the frozen sweep's `pooled10` role (the
       pooled-OOS bar-return series), so top_n_removal's internal
       restriction is a no-op on it, as in the frozen path. The frozen
       verdict's reasons and stats are copied through unchanged.
  6    null_p99 = np.quantile(null_sharpes, 0.99) — the same numpy
       quantile call as the frozen p95, at 0.99 — compared against the
       SAME strat Sharpe number clause 3 compares (lab.metrics.sharpe via
       the frozen gate). Any sweep-level unguarded-Sharpe substitution for
       the null clauses stays at the caller, exactly as in the frozen
       sweep.
  7    min_active_sample (REPORT §6.2.3 + §7): OOS trades >= 60 AND
       nonzero-position OOS bars >= 200 AND nonzero trades in >= 60% of
       feature-covered folds (the caller passes the covered-fold list per
       §7's coverage definition; the 60% bound is evaluated as the exact
       integer cross-product 5*folds_with_trades >= 3*n_covered, so the
       boundary is float-round-off-free; zero covered folds passes
       vacuously — the trades>=60 bound fails first for any such Variant)
       AND the fold-concentration rule: with per-fold OOS compounded nets
       r_i and pooled R = prod(1+r_i) - 1, evaluated ONLY when R > 0,
       contribution_i = ln(1+r_i)/ln(1+R); FAIL iff max contribution > 0.5.
       Negative folds give negative contributions; a contribution may
       exceed 1 — that fails; the small-R discontinuity is accepted as
       conservative (§7, verbatim).
  8    topk_pass via the frozen top_n_removal mechanics with
       K = max(5, ceil(0.02 * OOS trade count)); ceil(0.02 * n) is
       computed exactly as -(-n // 50) (0.02 == 1/50), immune to float
       round-off at integer multiples.

"Trades" in clauses 7 and 8 are the trade objects of the frozen
segmentation — lab/engine.run_backtest's maximal sign-constant nonzero-w
runs (TRADE_COLUMNS) — restricted to OOS by entry_ts membership exactly as
the frozen lab/hooks.top_n_removal restricts them. `w` is the
engine-contract position series (already guarded/lagged by the caller,
NaN-free); it may cover the full panel — only bars in oos_idx are counted.
Folds whose OOS slice holds no strat returns contribute r_i = 0 and a zero
contribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lab.gate import shipping_gate
# Frozen primitives reused as-is (NOT re-implemented): _net_return and
# _restrict are the byte-identical compounding/restriction mechanics every
# frozen hook uses; importing them pins clause 7's r_i to those mechanics.
from lab.hooks import _net_return, _restrict, top_n_removal

# Clause-7 bounds (registration §7, REPORT §6.2.3)
MIN_OOS_TRADES = 60
MIN_ACTIVE_OOS_BARS = 200
FOLD_COVERAGE_NUM = 3        # >= 60% of covered folds, as the exact
FOLD_COVERAGE_DEN = 5        # integer ratio 3/5
MAX_FOLD_CONTRIBUTION = 0.5


@dataclass
class GateVerdictW:
    passed: bool
    reasons: dict[str, bool]   # per-clause outcome, canonical keys (8)
    stats: dict                # every number the clauses compared (R3)


def shipping_gate_w(strat_oos_returns: pd.Series,
                    hodl_oos_returns: pd.Series,
                    null_sharpes: np.ndarray,
                    ladder: dict[int, dict],
                    trades: pd.DataFrame,
                    w: pd.Series,
                    oos_idx: pd.Index,
                    fold_oos_idx: dict[str, pd.Index],
                    covered_folds: list[str]) -> GateVerdictW:
    """Evaluate the registration-§7 8-clause gate on pooled-OOS evidence.

    Args:
      strat_oos_returns: pooled-OOS bar-return series @ 10 bps (the frozen
        sweep's `pooled10`).
      hodl_oos_returns: pooled-OOS HODL benchmark bar returns @ 10 bps.
      null_sharpes: the D pooled episode-shuffle null Sharpe draws; q95 and
        q99 are taken here with the same numpy quantile call as the frozen
        hooks.
      ladder: {5, 10, 20} -> {"net_return_oos", "sharpe_oos"} (frozen
        cost-ladder shape).
      trades: pooled trades frame from the frozen segmentation
        (TRADE_COLUMNS).
      w: position series (engine contract); nonzero-position OOS bars are
        counted on its restriction to oos_idx.
      oos_idx: pooled OOS index.
      fold_oos_idx: per-fold OOS indices for ALL folds of the panel, in
        panel order (clause 7's r_i are computed per entry).
      covered_folds: names of the feature-covered folds (§7: a fold is
        covered iff its OOS holds >= 1 non-`na` bar for the Variant's
        taxonomy) — keys into fold_oos_idx.
    """
    null_sharpes = np.asarray(null_sharpes, dtype=float)
    null_p95 = float(np.quantile(null_sharpes, 0.95))
    null_p99 = float(np.quantile(null_sharpes, 0.99))

    # Clauses 1-5: frozen gate, frozen inputs (see module docstring).
    top5_net = top_n_removal(trades, strat_oos_returns, oos_idx, 5)
    base = shipping_gate(strat_oos_returns, hodl_oos_returns, null_p95,
                         top5_net, ladder)
    strat_sharpe = base.stats["strat_sharpe_oos"]

    # Clause 7 — min_active_sample. OOS restriction by entry_ts membership,
    # byte-identical to the frozen top_n_removal restriction.
    oos_trades = trades[trades["entry_ts"].isin(oos_idx)]
    n_trades = int(len(oos_trades))
    trades_ok = n_trades >= MIN_OOS_TRADES

    n_active_bars = int((_restrict(w, oos_idx) != 0.0).sum())
    bars_ok = n_active_bars >= MIN_ACTIVE_OOS_BARS

    n_covered = len(covered_folds)
    folds_with_trades = sum(
        bool(oos_trades["entry_ts"].isin(fold_oos_idx[name]).any())
        for name in covered_folds)
    folds_ok = (FOLD_COVERAGE_DEN * folds_with_trades
                >= FOLD_COVERAGE_NUM * n_covered)

    fold_nets = {name: _net_return(_restrict(strat_oos_returns, idx))
                 for name, idx in fold_oos_idx.items()}
    pooled_fold_net = float(
        np.prod([1.0 + r for r in fold_nets.values()]) - 1.0)
    concentration_evaluated = pooled_fold_net > 0.0
    if concentration_evaluated:
        ln_pooled = math.log1p(pooled_fold_net)
        fold_contributions = {name: math.log1p(r) / ln_pooled
                              for name, r in fold_nets.items()}
        max_contribution = max(fold_contributions.values())
        concentration_ok = max_contribution <= MAX_FOLD_CONTRIBUTION
    else:                       # R <= 0: sub-clause not evaluated (§7)
        fold_contributions = {}
        max_contribution = None
        concentration_ok = True

    min_active_sample = bool(trades_ok and bars_ok and folds_ok
                             and concentration_ok)

    # Clause 8 — topk_pass: frozen top_n_removal mechanics at K.
    topk_k = max(5, -(-n_trades // 50))     # max(5, ceil(0.02 * n)), exact
    topk_net = top_n_removal(trades, strat_oos_returns, oos_idx, topk_k)

    reasons = dict(base.reasons)            # frozen 5, canonical order
    reasons["null_p99"] = bool(strat_sharpe > null_p99)
    reasons["min_active_sample"] = min_active_sample
    reasons["topk_pass"] = bool(topk_net > 0.0)

    stats = dict(base.stats)                # frozen six, unchanged
    stats.update({
        "null_p99": null_p99,
        "oos_trade_count": n_trades,
        "nonzero_oos_bars": n_active_bars,
        "covered_fold_count": int(n_covered),
        "folds_with_trades": int(folds_with_trades),
        "fold_nets": {k: float(v) for k, v in fold_nets.items()},
        "pooled_fold_net": pooled_fold_net,
        "fold_contributions": {k: float(v)
                               for k, v in fold_contributions.items()},
        "max_fold_contribution": (None if max_contribution is None
                                  else float(max_contribution)),
        "concentration_evaluated": bool(concentration_evaluated),
        "topk_k": int(topk_k),
        "topk_net_return": float(topk_net),
        "min_active_sample_parts": {
            "trades_ok": bool(trades_ok),
            "bars_ok": bool(bars_ok),
            "folds_ok": bool(folds_ok),
            "concentration_ok": bool(concentration_ok),
        },
    })
    return GateVerdictW(passed=all(reasons.values()), reasons=reasons,
                        stats=stats)
