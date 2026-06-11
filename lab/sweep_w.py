"""W-sweep driver — the pre-registered widened search, exactly as registered.

Registered spec: docs/plans/2026-06-10-widening-preregistration.md (§1
panels/folds/embargo incl. §13 amendment 27, §3 rule surface, §4/§5
taxonomies + enumeration, §6 lock layers, §7 gate + null mechanics + seed
map, §8 R3 disclosures, §9 NO performance shortcut). Architectural
template: the frozen lab/sweep.py — its semantics are mirrored exactly;
its frozen helpers (_pool, _pool_trades, _oos_turnover, cost rungs, gate
cost) are imported, never re-implemented.

Pipeline per (panel, taxonomy):
 1. E = panels_w.compute_embargo (repaired §13-27 formula), computed ONCE
    and printed in the artifact; folds = panels_w.w_folds.
 2. Per fold: thresholds re-derived on that fold's train rows only (R1,
    lab.classifiers_w), labels over the WHOLE index; the §3 vol-band cut
    q80(|pc_24h|, fold-train) likewise per fold.
 3. Common null draws per (panel, taxonomy, fold) via
    hooks_w.episode_shuffles_w — na episodes frozen in place, registered
    RNG map [17, panel_index, taxonomy_index, fold_ordinal] (§7); the
    index tables are printed in the artifact.
 4. Per variant: w = rules.apply (the frozen 1-bar lag) -> §3 time-stop /
    vol-band where the variant carries them -> PR-4 DD guard at the rung
    cost (engine-level composition per lab/rules_w; the guard supersedes
    any time-stop run) -> FULL-panel backtest via the frozen engine with
    returns restricted to the pooled OOS. NO OOS-window shortcut: the §9
    equivalence proofs do not exist, so the unoptimized path runs.
 5. Hooks: frozen top-5 removal + cost ladder {5, 10, 20} (guard
    re-applied per rung, frozen adaptation (c)); pooled null via
    hooks_w.shuffle_null_pooled_w over the common draws — each draw runs
    the variant's FULL registered rule surface (action map + time-stop +
    vol-band) UNGUARDED, the frozen null convention extended to the §3
    surface. shuffle_null_pooled_w iterates draws-outer/folds-inner over
    exactly the active-fold list it is handed, so the per-fold vol-band
    masks are supplied through an itertools.cycle aligned with that order.
 6. Gate: lab.gate_w.shipping_gate_w (8 clauses; §7 covered-folds list).
    SWEEP-LEVEL adaptation replicated from the frozen sweep (gate_w
    docstring: "any sweep-level unguarded-Sharpe substitution for the
    null clauses stays at the caller"): BOTH null clauses (null_pass,
    null_p99) are recomputed against the variant's UNGUARDED pooled-OOS
    Sharpe — the null draws are unguarded, so a guarded numerator would
    bias the comparison through guard asymmetry. All other clauses use
    the guarded runs.
 7. Rank key (§7 selection): mean per-fold TRAIN Sharpe @10 bps; tiebreak
    lower mean train max-DD; residual ties lexicographic on variant id.
 8. §6 lock layers 1-3 run for EVERY gate-passing variant (annex variants
    are always evaluated and never ship-eligible). Layer 2 re-runs the
    pooled OOS pipeline per fold on the extremity-neutralized twin of the
    final (guarded) w — what the engine actually held — and the twin
    passes iff net@10 > 0 AND twin Sharpe > q95 of the variant's common
    null draws. Layer 3 decomposes the guarded pooled-OOS bar returns.
 9. §8 era-split disclosure for every passer: pooled net / trade count /
    clause-by-clause status split at 2025-04-01, plus OOS-trade
    coincidence counts for the five published near-miss crash days
    (interval overlap: a trade coincides iff [entry_ts, exit_ts]
    intersects the UTC day). Era clause status re-evaluates the gate on
    era-restricted evidence against the FULL pooled-OOS null quantiles
    (era-restricted null distributions are not recomputed — disclosed in
    the artifact note).
10. §8 per-cell full-gate null calibration: the cell's top train-ranked
    GATED variant, min(200, draws) common draws (prefix) pushed through
    all 8 clauses (unguarded, frozen R3 mechanics), with the Monte-Carlo
    standard error sqrt(p(1-p)/n).

Structural feasibility (§5, TRAIN-side only): per-variant per-fold trade
counts from a fold-train-slice backtest of the variant's (unguarded) rule
surface; projected pooled-OOS trades = sum over folds of
(train trades / train bars) x OOS bar count; flagged
structurally-ungateable-as-registered iff projected < clause 7's 60-trade
floor. A code-level guard (_assert_train_side) asserts every consumed
index sits strictly before its fold boundary. OOS bar COUNTS are fold
geometry, not OOS-row evaluation.

Artifact: <out_dir>/sweep_results_w.json (R3 block with the registered
denominators 175/8/24 and the ~32 effective hypotheses, every E, the seed
-map index tables, per-cell calibration, era-split fields, structural
-feasibility flags, per-variant records mirroring the frozen artifact
shape). No wall-time field — the artifact is byte-deterministic; main()
prints timing to stdout only.

Tripwire: python -m lab.sweep_w refuses to run the sweep (the
OOS-contact event) unless W_SWEEP_CONFIRM=registered;
python -m lab.sweep_w --feasibility runs the train-side readout and
needs no confirmation. panel_loader / boundaries / taxonomies are
test-injection points (synthetic toys); the registered defaults are the
production path. Run: W_SWEEP_CONFIRM=registered uv run --no-sync
python -m lab.sweep_w [--draws N].
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lab import rules
from lab.benchmarks import flat, hodl, vol_target
from lab.classifier import episodes
from lab.classifiers_w import NA_LABEL_W, derive_thresholds_w, label_w
from lab.dd_guard import apply_dd_guard
from lab.engine import run_backtest
from lab.features_w import q_hi_abs
from lab.gate_w import MIN_OOS_TRADES, GateVerdictW, shipping_gate_w
from lab.hooks import _net_return, _restrict
from lab.hooks_w import (
    NULL_SEED_W,
    PANEL_INDEX_W,
    TAXONOMY_INDEX_W,
    episode_shuffles_w,
    shuffle_null_pooled_w,
)
from lab.lock_w import (
    layer1_pure_map_locked,
    layer2_twin,
    layer3_share,
    reference_extremity_mask,
    reference_mild_mask,
)
from lab.metrics import max_dd, sharpe
from lab.panels_w import (
    ASSETS_W,
    W_BOUNDARIES,
    compute_embargo,
    load_w_panel,
    w_folds,
)
from lab.rules_w import apply_time_stop, apply_vol_band
from lab.sweep import COST_RUNGS, GATE_COST_BPS, OHLCV, _oos_turnover, _pool, _pool_trades
from lab.variants_w import (
    PANEL_TAXONOMIES_W,
    enumerate_all_w,
    enumerate_forward_registration,
)

N_DRAWS_W = 1000           # §7: D = 1000 common draws per (panel, tax, fold)
CAL_DRAWS_W = 200          # §8: >= 200 draws per full-gate calibration cell
EFFECTIVE_HYPOTHESES_W = 32          # §8 registered convention
EXPECTED_CLAUSE6_RATE = 0.01         # §8: the only analytically binding rate
ERA_SPLIT_W = pd.Timestamp("2025-04-01")     # §8 era split
# §8: the five published near-miss crash days (UTC).
CRASH_DAY_GROUPS_W: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("2025-11-04", ("2025-11-04",)),
    ("2025-11-20", ("2025-11-20",)),
    ("2025-12-29", ("2025-12-29",)),
    ("2026-05-27/28", ("2026-05-27", "2026-05-28")),
    ("2026-06-01/02", ("2026-06-01", "2026-06-02")),
)
ERA_SPLIT_NOTE = (
    "era clause status re-evaluates the 8-clause gate on era-restricted "
    "evidence against the FULL pooled-OOS null quantiles (era-restricted "
    "null distributions are not recomputed); §8 disclosure framing"
)
SWEEP_ARTIFACT_W = "sweep_results_w.json"
FEASIBILITY_ARTIFACT_W = "structural_feasibility.json"
CONFIRM_ENV_W = "W_SWEEP_CONFIRM"
CONFIRM_VALUE_W = "registered"


def _tax_key(taxonomy: str) -> str:
    """Lab taxonomy id -> §7 registration id ("TD" -> "T-D")."""
    return f"T-{taxonomy[1]}"


def _na_set(taxonomy: str) -> set[str]:
    na_label = NA_LABEL_W[taxonomy]
    return {na_label} if na_label is not None else set()


def _strategy_w(variant, labels: pd.Series, hot_mask: pd.Series) -> pd.Series:
    """The variant's full registered rule surface (UNGUARDED final w).

    rules.apply owns the 1-bar lag; the §3 time-stop consumes the lagged
    labels (labels.shift(1)); the §3 vol-band multiplies the final w by
    0.5 on hot bars. The PR-4 DD guard is engine-level composition and is
    applied by the caller (never inside null draws — they run unguarded).
    """
    amap = variant.action_dict()
    w = rules.apply(labels, amap)
    if variant.time_stop is not None:
        w = apply_time_stop(w, labels.shift(1), amap, variant.time_stop)
    if variant.vol_band:
        w = apply_vol_band(w, hot_mask)
    return w


def _assert_train_side(consumed_idx: pd.Index, boundary: pd.Timestamp,
                       fold_name: str) -> None:
    """§5 code-level OOS-contact guard for the TRAIN-side feasibility path.

    Every index the readout consumes must sit STRICTLY before its fold
    boundary; anything at or beyond it is an OOS row and trips the guard.
    """
    if len(consumed_idx) and consumed_idx.max() >= boundary:
        raise AssertionError(
            f"OOS-contact guard: fold {fold_name} consumed index "
            f"{consumed_idx.max()} >= boundary {boundary} — the "
            f"structural-feasibility readout is TRAIN-side only (§5)")


def _projected_oos_trades(variant, fold_packs: list[dict],
                          funding: pd.Series) -> float:
    """§5 TRAIN-side projection: sum_f (train trade rate_f x OOS bars_f).

    Trade counts come from a fold-train-slice backtest of the variant's
    unguarded rule surface at the 10 bps gate rung (frozen trade
    segmentation). OOS bar counts are fold geometry — no OOS row is read.
    """
    total = 0.0
    for pack in fold_packs:
        _assert_train_side(pack["train_bars"].index, pack["boundary"],
                           pack["fold"])
        n_train = len(pack["train_bars"])
        if n_train == 0 or pack["oos_bars"] == 0:
            continue
        w = _strategy_w(variant, pack["labels_train"], pack["hot_train"])
        res = run_backtest(pack["train_bars"], w, funding, GATE_COST_BPS)
        total += len(res.trades) / n_train * pack["oos_bars"]
    return float(total)


def _verdict_w(pooled10, hodl_r10, null_sharpes, ladder, trades, w,
               oos_idx, fold_oos_idx, covered_folds,
               unguarded_sharpe) -> GateVerdictW:
    """gate_w verdict + the frozen sweep's unguarded-null substitution.

    The null draws run UNGUARDED, so BOTH null clauses compare the
    variant's unguarded pooled-OOS Sharpe to the null quantiles (frozen
    lab/sweep.py adaptation (a), extended to clause 6 — a sweep-level
    behavior, per the gate_w docstring; gate mechanics are untouched).
    """
    base = shipping_gate_w(pooled10, hodl_r10, null_sharpes, ladder,
                           trades, w, oos_idx, fold_oos_idx, covered_folds)
    reasons = dict(base.reasons)
    reasons["null_pass"] = bool(unguarded_sharpe > base.stats["null_p95"])
    reasons["null_p99"] = bool(unguarded_sharpe > base.stats["null_p99"])
    stats = dict(base.stats)
    stats["unguarded_oos_sharpe"] = float(unguarded_sharpe)
    return GateVerdictW(passed=all(reasons.values()), reasons=reasons,
                        stats=stats)


def _null_sharpes_w(variant, fold_ctx: list[dict],
                    shuffles: dict[str, list[pd.Series]],
                    bars: pd.DataFrame, funding: pd.Series,
                    draws: int) -> np.ndarray:
    """Pooled null Sharpes over the common draws (frozen pooled null).

    shuffle_null_pooled_w iterates draws-outer/folds-inner over exactly
    the (active-fold) list passed in, so the per-fold vol-band hot masks
    ride an itertools.cycle aligned with that iteration order. Only
    active (non-empty-OOS) folds are passed — matching the function's own
    internal filter — to keep the cycle aligned.
    """
    active = [fc for fc in fold_ctx if len(fc["fold"].oos_idx)]
    if not active:
        return np.zeros(draws)
    hot_cycle = itertools.cycle([fc["hot"] for fc in active])
    fold_shuffles = [(shuffles[fc["fold"].name], fc["fold"].oos_idx)
                     for fc in active]

    def strategy_fn(labs: pd.Series) -> pd.Series:
        return _strategy_w(variant, labs, next(hot_cycle))

    return shuffle_null_pooled_w(strategy_fn, fold_shuffles, bars, funding,
                                 GATE_COST_BPS)["null_sharpes"]


def _evaluate_lock(variant, fold_w: list[tuple[dict, pd.Series]],
                   bars: pd.DataFrame, funding: pd.Series,
                   funding_feat: pd.Series, null_sharpes: np.ndarray,
                   pooled10: pd.Series, pooled_w: pd.Series) -> dict:
    """§6 lock layers 1-3 for one gate-passing variant.

    Layer 2 builds the extremity-neutralized twin per fold from the FINAL
    (guarded) w — what the engine actually held — with per-fold train-only
    reference cuts on funding_rate_8h, re-runs the pooled OOS pipeline
    (same fills, costs, funding) and demands beats_flat@10 AND
    Sharpe > q95 of the variant's own common null draws. Layer 3 uses the
    guarded pooled-OOS bar-return decomposition (each bar's return
    includes its |dw| cost and funding accrual).
    """
    layer1 = bool(layer1_pure_map_locked(variant))

    twin_segs: list[pd.Series] = []
    ext_parts: list[pd.Series] = []
    for fc, wg10 in fold_w:
        f = fc["fold"]
        train_f = funding_feat.loc[f.train_idx]
        oos_f = funding_feat.loc[f.oos_idx]
        ext = reference_extremity_mask(oos_f, train_f)
        mild = reference_mild_mask(oos_f, train_f)
        ext_parts.append(ext)
        twin = layer2_twin(
            wg10,
            ext.reindex(wg10.index),
            pd.Series(f.name, index=wg10.index),
            mild_mask=mild.reindex(wg10.index),
        )
        res = run_backtest(bars, twin, funding, GATE_COST_BPS)
        twin_segs.append(_restrict(res.bar_returns, f.oos_idx))
    twin_pooled = _pool(twin_segs)
    twin_net = float(_net_return(twin_pooled))
    twin_sharpe = float(sharpe(twin_pooled))
    null_p95 = float(np.quantile(np.asarray(null_sharpes, dtype=float),
                                 0.95))
    twin_passes = bool(twin_net > 0.0 and twin_sharpe > null_p95)

    ext_pooled = (pd.concat(ext_parts).sort_index() if ext_parts
                  else pd.Series(dtype=bool))
    share = layer3_share(pooled10, ext_pooled, pooled_w)

    locked_layers = []
    if layer1:
        locked_layers.append("layer1")
    if not twin_passes:
        locked_layers.append("layer2")
    if share["locked"]:
        locked_layers.append("layer3")
    return {
        "layer1_locked": layer1,
        "layer2": {"twin_net_return": twin_net,
                   "twin_sharpe": twin_sharpe,
                   "null_p95": null_p95,
                   "twin_passes": twin_passes,
                   "locked": not twin_passes},
        "layer3": {"total": float(share["total"]),
                   "leg_sum": float(share["leg_sum"]),
                   "evaluated": bool(share["evaluated"]),
                   "share": (float(share["share"]) if share["evaluated"]
                             else None),
                   "locked": bool(share["locked"])},
        "locked": bool(locked_layers),
        "locked_layers": locked_layers,
    }


def _era_split(pooled10, pooled_u, pooled_rungs, trades, w, hodl_r10,
               null_sharpes, fold_oos_idx, covered_folds,
               pooled_oos_idx) -> dict:
    """§8 era-split disclosure: net / trades / clause status per era."""
    out: dict = {"split_at": str(ERA_SPLIT_W.date()), "note": ERA_SPLIT_NOTE}
    eras = (("pre", pooled_oos_idx[pooled_oos_idx < ERA_SPLIT_W]),
            ("post", pooled_oos_idx[pooled_oos_idx >= ERA_SPLIT_W]))
    for name, era_idx in eras:
        ladder_era = {
            c: {"net_return_oos": _net_return(_restrict(pooled_rungs[c],
                                                        era_idx)),
                "sharpe_oos": sharpe(_restrict(pooled_rungs[c], era_idx))}
            for c in COST_RUNGS
        }
        fold_era = {k: idx.intersection(era_idx)
                    for k, idx in fold_oos_idx.items()}
        verdict = _verdict_w(
            _restrict(pooled10, era_idx), _restrict(hodl_r10, era_idx),
            null_sharpes, ladder_era, trades, w, era_idx, fold_era,
            covered_folds, sharpe(_restrict(pooled_u, era_idx)))
        out[name] = {
            "oos_bars": int(len(era_idx)),
            "net_return": float(_net_return(_restrict(pooled10, era_idx))),
            "n_trades": int(trades["entry_ts"].isin(era_idx).sum()),
            "reasons": verdict.reasons,
        }
    return out


def _crash_day_counts(oos_trades: pd.DataFrame) -> dict:
    """§8 crash-day coincidence: OOS trades whose [entry_ts, exit_ts]
    interval overlaps a published near-miss UTC day."""
    out: dict = {}
    union = pd.Series(False, index=oos_trades.index)
    for name, days in CRASH_DAY_GROUPS_W:
        mask = pd.Series(False, index=oos_trades.index)
        for d in days:
            day_start = pd.Timestamp(d)
            day_end = day_start + pd.Timedelta(days=1)
            mask |= ((oos_trades["entry_ts"] < day_end)
                     & (oos_trades["exit_ts"] >= day_start))
        out[name] = int(mask.sum())
        union |= mask
    out["total"] = int(union.sum())
    return out


def _eval_variant_w(variant, fold_ctx: list[dict],
                    shuffles: dict[str, list[pd.Series]],
                    bars: pd.DataFrame, funding: pd.Series,
                    funding_feat: pd.Series, hodl_r10: pd.Series,
                    pooled_oos_idx: pd.Index,
                    fold_oos_idx: dict[str, pd.Index],
                    covered_folds: list[str], feas_packs: list[dict],
                    draws: int) -> tuple[dict, np.ndarray]:
    """Steps 4-9 for ONE variant -> (record dict, pooled null Sharpes)."""
    train_sharpes: dict[str, float] = {}
    train_dds: list[float] = []
    per_fold_oos: dict[str, dict] = {}
    oos_segs: list[pd.Series] = []
    u_segs: list[pd.Series] = []
    trades_list: list[pd.DataFrame] = []
    ladder_segs: dict[int, list[pd.Series]] = {c: [] for c in COST_RUNGS}
    fold_w: list[tuple[dict, pd.Series]] = []
    oos_turnover = 0.0

    for fc in fold_ctx:
        f, labels_f, hot = fc["fold"], fc["labels"], fc["hot"]
        w = _strategy_w(variant, labels_f, hot)
        wg10 = apply_dd_guard(w, bars, funding, GATE_COST_BPS, labels_f)
        res10 = run_backtest(bars, wg10, funding, GATE_COST_BPS)
        train_sharpes[f.name] = sharpe(_restrict(res10.bar_returns,
                                                 f.train_idx))
        train_dds.append(max_dd(_restrict(res10.equity, f.train_idx)))
        if not len(f.oos_idx):
            per_fold_oos[f.name] = {"oos_bars": 0, "net_return": 0.0,
                                    "sharpe": 0.0}
            continue
        seg10 = _restrict(res10.bar_returns, f.oos_idx)
        per_fold_oos[f.name] = {"oos_bars": int(len(seg10)),
                                "net_return": float(_net_return(seg10)),
                                "sharpe": float(sharpe(seg10))}
        oos_segs.append(seg10)
        ladder_segs[10].append(seg10)        # frozen (c): @10 reuses step 4
        trades_list.append(
            res10.trades[res10.trades["entry_ts"].isin(f.oos_idx)])
        oos_turnover += _oos_turnover(wg10, f.oos_idx)
        fold_w.append((fc, wg10))
        res_u = run_backtest(bars, w, funding, GATE_COST_BPS)  # frozen (a)
        u_segs.append(_restrict(res_u.bar_returns, f.oos_idx))
        for c in (5, 20):        # frozen (c): guard re-applied per rung
            wg_c = apply_dd_guard(w, bars, funding, float(c), labels_f)
            res_c = run_backtest(bars, wg_c, funding, float(c))
            ladder_segs[c].append(_restrict(res_c.bar_returns, f.oos_idx))

    pooled10 = _pool(oos_segs)
    pooled_u = _pool(u_segs)
    pooled_trades = _pool_trades(trades_list)
    pooled_rungs = {c: _pool(ladder_segs[c]) for c in COST_RUNGS}
    ladder = {c: {"net_return_oos": _net_return(pooled_rungs[c]),
                  "sharpe_oos": sharpe(pooled_rungs[c])}
              for c in COST_RUNGS}
    pooled_w = _pool([wg.loc[wg.index.intersection(fc["fold"].oos_idx)]
                      for fc, wg in fold_w])

    null_sharpes = _null_sharpes_w(variant, fold_ctx, shuffles, bars,
                                   funding, draws)
    unguarded_sharpe = sharpe(pooled_u)
    verdict = _verdict_w(pooled10, hodl_r10, null_sharpes, ladder,
                         pooled_trades, pooled_w, pooled_oos_idx,
                         fold_oos_idx, covered_folds, unguarded_sharpe)
    projected = _projected_oos_trades(variant, feas_packs, funding)

    record = {
        "id": variant.id,
        "panel": variant.panel,
        "family": variant.family,
        "taxonomy": variant.taxonomy,
        "annex": bool(variant.annex),
        "time_stop": variant.time_stop,
        "vol_band": bool(variant.vol_band),
        "rank_key": float(np.mean(list(train_sharpes.values()))),
        "train_sharpes": {k: float(v) for k, v in train_sharpes.items()},
        "train_max_dd_mean": float(np.mean(train_dds)),
        "per_fold_oos": per_fold_oos,
        "oos": {"sharpe": sharpe(pooled10),
                "net_return": _net_return(pooled10),
                "max_dd": max_dd((1.0 + pooled10).cumprod()),
                "n_trades": int(len(pooled_trades)),
                "turnover": float(oos_turnover)},
        "hooks": {"null_p95": float(verdict.stats["null_p95"]),
                  "null_p99": float(verdict.stats["null_p99"]),
                  "unguarded_oos_sharpe": float(unguarded_sharpe),
                  "top5_net": float(verdict.stats["top5_net_return"]),
                  "topk_net": float(verdict.stats["topk_net_return"]),
                  "topk_k": int(verdict.stats["topk_k"]),
                  "ladder": {str(c): ladder[c] for c in COST_RUNGS}},
        "verdict": {"passed": bool(verdict.passed),
                    "reasons": verdict.reasons,
                    "stats": verdict.stats},
        "structural_feasibility": {
            "projected_oos_trades": projected,
            "flagged": bool(projected < MIN_OOS_TRADES)},
        "lock": None,
        "era_split": None,
        "crash_day_trades": None,
        "ship_eligible": False,
    }

    if verdict.passed:
        lock = _evaluate_lock(variant, fold_w, bars, funding, funding_feat,
                              null_sharpes, pooled10, pooled_w)
        record["lock"] = lock
        record["era_split"] = _era_split(
            pooled10, pooled_u, pooled_rungs, pooled_trades, pooled_w,
            hodl_r10, null_sharpes, fold_oos_idx, covered_folds,
            pooled_oos_idx)
        record["crash_day_trades"] = _crash_day_counts(pooled_trades)
        record["ship_eligible"] = bool(not variant.annex
                                       and not lock["locked"])
    return record, null_sharpes


def _cell_calibration(variant, fold_ctx: list[dict],
                      shuffles: dict[str, list[pd.Series]],
                      bars: pd.DataFrame, funding: pd.Series,
                      hodl_r10: pd.Series, pooled_oos_idx: pd.Index,
                      fold_oos_idx: dict[str, pd.Index],
                      covered_folds: list[str],
                      null_sharpes: np.ndarray, n_cal: int) -> dict:
    """§8 per-cell full-gate null calibration (frozen R3 mechanics).

    The first n_cal common draws (the episode_shuffles_w prefix) run the
    variant's UNGUARDED rule surface through the ENTIRE 8-clause gate —
    ladder at {5, 10, 20} bps, top-5/top-K removal, the variant's own
    null quantiles, the cell's pooled-OOS HODL benchmark. Returns the
    pass rate and its Monte-Carlo standard error sqrt(p(1-p)/n).
    """
    active = [fc for fc in fold_ctx if len(fc["fold"].oos_idx)]
    if n_cal <= 0 or not active:
        return {"draws": 0, "full_gate_pass_rate": None, "mc_se": None}
    passes = 0
    for i in range(n_cal):
        segs: dict[int, list[pd.Series]] = {c: [] for c in COST_RUNGS}
        trades_list: list[pd.DataFrame] = []
        w_parts: list[pd.Series] = []
        for fc in active:
            f = fc["fold"]
            w = _strategy_w(variant, shuffles[f.name][i], fc["hot"])
            for c in COST_RUNGS:
                res = run_backtest(bars, w, funding, float(c))
                segs[c].append(_restrict(res.bar_returns, f.oos_idx))
                if c == 10:
                    trades_list.append(
                        res.trades[res.trades["entry_ts"].isin(f.oos_idx)])
                    w_parts.append(_restrict(w, f.oos_idx))
        ladder = {c: {"net_return_oos": _net_return(_pool(segs[c])),
                      "sharpe_oos": sharpe(_pool(segs[c]))}
                  for c in COST_RUNGS}
        verdict = shipping_gate_w(
            _pool(segs[10]), hodl_r10, null_sharpes, ladder,
            _pool_trades(trades_list), _pool(w_parts), pooled_oos_idx,
            fold_oos_idx, covered_folds)
        passes += int(verdict.passed)
    rate = passes / n_cal
    return {"draws": int(n_cal),
            "full_gate_pass_rate": float(rate),
            "mc_se": float(math.sqrt(rate * (1.0 - rate) / n_cal))}


def _cell_taxonomies(asset: str, taxonomies: dict | None) -> tuple:
    if taxonomies and taxonomies.get(asset):
        return tuple(taxonomies[asset])
    return PANEL_TAXONOMIES_W[f"P-{asset}"]


def _fold_packs(fold_ctx: list[dict], bars: pd.DataFrame) -> list[dict]:
    """TRAIN-side feasibility inputs sliced from the per-fold context.

    labels/hot restricted to the train rows are row-wise identical to
    labeling the train slice directly (the labelers and the |pc_24h| mask
    are bar-local), so the sweep-path flags match the standalone readout
    bit-for-bit.
    """
    packs = []
    for fc in fold_ctx:
        f = fc["fold"]
        packs.append({
            "fold": f.name,
            "boundary": fc["boundary"],
            "train_bars": bars.loc[f.train_idx],
            "labels_train": fc["labels"].loc[f.train_idx],
            "hot_train": fc["hot"].loc[f.train_idx],
            "oos_bars": int(len(f.oos_idx)),
        })
    return packs


def _build_fold_ctx(panel: pd.DataFrame, taxonomy: str,
                    bnds: list[pd.Timestamp], embargo: int) -> list[dict]:
    """Per-fold R1 context: train-derived cuts -> whole-index labels,
    plus the §3 vol-band hot mask from the fold-train q80 cut."""
    fold_ctx = []
    for i, f in enumerate(w_folds(panel.index, bnds, embargo)):
        train = panel.loc[f.train_idx]
        thr = derive_thresholds_w(train, taxonomy)
        labels_f = label_w(panel, taxonomy, thr)
        cut = q_hi_abs(train["pc_24h"])
        hot = panel["pc_24h"].abs() > cut
        fold_ctx.append({"fold": f, "labels": labels_f, "hot": hot,
                         "ordinal": i + 1, "boundary": bnds[i]})
    return fold_ctx


def run_w_sweep(panels: tuple = ASSETS_W, draws: int = N_DRAWS_W,
                out_dir: str = "artifacts/w", panel_loader=None, *,
                boundaries: dict | None = None,
                taxonomies: dict | None = None,
                calibration_draws: int = CAL_DRAWS_W) -> dict:
    """Run the registered W-sweep and write <out_dir>/sweep_results_w.json.

    panels are asset codes ("BTC", "ETH", "SOL"); panel_loader(asset) ->
    panel frame (None -> panels_w.load_w_panel). boundaries / taxonomies
    override the registered W_BOUNDARIES / PANEL_TAXONOMIES_W per asset —
    TEST-INJECTION points for synthetic toys only; production runs the
    defaults. Returns the JSON-serializable results dict (no wall-time
    field: the artifact is byte-deterministic).
    """
    loader = panel_loader or load_w_panel
    bmap = boundaries or W_BOUNDARIES
    all_w = enumerate_all_w()
    forward = enumerate_forward_registration()
    n_cal = min(calibration_draws, draws)

    records: list[dict] = []
    panels_block: dict[str, dict] = {}
    embargo_block: dict[str, dict] = {}
    cal_block: dict[str, dict] = {}
    rate95_acc: list[float] = []
    rate99_acc: list[float] = []

    for asset in panels:
        panel_id = f"P-{asset}"
        p_idx = PANEL_INDEX_W[panel_id]
        panel = loader(asset)
        bars = panel[OHLCV]
        funding = panel["funding_rate"]
        funding_feat = panel["funding_rate_8h"]
        bnds = [pd.Timestamp(b) for b in bmap[asset]]
        bench_returns = {
            "hodl": {c: hodl(bars, funding, float(c)).bar_returns
                     for c in COST_RUNGS},
            "flat": {c: flat(bars).bar_returns for c in COST_RUNGS},
            "vol_target": {c: vol_target(bars, funding,
                                         float(c)).bar_returns
                           for c in COST_RUNGS},
        }

        tax_block: dict[str, dict] = {}
        embargo_block[panel_id] = {}
        for tax in _cell_taxonomies(asset, taxonomies):
            t_start = time.perf_counter()
            t_idx = TAXONOMY_INDEX_W[_tax_key(tax)]
            na_set = _na_set(tax)
            embargo = compute_embargo(panel, tax, bnds)   # once, recorded
            embargo_block[panel_id][tax] = int(embargo)
            fold_ctx = _build_fold_ctx(panel, tax, bnds, embargo)

            per_fold_meta: dict[str, dict] = {}
            pooled_oos_idx = pd.DatetimeIndex([])
            for fc in fold_ctx:
                f = fc["fold"]
                oos_labels = fc["labels"].loc[f.oos_idx]
                eps = episodes(oos_labels)
                non_na_eps = (int((~eps["label"].isin(list(na_set))).sum())
                              if len(eps) else 0)
                covered = bool(len(f.oos_idx)) and bool(
                    (~oos_labels.isin(list(na_set))).any())
                per_fold_meta[f.name] = {"oos_bars": int(len(f.oos_idx)),
                                         "oos_episodes": non_na_eps,
                                         "covered": covered}
                pooled_oos_idx = pooled_oos_idx.append(f.oos_idx)
            pooled_oos_idx = pooled_oos_idx.unique().sort_values()
            honest_n = int(sum(m["oos_episodes"]
                               for m in per_fold_meta.values()))
            covered_folds = [name for name, m in per_fold_meta.items()
                             if m["covered"]]
            fold_oos_idx = {fc["fold"].name: fc["fold"].oos_idx
                            for fc in fold_ctx}
            hodl_r10 = _restrict(bench_returns["hodl"][10], pooled_oos_idx)
            bench_oos = {
                name: {str(c): {
                    "sharpe": sharpe(_restrict(series[c], pooled_oos_idx)),
                    "net_return": _net_return(_restrict(series[c],
                                                        pooled_oos_idx))}
                    for c in COST_RUNGS}
                for name, series in bench_returns.items()
            }
            feas_packs = _fold_packs(fold_ctx, bars)

            # §7 common draws, generated ONCE per (panel, taxonomy, fold)
            shuffles = {
                fc["fold"].name: episode_shuffles_w(
                    fc["labels"], na_set, draws, p_idx, t_idx,
                    fc["ordinal"])
                for fc in fold_ctx
            }

            cell_records: list[dict] = []
            null_by_id: dict[str, np.ndarray] = {}
            cell_variants = [v for v in all_w
                             if v.panel == panel_id and v.taxonomy == tax]
            for v in cell_variants:
                rec, ns = _eval_variant_w(
                    v, fold_ctx, shuffles, bars, funding, funding_feat,
                    hodl_r10, pooled_oos_idx, fold_oos_idx, covered_folds,
                    feas_packs, draws)
                records.append(rec)
                cell_records.append(rec)
                null_by_id[v.id] = ns
                q95 = float(np.quantile(ns, 0.95))
                q99 = float(np.quantile(ns, 0.99))
                rate95_acc.append(float(np.mean(ns > q95)))
                rate99_acc.append(float(np.mean(ns > q99)))
                print(f"[sweep_w] {panel_id} {tax} {rec['id']}: "
                      f"rank_key={rec['rank_key']:.2f} "
                      f"oos_sharpe={rec['oos']['sharpe']:.2f} "
                      f"gate={'PASS' if rec['verdict']['passed'] else 'fail'}",
                      flush=True)

            # §8 per-cell full-gate calibration on the top GATED variant
            gated = [r for r in cell_records if not r["annex"]]
            top = min(gated, key=lambda r: (-r["rank_key"],
                                            r["train_max_dd_mean"],
                                            r["id"]))
            by_id = {v.id: v for v in cell_variants}
            cal = _cell_calibration(
                by_id[top["id"]], fold_ctx, shuffles, bars, funding,
                hodl_r10, pooled_oos_idx, fold_oos_idx, covered_folds,
                null_by_id[top["id"]], n_cal)
            cal_block[f"{panel_id}/{tax}"] = {"variant_id": top["id"],
                                              **cal}
            del shuffles, null_by_id      # memory hygiene (frozen style)

            tax_block[tax] = {
                "embargo_bars": int(embargo),
                "per_fold": per_fold_meta,
                "honest_N": honest_n,
                "covered_folds": covered_folds,
                "benchmarks": bench_oos,
            }
            print(f"[sweep_w] {panel_id} {tax} done (E={embargo}, "
                  f"honest_N={honest_n}) in "
                  f"{time.perf_counter() - t_start:.1f}s", flush=True)

        panels_block[panel_id] = {
            "n_bars": int(len(panel)),
            "window": [str(panel.index[0]), str(panel.index[-1])],
            "taxonomies": tax_block,
        }

    # §7 rank order: rank_key desc, then lower mean train max-DD, then id
    records.sort(key=lambda r: (-r["rank_key"], r["train_max_dd_mean"],
                                r["id"]))

    n_gated_swept = sum(1 for r in records if not r["annex"])
    r3 = {
        "registered": {
            "n_gated": sum(1 for v in all_w if not v.annex),
            "n_annex": sum(1 for v in all_w if v.annex),
            "n_forward_recorded_not_evaluated": len(forward),
            "forward_ids": [v.id for v in forward],
            "effective_hypotheses": EFFECTIVE_HYPOTHESES_W,
            "expected_clause6_rate": EXPECTED_CLAUSE6_RATE,
            "expected_clause6_null_passers": float(
                EXPECTED_CLAUSE6_RATE
                * sum(1 for v in all_w if not v.annex)),
        },
        "swept": {
            "n_variants": len(records),
            "n_gated": n_gated_swept,
            "n_annex": len(records) - n_gated_swept,
            "gate_pass_count": int(sum(r["verdict"]["passed"]
                                       for r in records)),
            "ship_eligible_count": int(sum(r["ship_eligible"]
                                           for r in records)),
            "family_locked_count": int(sum(
                1 for r in records if r["lock"] and r["lock"]["locked"])),
            "structurally_flagged_count": int(sum(
                r["structural_feasibility"]["flagged"] for r in records)),
            "observed_null_p95_rate": (float(np.mean(rate95_acc))
                                       if rate95_acc else None),
            "observed_null_p99_rate": (float(np.mean(rate99_acc))
                                       if rate99_acc else None),
        },
        "per_cell_calibration": cal_block,
    }
    results = {
        "globals": {
            "n_draws": int(draws),
            "calibration_draws": int(n_cal),
            "gate_cost_bps": GATE_COST_BPS,
            "cost_rungs_bps": list(COST_RUNGS),
            "seed_map": {"seed_base": NULL_SEED_W,
                         "panel_index": PANEL_INDEX_W,
                         "taxonomy_index": TAXONOMY_INDEX_W,
                         "fold_ordinal": "panel-local 1-based fold index"},
            "embargo_bars": embargo_block,
            "era_split_at": str(ERA_SPLIT_W.date()),
            "crash_day_groups": {name: list(days)
                                 for name, days in CRASH_DAY_GROUPS_W},
            "panels": panels_block,
            "r3": r3,
        },
        "variants": records,
    }

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / SWEEP_ARTIFACT_W).write_text(
        json.dumps(results, indent=2) + "\n")
    return results


def structural_feasibility_readout(panels: tuple = ASSETS_W,
                                   panel_loader=None, *,
                                   boundaries: dict | None = None,
                                   taxonomies: dict | None = None,
                                   out_dir: str = "artifacts/w") -> dict:
    """§5 pre-OOS structural-feasibility readout — TRAIN-side only.

    Per (panel, taxonomy, fold): thresholds, labels and the vol-band cut
    are computed ON THE TRAIN SLICE (never the whole index); the variant's
    unguarded rule surface is backtested on the train slice; projected
    pooled-OOS trades = sum_f (train trade rate x OOS bar count). Every
    consumed index is guarded by _assert_train_side (strictly before its
    fold boundary). Writes <out_dir>/structural_feasibility.json.
    """
    loader = panel_loader or load_w_panel
    bmap = boundaries or W_BOUNDARIES
    all_w = enumerate_all_w()
    panels_block: dict[str, dict] = {}
    variant_rows: list[dict] = []

    for asset in panels:
        panel_id = f"P-{asset}"
        panel = loader(asset)
        bars = panel[OHLCV]
        funding = panel["funding_rate"]
        bnds = [pd.Timestamp(b) for b in bmap[asset]]
        panels_block[panel_id] = {}
        for tax in _cell_taxonomies(asset, taxonomies):
            embargo = compute_embargo(panel, tax, bnds)
            panels_block[panel_id][tax] = {"embargo_bars": int(embargo)}
            packs = []
            for i, f in enumerate(w_folds(panel.index, bnds, embargo)):
                _assert_train_side(f.train_idx, bnds[i], f.name)
                train = panel.loc[f.train_idx]
                thr = derive_thresholds_w(train, tax)
                labels_train = label_w(train, tax, thr)
                cut = q_hi_abs(train["pc_24h"])
                packs.append({
                    "fold": f.name,
                    "boundary": bnds[i],
                    "train_bars": bars.loc[f.train_idx],
                    "labels_train": labels_train,
                    "hot_train": train["pc_24h"].abs() > cut,
                    "oos_bars": int(len(f.oos_idx)),
                })
            for v in (v for v in all_w
                      if v.panel == panel_id and v.taxonomy == tax):
                projected = _projected_oos_trades(v, packs, funding)
                variant_rows.append({
                    "id": v.id,
                    "panel": panel_id,
                    "taxonomy": tax,
                    "annex": bool(v.annex),
                    "projected_oos_trades": projected,
                    "flagged": bool(projected < MIN_OOS_TRADES),
                })
            print(f"[feasibility] {panel_id} {tax}: E={embargo}, "
                  f"{sum(1 for r in variant_rows if r['panel'] == panel_id and r['taxonomy'] == tax)}"
                  f" variants projected", flush=True)

    result = {
        "clause7_trade_floor": MIN_OOS_TRADES,
        "panels": panels_block,
        "variants": variant_rows,
    }
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / FEASIBILITY_ARTIFACT_W).write_text(
        json.dumps(result, indent=2) + "\n")
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="W-sweep driver (registered). Without --feasibility "
                    "this RUNS THE OOS-CONTACT EVENT and refuses unless "
                    f"{CONFIRM_ENV_W}={CONFIRM_VALUE_W}.")
    parser.add_argument(
        "--feasibility", action="store_true",
        help="run the §5 TRAIN-side structural-feasibility readout only "
             "(no OOS contact; no confirmation needed)")
    parser.add_argument(
        "--draws", type=int, default=N_DRAWS_W,
        help="common null draws per (panel, taxonomy, fold); 1000 is the "
             "registered production value")
    parser.add_argument(
        "--out-dir", default="artifacts/w",
        help="artifact directory (default artifacts/w, repo-root relative)")
    parser.add_argument(
        "--calibration-draws", type=int, default=CAL_DRAWS_W,
        help="per-cell full-gate calibration draws (registered >= 200)")
    args = parser.parse_args(argv)

    if args.feasibility:
        t0 = time.perf_counter()
        res = structural_feasibility_readout(out_dir=args.out_dir)
        flagged = sum(r["flagged"] for r in res["variants"])
        print(f"[feasibility] done in {time.perf_counter() - t0:.1f}s: "
              f"{flagged}/{len(res['variants'])} variants flagged "
              f"structurally-ungateable-as-registered "
              f"-> {Path(args.out_dir) / FEASIBILITY_ARTIFACT_W}",
              flush=True)
        return

    if os.environ.get(CONFIRM_ENV_W) != CONFIRM_VALUE_W:
        print(
            "[sweep_w] REFUSED: this command is the OOS-contact event of "
            "the widening registration (first execution of the W-sweep "
            "gate path against OOS indices). Set "
            f"{CONFIRM_ENV_W}={CONFIRM_VALUE_W} to confirm the registered "
            "run, or use --feasibility for the train-side readout.",
            flush=True)
        raise SystemExit(2)

    t0 = time.perf_counter()
    results = run_w_sweep(draws=args.draws, out_dir=args.out_dir,
                          calibration_draws=args.calibration_draws)
    n = len(results["variants"])
    passes = sum(r["verdict"]["passed"] for r in results["variants"])
    print(f"[sweep_w] done in {time.perf_counter() - t0:.1f}s "
          f"-> {Path(args.out_dir) / SWEEP_ARTIFACT_W}", flush=True)
    print(f"[sweep_w] gate passes: {passes}/{n}", flush=True)


if __name__ == "__main__":
    main()
