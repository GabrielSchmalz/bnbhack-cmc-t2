"""Planted-edge power calibration for the W-sweep (registration §9, lane W-B).

Replicates the frozen lane-2 methodology
(docs/report/adversarial/lane2_gate_calibration.md §1) on the registered
W panels, aligned with the registered T-D D1 map
``fade_extremes_graded_sym`` — the map family behind all four committed
gate passes (artifacts/w/sweep_results_w.json). The question it answers:
would the unmodified W machinery DETECT a known regime-conditional edge
planted on each real panel, and at what size?

Construction (lane-2 §1 verbatim, extended to the graded symmetric map):
  - Injection mask from the DECISION bar: bar t carries drift iff
    label[t-1] is hot under the FULL-WINDOW T-D cuts of the unperturbed
    panel (q60/q90 of |funding_rate_8h|; lane-2's mask convention — the
    sweep re-derives per-fold cuts, so capture takes the same realistic
    threshold-mismatch haircut lane-2 documented). pos-hi/pos-x at t-1 ->
    DOWNWARD drift at t (the D1 short leg earns); neg-hi/neg-x -> UPWARD
    drift (the long leg earns). The drift magnitude is FLAT across the
    hi/x rungs; only the variant's exposure is graded.
  - Drift: per masked bar, m_t ~ Normal(edge, edge) from
    numpy.random.default_rng(99) in index order (noise sd = mean, lane-2
    verbatim); d_t = +m_t on pos bars, -m_t on neg bars, 0 elsewhere.
  - Price path, multiplicative and self-consistent:
    M_open[t] = prod_{s<t}(1-d_s), M_close[t] = M_open[t]*(1-d_t);
    open' = open*M_open, close' = close*M_close; high/low scaled by
    M_close then enveloped to contain open'/close'. Engine identity:
    r'[t] = (1+r[t])(1-d_t)-1 on the open-to-open convention, so a short
    held during bar t earns +d_t expected.
  - Labels and funding untouched: the perturbation is applied to the RAW
    bars rows (warmup rows before the span keep multiplier 1; post-span
    rows carry the final multiplier and are trimmed by the assembly) and
    the panel is REBUILT through the unmodified panels_w.build_w_panel
    with the original funding/fg/oi sources. Every price-derived Feature
    (pc_24h, rsi14_1d, close_vs_sma200_1d) is therefore recomputed from
    the perturbed closes — a fully consistent world; funding_rate_8h and
    the T-D labels are invariant by construction.

Execution: run_calibration_cell drives the UNMODIFIED lab.sweep_w
.run_w_sweep through its documented panel_loader injection point — one
(panel, rung) per run, all of that panel's registered taxonomies, the
registered D = 1000 common draws and 200 calibration draws — writing to
artifacts/w/calibration/P-<ASSET>_<rung>bps/sweep_results_w.json. The
committed artifact dir artifacts/w is guarded against
(_assert_isolated_out_dir). Registered rungs: 5/10/25 bps/bar per §9.
The registered OOS-contact event already happened (the committed sweep);
these runs evaluate planted derivative worlds of the same rows, so the
sweep CLI tripwire is not re-armed here.

Run one cell:  uv run --no-sync python -m lab.calibration_w \
                   --asset BTC --rung 10 --jobs 6
Chain of nine: scripts/run_w_calibration.sh (resumable, sequential).
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lab.classifiers_w import derive_thresholds_w, label_w
from lab.dataset import DATA_DIR
from lab.oi_cg import load_oi_cg_daily
from lab.panels_w import (
    _BARS_CSV,
    _FUNDING_CSV,
    ASSETS_W,
    OI_CG_CSV,
    W_SPANS,
    build_w_panel,
)
from lab.sweep_w import N_DRAWS_W, run_w_sweep

# Lane-2 drift seed, verbatim (single drift seed per rung — disclosed
# limitation there and here).
DRIFT_SEED_W = 99
# §9 registered rung set (bps/bar of true conditional edge).
RUNGS_BPS_W = (5, 10, 25)
# The D1 hot labels: decision-bar labels whose NEXT bar carries drift.
HOT_POS_W = ("pos-hi", "pos-x")     # D1 short leg: downward drift
HOT_NEG_W = ("neg-hi", "neg-x")     # D1 long leg: upward drift
# Output root for the nine calibration cells; the committed sweep
# artifact lives one level up and is NEVER written by this module.
CAL_OUT_ROOT_W = "artifacts/w/calibration"
_PRODUCTION_W_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "w"

OHLC_COLS = ("open", "high", "low", "close")


def injection_masks(labels: pd.Series) -> tuple[pd.Series, pd.Series]:
    """(pos_mask, neg_mask): bar t is masked iff label[t-1] is hot.

    Mirrors the rules.apply 1-bar lag: the regime known at the close of
    bar t-1 positions the variant during bar t, so bar t is where the
    drift must land (lane-2 probe (iii): the tent peaks at shift 1).
    Bar 0 has no decision bar and is never masked.
    """
    lagged = labels.shift(1)
    return lagged.isin(HOT_POS_W), lagged.isin(HOT_NEG_W)


def drift_series(pos_mask: pd.Series, neg_mask: pd.Series, edge_bps: float,
                 seed: int = DRIFT_SEED_W) -> pd.Series:
    """Per-bar drift d_t: +m on pos bars, -m on neg bars, 0 elsewhere.

    m ~ Normal(edge, edge) (mean = sd, lane-2 verbatim), one draw per
    masked bar in index order from default_rng(seed). The price is later
    multiplied by (1 - d_t), so positive d_t drifts the price DOWN.
    """
    edge = float(edge_bps) / 1e4
    masked = (pos_mask | neg_mask).to_numpy()
    rng = np.random.default_rng(seed)
    m = rng.normal(edge, edge, int(masked.sum()))
    d = np.zeros(len(masked))
    d[masked] = m
    d[neg_mask.to_numpy()] *= -1.0
    return pd.Series(d, index=pos_mask.index)


def perturb_prices(open_: pd.Series, high: pd.Series, low: pd.Series,
                   close: pd.Series, d: pd.Series
                   ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Lane-2 multiplicative price path on one index.

    M_open[t] = prod_{s<t}(1-d_s); M_close[t] = M_open[t]*(1-d_t);
    open' = open*M_open, close' = close*M_close (the close of bar t sits
    at open[t+1] time, so the whole bar-t drift lands inside bar t);
    high/low are scaled by M_close then enveloped to contain open'/close'.
    """
    m_close = (1.0 - d).cumprod()
    m_open = m_close.shift(1).fillna(1.0)
    o = open_ * m_open
    c = close * m_close
    h = pd.concat([high * m_close, o, c], axis=1).max(axis=1)
    lo = pd.concat([low * m_close, o, c], axis=1).min(axis=1)
    return o, h, lo, c


def plant_bars(bars: pd.DataFrame, d: pd.Series) -> pd.DataFrame:
    """Apply the drift multipliers to a RAW bars frame (open_time schema).

    d is indexed by the panel grid (the registered span). Rows before the
    span keep multiplier 1 (warmup feeds Feature construction untouched);
    rows after the span carry the final accumulated multiplier (they are
    trimmed by the assembly; carrying the product keeps the path
    consistent regardless). Duplicate open_time rows (D4.1) receive the
    same multiplier. A span row off the d grid is a wiring error and
    raises.
    """
    out = bars.copy()
    ot = pd.to_datetime(out["open_time"])
    m_close = (1.0 - d).cumprod()
    m_open = m_close.shift(1).fillna(1.0)
    final = float(m_close.iloc[-1]) if len(m_close) else 1.0

    mo = ot.map(m_open).to_numpy(dtype=float, copy=True)
    mc = ot.map(m_close).to_numpy(dtype=float, copy=True)
    if len(d):
        before = (ot < d.index[0]).to_numpy()
        after = (ot > d.index[-1]).to_numpy()
    else:
        before = np.ones(len(ot), dtype=bool)
        after = np.zeros(len(ot), dtype=bool)
    mo[before], mc[before] = 1.0, 1.0
    mo[after], mc[after] = final, final
    if np.isnan(mo).any() or np.isnan(mc).any():
        bad = ot[np.isnan(mo) | np.isnan(mc)].iloc[0]
        raise ValueError(
            f"bars row {bad} lies inside the span but off the panel grid — "
            "drift multipliers are undefined there")

    o = out["open"].to_numpy(dtype=float) * mo
    c = out["close"].to_numpy(dtype=float) * mc
    h = np.maximum(out["high"].to_numpy(dtype=float) * mc, np.maximum(o, c))
    lo = np.minimum(out["low"].to_numpy(dtype=float) * mc, np.minimum(o, c))
    out["open"], out["high"], out["low"], out["close"] = o, h, lo, c
    return out


def build_planted_panel_from_sources(
        bars: pd.DataFrame, funding: pd.DataFrame, fg: pd.DataFrame,
        span_start, span_end, edge_bps: float, *,
        oi_cg_daily: pd.Series | None = None,
        seed: int = DRIFT_SEED_W) -> tuple[pd.DataFrame, dict]:
    """Plant the D1-aligned drift into source frames -> (panel, meta).

    Builds the UNPERTURBED panel first (mask substrate: full-window T-D
    cuts on funding_rate_8h, invariant under the price perturbation),
    perturbs the raw bars, then rebuilds through the same unmodified
    assembly. meta carries the base panel, masks, thresholds and d for
    logging/tests.
    """
    base = build_w_panel(bars, funding, fg, span_start, span_end,
                         oi_cg_daily=oi_cg_daily)
    thresholds = derive_thresholds_w(base, "TD")
    labels = label_w(base, "TD", thresholds)
    pos_mask, neg_mask = injection_masks(labels)
    d = drift_series(pos_mask, neg_mask, edge_bps, seed)
    planted = build_w_panel(plant_bars(bars, d), funding, fg,
                            span_start, span_end, oi_cg_daily=oi_cg_daily)
    meta = {"base_panel": base, "thresholds": thresholds,
            "pos_mask": pos_mask, "neg_mask": neg_mask, "d": d}
    return planted, meta


def build_planted_panel(asset: str, edge_bps: float, *,
                        seed: int = DRIFT_SEED_W) -> pd.DataFrame:
    """Planted panel for a registered asset from the committed CSVs."""
    if asset not in W_SPANS:
        raise ValueError(
            f"unknown W asset {asset!r}; expected one of {list(ASSETS_W)}")
    start, end = W_SPANS[asset]
    lab_dir = DATA_DIR / "lab"
    backfill_dir = DATA_DIR / "backfill"
    planted, meta = build_planted_panel_from_sources(
        bars=pd.read_csv(lab_dir / _BARS_CSV[asset]),
        funding=pd.read_csv(backfill_dir / _FUNDING_CSV[asset]),
        fg=pd.read_csv(backfill_dir / "fear_greed.csv"),
        span_start=start,
        span_end=end,
        edge_bps=edge_bps,
        oi_cg_daily=load_oi_cg_daily(OI_CG_CSV) if asset == "BTC" else None,
        seed=seed,
    )
    n_pos = int(meta["pos_mask"].sum())
    n_neg = int(meta["neg_mask"].sum())
    print(f"[w-cal] P-{asset} planted {edge_bps} bps/bar (seed {seed}): "
          f"{n_pos} pos-masked + {n_neg} neg-masked of {len(planted)} bars; "
          f"full-window cuts c_hi={meta['thresholds']['c_hi']:.4g} "
          f"c_x={meta['thresholds']['c_x']:.4g}; "
          f"net log drift {float(np.log1p(-meta['d']).sum()):+.3f}",
          flush=True)
    return planted


def _assert_isolated_out_dir(cell_dir) -> None:
    """Refuse to write into artifacts/w itself — the committed sweep
    artifact (sweep_results_w.json) lives there and is an input of
    record for the adversarial lanes."""
    if Path(cell_dir).resolve() == _PRODUCTION_W_DIR:
        raise ValueError(
            f"calibration out dir {cell_dir} is the production W artifact "
            "directory; calibration cells must write under "
            f"{CAL_OUT_ROOT_W}/<panel>_<rung>bps")


def run_calibration_cell(asset: str, rung_bps: int, *,
                         draws: int = N_DRAWS_W, jobs: int = 1,
                         out_root: str = CAL_OUT_ROOT_W,
                         panel_builder=None, boundaries: dict | None = None,
                         taxonomies: dict | None = None) -> dict:
    """One calibration cell: UNMODIFIED run_w_sweep on the planted panel.

    panel_builder(asset, rung_bps) -> panel overrides build_planted_panel
    (toy-test injection, like run_w_sweep's own panel_loader);
    boundaries/taxonomies forward to run_w_sweep's documented injection
    points. Production calls use the registered defaults throughout.
    Writes <out_root>/P-<asset>_<rung>bps/sweep_results_w.json.
    """
    builder = panel_builder or build_planted_panel
    cell_dir = Path(out_root) / f"P-{asset}_{int(rung_bps)}bps"
    _assert_isolated_out_dir(cell_dir)

    def loader(a: str) -> pd.DataFrame:
        if a != asset:
            raise ValueError(f"loader built for {asset!r}, got {a!r}")
        return builder(a, rung_bps)

    return run_w_sweep(panels=(asset,), draws=draws, out_dir=str(cell_dir),
                       panel_loader=loader, boundaries=boundaries,
                       taxonomies=taxonomies, workers=jobs)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="W-sweep planted-edge power calibration (§9, lane-2 "
                    "method on the W panels). One (asset, rung) cell per "
                    "invocation; never touches artifacts/w itself.")
    parser.add_argument("--asset", required=True, choices=list(ASSETS_W))
    parser.add_argument("--rung", required=True, type=int,
                        help="planted edge in bps/bar (registered rungs: "
                             f"{RUNGS_BPS_W})")
    parser.add_argument("--draws", type=int, default=N_DRAWS_W,
                        help="common null draws (registered 1000)")
    parser.add_argument("--jobs", type=int, default=1,
                        help="fork-pool workers (scheduling only)")
    parser.add_argument("--out-root", default=CAL_OUT_ROOT_W)
    args = parser.parse_args(argv)
    if args.rung <= 0:
        parser.error("--rung must be a positive bps/bar integer")

    t0 = time.perf_counter()
    results = run_calibration_cell(args.asset, args.rung, draws=args.draws,
                                   jobs=args.jobs, out_root=args.out_root)
    n = len(results["variants"])
    passes = sum(r["verdict"]["passed"] for r in results["variants"])
    cell = Path(args.out_root) / f"P-{args.asset}_{args.rung}bps"
    print(f"[w-cal] P-{args.asset} {args.rung}bps done in "
          f"{time.perf_counter() - t0:.1f}s: gate passes {passes}/{n} "
          f"-> {cell / 'sweep_results_w.json'}", flush=True)


if __name__ == "__main__":
    main()
