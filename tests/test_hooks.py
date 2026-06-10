"""Tests for lab/hooks.py — honesty hooks (plan Task 1.8, PR-7).

Hand-constructed bars/labels/trades with hand-computed expectations. Never
touches data/.

Hooks under test:
  - shuffle_null: episode-block shuffle of regime labels (permute EPISODE
    ORDER with numpy default_rng(seed), keep lengths, same index), rerun the
    strategy per draw, Sharpe of bar_returns restricted to oos_idx;
    returns {"p95": float, "null_sharpes": np.ndarray}.
  - top_n_removal: restrict trades to entry_ts in oos_idx; remove the n
    largest POSITIVE pnl_pct; with
        total        = prod(1 + bar_returns[oos_idx]) - 1
        removed_gain = prod(1 + pnl_pct of removed trades) - 1
    return (1 + total) / (1 + removed_gain) - 1.
  - cost_ladder: backtest w = strategy_fn(labels) at {5, 10, 20} bps RT;
    per cost: {"net_return_oos", "sharpe_oos"} on oos_idx.
"""

import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.classifier import episodes  # noqa: E402
from lab.hooks import cost_ladder, shuffle_null, top_n_removal  # noqa: E402


def make_bars(opens, closes, start="2025-01-01 00:00"):
    """Tiny 4h-bar frame indexed by open_time (same shape as engine tests)."""
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


def _shuffle_fixture():
    """12 bars, labels A*3 + B*4 + C*5 (distinct labels: any episode-order
    permutation preserves the episode-length multiset exactly)."""
    opens = [100.0, 101.0, 103.0, 102.0, 105.0, 108.0,
             107.0, 110.0, 112.0, 111.0, 115.0, 118.0]
    closes = opens[1:] + [120.0]
    bars = make_bars(opens, closes)
    labels = pd.Series(["A"] * 3 + ["B"] * 4 + ["C"] * 5, index=bars.index)
    oos_idx = bars.index[6:]
    return bars, labels, oos_idx


# ------------------------------------------------------------- shuffle_null


def test_shuffle_null_defaults_pinned():
    sig = inspect.signature(shuffle_null)
    assert sig.parameters["n"].default == 1000
    assert sig.parameters["seed"].default == 17


def test_shuffle_preserves_label_and_episode_length_multisets():
    bars, labels, oos_idx = _shuffle_fixture()
    captured: list[pd.Series] = []

    def strategy_fn(labs: pd.Series) -> pd.Series:
        captured.append(labs.copy())
        return (labs == "A").astype(float)

    out = shuffle_null(strategy_fn, labels, bars, zero_funding(bars.index),
                       cost_bps_rt=0.0, oos_idx=oos_idx, n=5, seed=17)

    assert len(captured) == 5
    for shuffled in captured:
        # same index, same label multiset
        assert shuffled.index.equals(labels.index)
        assert sorted(shuffled.tolist()) == sorted(labels.tolist())
        # episode-length multiset preserved (labels distinct -> no merging)
        eps = episodes(shuffled)
        assert sorted(eps["n_bars"].tolist()) == [3, 4, 5]
        assert set(eps["label"]) == {"A", "B", "C"}

    assert set(out) == {"p95", "null_sharpes"}
    assert isinstance(out["null_sharpes"], np.ndarray)
    assert len(out["null_sharpes"]) == 5
    assert out["p95"] == pytest.approx(
        float(np.quantile(out["null_sharpes"], 0.95)))


def test_shuffle_null_seed_reproducible():
    bars, labels, oos_idx = _shuffle_fixture()

    def strategy_fn(labs: pd.Series) -> pd.Series:
        return (labs == "A").astype(float)

    kwargs = dict(labels=labels, bars=bars, funding=zero_funding(bars.index),
                  cost_bps_rt=10.0, oos_idx=oos_idx, n=20, seed=17)
    out1 = shuffle_null(strategy_fn, **kwargs)
    out2 = shuffle_null(strategy_fn, **kwargs)

    assert np.array_equal(out1["null_sharpes"], out2["null_sharpes"])
    assert out1["p95"] == out2["p95"]


# ------------------------------------------------------------ top_n_removal


def test_top_n_removal_default_n_is_5():
    assert inspect.signature(top_n_removal).parameters["n"].default == 5


def test_top_5_removal_hand_computed():
    idx = pd.date_range("2025-01-01 00:00", periods=12, freq="4h")
    oos_idx = idx[4:]

    # OOS bar returns: product = 1.10 * 1.05 = 1.155 -> total = 0.155.
    # Pre-OOS bars carry +50% returns that MUST be excluded.
    vals = [0.50, 0.50, 0.50, 0.50, 0.10, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0, 0.0]
    bar_returns = pd.Series(vals, index=idx)

    # 7 OOS trades + 1 pre-OOS trade with a huge pnl that must NOT be removed.
    trades = pd.DataFrame({
        "entry_ts": [idx[0], idx[4], idx[5], idx[6], idx[7],
                     idx[8], idx[9], idx[10]],
        "exit_ts":  [idx[1], idx[5], idx[6], idx[7], idx[8],
                     idx[9], idx[10], idx[11]],
        "w": 1.0,
        "pnl_pct": [5.0, 0.30, 0.20, 0.10, 0.05, 0.04, 0.01, -0.02],
    })

    # top-5 positive OOS pnl: 0.30, 0.20, 0.10, 0.05, 0.04
    removed_gain = 1.30 * 1.20 * 1.10 * 1.05 * 1.04 - 1.0
    expected = (1.0 + 0.155) / (1.0 + removed_gain) - 1.0

    got = top_n_removal(trades, bar_returns, oos_idx, n=5)
    assert got == pytest.approx(expected)


def test_top_n_removal_fewer_positive_trades_than_n():
    idx = pd.date_range("2025-01-01 00:00", periods=4, freq="4h")
    oos_idx = idx
    bar_returns = pd.Series([0.10, 0.0, -0.05, 0.0], index=idx)
    total = 1.10 * 0.95 - 1.0  # = 0.045

    # Only ONE positive trade; the negative trade is never removed.
    trades = pd.DataFrame({
        "entry_ts": [idx[0], idx[2]],
        "exit_ts": [idx[2], idx[3]],
        "w": [1.0, 1.0],
        "pnl_pct": [0.10, -0.50],
    })

    expected = (1.0 + total) / 1.10 - 1.0
    got = top_n_removal(trades, bar_returns, oos_idx, n=5)
    assert got == pytest.approx(expected)


def test_top_n_removal_no_positive_trades_returns_total():
    idx = pd.date_range("2025-01-01 00:00", periods=3, freq="4h")
    bar_returns = pd.Series([0.02, -0.01, 0.0], index=idx)
    trades = pd.DataFrame({
        "entry_ts": [idx[0]], "exit_ts": [idx[1]], "w": [1.0],
        "pnl_pct": [-0.10],
    })
    total = 1.02 * 0.99 - 1.0
    assert top_n_removal(trades, bar_returns, idx, n=5) == pytest.approx(total)


# -------------------------------------------------------------- cost_ladder


def test_cost_ladder_monotone_non_increasing_in_cost():
    # Steadily rising opens -> a long-on-A strategy is profitable; alternating
    # labels force fills so higher costs strictly bite.
    n = 12
    opens = [100.0 * 1.02 ** i for i in range(n)]
    closes = opens[1:] + [opens[-1] * 1.02]
    bars = make_bars(opens, closes)
    labels = pd.Series((["A", "A", "B"] * n)[:n], index=bars.index)
    oos_idx = bars.index[4:]
    captured: list[pd.Series] = []

    def strategy_fn(labs: pd.Series) -> pd.Series:
        captured.append(labs.copy())
        return (labs == "A").astype(float)

    ladder = cost_ladder(strategy_fn, labels, bars,
                         zero_funding(bars.index), oos_idx)

    assert set(ladder) == {5, 10, 20}
    for c in (5, 10, 20):
        assert set(ladder[c]) == {"net_return_oos", "sharpe_oos"}
        assert isinstance(ladder[c]["net_return_oos"], float)
        assert isinstance(ladder[c]["sharpe_oos"], float)

    # monotone non-increasing net return in cost; fills guarantee strictness
    assert ladder[5]["net_return_oos"] >= ladder[10]["net_return_oos"]
    assert ladder[10]["net_return_oos"] >= ladder[20]["net_return_oos"]
    assert ladder[5]["net_return_oos"] > ladder[20]["net_return_oos"]

    # the strategy runs on the TRUE labels, unshuffled
    for labs in captured:
        assert labs.equals(labels)
