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
