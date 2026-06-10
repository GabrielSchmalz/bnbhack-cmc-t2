"""Honesty hooks (plan Task 1.8, PR-7): shuffle null, top-N removal, ladder.

Generic over a strategy function so Phase-2 rules plug in later:
    strategy_fn: Callable[[pd.Series labels], pd.Series w]
The returned w must already satisfy the engine contract (lagged by the
caller's rule, index a contiguous run of bars.index).

Hooks:
  - shuffle_null: episode-block shuffle — segment labels into episodes
    (classifier.episodes), permute the EPISODE ORDER with numpy
    default_rng(seed), reconstruct a label series with the same lengths on
    the same index, w = strategy_fn(shuffled), backtest, Sharpe of
    bar_returns restricted to oos_idx. Returns {"p95", "null_sharpes"}.
  - top_n_removal: restrict trades to entry_ts in oos_idx; remove the n
    largest POSITIVE pnl_pct;
        total        = prod(1 + bar_returns[oos_idx]) - 1
        removed_gain = prod(1 + pnl_pct of removed trades) - 1
        result       = (1 + total) / (1 + removed_gain) - 1
  - cost_ladder: backtest w = strategy_fn(labels) at {5, 10, 20} bps RT;
    per cost: {"net_return_oos", "sharpe_oos"} on oos_idx.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from lab.classifier import episodes
from lab.engine import run_backtest
from lab.metrics import sharpe

COST_LADDER_BPS = (5, 10, 20)

StrategyFn = Callable[[pd.Series], pd.Series]


def _restrict(series: pd.Series, idx: pd.Index) -> pd.Series:
    """series restricted to timestamps present in both series.index and idx."""
    return series.loc[series.index.intersection(idx)]


def _net_return(bar_returns: pd.Series) -> float:
    return float((1.0 + bar_returns).prod() - 1.0)


def shuffle_null(strategy_fn: StrategyFn, labels: pd.Series,
                 bars: pd.DataFrame, funding: pd.Series, cost_bps_rt: float,
                 oos_idx: pd.Index, n: int = 1000, seed: int = 17) -> dict:
    """Episode-block shuffle null distribution of OOS Sharpe (PR-7)."""
    eps = episodes(labels)
    ep_labels = eps["label"].to_numpy(dtype=object)
    ep_lengths = eps["n_bars"].to_numpy()
    rng = np.random.default_rng(seed)

    null_sharpes = np.empty(n, dtype=float)
    for i in range(n):
        order = rng.permutation(len(eps))
        values = np.concatenate(
            [np.repeat(ep_labels[j], ep_lengths[j]) for j in order])
        shuffled = pd.Series(values, index=labels.index)
        w = strategy_fn(shuffled)
        res = run_backtest(bars, w, funding, cost_bps_rt)
        null_sharpes[i] = sharpe(_restrict(res.bar_returns, oos_idx))

    return {"p95": float(np.quantile(null_sharpes, 0.95)),
            "null_sharpes": null_sharpes}


def top_n_removal(trades: pd.DataFrame, bar_returns: pd.Series,
                  oos_idx: pd.Index, n: int = 5) -> float:
    """Pooled-OOS net return after removing the n best OOS trades."""
    total = _net_return(_restrict(bar_returns, oos_idx))
    oos_trades = trades[trades["entry_ts"].isin(oos_idx)]
    pnl = oos_trades["pnl_pct"]
    removed = pnl[pnl > 0].nlargest(n)
    removed_gain = float((1.0 + removed).prod() - 1.0)
    return (1.0 + total) / (1.0 + removed_gain) - 1.0


def cost_ladder(strategy_fn: StrategyFn, labels: pd.Series,
                bars: pd.DataFrame, funding: pd.Series,
                oos_idx: pd.Index) -> dict[int, dict]:
    """OOS gate metrics at each cost rung {5, 10, 20} bps RT (PR-7)."""
    w = strategy_fn(labels)
    out: dict[int, dict] = {}
    for c in COST_LADDER_BPS:
        res = run_backtest(bars, w, funding, float(c))
        r_oos = _restrict(res.bar_returns, oos_idx)
        out[c] = {"net_return_oos": _net_return(r_oos),
                  "sharpe_oos": sharpe(r_oos)}
    return out


# --------------------------------------------------------------------------
# Task 2.4 additions (lab/sweep.py pooled null) — pre-registered adaptations.
# The original hooks above are untouched.


def episode_shuffles(labels: pd.Series, n: int, seed: int) -> list[pd.Series]:
    """Pre-generate n episode-order-permuted label series (Task 2.4).

    Identical per-draw mechanics to shuffle_null: episodes via
    classifier.episodes, episode ORDER permuted with numpy
    default_rng(seed), episode lengths preserved, reassembled on
    labels.index. Draws come sequentially from one rng, so
    episode_shuffles(labels, m, seed) is a PREFIX of
    episode_shuffles(labels, n, seed) for m <= n — the sweep's R3 step
    relies on this to regenerate the first 200 of 1000 common draws.
    """
    eps = episodes(labels)
    ep_labels = eps["label"].to_numpy(dtype=object)
    ep_lengths = eps["n_bars"].to_numpy()
    rng = np.random.default_rng(seed)
    out: list[pd.Series] = []
    for _ in range(n):
        order = rng.permutation(len(eps))
        values = np.concatenate(
            [np.repeat(ep_labels[j], ep_lengths[j]) for j in order])
        out.append(pd.Series(values, index=labels.index))
    return out


def shuffle_null_pooled(strategy_fn: StrategyFn,
                        fold_shuffles: list[tuple[list[pd.Series], pd.Index]],
                        bars: pd.DataFrame, funding: pd.Series,
                        cost_bps_rt: float) -> dict:
    """Pooled common-random-shuffles null over walk-forward folds (Task 2.4).

    Pre-registered adaptation of shuffle_null to the fold pipeline:
    `fold_shuffles` holds, per fold, (the episode_shuffles output for that
    fold's label series — the COMMON draws shared across a taxonomy's
    variants — and that fold's OOS index). For draw i: per fold,
    w = strategy_fn(shuffles[i]) UNGUARDED, backtest at cost_bps_rt,
    restrict bar_returns to the fold's OOS, concat across folds -> pooled
    null Sharpe. Folds with an empty OOS contribute nothing (an all-empty
    pooled series scores Sharpe 0.0). Returns
    {"p95": float, "null_sharpes": np.ndarray of length n}.
    """
    n_set = {len(s) for s, _ in fold_shuffles}
    if len(n_set) != 1:
        raise ValueError(
            f"fold shuffle lists differ in length: {sorted(n_set)}")
    n = n_set.pop()
    active = [(s, oos) for s, oos in fold_shuffles if len(oos) > 0]

    null_sharpes = np.empty(n, dtype=float)
    for i in range(n):
        segments = []
        for shuffles, oos_idx in active:
            w = strategy_fn(shuffles[i])
            res = run_backtest(bars, w, funding, cost_bps_rt)
            segments.append(_restrict(res.bar_returns, oos_idx))
        pooled = (pd.concat(segments).sort_index() if segments
                  else pd.Series(dtype=float))
        null_sharpes[i] = sharpe(pooled)

    return {"p95": float(np.quantile(null_sharpes, 0.95)),
            "null_sharpes": null_sharpes}
