"""Task 2.4 — the pre-registered variant sweep pipeline (PR-6/PR-7/PR-8).

Pipeline (binding semantics, plan Task 2.4 + ADR-001):
 1. panel = add_features(load_panel("full")); bars = OHLCV columns;
    funding = panel.funding_rate (8h-stamp series).
 2. Folds per taxonomy: PR-6 calendar boundaries; the embargo is sized from
    REFERENCE labels computed with thresholds derived ONCE on the F1-train
    slice (rows strictly before 2025-10-01) — causal, never re-derived.
 3. Per (taxonomy, fold): thresholds re-derived on that fold's train rows
    only (R1), then applied to the WHOLE index.
 4. Per variant: w = rules.apply(labels_f, action_map) (pre-lagged by the
    rule); guarded by apply_dd_guard at the same cost rung; backtest
    @10 bps RT. Rank key = mean over folds of TRAIN Sharpe (PR-7; secondary
    sort: lower mean train max-DD, then id). Pooled OOS = concat of
    per-fold OOS bar-returns (sorted; disjoint by construction).

Pre-registered hook adaptations (plan Task 2.4, documented here):
 a. Pooled shuffle null with COMMON RANDOM SHUFFLES: per (taxonomy, fold),
    n_null episode-permuted label series are pre-generated ONCE with
    numpy default_rng(seed = 17 + fold_number) (hooks.episode_shuffles)
    and shared across that taxonomy's variants. Per variant per draw the
    shuffled strategy runs UNGUARDED @10 bps; fold-OOS returns are pooled
    across folds per draw; null_p95 = 95th pct of the pooled null Sharpes.
    DISCLOSURE: the gate's null clause compares the variant's UNGUARDED
    pooled-OOS Sharpe against null_p95 — the null draws are unguarded, so
    a guarded numerator would bias the comparison through guard asymmetry.
    All other gate clauses use the guarded runs: shipping_gate is evaluated
    on the guarded pooled returns and its null_pass reason is then
    recomputed from the unguarded Sharpe (both numbers are in the verdict
    stats as strat_sharpe_oos / unguarded_oos_sharpe).
 b. top5 = hooks.top_n_removal on the pooled GUARDED OOS trades + returns.
 c. cost ladder: the DD guard is re-applied per rung (the guard consumes
    the rung's costs), then backtest at {5, 10, 20} bps over folds and
    pool the OOS; the @10 rung reuses the step-4 run.

R3 disclosure: total variants, gate-pass count, expected pass-rate of the
null clause under the shuffle null (mean over variants of P(pooled null
Sharpe > that variant's own null_p95) — ~5% by construction), PLUS the
observed FULL-gate pass rate over the first min(200, n_null) common null
draws of the top train-ranked variant (unguarded draws pushed through the
entire gate with the variant's own null_p95 — a cheap honest extra).

Parallelization (execution scheduling only, no change to semantics): each
taxonomy's variants are evaluated in a fork-based multiprocessing pool.
The common shuffles are pre-generated in the parent BEFORE forking and
shared copy-on-write, and every variant's evaluation is independent, so
the results are identical to the serial path (n_jobs=1, the test path).

Outputs: artifacts/sweep_results.json + artifacts/sweep_summary.md.
Run: uv run --no-sync python -m lab.sweep [--n-null N] [--jobs J]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lab import rules
from lab.benchmarks import hodl
from lab.classifier import TaxonomyConfig, episodes, label
from lab.dataset import load_panel
from lab.dd_guard import apply_dd_guard
from lab.engine import TRADE_COLUMNS, run_backtest
from lab.features import add_features, derive_thresholds
from lab.gate import GateVerdict, shipping_gate
from lab.hooks import episode_shuffles, shuffle_null_pooled, top_n_removal
from lab.metrics import max_dd, sharpe
from lab.variants import Variant, enumerate_all
from lab.walkforward import _BOUNDARIES, embargo_bars, folds

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
OHLCV = ["open", "high", "low", "close", "volume"]
COST_RUNGS = (5, 10, 20)            # bps RT (PR-7 ladder; gate rung = 10)
GATE_COST_BPS = 10.0
SEED_BASE = 17                       # PR-7 seed; per-fold seed = 17 + fold_no
N_NULL_DEFAULT = 1000
N_GATE_NULL_DEFAULT = 200
TAXONOMIES = ("TA", "TB", "TC")
F1_TRAIN_END = _BOUNDARIES[0][1]     # 2025-10-01, the PR-6 F1 boundary


def _net(r: pd.Series) -> float:
    return float((1.0 + r).prod() - 1.0)


def _restrict(s: pd.Series, idx: pd.Index) -> pd.Series:
    return s.loc[s.index.intersection(idx)]


def _pool(segments: list[pd.Series]) -> pd.Series:
    nonempty = [s for s in segments if len(s)]
    if not nonempty:
        return pd.Series(dtype=float)
    return pd.concat(nonempty).sort_index()


def _pool_trades(trades_list: list[pd.DataFrame]) -> pd.DataFrame:
    nonempty = [t for t in trades_list if len(t)]
    if not nonempty:
        # typed empty frame (object-dtype pnl_pct breaks nlargest downstream)
        return pd.DataFrame({
            "entry_ts": pd.Series(dtype="datetime64[ns]"),
            "exit_ts": pd.Series(dtype="datetime64[ns]"),
            "w": pd.Series(dtype=float),
            "pnl_pct": pd.Series(dtype=float),
        })[TRADE_COLUMNS]
    return pd.concat(nonempty, ignore_index=True)


def _fold_number(name: str) -> int:
    """"F1" -> 1 (per-fold shuffle seed = SEED_BASE + fold number)."""
    return int(name[1:])


def _oos_turnover(w: pd.Series, oos_idx: pd.Index) -> float:
    """Sum of |dw| over OOS bars (entry-from-0 counted at the first bar)."""
    dw = w.diff()
    dw.iloc[0] = w.iloc[0]
    return float(dw.abs().loc[dw.index.intersection(oos_idx)].sum())


def _null_gate_pass_rate(variant: Variant, cache: dict, bars: pd.DataFrame,
                         funding: pd.Series, n_g: int,
                         null_p95: float) -> float:
    """R3 extra: FULL-gate pass rate over the first n_g common null draws.

    Draws are UNGUARDED (matching adaptation (a)); each draw is pushed
    through the entire gate — ladder at {5,10,20} bps, top-5 removal, the
    variant's own null_p95, the taxonomy's pooled-OOS HODL benchmark. The
    common draws are regenerated from their seeds via the episode_shuffles
    prefix property (first n_g of n_null draws are identical).
    """
    if n_g <= 0:
        return 0.0
    amap = variant.action_dict()
    fold_ctx = cache["fold_ctx"]
    pooled_oos_idx = cache["pooled_oos_idx"]
    hodl_r10 = cache["hodl_oos_r10"]
    regen = {
        fc["fold"].name: episode_shuffles(
            fc["labels"], n_g, SEED_BASE + _fold_number(fc["fold"].name))
        for fc in fold_ctx
    }
    passes = 0
    for i in range(n_g):
        segs: dict[int, list[pd.Series]] = {c: [] for c in COST_RUNGS}
        trades_list: list[pd.DataFrame] = []
        for fc in fold_ctx:
            f = fc["fold"]
            if not len(f.oos_idx):
                continue
            w = rules.apply(regen[f.name][i], amap)
            for c in COST_RUNGS:
                res = run_backtest(bars, w, funding, float(c))
                segs[c].append(_restrict(res.bar_returns, f.oos_idx))
                if c == 10:
                    trades_list.append(
                        res.trades[res.trades["entry_ts"].isin(f.oos_idx)])
        pooled10 = _pool(segs[10])
        ladder = {c: {"net_return_oos": _net(_pool(segs[c])),
                      "sharpe_oos": sharpe(_pool(segs[c]))}
                  for c in COST_RUNGS}
        top5 = top_n_removal(_pool_trades(trades_list), pooled10,
                             pooled_oos_idx, 5)
        if shipping_gate(pooled10, hodl_r10, null_p95, top5, ladder).passed:
            passes += 1
    return passes / n_g


def _eval_variant(v: Variant, fold_ctx: list[dict],
                  shuffles: dict[str, list[pd.Series]], bars: pd.DataFrame,
                  funding: pd.Series, hodl_r10: pd.Series,
                  pooled_oos_idx: pd.Index) -> tuple[dict, np.ndarray]:
    """Steps 4-8 for ONE variant -> (record dict, pooled null Sharpes)."""
    amap = v.action_dict()
    train_sharpes: dict[str, float] = {}
    train_dds: list[float] = []
    oos_segs: list[pd.Series] = []
    u_segs: list[pd.Series] = []
    trades_list: list[pd.DataFrame] = []
    ladder_segs: dict[int, list[pd.Series]] = {c: [] for c in COST_RUNGS}
    oos_turnover = 0.0

    for fc in fold_ctx:
        f, labels_f = fc["fold"], fc["labels"]
        w = rules.apply(labels_f, amap)
        wg10 = apply_dd_guard(w, bars, funding, GATE_COST_BPS, labels_f)
        res10 = run_backtest(bars, wg10, funding, GATE_COST_BPS)
        train_sharpes[f.name] = sharpe(
            _restrict(res10.bar_returns, f.train_idx))
        train_dds.append(max_dd(_restrict(res10.equity, f.train_idx)))
        if not len(f.oos_idx):
            continue
        seg10 = _restrict(res10.bar_returns, f.oos_idx)
        oos_segs.append(seg10)
        ladder_segs[10].append(seg10)            # (c) @10 reuses step 4
        trades_list.append(
            res10.trades[res10.trades["entry_ts"].isin(f.oos_idx)])
        oos_turnover += _oos_turnover(wg10, f.oos_idx)
        res_u = run_backtest(bars, w, funding, GATE_COST_BPS)        # (a)
        u_segs.append(_restrict(res_u.bar_returns, f.oos_idx))
        for c in (5, 20):        # (c) guard re-applied at the rung cost
            wg_c = apply_dd_guard(w, bars, funding, float(c), labels_f)
            res_c = run_backtest(bars, wg_c, funding, float(c))
            ladder_segs[c].append(_restrict(res_c.bar_returns, f.oos_idx))

    pooled = _pool(oos_segs)
    pooled_u = _pool(u_segs)
    pooled_trades = _pool_trades(trades_list)
    ladder = {c: {"net_return_oos": _net(_pool(ladder_segs[c])),
                  "sharpe_oos": sharpe(_pool(ladder_segs[c]))}
              for c in COST_RUNGS}

    null = shuffle_null_pooled(
        lambda labs, _amap=amap: rules.apply(labs, _amap),
        [(shuffles[fc["fold"].name], fc["fold"].oos_idx)
         for fc in fold_ctx],
        bars, funding, GATE_COST_BPS)
    top5 = top_n_removal(pooled_trades, pooled, pooled_oos_idx, 5)
    unguarded_sharpe = sharpe(pooled_u)

    base = shipping_gate(pooled, hodl_r10, null["p95"], top5, ladder)
    reasons = dict(base.reasons)
    reasons["null_pass"] = bool(unguarded_sharpe > null["p95"])      # (a)
    stats = dict(base.stats)
    stats["unguarded_oos_sharpe"] = float(unguarded_sharpe)
    verdict = GateVerdict(passed=all(reasons.values()),
                          reasons=reasons, stats=stats)

    record = {
        "id": v.id,
        "family": v.family,
        "taxonomy": v.taxonomy,
        "rank_key": float(np.mean(list(train_sharpes.values()))),
        "train_sharpes": {k: float(x) for k, x in train_sharpes.items()},
        "train_max_dd_mean": float(np.mean(train_dds)),
        "oos": {"sharpe": sharpe(pooled),
                "net_return": _net(pooled),
                "max_dd": max_dd((1.0 + pooled).cumprod()),
                "n_trades": int(len(pooled_trades)),
                "turnover": float(oos_turnover)},
        "hooks": {"null_p95": float(null["p95"]),
                  "unguarded_oos_sharpe": float(unguarded_sharpe),
                  "top5_net": float(top5),
                  "ladder": {str(c): ladder[c] for c in COST_RUNGS}},
        "verdict": {"passed": bool(verdict.passed),
                    "reasons": verdict.reasons,
                    "stats": verdict.stats},
    }
    return record, null["null_sharpes"]


# Fork-shared evaluation context: set in the parent right before the Pool is
# created so the workers inherit it copy-on-write (no per-task pickling of
# the pre-generated shuffles).
_MP_CTX: dict = {}


def _mp_eval(variant_id: str) -> tuple[dict, np.ndarray]:
    c = _MP_CTX
    return _eval_variant(c["by_id"][variant_id], c["fold_ctx"],
                         c["shuffles"], c["bars"], c["funding"],
                         c["hodl_r10"], c["pooled_oos_idx"])


def run_sweep(panel: pd.DataFrame, n_null: int = N_NULL_DEFAULT,
              n_gate_null: int = N_GATE_NULL_DEFAULT,
              n_jobs: int = 1) -> dict:
    """Run the full pre-registered sweep on a feature-augmented panel.

    `panel` must carry the lab.dataset OHLCV + funding_rate columns plus
    the canonical Feature columns of lab.features.add_features. The
    production entrypoint main() composes add_features(load_panel("full"));
    tests inject synthetic frames. n_jobs > 1 evaluates each taxonomy's
    variants in a fork pool (identical results, scheduling only). Returns
    the JSON-serializable results dict
    {"globals": ..., "variants": [... sorted by rank_key desc ...]}.
    """
    bars = panel[OHLCV]
    funding = panel["funding_rate"]
    f1_train = panel.loc[panel.index < F1_TRAIN_END]
    thr_ref = derive_thresholds(f1_train)   # causal reference (embargo only)

    variants = enumerate_all()
    by_id = {v.id: v for v in variants}
    hodl_returns = {c: hodl(bars, funding, float(c)).bar_returns
                    for c in COST_RUNGS}

    tax_globals: dict[str, dict] = {}
    tax_cache: dict[str, dict] = {}
    records: list[dict] = []
    null_sharpes_by_id: dict[str, np.ndarray] = {}

    for tax in TAXONOMIES:
        t_tax = time.perf_counter()
        ref_labels = label(panel, TaxonomyConfig(tax, thr_ref))
        tax_folds = folds(panel.index, ref_labels)
        e_bars = embargo_bars(ref_labels)

        fold_ctx: list[dict] = []
        per_fold_meta: dict[str, dict] = {}
        for f in tax_folds:
            thr = derive_thresholds(panel.loc[f.train_idx])          # R1
            labels_f = label(panel, TaxonomyConfig(tax, thr))  # whole index
            oos_eps = (len(episodes(labels_f.loc[f.oos_idx]))
                       if len(f.oos_idx) else 0)
            per_fold_meta[f.name] = {"oos_bars": int(len(f.oos_idx)),
                                     "oos_episodes": int(oos_eps)}
            fold_ctx.append({"fold": f, "labels": labels_f})

        pooled_oos_idx = pd.DatetimeIndex([])
        for fc in fold_ctx:
            pooled_oos_idx = pooled_oos_idx.append(fc["fold"].oos_idx)
        pooled_oos_idx = pooled_oos_idx.unique().sort_values()
        honest_n = int(sum(m["oos_episodes"] for m in per_fold_meta.values()))
        hodl_oos_r = {c: _restrict(hodl_returns[c], pooled_oos_idx)
                      for c in COST_RUNGS}

        tax_globals[tax] = {
            "embargo_bars": int(e_bars),
            "per_fold": per_fold_meta,
            "honest_N": honest_n,
            "hodl_oos": {str(c): {"sharpe": sharpe(hodl_oos_r[c]),
                                  "net_return": _net(hodl_oos_r[c])}
                         for c in COST_RUNGS},
        }
        tax_cache[tax] = {"fold_ctx": fold_ctx,
                          "pooled_oos_idx": pooled_oos_idx,
                          "hodl_oos_r10": hodl_oos_r[10]}

        # (a) common random shuffles, pre-generated ONCE per (tax, fold)
        shuffles = {
            fc["fold"].name: episode_shuffles(
                fc["labels"], n_null,
                SEED_BASE + _fold_number(fc["fold"].name))
            for fc in fold_ctx
        }

        tax_variants = [v for v in variants if v.taxonomy == tax]
        if n_jobs > 1 and len(tax_variants) > 1:
            global _MP_CTX
            _MP_CTX = {"by_id": by_id, "fold_ctx": fold_ctx,
                       "shuffles": shuffles, "bars": bars,
                       "funding": funding, "hodl_r10": hodl_oos_r[10],
                       "pooled_oos_idx": pooled_oos_idx}
            mp = multiprocessing.get_context("fork")
            with mp.Pool(min(n_jobs, len(tax_variants))) as pool:
                evaluated = pool.map(_mp_eval, [v.id for v in tax_variants])
            _MP_CTX = {}
        else:
            evaluated = [
                _eval_variant(v, fold_ctx, shuffles, bars, funding,
                              hodl_oos_r[10], pooled_oos_idx)
                for v in tax_variants
            ]
        for r, nulls in evaluated:
            records.append(r)
            null_sharpes_by_id[r["id"]] = nulls
            print(f"[sweep] {tax} {r['id']}: rank_key={r['rank_key']:.2f} "
                  f"oos_sharpe={r['oos']['sharpe']:.2f} "
                  f"null_p95={r['hooks']['null_p95']:.2f} "
                  f"gate={'PASS' if r['verdict']['passed'] else 'fail'}",
                  flush=True)

        del shuffles    # memory hygiene; R3 regenerates from seeds
        print(f"[sweep] {tax} done (E={e_bars}, honest_N={honest_n}) "
              f"in {time.perf_counter() - t_tax:.1f}s", flush=True)

    # PR-7 rank order: rank_key desc, then lower mean train max-DD, then id
    records.sort(key=lambda r: (-r["rank_key"], r["train_max_dd_mean"],
                                r["id"]))

    expected_null_pass_rate = float(np.mean([
        float(np.mean(null_sharpes_by_id[r["id"]] > r["hooks"]["null_p95"]))
        for r in records]))

    top = records[0]
    n_g = min(n_gate_null, n_null)
    top_rate = _null_gate_pass_rate(by_id[top["id"]],
                                    tax_cache[top["taxonomy"]],
                                    bars, funding, n_g,
                                    top["hooks"]["null_p95"])

    out_globals = {
        "n_variants": len(records),
        "n_null": int(n_null),
        "seed_base": SEED_BASE,
        "n_bars": int(len(panel)),
        "window": [str(panel.index[0]), str(panel.index[-1])],
        "cost_rungs_bps": list(COST_RUNGS),
        "gate_cost_bps": GATE_COST_BPS,
        "taxonomies": tax_globals,
        "r3": {
            "n_variants": len(records),
            "gate_pass_count": int(sum(r["verdict"]["passed"]
                                       for r in records)),
            "expected_null_pass_rate": expected_null_pass_rate,
            "top_variant_id": top["id"],
            "top_variant_null_gate_pass_rate": float(top_rate),
            "n_null_gate_draws": int(n_g),
        },
    }
    return {"globals": out_globals, "variants": records}


def render_summary(results: dict) -> str:
    """artifacts/sweep_summary.md: top-15 rank table, survivors, R3 block."""
    g = results["globals"]
    recs = results["variants"]
    lines = [
        "# Sweep summary — plan Task 2.4 (pre-registered pipeline)",
        "",
        f"- variants swept: {g['n_variants']} (PR-8 denominator)",
        f"- null draws per (taxonomy, fold): {g['n_null']} "
        f"(seed base {g['seed_base']}, common random shuffles)",
        f"- window: {g['window'][0]} .. {g['window'][1]} "
        f"({g['n_bars']} bars)",
        "",
        "## Taxonomy globals",
        "",
        "| taxonomy | embargo E (bars) | honest_N (pooled OOS episodes) "
        "| per-fold OOS bars | per-fold OOS episodes "
        "| HODL pooled-OOS Sharpe @10bps | HODL pooled-OOS net @10bps |",
        "|---|---|---|---|---|---|---|",
    ]
    for tax, tg in g["taxonomies"].items():
        bars_s = ", ".join(f"{k}:{m['oos_bars']}"
                           for k, m in tg["per_fold"].items())
        eps_s = ", ".join(f"{k}:{m['oos_episodes']}"
                          for k, m in tg["per_fold"].items())
        h = tg["hodl_oos"]["10"]
        lines.append(
            f"| {tax} | {tg['embargo_bars']} | {tg['honest_N']} | {bars_s} "
            f"| {eps_s} | {h['sharpe']:.2f} | {h['net_return']:.4f} |")
    lines += [
        "",
        "## Top 15 by rank key (mean per-fold TRAIN Sharpe @10 bps RT, PR-7)",
        "",
        "| # | id | family | tax | rank_key | OOS Sharpe | OOS net "
        "| OOS maxDD | null_p95 | unguarded OOS Sharpe | top5 net | gate |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(recs[:15], 1):
        v = r["verdict"]
        failed = [k for k, ok in v["reasons"].items() if not ok]
        gate_s = "PASS" if v["passed"] else "fail: " + ",".join(failed)
        o, h_ = r["oos"], r["hooks"]
        lines.append(
            f"| {i} | {r['id']} | {r['family']} | {r['taxonomy']} "
            f"| {r['rank_key']:.2f} | {o['sharpe']:.2f} "
            f"| {o['net_return']:.4f} | {o['max_dd']:.3f} "
            f"| {h_['null_p95']:.2f} | {h_['unguarded_oos_sharpe']:.2f} "
            f"| {h_['top5_net']:.4f} | {gate_s} |")
    survivors = [r["id"] for r in recs if r["verdict"]["passed"]]
    lines += ["", "## Survivors (gate passes)", ""]
    if survivors:
        lines += [f"- {s}" for s in survivors]
    else:
        lines.append("- none — R-NULL branch (PR-10)")
    r3 = g["r3"]
    lines += [
        "", "## R3 disclosure", "",
        f"- variants swept: {r3['n_variants']}",
        f"- gate passes: {r3['gate_pass_count']}",
        f"- expected pass-rate of the null clause under the shuffle null: "
        f"{r3['expected_null_pass_rate']:.4f} (~0.05 by construction)",
        f"- FULL-gate pass rate over {r3['n_null_gate_draws']} null draws "
        f"of the top train-ranked variant ({r3['top_variant_id']}): "
        f"{r3['top_variant_null_gate_pass_rate']:.4f}",
        "",
    ]
    if "wall_time_sec" in g:
        lines.append(f"_Wall time: {g['wall_time_sec']} s._")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the pre-registered Task 2.4 variant sweep "
                    "(writes artifacts/sweep_results.json + "
                    "artifacts/sweep_summary.md).")
    parser.add_argument(
        "--n-null", type=int, default=N_NULL_DEFAULT,
        help="shuffle-null draws per (taxonomy, fold); 1000 is the "
             "pre-registered production value (smaller = smoke run)")
    parser.add_argument(
        "--jobs", type=int, default=os.cpu_count() or 1,
        help="fork-pool workers for per-variant evaluation (results are "
             "identical to --jobs 1; scheduling only)")
    args = parser.parse_args(argv)

    t0 = time.perf_counter()
    print(f"[sweep] loading panel + features ... (jobs={args.jobs})",
          flush=True)
    panel = add_features(load_panel("full"))
    results = run_sweep(panel, n_null=args.n_null, n_jobs=args.jobs)
    results["globals"]["wall_time_sec"] = round(time.perf_counter() - t0, 1)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = ARTIFACTS_DIR / "sweep_results.json"
    out_json.write_text(json.dumps(results, indent=2) + "\n")
    out_md = ARTIFACTS_DIR / "sweep_summary.md"
    out_md.write_text(render_summary(results))

    r3 = results["globals"]["r3"]
    print(f"[sweep] done in {results['globals']['wall_time_sec']}s "
          f"-> {out_json} + {out_md}", flush=True)
    print(f"[sweep] gate passes: {r3['gate_pass_count']}/{r3['n_variants']}; "
          f"top train-ranked: {r3['top_variant_id']}", flush=True)


if __name__ == "__main__":
    main()
