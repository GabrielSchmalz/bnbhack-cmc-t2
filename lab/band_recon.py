"""Band reconciliation — lab-only discovery aid (plan Task 2.2).

NOT part of the shipped pipeline. Cross-tabs the distilled taxonomy labels
(T-A / T-B / T-C, lab/classifier.py) against the rm17-derivs Bands
(`4h::region01/02/03` = balanced / squeeze_prone / stressed, CONTEXT.md) on
their overlap — every full-stack panel bar where `band` is non-NaN
(2025-10-04 .. 2026-05-18).

Method (descriptive, leak-free by construction):
  * Thresholds come from lab.features.derive_thresholds on the PRE-overlap
    span 2025-04-03 00:00 <= t < 2025-10-01 00:00 (the F1-train convention
    of lab/walkforward.py: train = bars strictly before the boundary). The
    Band span starts 2025-10-04, so no overlap row touches the derivation.
  * Bands are a comparison axis only — never a fit target, never shipped.

Per taxonomy this script emits: a band x regime occupancy cross-tab
(counts + row %), normalized mutual information computed from the
contingency table with numpy (NMI = MI / mean(H_band, H_regime), natural
log; sklearn-free), and an episode-count comparison (classifier.episodes on
our labels vs on the Band series, same overlap index).

Run:  uv run --no-sync python -m lab.band_recon
Out:  docs/report/band_recon.md  (+ a stdout summary)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from lab.classifier import TaxonomyConfig, episodes, label
from lab.dataset import load_panel
from lab.features import add_features, derive_thresholds

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "docs" / "report" / "band_recon.md"

# F1 boundary (lab/walkforward.py _BOUNDARIES); train = strictly before.
TRAIN_END = pd.Timestamp("2025-10-01")

TAXONOMIES = ("TA", "TB", "TC")

BAND_ORDER = ["4h::region01", "4h::region02", "4h::region03"]
BAND_GLOSS = {
    "4h::region01": "region01 (balanced)",
    "4h::region02": "region02 (squeeze_prone)",
    "4h::region03": "region03 (stressed)",
}

# Three-sentence honest interpretation per taxonomy, authored against the
# 2026-06-10 run of this script (numbers in docs/report/band_recon.md).
INTERPRETATION = {
    "TA": (
        "At NMI 0.045 the T-A stress count is close to independent of the "
        "Band terciles; the visible structure is that the squeeze_prone Band "
        "almost never reads calm (0.4% of region02 bars vs 16.2% in balanced "
        "region01) and is the most extreme-flagged (62.6%). Crucially the "
        "relationship is not monotone — the stressed Band (region03) is LESS "
        "stress-flagged than squeeze_prone, and its row profile sits close "
        "to the balanced Band's. The distilled funding/OI/F&G stress axis is "
        "at best weakly and non-monotonically related to the LS-skew "
        "structure; it is a different axis, not a reproduction of this one."
    ),
    "TB": (
        "T-B posts the only non-trivial NMI (0.211), but it is carried by "
        "the trend half of the label, not the stress half: up-trend share by "
        "Band (read off the cross-tab) is 78.7% / 7.9% / 28.1% for "
        "region01/02/03, and Band occupancy is heavily month-clustered — "
        "region02 dominates the Nov-2025..Feb-2026 down-leg (where up-trend "
        "share is ~0%) while region01 dominates the Mar..May-2026 up-leg "
        "(77-89% up), so the trend clause is picking up calendar "
        "co-location. Conditioned on a trend branch the stress split is "
        "again near-uniform across Bands (within down-trend bars all three "
        "Bands are >=99% stressed; within up-trend bars the stressed share "
        "is 80-94%). Since Bands are direction-less by construction, this "
        "trend-mediated association is not evidence that the stress Feature "
        "set tracks LS-skew."
    ),
    "TC": (
        "T-C is the nearest to outright independence (NMI 0.023): pos-mild "
        "dominates every Band (55-72%), and the only structure is a "
        "positive-funding tilt in the squeeze_prone Band — region02 is 79% "
        "positive-funding vs 58% in region01, with pos-extreme at 7.0% vs "
        "2.9%. That tilt is directionally sensible (squeeze-prone implies "
        "crowded longs paying funding) but amounts to a few percentage "
        "points of occupancy, not a mapping. A funding-sign/extremity axis "
        "is a faint echo of the LS-skew terciles, nothing more."
    ),
}


def _nmi(contingency: np.ndarray) -> float:
    """Normalized mutual information from a counts table (numpy only).

    MI in nats from the joint/marginal empirical distribution; normalized by
    the arithmetic mean of the two marginal entropies (sklearn's default
    normalization). Degenerate marginals (either entropy 0) -> 0.0.
    """
    n = contingency.sum()
    if n == 0:
        return 0.0
    pij = contingency.astype(float) / n
    pi = pij.sum(axis=1, keepdims=True)
    pj = pij.sum(axis=0, keepdims=True)
    outer = pi @ pj
    nz = pij > 0
    mi = float((pij[nz] * np.log(pij[nz] / outer[nz])).sum())
    h_i = float(-(pi[pi > 0] * np.log(pi[pi > 0])).sum())
    h_j = float(-(pj[pj > 0] * np.log(pj[pj > 0])).sum())
    denom = 0.5 * (h_i + h_j)
    return mi / denom if denom > 0 else 0.0


def _md_table(header: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def _crosstab_md(band: pd.Series, regime: pd.Series,
                 regime_order: list[str]) -> tuple[str, np.ndarray]:
    """Band x regime counts + row % as one markdown table; returns the
    raw counts matrix (band rows x regime cols) for the NMI computation."""
    counts = np.array(
        [[int(((band == b) & (regime == r)).sum()) for r in regime_order]
         for b in BAND_ORDER]
    )
    rows = []
    for b, cnt_row in zip(BAND_ORDER, counts):
        total = cnt_row.sum()
        cells = [
            f"{c} ({100.0 * c / total:.1f}%)" if total else "0 (—)"
            for c in cnt_row
        ]
        rows.append([BAND_GLOSS[b], *cells, str(int(total))])
    col_tot = counts.sum(axis=0)
    rows.append(["**all bands**",
                 *[str(int(c)) for c in col_tot],
                 str(int(counts.sum()))])
    table = _md_table(["band \\ regime", *regime_order, "row total"], rows)
    return table, counts


def main() -> None:
    panel = load_panel("full")
    feats = add_features(panel)

    train = feats[feats.index < TRAIN_END]
    thresholds = derive_thresholds(train)

    overlap = feats[feats["band"].notna()]
    band = overlap["band"]
    band_eps = episodes(band)

    sections: list[str] = []
    summary: dict[str, dict[str, float | int]] = {}
    for name in TAXONOMIES:
        cfg = TaxonomyConfig(name=name, thresholds=thresholds)
        regime = label(overlap, cfg)
        regime_order = sorted(regime.unique())
        table, counts = _crosstab_md(band, regime, regime_order)
        nmi = _nmi(counts)
        ours = episodes(regime)
        summary[name] = {"nmi": nmi, "episodes": len(ours)}
        ep_table = _md_table(
            ["series", "episodes", "median bars/episode"],
            [
                [f"T-{name[1]} regimes", str(len(ours)),
                 f"{float(ours['n_bars'].median()):.1f}"],
                ["rm17 Bands", str(len(band_eps)),
                 f"{float(band_eps['n_bars'].median()):.1f}"],
            ],
        )
        sections.append("\n".join([
            f"## Taxonomy T-{name[1]} ({name})",
            "",
            "### Band x regime occupancy — counts (row %)",
            "",
            table,
            "",
            f"**Normalized mutual information (band vs regime): "
            f"{nmi:.4f}** (0 = independent, 1 = identical partitions; "
            "natural-log MI / arithmetic-mean entropy).",
            "",
            "### Episode comparison (overlap span)",
            "",
            ep_table,
            "",
            "### Interpretation",
            "",
            INTERPRETATION[name],
        ]))

    thr_table = _md_table(
        ["threshold", "value"],
        [[k, f"{v:.6g}"] for k, v in thresholds.items()],
    )
    doc = "\n".join([
        "# Band reconciliation — distilled taxonomies vs rm17 Bands",
        "",
        "*Lab-only discovery aid (plan Task 2.2). Generated by "
        "`uv run --no-sync python -m lab.band_recon`; regenerating "
        "overwrites this file.*",
        "",
        "> **Caveat (CONTEXT.md vocabulary):** Bands are rm17-derivs tercile "
        "labels built from direction-less LS-skew (`|ln(LS)|`) — lab-side "
        "training labels ONLY. They are never shipped, never a fit target, "
        "and never an input to the distilled classifier; this document is "
        "descriptive evidence about the G1 “distill” story, not "
        "validation of anything.",
        "",
        "## Setup",
        "",
        f"- Overlap: {len(overlap)} four-hour bars where `band` is non-NaN, "
        f"{overlap.index[0]} .. {overlap.index[-1]} (UTC bar opens).",
        "- Thresholds: `lab.features.derive_thresholds` on the pre-overlap "
        f"span 2025-04-03 00:00 <= t < {TRAIN_END.date()} "
        "(F1-train convention, lab/walkforward.py) — leak-free by "
        "construction since the Band span starts 2025-10-04.",
        "- Labels: `lab.classifier.label` per taxonomy on the overlap rows; "
        "NaN Feature clauses evaluate FALSE (FREEZE-ADDENDUM D4.3).",
        "- NMI computed from the contingency table with numpy "
        "(no sklearn); episodes via `lab.classifier.episodes`.",
        "",
        "### Thresholds used (pre-overlap-derived absolutes)",
        "",
        thr_table,
        "",
        "\n\n".join(sections),
        "",
        "## Bottom line",
        "",
        " ".join(
            f"T-{n[1]} NMI = {summary[n]['nmi']:.4f}." for n in TAXONOMIES
        ) + " The pure stress/funding axes (T-A, T-C) are close to "
        "independent of the Band partition, and the one non-trivial "
        "association (T-B) is carried by the direction-ful trend clause "
        "co-locating in calendar time with the Band mix — Bands are "
        "direction-less, so that is not distillation evidence. The G1 story "
        "should be framed as “Band-inspired, independently gated on its own "
        "walk-forward”, not as a faithful distillation of the Band "
        "structure.",
        "",
    ])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(doc)

    print(f"overlap bars: {len(overlap)} "
          f"({overlap.index[0]} .. {overlap.index[-1]})")
    print(f"band episodes on overlap: {len(band_eps)}")
    for name in TAXONOMIES:
        print(f"{name}: NMI={summary[name]['nmi']:.4f} "
              f"episodes={summary[name]['episodes']}")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
