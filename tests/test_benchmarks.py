"""Tests for lab/benchmarks.py — fixed benchmark trio (plan Task 1.5, PR-5).

Hand-constructed bars with hand-computed expectations. Never touches data/.

PR-5 under test (everything runs THROUGH lab.engine.run_backtest):
  - hodl(bars, funding, cost_bps_rt): w ≡ 1 perp long incl. funding,
    exactly ONE entry cost at the first bar (engine never charges exit).
  - flat(bars): w ≡ 0, zero-cost, equity pinned at 1.0.
  - vol_target(bars, funding, cost_bps_rt, target=0.30, lam=0.94):
    sigma2[t] = lam*sigma2[t-1] + (1-lam)*logret[t]^2 on 4h close-to-close
    log returns, seeded with the first squared return; ann vol =
    sqrt(sigma2*2190); w_raw = clip(target/ann_vol, 0, 1); w shifted 1 bar
    (decided at close t -> held bar t+1); seed-NaN -> 0.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package and pytest
# only inserts tests/ (rootdir-wide fix belongs in shared config, not here)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.benchmarks import flat, hodl, vol_target, vol_target_weights
from lab.engine import BTResult, run_backtest

ANN = np.sqrt(2190.0)  # 4h bars per year, PR-3 annualization


def make_bars(opens, closes, start="2025-01-01 00:00"):
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


# ---------------------------------------------------------------- HODL


def test_hodl_equity_matches_hand_calc():
    # 3 bars from 00:00 -> funding stamps at bars 0 (00:00) and 2 (08:00),
    # NOT bar 1 (04:00). w ≡ 1, one entry cost of 5 bps (10 bps RT per side).
    bars = make_bars([100.0, 110.0, 121.0], [110.0, 121.0, 133.1])
    funding = pd.Series(1e-4, index=bars.index)
    res = hodl(bars, funding, cost_bps_rt=10.0)

    side = 5.0 / 1e4
    # r = [110/100-1, 121/110-1, 133.1/121-1] = [0.10, 0.10, 0.10]
    e0 = (1.0 - side) * (1.0 - 1e-4) * 1.10  # entry cost + funding + price
    e1 = e0 * 1.10                           # 04:00 is not a stamp
    e2 = e1 * (1.0 - 1e-4) * 1.10            # 08:00 stamp accrues again

    assert isinstance(res, BTResult)
    assert list(res.equity.index) == list(bars.index)
    assert res.equity.to_numpy() == pytest.approx([e0, e1, e2])


def test_hodl_pays_exactly_one_entry_cost():
    bars = make_bars([100.0, 110.0, 121.0], [110.0, 121.0, 133.1])
    zero = zero_funding(bars.index)
    res_cost = hodl(bars, zero, cost_bps_rt=10.0)
    res_free = hodl(bars, zero, cost_bps_rt=0.0)

    side = 5.0 / 1e4
    # one entry fill at bar 0 and nothing after: the whole curve differs by
    # exactly the single (1 - side) factor
    ratio = (res_cost.equity / res_free.equity).to_numpy()
    assert ratio == pytest.approx([1.0 - side] * 3)


# ---------------------------------------------------------------- flat


def test_flat_equity_all_one():
    # crashing market: flat must not care, zero cost, zero funding exposure
    bars = make_bars([100.0, 90.0, 80.0], [90.0, 80.0, 70.0])
    res = flat(bars)

    assert isinstance(res, BTResult)
    assert res.equity.to_numpy() == pytest.approx([1.0, 1.0, 1.0])
    assert res.bar_returns.to_numpy() == pytest.approx([0.0, 0.0, 0.0])
    assert res.turnover == pytest.approx(0.0)
    assert len(res.trades) == 0


# ---------------------------------------------------------- vol-target


def test_vol_target_weights_lagged_and_seeded():
    # closes grow 10% per bar -> logret[t] = log(1.1) for t >= 1,
    # sigma2 = log(1.1)^2 exactly at every bar (seed == recursion fixpoint).
    bars = make_bars([100.0, 110.0, 121.0, 133.1, 146.41],
                     [110.0, 121.0, 133.1, 146.41, 161.051])
    w = vol_target_weights(bars)

    w_const = 0.30 / (np.log(1.1) * ANN)  # ≈ 0.0673, interior of [0, 1]
    assert w.iloc[0] == 0.0               # shift: nothing known at bar 0
    assert w.iloc[1] == 0.0               # w_raw[0] is seed-NaN -> 0
    assert w.iloc[2:].to_numpy() == pytest.approx([w_const] * 3)
    assert ((w >= 0.0) & (w <= 1.0)).all()


def test_vol_target_w_uses_only_past_returns():
    # tiny first return, huge second return. w held on bar 2 must be decided
    # from logret[1] ONLY (clipped to 1.0); an unlagged implementation would
    # blend in the bar-2 crash and produce ~0.10 instead.
    bars = make_bars([100.0, 100.0, 100.1, 130.0],
                     [100.0, 100.1, 130.0, 130.13])
    w = vol_target_weights(bars)

    lr1 = np.log(100.1 / 100.0)
    lr2 = np.log(130.0 / 100.1)
    assert 0.30 / (lr1 * ANN) > 1.0       # sanity: raw demand exceeds cap
    assert w.iloc[2] == pytest.approx(1.0)

    # bar 3 weight: sigma2[2] = lam*lr1^2 + (1-lam)*lr2^2, hand-recursed
    sigma2_2 = 0.94 * lr1**2 + 0.06 * lr2**2
    assert w.iloc[3] == pytest.approx(0.30 / np.sqrt(sigma2_2 * 2190.0))
    assert ((w >= 0.0) & (w <= 1.0)).all()


def test_vol_target_monotone_in_realized_vol():
    # same shape, different amplitude: ±1% vs ±5% alternating closes.
    # |log up| == |log down| so sigma2 is constant per frame; higher realized
    # vol must give strictly lower w (both interior, away from the clip).
    calm = make_bars([100.0] * 6, [100.0, 101.0, 100.0, 101.0, 100.0, 101.0])
    wild = make_bars([100.0] * 6, [100.0, 105.0, 100.0, 105.0, 100.0, 105.0])
    w_calm = vol_target_weights(calm)
    w_wild = vol_target_weights(wild)

    assert 0.0 < w_wild.iloc[-1] < w_calm.iloc[-1] < 1.0
    assert w_calm.iloc[-1] == pytest.approx(0.30 / (np.log(1.01) * ANN))
    assert w_wild.iloc[-1] == pytest.approx(0.30 / (np.log(1.05) * ANN))


def test_vol_target_equity_hand_calc():
    # 3 bars, zero funding, zero cost: w = [0, 0, c] with
    # c = 0.30 / (log(1.1)*sqrt(2190)); only the final bar earns, at
    # r[2] = close[2]/open[2] - 1 = 0.10 (final-bar convention).
    bars = make_bars([100.0, 110.0, 121.0], [110.0, 121.0, 133.1])
    res = vol_target(bars, zero_funding(bars.index), cost_bps_rt=0.0)

    c = 0.30 / (np.log(1.1) * ANN)
    assert isinstance(res, BTResult)
    assert res.equity.to_numpy() == pytest.approx([1.0, 1.0, 1.0 + 0.10 * c])


def test_vol_target_runs_through_engine():
    # vol_target == run_backtest(bars, vol_target_weights(bars), ...) exactly:
    # same costs + funding plumbing as every variant (PR-5).
    bars = make_bars([100.0, 110.0, 121.0, 115.0, 120.0],
                     [110.0, 121.0, 115.0, 120.0, 118.0])
    funding = pd.Series(1e-4, index=bars.index)
    res = vol_target(bars, funding, cost_bps_rt=10.0, target=0.5, lam=0.9)
    expected = run_backtest(bars, vol_target_weights(bars, target=0.5, lam=0.9),
                            funding, cost_bps_rt=10.0)

    assert res.equity.to_numpy() == pytest.approx(expected.equity.to_numpy())
    assert res.bar_returns.to_numpy() == pytest.approx(
        expected.bar_returns.to_numpy())
    assert res.turnover == pytest.approx(expected.turnover)
