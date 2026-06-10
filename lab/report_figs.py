"""Report figures (plan Task 4.1) — rendered from committed artifacts + CSVs.

No network. Everything recomputed here is asserted against
artifacts/sweep_results.json before a figure is drawn (tolerance 1e-9), so
the figures are provably consistent with the committed sweep artifact.

Figures -> docs/report/figs/:
  fig1_pooled_oos_equity.png   pooled-OOS equity overlay (top train-ranked
                               variant, H8 near-miss, HODL, vol-target,
                               flat), guarded @10 bps, OOS segments
                               concatenated with fold boundaries marked
  fig2_h8_concentration.png    H8 OOS equity with its 5 top trades
                               highlighted (the concentration picture)
  fig3_null_distribution.png   pooled episode-shuffle null Sharpes for H8
                               (n=1000, regenerated with the sweep's exact
                               seeds; p95 asserted == artifact)
  fig4_gate_power.png          gate power curve — hardcoded from
                               docs/report/adversarial/lane2_gate_calibration.md §2
  fig5_regime_ribbon.png       TC regime ribbon (frozen F4-train threshold)
                               over the full-stack window price
  fig6_deep_replay.png         failed-candidate deep-history replay
                               (rendered by lab.deep_replay; falsification
                               context, never a track record)

Also prints the PR-5 benchmark block (HODL / flat / vol-target pooled OOS
@10 bps) for the report's benchmarks table; HODL is asserted against the
artifact, vol-target is recomputed from committed CSVs (it is not stored
in sweep_results.json).

Run: uv run --no-sync python -m lab.report_figs [--skip-null]
(--skip-null skips fig3's 1000-draw regeneration during iteration; the
committed figure must be produced WITHOUT the flag.)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lab import deep_replay, rules
from lab.benchmarks import hodl, vol_target
from lab.classifier import TaxonomyConfig, episodes, label
from lab.dataset import load_panel
from lab.dd_guard import apply_dd_guard
from lab.engine import run_backtest
from lab.features import add_features, derive_thresholds
from lab.hooks import episode_shuffles, shuffle_null_pooled
from lab.metrics import sharpe
from lab.sweep import F1_TRAIN_END, GATE_COST_BPS, SEED_BASE, _fold_number
from lab.variants import enumerate_all
from lab.walkforward import folds

REPO = Path(__file__).resolve().parent.parent
FIGS_DIR = REPO / "docs" / "report" / "figs"
SWEEP_JSON = REPO / "artifacts" / "sweep_results.json"

TOP_RANKED_ID = "DIR-TC-H10-short_crowded_long-0.5"
H8_ID = "DIR-TC-H8-fade_pos_extreme_only-1.0"
TOL = 1e-9

# Frozen F4-train cut, verbatim (docs/FREEZE.md §2.2) — asserted below to
# equal the committed pipeline's F4-train derivation.
FROZEN_FUNDING_HI_ABS = 8.385600000000002e-05

REGIME_COLORS = {
    "pos-mild": "#fde9c8",
    "pos-extreme": "#f4a460",
    "neg-mild": "#cfe3f5",
    "neg-extreme": "#5b8db8",
}

# Lane 2 power curve, hardcoded from
# docs/report/adversarial/lane2_gate_calibration.md §2 (the 0 bps row is the
# committed real sweep; all rows are DIR-TC-H8-fade_pos_extreme_only-1.0 at
# the 10 bps gate rung on pooled OOS).
LANE2_POWER = [
    # edge bps/bar, n_null, train rank, OOS Sharpe, OOS net %, null_p95,
    # top5 net %, gate passed
    (0, 1000, 4, 2.38, 15.50, 2.26, -2.13, False),
    (5, 300, 3, 2.94, 19.98, 2.17, 0.59, True),
    (10, 300, 1, 3.48, 24.62, 2.25, 3.38, True),
    (25, 1000, 1, 4.83, 39.62, 2.79, 12.19, True),
    (50, 300, 1, 6.30, 68.61, 3.11, 28.52, True),
]


def _assert_close(name: str, got: float, want: float, tol: float = TOL):
    if abs(got - want) > tol:
        raise AssertionError(
            f"consistency check failed: {name} recomputed {got!r} != "
            f"artifact {want!r} (tol {tol})")
    print(f"[figs] consistency OK: {name} = {got:.12g} (matches artifact)")


def _net(r: pd.Series) -> float:
    return float((1.0 + r).prod() - 1.0)


class TCContext:
    """The sweep's TC fold pipeline, reassembled from committed code/CSVs."""

    def __init__(self):
        self.panel = add_features(load_panel("full"))
        self.bars = self.panel[["open", "high", "low", "close", "volume"]]
        self.funding = self.panel["funding_rate"]
        thr_ref = derive_thresholds(
            self.panel.loc[self.panel.index < F1_TRAIN_END])
        ref_labels = label(self.panel, TaxonomyConfig("TC", thr_ref))
        self.folds = folds(self.panel.index, ref_labels)
        self.fold_labels = {}
        self.fold_thresholds = {}
        for f in self.folds:
            thr = derive_thresholds(self.panel.loc[f.train_idx])     # R1
            self.fold_thresholds[f.name] = thr
            self.fold_labels[f.name] = label(
                self.panel, TaxonomyConfig("TC", thr))
        idx = pd.DatetimeIndex([])
        for f in self.folds:
            idx = idx.append(f.oos_idx)
        self.pooled_oos_idx = idx.unique().sort_values()
        self.variants = {v.id: v for v in enumerate_all()}

    def run_variant(self, variant_id: str) -> dict:
        """Guarded @10 bps per-fold runs -> pooled OOS returns + trades."""
        amap = self.variants[variant_id].action_dict()
        segs, trades = [], []
        for f in self.folds:
            labs = self.fold_labels[f.name]
            w = rules.apply(labs, amap)
            wg = apply_dd_guard(w, self.bars, self.funding, GATE_COST_BPS,
                                labs)
            res = run_backtest(self.bars, wg, self.funding, GATE_COST_BPS)
            segs.append(res.bar_returns.loc[
                res.bar_returns.index.intersection(f.oos_idx)])
            trades.append(res.trades[res.trades["entry_ts"].isin(f.oos_idx)])
        pooled = pd.concat(segs).sort_index()
        return {"pooled_returns": pooled,
                "trades": pd.concat(trades, ignore_index=True)}


def _fold_boundaries(ctx: TCContext) -> list[tuple[str, int, int]]:
    """(fold name, start position, end position) on the pooled-OOS axis."""
    out, pos = [], 0
    for f in ctx.folds:
        out.append((f.name, pos, pos + len(f.oos_idx)))
        pos += len(f.oos_idx)
    return out


def fig1_pooled_oos_equity(ctx: TCContext, art: dict) -> dict:
    """Pooled-OOS equity overlay; returns the benchmark block numbers."""
    by_id = {v["id"]: v for v in art["variants"]}

    top = ctx.run_variant(TOP_RANKED_ID)
    h8 = ctx.run_variant(H8_ID)
    _assert_close(f"{TOP_RANKED_ID} pooled OOS Sharpe",
                  sharpe(top["pooled_returns"]),
                  by_id[TOP_RANKED_ID]["oos"]["sharpe"])
    _assert_close(f"{TOP_RANKED_ID} pooled OOS net",
                  _net(top["pooled_returns"]),
                  by_id[TOP_RANKED_ID]["oos"]["net_return"])
    _assert_close(f"{H8_ID} pooled OOS Sharpe", sharpe(h8["pooled_returns"]),
                  by_id[H8_ID]["oos"]["sharpe"])
    _assert_close(f"{H8_ID} pooled OOS net", _net(h8["pooled_returns"]),
                  by_id[H8_ID]["oos"]["net_return"])

    hodl_r = hodl(ctx.bars, ctx.funding,
                  GATE_COST_BPS).bar_returns.loc[ctx.pooled_oos_idx]
    vt_r = vol_target(ctx.bars, ctx.funding,
                      GATE_COST_BPS).bar_returns.loc[ctx.pooled_oos_idx]
    art_hodl = art["globals"]["taxonomies"]["TC"]["hodl_oos"]["10"]
    _assert_close("HODL pooled OOS Sharpe", sharpe(hodl_r),
                  art_hodl["sharpe"])
    _assert_close("HODL pooled OOS net", _net(hodl_r),
                  art_hodl["net_return"])

    x = np.arange(len(ctx.pooled_oos_idx))
    fig, ax = plt.subplots(figsize=(11, 5.5))
    curves = [
        (h8["pooled_returns"], f"{H8_ID} — near-miss, FAILED gate (top-5 "
                               "clause)", "#b22222", 1.6, "-"),
        (top["pooled_returns"], f"{TOP_RANKED_ID} — top train-ranked, "
                                "FAILED gate (3 clauses)", "#7a5fa0", 1.2,
         "-"),
        (vt_r, "vol-target benchmark (PR-5)", "#2e7d32", 1.0, "--"),
        (hodl_r, "HODL perp incl. funding (PR-5)", "#888888", 1.0, "-"),
    ]
    for r, lab_, color, lw, ls in curves:
        eq = (1.0 + r.loc[ctx.pooled_oos_idx].fillna(0.0)).cumprod()
        ax.plot(x, eq, label=lab_, color=color, lw=lw, ls=ls)
    ax.axhline(1.0, color="black", lw=0.8, label="flat (w = 0)")

    for name, start, end in _fold_boundaries(ctx):
        if start > 0:
            ax.axvline(start, color="black", lw=0.6, ls=":", alpha=0.6)
        seg = ctx.pooled_oos_idx[start:end]
        ax.text((start + end) / 2, 0.515,
                f"{name} OOS\n{seg[0]:%Y-%m-%d} → {seg[-1]:%Y-%m-%d}",
                ha="center", fontsize=7, color="#444444")
    ax.set_ylim(0.48, 1.30)
    ax.set_xlabel("pooled OOS bar # (4 embargoed fold-OOS segments, "
                  "concatenated — calendar gaps removed)")
    ax.set_ylabel("equity (start = 1.0 per pooled-OOS compounding)")
    ax.set_title("Pooled walk-forward OOS @10 bps RT — nothing passed the "
                 "pre-registered shipping gate (0/36)", fontsize=11)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "fig1_pooled_oos_equity.png", dpi=140)
    plt.close(fig)
    print("[figs] fig1_pooled_oos_equity.png")

    bench = {
        "hodl": {"sharpe": sharpe(hodl_r), "net": _net(hodl_r)},
        "flat": {"sharpe": 0.0, "net": 0.0},
        "vol_target": {"sharpe": sharpe(vt_r), "net": _net(vt_r),
                       "max_dd": float(
                           (1 - (1 + vt_r).cumprod()
                            / (1 + vt_r).cumprod().cummax()).max())},
        "h8": h8,
    }
    print("[figs] benchmark block (pooled OOS @10 bps RT, PR-5):")
    print(f"[figs]   HODL       sharpe={bench['hodl']['sharpe']:.4f} "
          f"net={bench['hodl']['net']:+.4%}")
    print(f"[figs]   flat       sharpe=0.0000 net=+0.0000%")
    print(f"[figs]   vol-target sharpe={bench['vol_target']['sharpe']:.4f} "
          f"net={bench['vol_target']['net']:+.4%} "
          f"max_dd={bench['vol_target']['max_dd']:.4%}")
    return bench


def fig2_h8_concentration(ctx: TCContext, art: dict, h8_run: dict) -> None:
    by_id = {v["id"]: v for v in art["variants"]}
    _assert_close("H8 top5_net (recomputed set)",
                  _top5_net(h8_run, ctx.pooled_oos_idx),
                  by_id[H8_ID]["hooks"]["top5_net"])

    r = h8_run["pooled_returns"].loc[ctx.pooled_oos_idx].fillna(0.0)
    eq = (1.0 + r).cumprod()
    x = np.arange(len(ctx.pooled_oos_idx))

    trades = h8_run["trades"]
    top5 = trades.loc[trades["pnl_pct"].nlargest(5).index]

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(x, eq, color="#b22222", lw=1.4,
            label=f"{H8_ID} pooled OOS equity @10 bps (guarded)")
    for _, t in top5.iterrows():
        i0 = ctx.pooled_oos_idx.searchsorted(t["entry_ts"])
        i1 = ctx.pooled_oos_idx.searchsorted(t["exit_ts"])
        ax.axvspan(i0, max(i1, i0 + 1), color="#f4a460", alpha=0.55,
                   zorder=0)
        ax.annotate(f"{t['entry_ts']:%Y-%m-%d}\n{t['pnl_pct']:+.2%}",
                    xy=(i0, float(eq.iloc[min(i1, len(eq) - 1)])),
                    xytext=(i0, float(eq.iloc[min(i1, len(eq) - 1)]) + 0.025),
                    fontsize=7, ha="center", color="#7a3b00")
    for name, start, end in _fold_boundaries(ctx):
        if start > 0:
            ax.axvline(start, color="black", lw=0.6, ls=":", alpha=0.6)
        ax.text((start + end) / 2, 0.972, name, ha="center", fontsize=8,
                color="#444444")
    ax.axhline(1.0, color="black", lw=0.6, alpha=0.6)
    top5_net = by_id[H8_ID]["hooks"]["top5_net"]
    net = by_id[H8_ID]["oos"]["net_return"]
    ax.set_title(
        "The concentration picture — FAILED candidate "
        f"{H8_ID}\n5 highlighted trades carry >100% of the OOS gain: "
        f"net {net:+.2%} → {top5_net:+.2%} after pre-registered top-5 "
        "removal (the failing clause)", fontsize=10)
    ax.set_xlabel("pooled OOS bar # (fold segments concatenated)")
    ax.set_ylabel("equity")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "fig2_h8_concentration.png", dpi=140)
    plt.close(fig)
    print("[figs] fig2_h8_concentration.png")


def _top5_net(run: dict, pooled_oos_idx: pd.Index) -> float:
    from lab.hooks import top_n_removal
    return top_n_removal(run["trades"], run["pooled_returns"],
                         pooled_oos_idx, 5)


def fig3_null_distribution(ctx: TCContext, art: dict) -> None:
    """Regenerate the 1000-draw pooled null for H8 with the sweep's seeds."""
    by_id = {v["id"]: v for v in art["variants"]}
    art_p95 = by_id[H8_ID]["hooks"]["null_p95"]
    art_sharpe = by_id[H8_ID]["hooks"]["unguarded_oos_sharpe"]
    n_null = art["globals"]["n_null"]

    t0 = time.perf_counter()
    amap = ctx.variants[H8_ID].action_dict()
    fold_shuffles = [
        (episode_shuffles(ctx.fold_labels[f.name], n_null,
                          SEED_BASE + _fold_number(f.name)), f.oos_idx)
        for f in ctx.folds
    ]
    null = shuffle_null_pooled(
        lambda labs: rules.apply(labs, amap), fold_shuffles, ctx.bars,
        ctx.funding, GATE_COST_BPS)
    wall = time.perf_counter() - t0
    _assert_close("H8 null_p95 (1000 draws, seeds 17+fold#)",
                  null["p95"], art_p95)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(null["null_sharpes"], bins=50, color="#9bb7d4",
            edgecolor="white",
            label=f"episode-shuffle null, n={n_null} pooled-OOS Sharpes\n"
                  "(common draws, numpy default_rng(17 + fold#), "
                  "unguarded @10 bps)")
    ax.axvline(null["p95"], color="#2f5d8a", lw=1.6, ls="--",
               label=f"null p95 = {null['p95']:.3f} (gate hurdle)")
    ax.axvline(art_sharpe, color="#b22222", lw=1.8,
               label=f"{H8_ID}\nobserved pooled-OOS Sharpe = "
                     f"{art_sharpe:.3f} (one-sided p ≈ "
                     f"{float(np.mean(null['null_sharpes'] >= art_sharpe)):.3f})")
    ax.set_xlabel("pooled OOS Sharpe under episode-shuffled regime labels")
    ax.set_ylabel("draws")
    ax.set_title(
        "Null-clause anatomy of the near-miss — the 0.12-Sharpe margin is "
        "inside 36-variant selection noise\n(regenerated from committed "
        f"CSVs with the sweep's exact seeds in {wall:.1f}s; p95 matches "
        "artifacts/sweep_results.json to 1e-9)", fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "fig3_null_distribution.png", dpi=140)
    plt.close(fig)
    print(f"[figs] fig3_null_distribution.png "
          f"(null regeneration wall time: {wall:.1f}s)")


def fig4_gate_power() -> None:
    edges = [r[0] for r in LANE2_POWER]
    top5 = [r[6] for r in LANE2_POWER]
    nets = [r[4] for r in LANE2_POWER]
    passed = [r[7] for r in LANE2_POWER]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(edges, top5, color="#2f5d8a", lw=1.4, zorder=2)
    for e, t, p in zip(edges, top5, passed):
        ax.scatter([e], [t], s=70, zorder=3,
                   color="#2e7d32" if p else "#b22222",
                   label=None)
        ax.annotate("PASS" if p else "fail", (e, t),
                    xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=8,
                    color="#2e7d32" if p else "#b22222")
    ax.axhline(0.0, color="black", lw=0.8, ls="--",
               label="top-5 clause boundary (top5_net > 0)")
    ax.annotate("real sweep (0 bps planted):\nfails ONLY the top-5 clause",
                xy=(0, top5[0]), xytext=(8, 6.5), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax2 = ax.twinx()
    ax2.plot(edges, nets, color="#999999", lw=1.0, ls=":",
             label="pooled OOS net % (right axis)")
    ax2.set_ylabel("pooled OOS net return (%)", color="#777777")
    ax.set_xlabel("planted regime-conditional edge (bps per positioned bar) "
                  "on the REAL panel")
    ax.set_ylabel("top-5-removal net return (%) — the binding clause")
    ax.set_title(
        "Gate power curve (unmodified pre-registered pipeline, planted "
        "edges, 10 bps RT)\nrobust detection at ≥10 bps/bar, marginal at "
        "5 — hardcoded from "
        "docs/report/adversarial/lane2_gate_calibration.md §2", fontsize=9)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "fig4_gate_power.png", dpi=140)
    plt.close(fig)
    print("[figs] fig4_gate_power.png")


def fig5_regime_ribbon(ctx: TCContext) -> None:
    f4_train_thr = ctx.fold_thresholds["F4"]
    if abs(f4_train_thr["funding_hi_abs"] - FROZEN_FUNDING_HI_ABS) > 1e-15:
        raise AssertionError(
            "frozen funding_hi_abs drifted from the F4-train derivation: "
            f"{f4_train_thr['funding_hi_abs']!r} != "
            f"{FROZEN_FUNDING_HI_ABS!r}")
    print(f"[figs] consistency OK: frozen funding_hi_abs = "
          f"{FROZEN_FUNDING_HI_ABS!r} (== F4-train derivation)")

    labs = label(ctx.panel,
                 TaxonomyConfig("TC",
                                {"funding_hi_abs": FROZEN_FUNDING_HI_ABS}))
    eps = episodes(labs)

    fig, ax = plt.subplots(figsize=(12, 5))
    for _, ep in eps.iterrows():
        end = ep["end"] + pd.Timedelta(hours=4)
        ax.axvspan(ep["start"], end, color=REGIME_COLORS[ep["label"]],
                   lw=0, zorder=0)
    ax.plot(ctx.panel.index, ctx.panel["close"], color="#222222", lw=0.9,
            zorder=2, label="BTCUSDT 4h close")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c)
               for c in REGIME_COLORS.values()]
    shares = labs.value_counts(normalize=True)
    labels_leg = [f"{k} ({shares.get(k, 0.0):.1%} of bars)"
                  for k in REGIME_COLORS]
    ax.legend(handles + ax.get_legend_handles_labels()[0],
              labels_leg + ["BTCUSDT 4h close"], fontsize=8,
              loc="upper right")
    ax.set_ylabel("price (USDT)")
    ax.set_title(
        "TC regime ribbon over the full-stack window — frozen F4-train "
        "threshold |funding_8h| q80 = 8.3856e-05\n(the shipped monitor's "
        "classifier; descriptive only — no variant on this taxonomy "
        "passed the shipping gate)", fontsize=10)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGS_DIR / "fig5_regime_ribbon.png", dpi=140)
    plt.close(fig)
    print("[figs] fig5_regime_ribbon.png")


def fig6_deep(skip_compute: bool = False) -> None:
    record = deep_replay.compute()
    deep_replay.render_figure(record, FIGS_DIR / "fig6_deep_replay.png")
    print("[figs] fig6_deep_replay.png (via lab.deep_replay — "
          "falsification context, never a track record)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-null", action="store_true",
                        help="skip fig3's 1000-draw null regeneration "
                             "(iteration only; committed figures need the "
                             "full run)")
    args = parser.parse_args(argv)

    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    art = json.loads(SWEEP_JSON.read_text())
    print("[figs] building TC fold context from committed CSVs ...")
    ctx = TCContext()

    bench = fig1_pooled_oos_equity(ctx, art)
    fig2_h8_concentration(ctx, art, bench["h8"])
    if args.skip_null:
        print("[figs] fig3 SKIPPED (--skip-null)")
    else:
        fig3_null_distribution(ctx, art)
    fig4_gate_power()
    fig5_regime_ribbon(ctx)
    fig6_deep()
    print(f"[figs] done -> {FIGS_DIR}")


if __name__ == "__main__":
    main()
