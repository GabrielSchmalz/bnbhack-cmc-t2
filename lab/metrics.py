"""Performance metrics over engine outputs (plan Task 1.3).

Pure functions over pd.Series / a duck-typed trades frame (any DataFrame with
a ``pnl_pct`` column — no import from lab.engine). Conventions, pinned by
tests/test_metrics.py:

  - Annualization: sqrt(2190) — 4h bars per year (PR-3).
  - std is POPULATION std (ddof=0).
  - Degenerate inputs return 0.0 (never inf/nan): empty series, zero std,
    no negative returns (sortino), flat/empty equity, empty trades.
"""

import math

import pandas as pd

BARS_PER_YEAR = 2190.0  # 4h bars per year (PR-3)
_SQRT_BARS_PER_YEAR = math.sqrt(BARS_PER_YEAR)


def sharpe(bar_returns: pd.Series) -> float:
    """Annualized Sharpe: mean/std(ddof=0) * sqrt(2190); std==0 -> 0.0."""
    if len(bar_returns) == 0:
        return 0.0
    std = float(bar_returns.std(ddof=0))
    if std == 0.0:
        return 0.0
    return float(bar_returns.mean()) / std * _SQRT_BARS_PER_YEAR


def sortino(bar_returns: pd.Series) -> float:
    """Annualized Sortino: mean / std(ddof=0 of NEGATIVE returns) * sqrt(2190).

    No negative returns (or degenerate downside std) -> 0.0 guard.
    """
    if len(bar_returns) == 0:
        return 0.0
    downside = bar_returns[bar_returns < 0]
    if len(downside) == 0:
        return 0.0
    downside_std = float(downside.std(ddof=0))
    if downside_std == 0.0:
        return 0.0
    return float(bar_returns.mean()) / downside_std * _SQRT_BARS_PER_YEAR


def cagr(equity: pd.Series) -> float:
    """Compound annual growth rate; years = len(equity) / 2190."""
    if len(equity) == 0:
        return 0.0
    start = float(equity.iloc[0])
    end = float(equity.iloc[-1])
    if start <= 0.0 or end <= 0.0:
        return 0.0
    years = len(equity) / BARS_PER_YEAR
    return (end / start) ** (1.0 / years) - 1.0


def max_dd(equity: pd.Series) -> float:
    """Maximum trailing drawdown as a POSITIVE fraction (0.25 == 25%)."""
    if len(equity) == 0:
        return 0.0
    peak = equity.cummax()
    drawdown = (peak - equity) / peak
    return float(drawdown.max())


def hit_rate(trades: pd.DataFrame) -> float:
    """Fraction of trades with pnl_pct strictly > 0; empty frame -> 0.0."""
    n = len(trades)
    if n == 0:
        return 0.0
    return float((trades["pnl_pct"] > 0).sum()) / n
