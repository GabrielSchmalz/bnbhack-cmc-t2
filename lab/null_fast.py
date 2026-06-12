"""Fast pooled-null kernel — opt-in (`W_NULL_FAST=1`), bit-identical.

Design of record: docs/plans/2026-06-12-null-fast-design.md; grill
verdicts + adopted amendments A1-A8:
docs/plans/2026-06-12-null-fast-grill.md. Proof battery: Layer 1
tests/test_null_fast.py (unit bit-equality, zero tolerance), Layer 2
scripts/prove_null_fast.sh (full-cell byte-diff vs the committed lane W-B
P-BTC_5bps artifact), Layer 3 the flag-unset import guard.

What it replaces: the per-(draw, fold) work of
`sweep_w._null_sharpes_w` -> `hooks_w.shuffle_null_pooled_w` — object-
dtype label Series materialization, `rules.apply`, the §3 time-stop /
vol-band dressings, the full engine backtest (whose trade table the null
DISCARDS), restriction and pooling — with numpy on precomputed
invariants. Every float64 value is produced by the same elementary
operations in the same order on the same inputs; what moves is WHEN the
draw-invariant subexpressions are evaluated, never WHAT they are. The
final reduction goes through the frozen `lab.metrics.sharpe` on a Series
with identical values in identical order. The §7 RNG stream is untouched:
the kernel consumes the already-constructed `_EpisodeShufflesW._orders`.

Equivalence skeleton (each step pinned bit-level in Layer 1):
  - labels -> int codes via an equality-faithful factorization (one
    reserved code for every NA value, preserving `_same_label`'s
    NaN == NaN semantics); per unique label ONE pass through the frozen
    `float(action_map.get(label, 0.0))` scalar path;
  - `rules.apply`'s lag = shift of the per-code action lookup;
  - the §3 time-stop ported branch-for-branch on int codes (grill Q1/A4:
    per-bar predicates precomputed, branch skeleton 1:1, k-validation
    mirrored);
  - vol-band as `np.where(hot, w*0.5, w)` on the frozen
    `reindex(...).eq(True)` mask (grill Q2, probed bit-equal);
  - engine returns-only: `dw[0]=w[0]; dw[1:]=w[1:]-w[:-1]` (A1), the
    frozen growth product, no equity/trades/turnover — none are consumed
    by the null;
  - restriction + pooling replayed from permutations CAPTURED by running
    the frozen `_restrict` / `concat(...).sort_index()` ops once over
    arange payloads (A2 — no index-geometry assumption survives).

Coupling note (grill Q5/A5): this module re-states frozen EXPRESSIONS
as well as reading frozen state — `pooled_null_sharpes` duplicates the
return/funding/growth math of `lab/engine.py::run_backtest` (lines
95-113) verbatim, so any change to the frozen engine (or to
`lab/rules.py` / `lab/rules_w.py`) re-opens the equivalence claim and
the proof battery must re-run before the flag is used again. It also
reads `_EpisodeShufflesW`'s private slots (`_index`, `_base`,
`_na_mask`, `_non_na`, `_ep_labels`, `_ep_lengths`, `_orders`)
READ-ONLY. The frozen `lab/hooks_w.py` cannot
gain an accessor (frozen-file discipline); the slots are pinned by that
module's own tests and any drift fails loudly here (AttributeError). The
design's index invariants are CHECKED preconditions (A3): the kernel
raises on violation, never silently falls back.

Default OFF: `lab/sweep_w.py::_null_sharpes_w` imports this module ONLY
inside its `W_NULL_FAST == "1"` branch; the frozen path cannot be
perturbed by anything here (Layer 3). Production runs keep the flag
unset until a lane's pre-registration cites the proof artifacts (design
§6); stdout discloses provenance whenever the kernel is live.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lab.engine import _is_8h_stamp
from lab.hooks import _restrict
from lab.metrics import sharpe

NAN_CODE = 0  # reserved label code for every NA value (NaN == NaN, §3 port)

_DESIGN_DOC = "docs/plans/2026-06-12-null-fast-design.md"
_announced = False


def _announce() -> None:
    """One provenance line per process when the fast path is live (A7)."""
    global _announced
    if not _announced:
        print(f"[sweep_w] null path: fast (proof: {_DESIGN_DOC})",
              flush=True)
        _announced = True


def _time_stop_codes(wv: np.ndarray, lagged_codes: np.ndarray,
                     act_nonzero_by_code: np.ndarray, k) -> np.ndarray:
    """`rules_w.apply_time_stop` ported branch-for-branch to int codes.

    wv: the post-lag position values (float64). lagged_codes: codes of
    `labels.shift(1)` (NAN_CODE at t=0). act_nonzero_by_code[c] is the
    frozen `_act(label_c, action_map) != 0.0`. The two per-bar predicates
    — `transition = t > 0 and not _same_label(labs[t], labs[t-1])` and
    `_act(labs[t]) != 0.0` — are pure functions of the constant code
    array, precomputed below (grill A4); the loop keeps the frozen branch
    skeleton exactly: stopped-block first, fall-through re-entry at the
    SAME bar (the pinned boundary convention), zeros-initialized output.
    """
    if int(k) != k or int(k) < 1:
        raise ValueError(f"time-stop k must be a positive integer, got {k!r}")
    k = int(k)

    wv = np.where(np.isnan(wv), 0.0, wv)          # defensive: missing => flat
    n = len(wv)
    reenter = np.zeros(n, dtype=bool)
    if n > 1:
        reenter[1:] = ((lagged_codes[1:] != lagged_codes[:-1])
                       & act_nonzero_by_code[lagged_codes[1:]])

    out = np.zeros(n)
    wl = wv.tolist()
    rl = reenter.tolist()
    run_len = 0                                   # 0 => not inside a run
    stopped = False                               # waiting for re-entry

    for t in range(n):                            # frozen state machine
        if stopped:
            if not rl[t]:
                continue                          # forced flat: out[t] = 0.0
            stopped = False                       # re-entry at this bar
            run_len = 0
        u = wl[t]
        if u == 0.0:
            run_len = 0                           # flat bar ends any run
            continue
        run_len += 1                              # start or continue the run
        out[t] = u
        if run_len == k:                          # close of the k-th run bar
            stopped = True
            run_len = 0

    return out


def _fold_pre(sh, fold, hot: pd.Series, action_map: dict, idx: pd.Index,
              need_hot: bool) -> dict:
    """Draw-invariant per-fold precompute from one `_EpisodeShufflesW`.

    Codes are factorized over the union of the frozen base labels and the
    episode labels so base/episode codes share one table; the NA sentinel
    maps to NAN_CODE. `act_by_code` applies the frozen
    `float(action_map.get(label, 0.0))` path once per unique label.
    """
    if not sh._index.equals(idx):
        raise ValueError(
            f"fold {fold.name}: shuffle index differs from bars index — "
            "the null-fast kernel requires the §3 whole-index invariant "
            "(design docs/plans/2026-06-12-null-fast-design.md)")
    base = sh._base
    ep_labels = sh._ep_labels
    codes, uniques = pd.factorize(np.concatenate([base, ep_labels]),
                                  use_na_sentinel=True)
    codes = codes + 1                             # NA sentinel -1 -> NAN_CODE
    act_by_code = np.empty(len(uniques) + 1, dtype=float)
    act_by_code[NAN_CODE] = 0.0
    for c, lab in enumerate(uniques):
        act_by_code[c + 1] = float(action_map.get(lab, 0.0))

    # exact `_restrict` positions, captured from the frozen op (A2)
    pos = _restrict(pd.Series(np.arange(len(idx)), index=idx),
                    fold.oos_idx)
    return {
        "base_codes": codes[:len(base)],
        "ep_codes": codes[len(base):],
        "fill_mask": ~sh._na_mask,
        "non_na": sh._non_na,
        "ep_lengths": sh._ep_lengths,
        "orders": sh._orders,
        "act_by_code": act_by_code,
        "act_nonzero": act_by_code != 0.0,
        "oos_pos": pos.to_numpy(),
        "oos_index": pos.index,
        "hot_v": (hot.reindex(idx).eq(True).to_numpy() if need_hot
                  else None),
    }


def pooled_null_sharpes(variant, fold_ctx: list[dict], shuffles: dict,
                        bars: pd.DataFrame, funding: pd.Series,
                        cost_bps_rt: float, draws: int) -> np.ndarray:
    """Drop-in fast path for `sweep_w._null_sharpes_w` (bit-identical).

    Same inputs as the frozen path (fold_ctx entries carry the fold and
    its §3 hot mask; `shuffles` maps fold name -> the cell's
    `_EpisodeShufflesW` common draws); returns the identical float64
    null-Sharpe vector. Degenerate behavior mirrored exactly: no active
    fold -> `np.zeros(draws)`; mismatched draw-list lengths -> the frozen
    ValueError (A6).
    """
    _announce()
    active = [fc for fc in fold_ctx if len(fc["fold"].oos_idx)]
    if not active:
        return np.zeros(draws)
    n_set = {len(shuffles[fc["fold"].name]) for fc in active}
    if len(n_set) != 1:
        raise ValueError(
            f"fold shuffle lists differ in length: {sorted(n_set)}")
    n = n_set.pop()

    idx = bars.index
    # panel invariants — the identical frozen engine expressions, once
    opens = bars["open"].astype(float)
    closes = bars["close"].astype(float)
    r_full = opens.shift(-1) / opens - 1.0
    r_full.iloc[-1] = closes.iloc[-1] / opens.iloc[-1] - 1.0
    r_v = r_full.to_numpy()
    fund = funding.reindex(idx).fillna(0.0).astype(float)
    fund_v = fund.where(_is_8h_stamp(idx), 0.0).to_numpy()
    per_side = (cost_bps_rt / 2.0) / 1e4

    amap = variant.action_dict()
    k = variant.time_stop
    vb = bool(variant.vol_band)
    pre = [_fold_pre(shuffles[fc["fold"].name], fc["fold"], fc["hot"],
                     amap, idx, vb)
           for fc in active]

    # pooled ordering, captured from the frozen concat+sort_index op (A2)
    payloads, offset = [], 0
    for p in pre:
        m = len(p["oos_pos"])
        payloads.append(pd.Series(np.arange(offset, offset + m),
                                  index=p["oos_index"]))
        offset += m
    captured = pd.concat(payloads).sort_index()
    perm = captured.to_numpy()
    pooled_index = captured.index

    nbar = len(idx)
    out = np.empty(n, dtype=float)
    for i in range(n):
        segs = []
        for p in pre:
            order = p["orders"][i]
            bar_codes = p["base_codes"].copy()
            if len(p["non_na"]):
                sel = p["non_na"][order]
                bar_codes[p["fill_mask"]] = np.repeat(
                    p["ep_codes"][sel], p["ep_lengths"][sel])
            # rules.apply: per-code action lookup + the frozen 1-bar lag
            w = np.empty(nbar)
            w[0] = 0.0
            w[1:] = p["act_by_code"][bar_codes[:-1]]
            if k is not None:                     # §3 time-stop (ts Variants)
                lagged = np.empty(nbar, dtype=bar_codes.dtype)
                lagged[0] = NAN_CODE
                lagged[1:] = bar_codes[:-1]
                w = _time_stop_codes(w, lagged, p["act_nonzero"], k)
            if vb:                                # §3 vol-band (vb Variants)
                w = np.where(p["hot_v"], w * 0.5, w)
            # engine, returns-only (A1): frozen expression order exactly
            dw = np.empty(nbar)
            dw[0] = w[0]
            dw[1:] = w[1:] - w[:-1]
            growth = ((1.0 - np.abs(dw) * per_side)
                      * (1.0 - w * fund_v)
                      * (1.0 + w * r_v))
            segs.append(growth[p["oos_pos"]] - 1.0)
        pooled = np.concatenate(segs)[perm]
        out[i] = sharpe(pd.Series(pooled, index=pooled_index))
    return out
