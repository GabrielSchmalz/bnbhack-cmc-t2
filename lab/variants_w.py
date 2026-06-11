"""W-sweep Variant enumeration — registration §5 grids + §6 annex/forward.

Registered spec: docs/plans/2026-06-10-widening-preregistration.md §5
(exact grids, test-pinned counts, id scheme) and §6 (locked annex,
forward registration); build phase §12.1. The frozen 36-variant
enumeration (lab/variants.py) is untouched.

enumerate_all_w() — every Variant evaluated this cycle, 183 total
(test-pinned): 175 gated (73 P-BTC / 51 P-ETH / 51 P-SOL; on P-BTC
24 T-D / 22 T-E / 10 T-F / 9 T-G / 8 T-H) plus the 8 §6 locked-annex
Variants (A1/A2 x sizes x time-stop, P-BTC, flagged annex=True —
evaluated and published as falsification context, NEVER in the gated
survivor pool, cannot ship this cycle).

Grids exactly as registered: direction maps x sizes {1.0, 0.5}, with the
time-stop axis {none, 6} only where §5 registers it (T-D and T-E
direction maps, and the §6 annex); risk ladders with the vol-band axis
{off, on} only where §5 registers it (T-D ladders). §4 na labels — and,
for T-F direction maps, fg-mid — always act 0; T-F ladders carry fg-mid
exposure 1 (na 0) per §5. Vectors zip against the §5 per-taxonomy label
orders; emitted action maps cover the FULL §4 canonical label space
(lab/classifiers_w.LABELS_W order).

Ids (§5): <PANEL>-DIR-<TAX>-<map>-<size>[-ts6] /
<PANEL>-RISK-<TAX>-ladder-<vec>[-vb], with <map> spelled
<code>-<name> (frozen lab/variants.py convention) and <vec> the §5
registered ladder vector (na/fg-mid entries excluded, as written there).

enumerate_forward_registration() — the §6 forward registration RECORD:
A1/A2 x 2 sizes x time-stop {none, 6} on all three assets (24 forward
Variants, flagged forward=True), registered on post-freeze data
(OOS 2026-06-11 00:00 UTC onward) and NEVER evaluated this cycle. The
P-BTC subset shares ids with the in-cycle annex — same registered
Variants, different evaluation window; annex=False because the forward
cycle gates them under §6.2's own protocol.

Deterministic: stable order, stable ids; VariantW is a frozen dataclass
with a tuple-of-pairs action_map (hashable), like the frozen Variant.
"""

from __future__ import annotations

from dataclasses import dataclass

from lab.classifiers_w import LABELS_W

PANELS_W = ("P-BTC", "P-ETH", "P-SOL")

# §5 counts table: T-E is P-BTC only (daily-OI Feature, §2).
PANEL_TAXONOMIES_W = {
    "P-BTC": ("TD", "TE", "TF", "TG", "TH"),
    "P-ETH": ("TD", "TF", "TG", "TH"),
    "P-SOL": ("TD", "TF", "TG", "TH"),
}


@dataclass(frozen=True)
class VariantW:
    """One complete W-sweep candidate strategy (ADR-002 gating domains)."""

    id: str
    panel: str  # "P-BTC" | "P-ETH" | "P-SOL"
    family: str  # "direction" | "risk"
    taxonomy: str  # "TD" | "TE" | "TF" | "TG" | "TH" (lab convention)
    action_map: tuple[tuple[str, float], ...]  # tuple-of-pairs -> hashable
    time_stop: int | None = None  # §3 registered values {None, 6}
    vol_band: bool = False        # §3 overlay, registered {off, on}
    annex: bool = False           # §6 locked annex (cannot ship this cycle)
    forward: bool = False         # §6 forward registration record only

    def action_dict(self) -> dict[str, float]:
        return dict(self.action_map)


# §5 per-taxonomy direction-vector zip orders (the non-na, non-fg-mid
# label orders written in the registration).
_VECTOR_LABELS_W: dict[str, tuple[str, ...]] = {
    "TD": ("pos-mid", "pos-hi", "pos-x", "neg-mid", "neg-hi", "neg-x"),
    "TE": ("pos-build", "pos-unwind", "neg-build", "neg-unwind"),
    "TF": ("pos-fear", "pos-greed", "neg-fear", "neg-greed"),
    "TG": ("pos-above", "neg-above", "pos-below", "neg-below"),
    "TH": ("pos-os", "pos-mid", "pos-ob", "neg-os", "neg-mid", "neg-ob"),
}

# §5 direction maps, verbatim: (code, name, vector in _VECTOR_LABELS_W order).
_DIRECTION_MAPS_W: dict[str, tuple[tuple[str, str, tuple[float, ...]], ...]] = {
    "TD": (
        ("D1", "fade_extremes_graded_sym", (0.0, -0.5, -1.0, 0.0, 0.5, 1.0)),
        ("D2", "fade_x_only_sym", (0.0, 0.0, -1.0, 0.0, 0.0, 1.0)),
        ("D3", "follow_extremes_graded_sym",
         (0.0, 0.5, 1.0, 0.0, -0.5, -1.0)),
        ("D4", "follow_x_only_sym", (0.0, 0.0, 1.0, 0.0, 0.0, -1.0)),
    ),
    "TE": (
        ("E1", "fade_build_sym", (-1.0, 0.0, 1.0, 0.0)),
        ("E2", "follow_unwind_sym", (0.0, -1.0, 0.0, 1.0)),
        ("E3", "fade_pos_long_neg", (-1.0, -1.0, 1.0, 1.0)),  # axis-collapse
        ("E4", "follow_build_sym", (1.0, 0.0, -1.0, 0.0)),    # mirror of E1
        ("E5", "fade_unwind_sym", (0.0, 1.0, 0.0, -1.0)),     # mirror of E2
    ),
    "TF": (
        ("F1", "capitulation_euphoria", (0.0, -1.0, 1.0, 0.0)),
        ("F2", "contrarian_fg", (1.0, -1.0, 1.0, -1.0)),      # axis-collapse
        ("F3", "follow_fg", (-1.0, 1.0, -1.0, 1.0)),          # mirror of F2
        ("F4", "euphoria_follow", (0.0, 1.0, -1.0, 0.0)),     # mirror of F1
    ),
    "TG": (
        ("G1", "follow_trend", (1.0, 1.0, -1.0, -1.0)),       # axis-collapse
        ("G2", "trend_crowding_filtered", (0.0, 1.0, -1.0, 0.0)),  # asym, §8
        ("G3", "fade_trend", (-1.0, -1.0, 1.0, 1.0)),         # mirror of G1
    ),
    "TH": (
        ("H1", "fade_ob_pos_buy_os_neg", (0.0, 0.0, -1.0, 1.0, 0.0, 0.0)),
        ("H2", "contrarian_rsi", (1.0, 0.0, -1.0, 1.0, 0.0, -1.0)),  # a-c
        ("H3", "momentum_rsi", (-1.0, 0.0, 1.0, -1.0, 0.0, 1.0)),  # mirror H2
    ),
}

# §5 risk ladders (long-only by family design, disclosed in §8), verbatim.
_RISK_LADDERS_W: dict[str, tuple[tuple[float, ...], ...]] = {
    "TD": (
        (1.0, 0.5, 0.0, 1.0, 0.5, 0.0),       # R1
        (1.0, 0.5, 0.25, 1.0, 0.5, 0.25),     # R2
        (1.0, 1.0, 0.0, 1.0, 1.0, 0.0),       # R3
        (1.0, 0.5, 0.0, 1.0, 1.0, 0.5),       # R4
    ),
    "TE": (
        (1.0, 0.5, 1.0, 0.5),                 # L1
        (1.0, 0.0, 1.0, 1.0),                 # L2
    ),
    "TF": (
        (1.0, 0.5, 1.0, 0.5),                 # L1 de-risk-greed
        (0.5, 1.0, 0.5, 1.0),                 # L2 de-risk-fear
    ),
    "TG": (
        (1.0, 1.0, 0.0, 0.0),                 # L1
        (1.0, 1.0, 0.5, 0.0),                 # L2
        (0.5, 1.0, 0.0, 0.0),                 # L3
    ),
    "TH": (
        (1.0, 1.0, 0.5, 1.0, 1.0, 0.5),       # L1
        (1.0, 1.0, 0.0, 1.0, 1.0, 0.0),       # L2
    ),
}

# §5 T-F ladders: "(fg-mid exposure 1, na 0)". Every other off-vector label
# (na labels; fg-mid in DIRECTION maps) acts 0 per §4/§5.
_LADDER_EXTRA_W: dict[str, dict[str, float]] = {"TF": {"fg-mid": 1.0}}

# §3 axes where §5 registers them: time-stop dresses T-D/T-E direction maps
# (and the §6 annex); vol-band dresses T-D ladders only.
_TIME_STOPS_BY_TAX = {
    "TD": (None, 6), "TE": (None, 6), "TF": (None,), "TG": (None,),
    "TH": (None,),
}
_VOL_BANDS_BY_TAX = {
    "TD": (False, True), "TE": (False,), "TF": (False,), "TG": (False,),
    "TH": (False,),
}

# §6 locked annex maps (T-D label space), verbatim.
_ANNEX_MAPS_W: tuple[tuple[str, str, tuple[float, ...]], ...] = (
    ("A1", "fade_pos_x_only", (0.0, 0.0, -1.0, 0.0, 0.0, 0.0)),
    ("A2", "fade_pos_graded", (0.0, -0.5, -1.0, 0.0, 0.0, 0.0)),
)

_DIRECTION_SIZES_W = (1.0, 0.5)  # PR-8 size multipliers, carried forward


def _fmt(v: float) -> str:
    """Compact deterministic float formatting for ids: 1 / 0.5 / 0.25 / 0."""
    return f"{v:g}"


def _map_from_vector(taxonomy: str, vector: tuple[float, ...],
                     extra: dict[str, float] | None = None
                     ) -> tuple[tuple[str, float], ...]:
    """Full-label-space action map from a §5 vector; off-vector labels 0."""
    values = dict(zip(_VECTOR_LABELS_W[taxonomy], vector, strict=True))
    if extra:
        values.update(extra)
    return tuple(
        (lab, float(values.get(lab, 0.0))) for lab in LABELS_W[taxonomy])


def _direction_variants(panel: str, taxonomy: str,
                        maps: tuple[tuple[str, str, tuple[float, ...]], ...],
                        *, annex: bool = False, forward: bool = False
                        ) -> list[VariantW]:
    out: list[VariantW] = []
    for code, name, base in maps:
        for size in _DIRECTION_SIZES_W:
            sized = tuple(v * size for v in base)
            for ts in _TIME_STOPS_BY_TAX[taxonomy]:
                suffix = "-ts6" if ts == 6 else ""
                out.append(VariantW(
                    id=f"{panel}-DIR-{taxonomy}-{code}-{name}-{size}{suffix}",
                    panel=panel,
                    family="direction",
                    taxonomy=taxonomy,
                    action_map=_map_from_vector(taxonomy, sized),
                    time_stop=ts,
                    vol_band=False,
                    annex=annex,
                    forward=forward,
                ))
    return out


def _risk_variants(panel: str, taxonomy: str) -> list[VariantW]:
    out: list[VariantW] = []
    extra = _LADDER_EXTRA_W.get(taxonomy)
    for ladder in _RISK_LADDERS_W[taxonomy]:
        vec = "_".join(_fmt(v) for v in ladder)
        for vb in _VOL_BANDS_BY_TAX[taxonomy]:
            suffix = "-vb" if vb else ""
            out.append(VariantW(
                id=f"{panel}-RISK-{taxonomy}-ladder-{vec}{suffix}",
                panel=panel,
                family="risk",
                taxonomy=taxonomy,
                action_map=_map_from_vector(taxonomy, ladder, extra),
                time_stop=None,
                vol_band=vb,
                annex=False,
                forward=False,
            ))
    return out


def _annex_variants(panel: str, *, forward: bool) -> list[VariantW]:
    """§6 A1/A2 x sizes x time-stop {none, 6} on one panel.

    In-cycle (forward=False): the P-BTC locked annex, annex=True. Forward
    record (forward=True): annex=False — the forward cycle gates them
    under the §6.2 protocol itself.
    """
    return _direction_variants(
        panel, "TD", _ANNEX_MAPS_W, annex=not forward, forward=forward)


def enumerate_all_w() -> list[VariantW]:
    """All 183 Variants evaluated this cycle (175 gated + 8 locked annex).

    Order: per panel (P-BTC, P-ETH, P-SOL), per taxonomy in canonical
    order, direction maps (registration order; full then half size; ts
    none then 6) then ladders (registration order; vb off then on); the
    8 P-BTC annex Variants last (reported separately in R3, §6).
    """
    out: list[VariantW] = []
    for panel in PANELS_W:
        for taxonomy in PANEL_TAXONOMIES_W[panel]:
            out.extend(_direction_variants(
                panel, taxonomy, _DIRECTION_MAPS_W[taxonomy]))
            out.extend(_risk_variants(panel, taxonomy))
    out.extend(_annex_variants("P-BTC", forward=False))
    return out


def enumerate_forward_registration() -> list[VariantW]:
    """The §6 forward registration record: 24 Variants, NEVER evaluated
    this cycle (OOS 2026-06-11 00:00 UTC onward; earliest readout
    2027-07-01). This cycle's submission reports the registration itself,
    not a result."""
    out: list[VariantW] = []
    for panel in PANELS_W:
        out.extend(_annex_variants(panel, forward=True))
    return out
