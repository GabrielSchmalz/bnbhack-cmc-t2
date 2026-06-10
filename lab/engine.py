"""Fill simulator + equity accounting — plan Task 1.2, PR-3 execution model.

Mechanics (PR-3, G8):
  - w[t] in [-1, 1] is the position held during bar t (open[t] -> open[t+1]).
  - **w is expected ALREADY LAGGED by the caller**: w[t] must be decided from
    data <= close[t-1] (signal at close, next-bar-open fill). The engine
    applies NO additional shift — it multiplies w[t] by r[t] as given.
  - period return r[t] = open[t+1]/open[t] - 1; for the final bar of `bars`
    (no next open): r[T] = close[T]/open[T] - 1.
  - costs: round-trip cost_bps_rt bps => per-side cost_bps_rt/2 bps charged on
    |dw| traded notional at each fill (bar open where w changes), including
    the entry from 0 at the first bar. The end-of-backtest position is NOT
    force-liquidated in equity (PR-5 HODL pays exactly one entry cost); the
    final exit DOES count in turnover.
  - funding: at each bar whose open_time is an 8h stamp (00/08/16 UTC),
    equity *= 1 - w[t]*rate. R-FUND sign, pinned by test: a short (w<0)
    EARNS when rate > 0. Non-stamp bars never accrue funding, even if the
    passed series carries values there (robust to ffilled feature columns).
  - equity starts at 1.0 (reported per bar AFTER that bar completes).

Trades: maximal runs of sign-constant nonzero w (magnitude may vary within a
run). pnl_pct = equity at the run's last bar / equity just before the run - 1
(includes the entry cost, funding and price moves; the exit fill cost is
charged on the bar after the run). exit_ts = open_time of the bar after the
run; a run reaching the final bar exits at the final close, reported as the
final bar's open_time.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BTResult:
    equity: pd.Series      # indexed by bar open_time, starts 1.0
    bar_returns: pd.Series # per-bar strategy simple returns (net of costs+funding)
    trades: pd.DataFrame   # entry_ts, exit_ts, w, pnl_pct (sign-constant nonzero-w runs)
    turnover: float        # sum |dw| incl. entry from 0 and final exit if any


TRADE_COLUMNS = ["entry_ts", "exit_ts", "w", "pnl_pct"]


def _is_8h_stamp(idx: pd.DatetimeIndex) -> np.ndarray:
    """True where a bar open_time sits on a funding stamp (00/08/16 UTC)."""
    return np.asarray((idx.hour % 8 == 0) & (idx.minute == 0)
                      & (idx.second == 0), dtype=bool)


def _extract_trades(w: pd.Series, equity: pd.Series) -> pd.DataFrame:
    """Maximal sign-constant nonzero-w runs -> trades frame (TRADE_COLUMNS)."""
    wv = w.to_numpy(dtype=float)
    ev = equity.to_numpy(dtype=float)
    idx = w.index
    n = len(wv)
    sgn = np.sign(wv)
    # run starts: positions where the sign differs from the previous bar
    starts = np.flatnonzero(np.concatenate(([True], sgn[1:] != sgn[:-1])))
    ends = np.append(starts[1:], n) - 1          # inclusive run ends
    rows = []
    for i0, i1 in zip(starts, ends):             # bar loop allowed here (plan)
        if sgn[i0] == 0:
            continue
        eq_before = ev[i0 - 1] if i0 > 0 else 1.0
        rows.append({
            "entry_ts": idx[i0],
            "exit_ts": idx[i1 + 1] if i1 + 1 < n else idx[i1],
            "w": float(wv[i0:i1 + 1].mean()),
            "pnl_pct": float(ev[i1] / eq_before - 1.0),
        })
    return pd.DataFrame(rows, columns=TRADE_COLUMNS)


def run_backtest(bars: pd.DataFrame, w: pd.Series, funding: pd.Series,
                 cost_bps_rt: float) -> BTResult:
    """Run the PR-3 fill simulator.

    Args:
      bars: frame indexed by bar open_time with at least `open` and `close`
            columns (the lab 4h panel, or any subset/superset of w's bars).
      w: position series in [-1, 1] indexed by bar open_time — a contiguous
         run of bars.index. **Must already be lagged by the caller** (decided
         from data <= close[t-1]); the engine applies no shift.
      funding: 8h funding rate series (decimal, e.g. 1e-4) indexed by
         timestamp; reindexed onto w's bars, missing -> 0.0. Only values on
         8h stamps (00/08/16 UTC) accrue.
      cost_bps_rt: round-trip cost in bps; per-side cost_bps_rt/2 applies to
         |dw| at each fill.
    """
    opens = bars["open"].astype(float)
    closes = bars["close"].astype(float)

    # r[t] = open[t+1]/open[t] - 1; final bar of `bars`: close[T]/open[T] - 1
    r_full = opens.shift(-1) / opens - 1.0
    r_full.iloc[-1] = closes.iloc[-1] / opens.iloc[-1] - 1.0

    w = w.astype(float)
    r = r_full.loc[w.index]

    fund = funding.reindex(w.index).fillna(0.0).astype(float)
    fund = fund.where(_is_8h_stamp(w.index), 0.0)

    dw = w.diff()
    dw.iloc[0] = w.iloc[0]                       # entry from 0
    per_side = (cost_bps_rt / 2.0) / 1e4

    growth = ((1.0 - dw.abs() * per_side)        # fill cost at bar open
              * (1.0 - w * fund)                 # funding accrual (R-FUND)
              * (1.0 + w * r))                   # price leg
    equity = growth.cumprod()
    bar_returns = growth - 1.0

    turnover = float(dw.abs().sum() + abs(w.iloc[-1]))  # final exit if any

    return BTResult(
        equity=equity,
        bar_returns=bar_returns,
        trades=_extract_trades(w, equity),
        turnover=turnover,
    )
