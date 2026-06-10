"""Task 1.3 — lab/metrics.py.

Hand-constructed series with hand-computed expectations only (never lab CSVs).
Conventions pinned here:
  - sharpe/sortino annualize with sqrt(2190) (4h bars/year, PR-3).
  - std is POPULATION std (ddof=0) — pinned by test_sharpe_hand_computed
    ([0.01, 0.03] -> mean 0.02, ddof-0 std 0.01 -> sharpe = 2*sqrt(2190);
    ddof=1 would give sqrt(2)*sqrt(2190), so the test discriminates).
  - sortino downside std = ddof-0 std of the NEGATIVE returns only.
  - cagr years = len(equity) / 2190.
  - max_dd returned as a POSITIVE fraction (0.25 == 25% drawdown).
  - hit_rate counts trades with pnl_pct strictly > 0 (zero-pnl is not a win).
"""

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as tests/test_dataset.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.metrics import cagr, hit_rate, max_dd, sharpe, sortino  # noqa: E402

SQRT_BARS_PER_YEAR = math.sqrt(2190.0)


# ---------------------------------------------------------------- sharpe

def test_sharpe_constant_returns_zero_std_guard():
    # constant +10 bps/bar -> std == 0 -> guard returns 0.0 (not inf/nan)
    r = pd.Series([0.001, 0.001, 0.001, 0.001])
    assert sharpe(r) == 0.0


def test_sharpe_alternating_pm_1pct_is_zero():
    # mean of [+1%, -1%, +1%, -1%] is exactly 0 -> sharpe 0
    r = pd.Series([0.01, -0.01, 0.01, -0.01])
    assert sharpe(r) == pytest.approx(0.0, abs=1e-12)


def test_sharpe_hand_computed():
    # [0.01, 0.03]: mean = 0.02, population std = 0.01
    # sharpe = (0.02 / 0.01) * sqrt(2190) = 2 * sqrt(2190)
    r = pd.Series([0.01, 0.03])
    assert sharpe(r) == pytest.approx(2.0 * SQRT_BARS_PER_YEAR, rel=1e-12)


def test_sharpe_empty_series_guard():
    assert sharpe(pd.Series([], dtype=float)) == 0.0


# ---------------------------------------------------------------- sortino

def test_sortino_hand_computed():
    # [0.03, -0.01, 0.02, -0.03]: mean = 0.0025
    # negatives [-0.01, -0.03]: mean -0.02, population std = 0.01
    # sortino = (0.0025 / 0.01) * sqrt(2190) = 0.25 * sqrt(2190)
    r = pd.Series([0.03, -0.01, 0.02, -0.03])
    assert sortino(r) == pytest.approx(0.25 * SQRT_BARS_PER_YEAR, rel=1e-12)


def test_sortino_no_negative_returns_guard():
    # no negative returns -> downside std undefined -> guard 0.0
    r = pd.Series([0.01, 0.02, 0.0, 0.005])
    assert sortino(r) == 0.0


def test_sortino_single_negative_return_guard():
    # one negative return: ddof-0 std of a single value is 0 -> guard 0.0
    r = pd.Series([0.01, -0.02, 0.03])
    assert sortino(r) == 0.0


def test_sortino_empty_series_guard():
    assert sortino(pd.Series([], dtype=float)) == 0.0


# ---------------------------------------------------------------- cagr

def test_cagr_half_year_hand_computed():
    # 1095 bars = 1095/2190 = 0.5 years; equity 1.0 -> 1.1
    # cagr = (1.1/1.0)^(1/0.5) - 1 = 1.1^2 - 1 = 0.21
    eq = pd.Series([1.0] * 1094 + [1.1])
    assert cagr(eq) == pytest.approx(0.21, rel=1e-12)


def test_cagr_one_year_hand_computed():
    # 2190 bars = exactly 1 year; equity 1.0 -> 1.21 -> cagr = 0.21
    eq = pd.Series([1.0] * 2189 + [1.21])
    assert cagr(eq) == pytest.approx(0.21, rel=1e-12)


def test_cagr_flat_equity_is_zero():
    eq = pd.Series([1.0] * 100)
    assert cagr(eq) == pytest.approx(0.0, abs=1e-12)


def test_cagr_empty_series_guard():
    assert cagr(pd.Series([], dtype=float)) == 0.0


# ---------------------------------------------------------------- max_dd

def test_max_dd_known_path_quarter():
    # peak 1.2, trough 0.9 -> (1.2 - 0.9) / 1.2 = 0.25 (positive fraction)
    eq = pd.Series([1.0, 1.2, 0.9, 1.0])
    assert max_dd(eq) == pytest.approx(0.25, rel=1e-12)


def test_max_dd_takes_deepest_drawdown():
    # dd1: (1.2-0.9)/1.2 = 0.25 ; dd2: (1.5-1.05)/1.5 = 0.30 -> max 0.30
    eq = pd.Series([1.0, 1.2, 0.9, 1.5, 1.05])
    assert max_dd(eq) == pytest.approx(0.30, rel=1e-12)


def test_max_dd_monotone_up_is_zero():
    eq = pd.Series([1.0, 1.1, 1.2, 1.3])
    assert max_dd(eq) == 0.0


def test_max_dd_empty_series_guard():
    assert max_dd(pd.Series([], dtype=float)) == 0.0


# ---------------------------------------------------------------- hit_rate

def test_hit_rate_hand_computed():
    # wins are pnl_pct strictly > 0: [0.05, 0.01] -> 2 of 4 -> 0.5
    trades = pd.DataFrame({"pnl_pct": [0.05, -0.02, 0.0, 0.01]})
    assert hit_rate(trades) == pytest.approx(0.5, rel=1e-12)


def test_hit_rate_empty_trades_guard():
    trades = pd.DataFrame({"pnl_pct": []})
    assert hit_rate(trades) == 0.0


def test_hit_rate_all_winners():
    trades = pd.DataFrame({"pnl_pct": [0.01, 0.02]})
    assert hit_rate(trades) == pytest.approx(1.0)
