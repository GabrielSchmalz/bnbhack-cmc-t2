"""W-sweep rule-surface extensions: time-stop + vol-band (registration §3).

Implements the two registered rule-surface extensions of
docs/plans/2026-06-10-widening-preregistration.md §3 (pinned semantics,
amendment W6; build phase §12.1) — variant parameters, not
execution-model changes. Both transforms operate on the POST-LAG pair
produced by lab/rules.apply: w[t] = action_map[lagged_labels[t]] where
lagged_labels = labels.shift(1). Never hand them raw (unlagged) labels;
the engine still expects the returned w pre-lagged, as always.

Time-stop k (apply_time_stop), §3 verbatim:
  - a run starts at the first bar with w != 0 preceded by w == 0 (or
    series/panel start);
  - a sign flip — or any label change — without an intervening flat bar
    CONTINUES the same run (runs start only after a flat bar, so mid-run
    transitions never reset the clock);
  - the position is forced to w = 0 from the close of the k-th bar of the
    run: run bars 1..k keep their position, bar k+1 onward is forced flat;
  - re-entry occurs only at the first label TRANSITION (lagged label
    changes value) into a label whose mapped action is nonzero,
    regardless of intervening zero-action labels; same-label persistence
    never re-enters.

Boundary convention (test-pinned): a qualifying transition observed at
the same close where the stop fires (lagged label changes at run bar
k+1) re-enters immediately AT that bar — the forced exit and the fresh
entry share one fill, which under PR-3 per-side |dw| costs is
cost-identical to exiting to 0 and re-entering at the same open. This
mirrors lab/dd_guard.py, whose guard flat also re-arms at the first
differing-label bar. The re-entered run starts a fresh k-bar budget.

DD-guard precedence (§3: "a DD-guard flat supersedes and terminates the
run") is ENGINE-LEVEL composition: the guard runs over the final w in
the engine/sweep layer and is out of scope here — this module is a pure
series transform and implements no guard interaction.

Vol-band overlay (apply_vol_band): final w is multiplied by 0.5 on bars
where hot_mask is True. The mask is computed BY THE CALLER as
|pc_24h| > q80(|pc_24h|, fold-train) — an R1 train-only cut; this module
never sees Feature data. NaN or missing mask bars scale nothing
(FREEZE-ADDENDUM D4.3: a NaN clause evaluates FALSE). §3's "final w":
vol-band applies after any time-stop, though the registered §5 grids
never combine them on one Variant (ts6 dresses direction maps, vb
dresses ladders).

NaN policy: NaN lagged labels act as zero-action labels (rules.apply
maps them to w = 0); consecutive NaNs are NOT a transition; a NaN w bar
is treated as flat (defensive — lab/rules.apply cannot emit one;
missing => flat, §4).

Like the DD guard, the time-stop is a path-dependent state machine and
loops over bars (§9: guard/time-stop state is path-dependent).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _same_label(a, b) -> bool:
    """Label equality with NaN-safe semantics: NaN == NaN, NaN != value."""
    a_na, b_na = pd.isna(a), pd.isna(b)
    if a_na or b_na:
        return bool(a_na and b_na)
    return bool(a == b)


def _act(label, action_map: dict[str, float]) -> float:
    """Mapped action of a lagged label; unknown or NaN labels act 0.0."""
    if pd.isna(label):
        return 0.0
    return float(action_map.get(label, 0.0))


def apply_time_stop(w: pd.Series, lagged_labels: pd.Series,
                    action_map: dict[str, float], k: int | None) -> pd.Series:
    """Force w = 0 from the close of the k-th bar of every run (§3).

    Args:
      w: post-lag position series (lab/rules.apply output, already lagged).
      lagged_labels: labels.shift(1) aligned with w — the label whose
         mapped action produced w[t]; used for the re-entry transitions.
      action_map: the variant's label -> action dict (sizes baked in);
         only the NONZERO-ness of mapped actions matters here.
      k: registered rung — None ("none", no stop) or a positive integer
         ({none, 6} are the registered values).

    Returns a new float series on w's index; never mutates inputs.
    """
    if k is None:
        return w.astype(float).copy()
    if int(k) != k or int(k) < 1:
        raise ValueError(f"time-stop k must be a positive integer, got {k!r}")
    k = int(k)

    wv = w.astype(float).to_numpy()
    wv = np.where(np.isnan(wv), 0.0, wv)          # defensive: missing => flat
    labs = lagged_labels.loc[w.index].to_numpy()

    out = np.zeros(len(wv))
    run_len = 0                                   # 0 => not inside a run
    stopped = False                               # waiting for re-entry

    for t in range(len(wv)):                      # state machine (cf. dd_guard)
        if stopped:
            transition = t > 0 and not _same_label(labs[t], labs[t - 1])
            if not (transition and _act(labs[t], action_map) != 0.0):
                continue                          # forced flat: out[t] = 0.0
            stopped = False                       # re-entry at this bar
            run_len = 0
        u = wv[t]
        if u == 0.0:
            run_len = 0                           # flat bar ends any run
            continue
        run_len += 1                              # start or continue the run
        out[t] = u
        if run_len == k:                          # close of the k-th run bar
            stopped = True
            run_len = 0

    return pd.Series(out, index=w.index, name=w.name)


def apply_vol_band(w: pd.Series, hot_mask: pd.Series) -> pd.Series:
    """Multiply w by 0.5 on hot bars (§3 vol-band overlay, {off, on}).

    Args:
      w: final position series (post-lag; after any time-stop).
      hot_mask: boolean series, True where |pc_24h| > q80(|pc_24h|,
         fold-train) — computed by the caller from the R1 train-only cut.
         Aligned onto w's index; missing or NaN bars are cold (D4.3).

    Returns a new float series on w's index; never mutates inputs.
    """
    wf = w.astype(float).copy()
    hot = hot_mask.reindex(wf.index).eq(True)     # NaN/missing -> cold
    return wf.mask(hot, wf * 0.5)
