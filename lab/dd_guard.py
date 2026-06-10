"""DD guard overlay — plan Task 1.4, PR-4 (fixed plumbing, never swept).

Trailing-equity drawdown stop applied OVER a variant's (already-lagged) w
series. State machine over bars (the one lab component allowed to loop):

  - simulate equity bar-by-bar under the GUARDED w with the engine's exact
    PR-3 mechanics — per-side fill cost on |dw| traded notional (including
    the entry from 0), funding accrual only at 8h stamps (R-FUND sign), and
    r[t] = open[t+1]/open[t] - 1 (final bar of `bars`: close/open - 1) —
    using the identical factor order as `lab.engine.run_backtest` so the
    internal equity matches the engine's bit-for-bit;
  - track the running peak, seeded at the 1.0 starting equity;
  - when drawdown is STRICTLY greater than `threshold`, force w = 0 starting
    the NEXT bar (the breach-detection bar still holds its position);
  - stay flat until the first bar whose regime label differs from the label
    at the breach-detection bar; passthrough of w resumes AT that bar and
    the peak re-arms to the current equity (a fresh guard cycle);
  - multiple breach cycles are supported.

Benchmarks (PR-5) are NOT guarded — the guard applies to variants only (PR-4).
"""

import numpy as np
import pandas as pd

from lab.engine import _is_8h_stamp


def apply_dd_guard(w: pd.Series, bars: pd.DataFrame, funding: pd.Series,
                   cost_bps_rt: float, regimes: pd.Series,
                   threshold: float = 0.20) -> pd.Series:
    """Return the guarded w series (same index as `w`).

    Args:
      w: position series in [-1, 1] indexed by bar open_time, ALREADY lagged
         by the caller (engine convention).
      bars: frame with `open`/`close` columns covering w's bars (may be a
         superset; final-bar return special case follows `bars`, as in the
         engine).
      funding: 8h funding rate series (decimal); reindexed onto w's bars,
         missing -> 0.0; only 8h-stamp bars accrue.
      cost_bps_rt: round-trip cost in bps; per-side cost_bps_rt/2 on |dw|.
      regimes: regime label series covering w's index (used for re-entry).
      threshold: trailing drawdown trigger (strict >), default 0.20 (PR-4).
    """
    opens = bars["open"].astype(float)
    closes = bars["close"].astype(float)
    r_full = opens.shift(-1) / opens - 1.0
    r_full.iloc[-1] = closes.iloc[-1] / opens.iloc[-1] - 1.0

    wv = w.astype(float).to_numpy()
    rv = r_full.loc[w.index].to_numpy()
    fund = funding.reindex(w.index).fillna(0.0).astype(float)
    fund = fund.where(_is_8h_stamp(w.index), 0.0).to_numpy()
    labels = regimes.loc[w.index].to_numpy()

    per_side = (cost_bps_rt / 2.0) / 1e4

    g = np.zeros(len(wv))
    equity, peak, prev = 1.0, 1.0, 0.0
    breached, breach_label = False, None

    for t in range(len(wv)):                      # state machine (plan 1.4)
        if breached and labels[t] != breach_label:
            breached = False
            peak = equity                         # re-arm: fresh guard cycle
        gt = 0.0 if breached else wv[t]
        g[t] = gt
        dw = gt - prev
        equity *= ((1.0 - abs(dw) * per_side)     # fill cost at bar open
                   * (1.0 - gt * fund[t])         # funding accrual (R-FUND)
                   * (1.0 + gt * rv[t]))          # price leg
        peak = max(peak, equity)
        if not breached and (peak - equity) / peak > threshold:
            breached, breach_label = True, labels[t]
        prev = gt

    return pd.Series(g, index=w.index, name=w.name)
