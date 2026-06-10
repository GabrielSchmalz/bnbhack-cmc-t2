"""Tests for lab/dd_guard.py — PR-4 trailing-DD guard overlay (plan Task 1.4).

Hand-constructed bars with hand-computed expectations. Never touches data/.

PR-4 semantics under test:
  - simulate equity under the GUARDED w with the engine's exact mechanics
    (per-side costs on |dw| fills, 8h-stamp funding accrual, PR-3 returns);
    running peak seeded at the 1.0 starting equity
  - drawdown STRICTLY > threshold at bar t  =>  guarded w = 0 from bar t+1
  - stay flat until the first bar whose regime label differs from the label
    at the breach-detection bar; passthrough resumes AT that bar
  - on resume the peak re-arms to current equity (fresh guard cycle);
    multiple breach cycles supported
  - no breach => w returned unchanged (exact equality)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package and pytest
# only inserts tests/ (rootdir-wide fix belongs in shared config, not here)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.dd_guard import apply_dd_guard
from lab.engine import run_backtest


def bars_from_opens(opens, start="2025-01-01 04:00"):
    """4h-bar frame where close[t] = open[t+1] (final close = final open)."""
    opens = np.asarray(opens, dtype=float)
    closes = np.append(opens[1:], opens[-1])
    idx = pd.date_range(start, periods=len(opens), freq="4h")
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


def regimes_of(labels, index):
    return pd.Series(list(labels), index=index)


def test_crash_path_triggers_at_breach_bar():
    # long 1.0 into three -10% bars: equity 0.9, 0.81, 0.729 vs peak 1.0
    # dd: 10%, 19% (NOT a breach), 27.1% (> 20% -> breach detected at bar 2)
    # guard forces w=0 starting NEXT bar (bar 3); regime never changes
    bars = bars_from_opens([100.0, 90.0, 81.0, 72.9, 72.9, 72.9, 72.9, 72.9])
    w = pd.Series(1.0, index=bars.index)
    regimes = regimes_of("AAAAAAAA", bars.index)

    guarded = apply_dd_guard(w, bars, zero_funding(bars.index),
                             cost_bps_rt=0.0, regimes=regimes, threshold=0.20)

    assert isinstance(guarded, pd.Series)
    assert list(guarded.index) == list(w.index)
    # bar 2 (dd 19% at bar 1) still holds — breach must NOT fire early
    assert guarded.to_numpy() == pytest.approx([1, 1, 1, 0, 0, 0, 0, 0])


def test_stays_flat_until_regime_change():
    # same crash; regime flips A->B at bar 6: flat exactly bars 3-5, then
    # passthrough resumes AT the first label-change bar
    bars = bars_from_opens([100.0, 90.0, 81.0, 72.9, 72.9, 72.9, 72.9, 72.9])
    w = pd.Series(1.0, index=bars.index)
    regimes = regimes_of("AAAAAABB", bars.index)

    guarded = apply_dd_guard(w, bars, zero_funding(bars.index),
                             cost_bps_rt=0.0, regimes=regimes, threshold=0.20)

    assert guarded.to_numpy() == pytest.approx([1, 1, 1, 0, 0, 0, 1, 1])
    assert guarded.iloc[6] == w.iloc[6]          # resume = passthrough of w


def test_exact_threshold_is_not_a_breach():
    # one -25% bar: dd == threshold == 0.25 EXACTLY (0.75 is float-exact);
    # breach requires STRICTLY greater -> no breach, w unchanged
    bars = bars_from_opens([100.0, 75.0, 75.0, 75.0])
    w = pd.Series(1.0, index=bars.index)
    regimes = regimes_of("AAAA", bars.index)

    guarded = apply_dd_guard(w, bars, zero_funding(bars.index),
                             cost_bps_rt=0.0, regimes=regimes, threshold=0.25)

    pd.testing.assert_series_equal(guarded, w, check_exact=True)


def test_no_breach_returns_w_unchanged():
    # gentle wander, mixed signs/sizes, real costs+funding -> exact passthrough
    bars = bars_from_opens([100.0, 101.0, 100.0, 100.5, 100.5],
                           start="2025-01-01 00:00")
    w = pd.Series([0.5, -1.0, 0.0, 1.0, 0.25], index=bars.index)
    funding = pd.Series(1e-4, index=bars.index)
    regimes = regimes_of("AABBA", bars.index)

    guarded = apply_dd_guard(w, bars, funding, cost_bps_rt=10.0,
                             regimes=regimes, threshold=0.20)

    pd.testing.assert_series_equal(guarded, w, check_exact=True)


def test_funding_mechanics_drive_breach():
    # price alone never breaches: one -19% bar then flat (dd 19% < 20%).
    # long pays +0.5% funding at each 8h stamp (bars 0,2,4 from 00:00 start):
    # equity after bar 4 = 0.81 * 0.995^3 = 0.79791065 -> dd 20.209% > 20%.
    # bar 3 sits at dd 1 - 0.81*0.995^2 = 19.808% (no breach yet).
    # An implementation ignoring funding would never trigger here.
    bars = bars_from_opens([100.0, 100.0, 81.0, 81.0, 81.0, 81.0, 81.0,
                            81.0, 81.0], start="2025-01-01 00:00")
    w = pd.Series(1.0, index=bars.index)
    funding = pd.Series(0.005, index=bars.index)
    regimes = regimes_of("AAAAAAAAA", bars.index)

    guarded = apply_dd_guard(w, bars, funding, cost_bps_rt=0.0,
                             regimes=regimes, threshold=0.20)

    assert guarded.to_numpy() == pytest.approx([1, 1, 1, 1, 1, 0, 0, 0, 0])


def test_cost_mechanics_drive_breach():
    # flat prices, zero funding, w toggles 0<->1 each bar at 500 bps RT
    # (2.5% per side): one |dw|=1 fill per bar -> equity 0.975^(t+1).
    # bar 7: 0.975^8 = 0.816652 (dd 18.33%, no breach)
    # bar 8: 0.975^9 = 0.796236 (dd 20.376% > 20% -> breach), flat from bar 9.
    # An implementation ignoring fill costs would never trigger here.
    bars = bars_from_opens([100.0] * 12)
    w = pd.Series([1.0, 0.0] * 6, index=bars.index)
    regimes = regimes_of("AAAAAAAAAAAA", bars.index)

    guarded = apply_dd_guard(w, bars, zero_funding(bars.index),
                             cost_bps_rt=500.0, regimes=regimes,
                             threshold=0.20)

    assert guarded.to_numpy() == pytest.approx(
        [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0])


def test_second_breach_after_reentry():
    # cycle 1: three -10% bars -> breach at bar 2 (dd 27.1%), flat bars 3-4
    # (regime A persists), resume at bar 5 (first B); peak re-arms to 0.729.
    # cycle 2: three more -10% bars -> dd vs new peak 10%, 19%, 27.1% ->
    # second breach at bar 7, flat bars 8-9 (regime stays B).
    bars = bars_from_opens([100.0, 90.0, 81.0, 72.9, 72.9, 72.9,
                            65.61, 59.049, 53.1441, 53.1441])
    w = pd.Series(1.0, index=bars.index)
    regimes = regimes_of("AAAAABBBBB", bars.index)

    guarded = apply_dd_guard(w, bars, zero_funding(bars.index),
                             cost_bps_rt=0.0, regimes=regimes, threshold=0.20)

    assert guarded.to_numpy() == pytest.approx([1, 1, 1, 0, 0, 1, 1, 1, 0, 0])


def test_consistency_with_run_backtest():
    # run_backtest equity under the guarded w never breaches
    # threshold + one-bar slack of its own running peak; dd > threshold only
    # appears via the breach-detection bar; once flat (after the single
    # exit-cost bar) equity is frozen.
    moves = [1.01, 0.99, 1.02, 0.95, 0.93, 0.92, 0.95] + [1.0] * 6
    opens = [100.0]
    for m in moves:
        opens.append(opens[-1] * m)
    bars = bars_from_opens(opens, start="2025-01-01 00:00")
    w = pd.Series([0.5, 0.5] + [1.0] * 12, index=bars.index)
    funding = pd.Series(2e-4, index=bars.index)
    regimes = regimes_of("A" * 14, bars.index)
    threshold = 0.20

    guarded = apply_dd_guard(w, bars, funding, cost_bps_rt=10.0,
                             regimes=regimes, threshold=threshold)
    res = run_backtest(bars, guarded, funding, cost_bps_rt=10.0)

    eq = res.equity.to_numpy()
    peak = np.maximum.accumulate(np.concatenate(([1.0], eq)))[1:]
    dd = 1.0 - eq / peak

    # one-bar slack: worst single-bar move (8%) + exit cost, generously 6 pts
    assert dd.max() <= threshold + 0.06

    breach_pos = int(np.argmax(dd > threshold))
    assert dd[breach_pos] > threshold
    assert breach_pos == 6                       # hand-anchored breach bar

    # passthrough up to and including the breach bar; flat ever after
    pd.testing.assert_series_equal(guarded.iloc[:breach_pos + 1],
                                   w.iloc[:breach_pos + 1], check_exact=True)
    assert (guarded.iloc[breach_pos + 1:] == 0.0).all()

    # after the exit-cost bar the flat equity cannot move (dd stops growing)
    assert (eq[breach_pos + 2:] == eq[breach_pos + 1]).all()
