"""Fixed benchmark trio — plan Task 1.5, PR-5.

All three benchmarks run THROUGH lab.engine.run_backtest so they pay the
same costs and funding as variants (CONTEXT.md: Benchmark). The PR-4 DD
guard does NOT apply here — benchmarks are pure reference curves (HODL must
be allowed to draw down, else it's not HODL).

  hodl       w ≡ 1 perp long incl. funding; exactly one entry cost (the
             engine never force-liquidates the end-of-backtest position).
  flat       w ≡ 0, zero-cost, zero-funding by construction.
  vol_target long-only EWMA vol targeting:
               sigma2[t] = lam*sigma2[t-1] + (1-lam)*logret[t]^2
             on 4h close-to-close log returns, seeded with the first squared
             return; ann vol = sqrt(sigma2 * 2190); w_raw = clip(target /
             ann_vol, 0, 1); **shifted 1 bar** (decided at close t -> held
             bar t+1, the same lag discipline as every variant); the
             un-seeded first weights are 0.
"""

import numpy as np
import pandas as pd

from lab.engine import BTResult, run_backtest

BARS_PER_YEAR = 2190  # 4h bars per year (PR-3 annualization)


def hodl(bars: pd.DataFrame, funding: pd.Series,
         cost_bps_rt: float) -> BTResult:
    """Buy & hold the perp: w ≡ 1, funding paid, one entry cost (PR-5)."""
    w = pd.Series(1.0, index=bars.index)
    return run_backtest(bars, w, funding, cost_bps_rt)


def flat(bars: pd.DataFrame) -> BTResult:
    """Stay out: w ≡ 0 — zero cost, zero funding, equity pinned at 1.0."""
    w = pd.Series(0.0, index=bars.index)
    return run_backtest(bars, w, pd.Series(0.0, index=bars.index), 0.0)


def vol_target_weights(bars: pd.DataFrame, target: float = 0.30,
                       lam: float = 0.94) -> pd.Series:
    """Lagged long-only vol-target weight series in [0, 1] (PR-5).

    pandas ewm(alpha=1-lam, adjust=False) IS the PR-5 recursion: it seeds at
    the first valid squared return and applies
    sigma2[t] = lam*sigma2[t-1] + (1-lam)*logret[t]^2 thereafter.
    Zero realized vol -> raw weight inf -> clipped to 1. The shift(1) makes
    w[t+1] the weight decided at close t; seed-NaN weights become 0.
    """
    close = bars["close"].astype(float)
    logret = np.log(close / close.shift(1))
    sigma2 = logret.pow(2).ewm(alpha=1.0 - lam, adjust=False).mean()
    ann_vol = np.sqrt(sigma2 * BARS_PER_YEAR)
    w_raw = (target / ann_vol).clip(0.0, 1.0)
    return w_raw.shift(1).fillna(0.0)


def vol_target(bars: pd.DataFrame, funding: pd.Series, cost_bps_rt: float,
               target: float = 0.30, lam: float = 0.94) -> BTResult:
    """EWMA vol-target benchmark — same costs + funding as variants."""
    w = vol_target_weights(bars, target=target, lam=lam)
    return run_backtest(bars, w, funding, cost_bps_rt)
