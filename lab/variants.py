"""PR-8 variant enumeration — curated grids, pre-registered and binding.

Two families over the taxonomy candidates of lab/classifier.py:

- direction (20): 10 hypothesis base maps (H1-H6 on TB, H7-H10 on TC),
  each at full size and at half size (every entry x 0.5).
- risk (16): long-only exposure ladders — 6 on TA, 6 on TB, 4 on TC.

TOTAL = 36 exactly (test-pinned; the R3 multiple-testing denominator).

enumerate_all() is deterministic: stable order, stable ids. Variant is a
frozen dataclass with a tuple-of-pairs action_map so it is hashable;
.action_dict() gives the dict form consumed by lab/rules.apply.
"""

from __future__ import annotations

from dataclasses import dataclass

# Canonical label order per taxonomy (matches lab/classifier.py emissions).
TAXONOMY_LABELS: dict[str, tuple[str, ...]] = {
    "TA": ("calm", "stressed", "extreme"),
    "TB": ("calm-up", "calm-down", "stressed-up", "stressed-down"),
    "TC": ("pos-mild", "pos-extreme", "neg-mild", "neg-extreme"),
}


@dataclass(frozen=True)
class Variant:
    """One complete candidate strategy (CONTEXT.md: Variant)."""

    id: str
    family: str  # "direction" | "risk"
    taxonomy: str  # "TA" | "TB" | "TC"
    action_map: tuple[tuple[str, float], ...]  # tuple-of-pairs -> hashable

    def action_dict(self) -> dict[str, float]:
        return dict(self.action_map)


# DIRECTION family base maps (PR-8, binding). Values are in canonical label
# order for the hypothesis's taxonomy. Each also runs at half size.
_DIRECTION_HYPOTHESES: tuple[tuple[str, str, str, tuple[float, ...]], ...] = (
    # TB: (calm-up, calm-down, stressed-up, stressed-down)
    ("TB", "H1", "follow_calm_flat_stress", (1.0, -1.0, 0.0, 0.0)),
    ("TB", "H2", "follow_calm_fade_stress", (1.0, -1.0, -1.0, 1.0)),
    ("TB", "H3", "follow_all", (1.0, -1.0, 1.0, -1.0)),
    ("TB", "H4", "long_calm_only", (1.0, 0.0, 0.0, 0.0)),
    ("TB", "H5", "fade_stress_only", (0.0, 0.0, -1.0, 1.0)),
    ("TB", "H6", "follow_calm_half_stress", (1.0, -1.0, 0.5, -0.5)),
    # TC: (pos-mild, pos-extreme, neg-mild, neg-extreme)
    ("TC", "H7", "carry_fade_extremes", (0.0, -1.0, 0.0, 1.0)),
    ("TC", "H8", "fade_pos_extreme_only", (0.0, -1.0, 0.0, 0.0)),
    ("TC", "H9", "follow_mild_fade_extreme", (0.5, -1.0, -0.5, 1.0)),
    ("TC", "H10", "short_crowded_long", (0.0, -1.0, 0.5, 1.0)),
)

# RISK family long-only exposure ladders (PR-8, binding), canonical order.
_RISK_LADDERS: tuple[tuple[str, tuple[tuple[float, ...], ...]], ...] = (
    (
        "TA",  # (calm, stressed, extreme)
        (
            (1.0, 0.5, 0.0),
            (1.0, 0.5, 0.25),
            (1.0, 0.25, 0.0),
            (0.5, 0.25, 0.0),
            (1.0, 1.0, 0.0),
            (1.0, 0.0, 0.0),
        ),
    ),
    (
        "TB",  # (calm-up, calm-down, stressed-up, stressed-down)
        (
            (1.0, 1.0, 0.5, 0.5),
            (1.0, 0.5, 0.5, 0.0),
            (1.0, 1.0, 0.0, 0.0),
            (1.0, 0.5, 0.25, 0.25),
            (1.0, 0.0, 0.5, 0.0),
            (0.5, 0.5, 0.0, 0.0),
        ),
    ),
    (
        "TC",  # (pos-mild, pos-extreme, neg-mild, neg-extreme)
        (
            (1.0, 0.0, 1.0, 0.5),
            (1.0, 0.25, 1.0, 1.0),
            (0.5, 0.0, 1.0, 0.5),
            (1.0, 0.0, 0.5, 0.0),
        ),
    ),
)

_DIRECTION_SIZES = (1.0, 0.5)


def _fmt(v: float) -> str:
    """Compact deterministic float formatting for ids: 1 / 0.5 / 0.25 / 0."""
    return f"{v:g}"


def enumerate_all() -> list[Variant]:
    """All 36 PR-8 variants in deterministic order with stable ids.

    Order: direction H1..H10 (full then half size each), then risk ladders
    TA, TB, TC in registration order.
    """
    out: list[Variant] = []
    for taxonomy, hyp, name, base in _DIRECTION_HYPOTHESES:
        labels = TAXONOMY_LABELS[taxonomy]
        for size in _DIRECTION_SIZES:
            sizes = tuple(v * size for v in base)
            out.append(
                Variant(
                    id=f"DIR-{taxonomy}-{hyp}-{name}-{size}",
                    family="direction",
                    taxonomy=taxonomy,
                    action_map=tuple(zip(labels, sizes, strict=True)),
                )
            )
    for taxonomy, ladders in _RISK_LADDERS:
        labels = TAXONOMY_LABELS[taxonomy]
        for ladder in ladders:
            out.append(
                Variant(
                    id=f"RISK-{taxonomy}-ladder-" + "_".join(_fmt(v) for v in ladder),
                    family="risk",
                    taxonomy=taxonomy,
                    action_map=tuple(zip(labels, ladder, strict=True)),
                )
            )
    return out
