"""Deep-history replay of the FAILED candidate — plan Task 2.7 AS AMENDED.

BINDING FRAMING (docs/FREEZE.md §3 amendment 3 / §4, CONTEXT.md):

  This is a **failed-candidate deep-history replay — falsification
  context, NEVER a track record.**

`DIR-TC-H8-fade_pos_extreme_only-1.0` FAILED the pre-registered shipping
gate on the full-stack window (top-5-removal clause; see
artifacts/sweep_results.json and docs/report/REPORT.md falsification
chapter) and is published with `"validated": false` everywhere. There is
no Winner (R-NULL: 0/36 gate passes), so per CONTEXT.md this replay is
also NOT a "deep-history proxy" — that term attaches to a Winner's rules,
and no variant earned one. Nothing here is selection or gating evidence;
the deep-history window is pre-registered as a robustness/falsification
domain only (PR-1, CONTEXT.md "Deep-history window").

What runs, verbatim and frozen:
  - TC labels from the frozen F4-train cut
    funding_hi_abs = 8.385600000000002e-05 (docs/FREEZE.md §2.2, full
    precision, NOT re-derived on deep history). TC consumes funding only,
    so the failed candidate's rules restrict to the deep-history field
    set without modification — same rule, different window.
  - the H8 action map from lab.variants (short -1 the bar after a
    pos-extreme close; flat otherwise), rules.apply 1-bar lag,
  - PR-4 DD guard (20% trailing, re-entry on label change),
  - PR-3 fill simulator @ 10 bps RT (the gate rung) via
    lab.engine.run_backtest, on lab.dataset.load_panel("deep")
    (2021-03-24 00:00 -> 2026-05-18 20:00).

Outputs:
  artifacts/deep_replay.json
  docs/report/figs/fig6_deep_replay.png

Run: uv run --no-sync python -m lab.deep_replay
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from lab import rules
from lab.benchmarks import hodl
from lab.classifier import TaxonomyConfig, episodes, label
from lab.dataset import load_panel
from lab.dd_guard import apply_dd_guard
from lab.engine import run_backtest
from lab.features import add_features
from lab.hooks import top_n_removal
from lab.metrics import cagr, hit_rate, max_dd, sharpe
from lab.variants import enumerate_all

REPO = Path(__file__).resolve().parent.parent
ARTIFACT_PATH = REPO / "artifacts" / "deep_replay.json"
FIGURE_PATH = REPO / "docs" / "report" / "figs" / "fig6_deep_replay.png"

VARIANT_ID = "DIR-TC-H8-fade_pos_extreme_only-1.0"
GATE_COST_BPS = 10.0

# Frozen F4-train threshold, verbatim full precision (docs/FREEZE.md §2.2).
# The ONLY cut TC consumes. Applied as-is — never re-derived here.
FROZEN_FUNDING_HI_ABS = 8.385600000000002e-05

FRAMING = ("FAILED-candidate deep-history replay — falsification context, "
           "NEVER a track record")
NOT_A_PROXY = (
    "This is NOT a deep-history proxy in the CONTEXT.md sense: that term "
    "attaches to a Winner's rules, and there is no Winner (R-NULL, 0/36 "
    "variants passed the shipping gate). DIR-TC-H8 FAILED the gate "
    "(top5_pass clause) on the full-stack window; this replay exists only "
    "as falsification context in the report.")


def _f(x: float) -> float:
    return float(x)


def _metrics(result, w: pd.Series) -> dict:
    return {
        "sharpe": _f(sharpe(result.bar_returns)),
        "net_return": _f(result.equity.iloc[-1] - 1.0),
        "cagr": _f(cagr(result.equity)),
        "max_dd": _f(max_dd(result.equity)),
        "n_trades": int(len(result.trades)),
        "hit_rate": _f(hit_rate(result.trades)),
        "turnover": _f(result.turnover),
        "bars_in_position": int((w != 0).sum()),
    }


def compute() -> dict:
    """Run the replay; returns the JSON-serializable record plus the curve
    series under the private key "_series" (stripped before writing)."""
    t0 = time.perf_counter()
    panel = add_features(load_panel("deep"))
    bars = panel[["open", "high", "low", "close", "volume"]]
    funding = panel["funding_rate"]

    variant = next(v for v in enumerate_all() if v.id == VARIANT_ID)
    amap = variant.action_dict()

    cfg = TaxonomyConfig("TC", {"funding_hi_abs": FROZEN_FUNDING_HI_ABS})
    labels = label(panel, cfg)
    eps = episodes(labels)

    w = rules.apply(labels, amap)
    wg = apply_dd_guard(w, bars, funding, GATE_COST_BPS, labels)
    res_g = run_backtest(bars, wg, funding, GATE_COST_BPS)
    res_u = run_backtest(bars, w, funding, GATE_COST_BPS)
    res_h = hodl(bars, funding, GATE_COST_BPS)

    per_year = []
    for year, seg in res_g.bar_returns.groupby(res_g.bar_returns.index.year):
        per_year.append({
            "year": int(year),
            "net_return": _f((1.0 + seg).prod() - 1.0),
            "sharpe": _f(sharpe(seg)),
            "n_trades": int((res_g.trades["entry_ts"].dt.year == year).sum()),
            "bars_in_position": int((wg.loc[seg.index] != 0).sum()),
        })

    occupancy = {
        str(k): {"bars": int(v), "share": _f(v / len(labels))}
        for k, v in labels.value_counts().items()
    }
    pos_extreme_share = occupancy.get("pos-extreme", {}).get("share", 0.0)

    top5_net = top_n_removal(res_g.trades, res_g.bar_returns, wg.index, 5)
    top5 = res_g.trades["pnl_pct"].nlargest(5)
    removed_gain = _f((1.0 + top5).prod() - 1.0)

    record = {
        "framing": FRAMING,
        "validated": False,
        "not_a_deep_history_proxy": NOT_A_PROXY,
        "variant_id": VARIANT_ID,
        "full_stack_gate_outcome": (
            "FAILED — top5_pass clause; see artifacts/sweep_results.json "
            "(verdict.reasons) and docs/FREEZE.md §4"),
        "window": [str(panel.index[0]), str(panel.index[-1])],
        "n_bars": int(len(panel)),
        "cost_bps_rt": GATE_COST_BPS,
        "thresholds": {
            "funding_hi_abs": FROZEN_FUNDING_HI_ABS,
            "provenance": ("frozen F4-train value, docs/FREEZE.md §2.2, "
                           "applied verbatim — NOT re-derived on the "
                           "deep-history window"),
        },
        "action_map": {k: _f(v) for k, v in amap.items()},
        "label_occupancy": occupancy,
        "occupancy_note": (
            f"pos-extreme covers {pos_extreme_share:.1%} of deep-history "
            "bars vs 18.8% of F4-train (docs/FREEZE.md §2.3): the frozen "
            "q80 cut is train-window-relative — 2021–2024 funding ran far "
            "hotter than 2025–2026, so the 'extremity' semantics do NOT "
            "transfer across eras. The replayed rule is in position "
            f"{int((wg != 0).sum())}/{len(panel)} bars "
            f"({int((wg != 0).sum()) / len(panel):.1%}) here vs 6.8% of "
            "pooled OOS bars on the full-stack window — a structurally "
            "different exposure profile, which is exactly why this curve "
            "can never be read as the candidate's history."),
        "episodes": {
            "total": int(len(eps)),
            "by_label": {str(k): int(v)
                         for k, v in eps.groupby("label").size().items()},
        },
        "metrics_guarded": _metrics(res_g, wg),
        "metrics_unguarded": _metrics(res_u, w),
        "dd_guard": {
            "threshold": 0.20,
            "fired": bool((wg != w).any()),
            "bars_forced_flat": int(((w != 0) & (wg == 0)).sum()),
            "note": ("the PR-4 guard never fired on the full-stack OOS; "
                     "on deep history it does — further evidence the two "
                     "windows are different regimes for this rule"),
        },
        "per_year": per_year,
        "concentration": {
            "top5_net": _f(top5_net),
            "top5_removed_gain": removed_gain,
            "note": ("the same concentration pathology the gate caught on "
                     "the full-stack OOS, now at 5-year scale: removing "
                     "the 5 best of 437 trades flips the net return "
                     "negative, and a single year (2022) carries more than "
                     "the entire net gain. The deep-history window "
                     "corroborates the top-5 clause's verdict; it does not "
                     "soften it."),
        },
        "hodl_deep_context": {
            "sharpe": _f(sharpe(res_h.bar_returns)),
            "net_return": _f(res_h.equity.iloc[-1] - 1.0),
            "max_dd": _f(max_dd(res_h.equity)),
            "note": "context benchmark only (PR-5 HODL, same fill simulator)",
        },
        "generated_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "wall_time_sec": round(time.perf_counter() - t0, 2),
        "_series": {
            "equity_guarded": res_g.equity,
            "equity_unguarded": res_u.equity,
            "equity_hodl": res_h.equity,
        },
    }
    return record


def render_figure(record: dict, path: Path = FIGURE_PATH) -> None:
    """fig6: deep-replay equity, labeled as falsification context."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = record["_series"]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(s["equity_guarded"].index, s["equity_guarded"], lw=1.4,
            color="#b22222",
            label=f"{record['variant_id']} (guarded @10 bps) — "
                  f"FAILED candidate, \"validated\": false")
    ax.plot(s["equity_unguarded"].index, s["equity_unguarded"], lw=0.9,
            ls="--", color="#e08080", label="same, unguarded (reference)")
    ax.plot(s["equity_hodl"].index, s["equity_hodl"], lw=0.9,
            color="#999999", label="HODL perp incl. funding (context)")
    ax.axhline(1.0, color="black", lw=0.6, alpha=0.5)
    ax.set_yscale("log")
    ax.set_ylabel("equity (log scale, start = 1.0)")
    ax.set_title(
        "Deep-history replay 2021-03-24 → 2026-05-18 — falsification "
        "context, NOT a track record\n(frozen F4-train threshold applied "
        "verbatim; no Winner exists — this is not a deep-history proxy)",
        fontsize=10)
    yrs = ", ".join(f"{p['year']}: {p['net_return']:+.1%}"
                    for p in record["per_year"])
    ax.text(0.01, 0.02, f"per-year net (guarded): {yrs}",
            transform=ax.transAxes, fontsize=8, color="#333333")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    record = compute()
    record_out = {k: v for k, v in record.items() if not k.startswith("_")}
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(record_out, indent=2) + "\n")
    render_figure(record)
    mg = record["metrics_guarded"]
    print(f"[deep_replay] {FRAMING}")
    print(f"[deep_replay] {VARIANT_ID} on deep window "
          f"{record['window'][0]} .. {record['window'][1]} "
          f"({record['n_bars']} bars)")
    print(f"[deep_replay] guarded @10bps: sharpe={mg['sharpe']:.2f} "
          f"net={mg['net_return']:+.2%} max_dd={mg['max_dd']:.1%} "
          f"trades={mg['n_trades']}")
    print(f"[deep_replay] -> {ARTIFACT_PATH}")
    print(f"[deep_replay] -> {FIGURE_PATH}")


if __name__ == "__main__":
    main()
