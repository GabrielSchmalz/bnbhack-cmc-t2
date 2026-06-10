"""Tests for lab/engine.py — fill simulator + equity (plan Task 1.2, PR-3).

Hand-constructed bars with hand-computed expectations. Never touches data/.

PR-3 mechanics under test:
  - period return r[t] = open[t+1]/open[t] - 1; final bar: close[T]/open[T] - 1
  - per-side cost = cost_bps_rt/2 bps on |dw| traded notional at fills
  - funding only at bars whose open_time is an 8h stamp (00/08/16 UTC):
    equity *= 1 - w[t]*rate  (R-FUND: short earns when rate > 0)
  - equity starts at 1.0; w is already lagged by the caller
  - trades = maximal sign-constant nonzero-w runs
  - turnover = sum |dw| incl. entry from 0 and final exit if any
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package and pytest
# only inserts tests/ (rootdir-wide fix belongs in shared config, not here)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.engine import BTResult, run_backtest


def make_bars(opens, closes, start="2025-01-01 04:00"):
    """Tiny 4h-bar frame indexed by open_time."""
    idx = pd.date_range(start, periods=len(opens), freq="4h")
    opens = np.asarray(opens, dtype=float)
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes),
            "low": np.minimum(opens, closes),
            "close": closes,
            "volume": 1.0,
        },
        index=idx,
    )


def zero_funding(index):
    return pd.Series(0.0, index=index)


def test_long_one_bar_no_costs():
    # opens [100, 110, 121] -> w=[1,1] -> equity [1.10, 1.21]
    bars = make_bars([100.0, 110.0, 121.0], [110.0, 121.0, 133.1])
    w = pd.Series([1.0, 1.0], index=bars.index[:2])
    res = run_backtest(bars, w, zero_funding(bars.index), cost_bps_rt=0.0)

    assert isinstance(res, BTResult)
    assert list(res.equity.index) == list(bars.index[:2])
    assert res.equity.to_numpy() == pytest.approx([1.10, 1.21])
    assert res.bar_returns.to_numpy() == pytest.approx([0.10, 0.10])


def test_next_bar_open_convention():
    # w produced from close[t-1] must multiply r[t] = open[t+1]/open[t] - 1.
    # closes are deliberately absurd (999) so any close-based bar return
    # computation breaks the hand-computed numbers.
    bars = make_bars([100.0, 110.0, 132.0, 145.0],
                     [105.0, 999.0, 130.0, 144.0])
    w = pd.Series([0.0, 1.0, 0.0, 0.0], index=bars.index)
    res = run_backtest(bars, w, zero_funding(bars.index), cost_bps_rt=0.0)

    # bar 1 position earns open[2]/open[1] - 1 = 132/110 - 1 = 0.20 exactly
    assert res.bar_returns.to_numpy() == pytest.approx([0.0, 0.20, 0.0, 0.0])
    assert res.equity.to_numpy() == pytest.approx([1.0, 1.20, 1.20, 1.20])

    # final bar uses close[T]/open[T] - 1 (no next open exists)
    w2 = pd.Series([0.0, 1.0, 0.0, 1.0], index=bars.index)
    res2 = run_backtest(bars, w2, zero_funding(bars.index), cost_bps_rt=0.0)
    assert res2.bar_returns.iloc[-1] == pytest.approx(144.0 / 145.0 - 1.0)
    assert res2.equity.iloc[-1] == pytest.approx(1.20 * (144.0 / 145.0))


def test_costs_per_side():
    # w goes 0 -> 1 -> 0 at 10 bps RT: two fills, 5 bps each on |dw|=1
    bars = make_bars([100.0, 100.0], [100.0, 100.0])
    w = pd.Series([1.0, 0.0], index=bars.index)
    res = run_backtest(bars, w, zero_funding(bars.index), cost_bps_rt=10.0)

    side = 5.0 / 1e4
    assert res.bar_returns.iloc[0] == pytest.approx(-side)
    assert res.equity.iloc[0] == pytest.approx(1.0 - side)
    assert res.equity.iloc[-1] == pytest.approx((1.0 - side) ** 2)
    assert res.turnover == pytest.approx(2.0)

    # held-to-end position: final exit counts in turnover but is NOT a fill,
    # so equity pays only the single entry cost (PR-5 HODL: one entry cost)
    w_hold = pd.Series([1.0, 1.0], index=bars.index)
    res_hold = run_backtest(bars, w_hold, zero_funding(bars.index),
                            cost_bps_rt=10.0)
    assert res_hold.equity.iloc[-1] == pytest.approx(1.0 - side)
    assert res_hold.turnover == pytest.approx(2.0)


def test_short_funding_sign():
    # R-FUND pin: w=-1, rate=+0.0001 at an 8h stamp -> equity INCREASES ~1e-4
    bars = make_bars([100.0, 100.0], [100.0, 100.0],
                     start="2025-01-01 08:00")  # 08:00 IS a stamp, 12:00 not
    funding = pd.Series([1e-4, 1e-4], index=bars.index)
    w = pd.Series([-1.0, -1.0], index=bars.index)
    res = run_backtest(bars, w, funding, cost_bps_rt=0.0)

    assert res.equity.iloc[0] == pytest.approx(1.0001)
    assert res.equity.iloc[0] > 1.0
    # 12:00 bar is NOT an 8h stamp: its funding value must NOT accrue
    assert res.equity.iloc[1] == pytest.approx(1.0001)


def test_long_funding_sign():
    # w=+1, rate=+0.0001 at an 8h stamp -> equity DECREASES
    bars = make_bars([100.0], [100.0], start="2025-01-01 08:00")
    funding = pd.Series([1e-4], index=bars.index)
    w = pd.Series([1.0], index=bars.index)
    res = run_backtest(bars, w, funding, cost_bps_rt=0.0)

    assert res.equity.iloc[0] == pytest.approx(0.9999)
    assert res.equity.iloc[0] < 1.0


def test_trades_extraction():
    # w=[0,1,1,-1,0] -> exactly 2 trades with correct entry/exit ts and pnl
    bars = make_bars([100.0, 100.0, 110.0, 121.0, 108.9],
                     [100.0, 110.0, 121.0, 108.9, 108.9])
    idx = bars.index
    w = pd.Series([0.0, 1.0, 1.0, -1.0, 0.0], index=idx)
    res = run_backtest(bars, w, zero_funding(idx), cost_bps_rt=0.0)

    # equity path: [1, 1.10, 1.21, 1.331, 1.331] (short earns the -10% bar)
    assert res.equity.to_numpy() == pytest.approx(
        [1.0, 1.10, 1.21, 1.331, 1.331])

    t = res.trades
    assert list(t.columns) == ["entry_ts", "exit_ts", "w", "pnl_pct"]
    assert len(t) == 2

    # trade 1: long over bars 1-2, exits at bar-3 open
    assert t["entry_ts"].iloc[0] == idx[1]
    assert t["exit_ts"].iloc[0] == idx[3]
    assert t["w"].iloc[0] == pytest.approx(1.0)
    assert t["pnl_pct"].iloc[0] == pytest.approx(0.21)

    # trade 2: short over bar 3, exits at bar-4 open
    assert t["entry_ts"].iloc[1] == idx[3]
    assert t["exit_ts"].iloc[1] == idx[4]
    assert t["w"].iloc[1] == pytest.approx(-1.0)
    assert t["pnl_pct"].iloc[1] == pytest.approx(0.10)

    # turnover: |dw| = [0,1,0,2,1], final w=0 so no final exit -> 4.0
    assert res.turnover == pytest.approx(4.0)
