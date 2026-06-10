"""Tests for lab/variants.py — Task 2.3, PR-8 curated grids (binding).

Pins: exact count 36 (R3 denominator, printed), unique stable ids,
deterministic enumeration, and per-taxonomy label-set consistency
cross-checked against actual classifier label emissions on synthetic
frames covering all states. Never lab CSVs.
"""

import sys
from pathlib import Path

import pandas as pd

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.classifier import TaxonomyConfig, label  # noqa: E402
from lab.variants import Variant, enumerate_all  # noqa: E402

# ------------------------------------------------------------------ count + ids


def test_exact_count_is_36():
    variants = enumerate_all()
    print(f"PR-8 variant count (R3 denominator): {len(variants)}")
    assert len(variants) == 36


def test_family_split_20_direction_16_risk():
    variants = enumerate_all()
    fams = [v.family for v in variants]
    assert fams.count("direction") == 20
    assert fams.count("risk") == 16
    assert set(fams) == {"direction", "risk"}


def test_ids_unique():
    variants = enumerate_all()
    ids = [v.id for v in variants]
    assert len(set(ids)) == len(ids)


def test_deterministic_across_two_calls():
    a = enumerate_all()
    b = enumerate_all()
    assert a == b
    assert [v.id for v in a] == [v.id for v in b]


def test_variants_are_hashable_and_frozen():
    variants = enumerate_all()
    assert len(set(variants)) == 36  # tuple-of-pairs action_map -> hashable
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        variants[0].id = "nope"


def test_action_dict_roundtrip():
    for v in enumerate_all():
        d = v.action_dict()
        assert isinstance(d, dict)
        assert tuple(d.items()) == v.action_map


# ----------------------------------------------------- pre-registered contents


def test_direction_h2_full_and_half_size_pinned():
    by_id = {v.id: v for v in enumerate_all()}
    full = by_id["DIR-TB-H2-follow_calm_fade_stress-1.0"]
    assert full.family == "direction"
    assert full.taxonomy == "TB"
    assert full.action_dict() == {
        "calm-up": 1.0,
        "calm-down": -1.0,
        "stressed-up": -1.0,
        "stressed-down": 1.0,
    }
    half = by_id["DIR-TB-H2-follow_calm_fade_stress-0.5"]
    assert half.action_dict() == {
        "calm-up": 0.5,
        "calm-down": -0.5,
        "stressed-up": -0.5,
        "stressed-down": 0.5,
    }


def test_direction_h10_pinned():
    by_id = {v.id: v for v in enumerate_all()}
    v = by_id["DIR-TC-H10-short_crowded_long-1.0"]
    assert v.taxonomy == "TC"
    assert v.action_dict() == {
        "pos-mild": 0.0,
        "pos-extreme": -1.0,
        "neg-mild": 0.5,
        "neg-extreme": 1.0,
    }


def test_risk_ta_ladder_pinned():
    by_id = {v.id: v for v in enumerate_all()}
    v = by_id["RISK-TA-ladder-1_0.5_0"]
    assert v.family == "risk"
    assert v.taxonomy == "TA"
    assert v.action_dict() == {"calm": 1.0, "stressed": 0.5, "extreme": 0.0}


def test_every_half_size_direction_variant_is_half_its_base():
    by_id = {v.id: v for v in enumerate_all()}
    halves = [i for i in by_id if i.startswith("DIR-") and i.endswith("-0.5")]
    assert len(halves) == 10
    for hid in halves:
        bid = hid[: -len("-0.5")] + "-1.0"
        base = by_id[bid].action_dict()
        half = by_id[hid].action_dict()
        assert set(half) == set(base)
        for k in base:
            assert half[k] == base[k] * 0.5


def test_risk_family_is_long_only():
    for v in enumerate_all():
        if v.family == "risk":
            for _, size in v.action_map:
                assert 0.0 <= size <= 1.0


def test_direction_taxonomies_are_tb_tc_and_risk_covers_all_three():
    variants = enumerate_all()
    assert {v.taxonomy for v in variants if v.family == "direction"} == {"TB", "TC"}
    assert {v.taxonomy for v in variants if v.family == "risk"} == {"TA", "TB", "TC"}


# -------------------------------- label-set cross-check vs classifier emissions

TA_THRESHOLDS = {
    "funding_hi": 0.0005,
    "funding_lo": -0.0003,
    "oi_surge": 0.05,
    "fg_lo": 20.0,
    "fg_hi": 80.0,
}
TC_THRESHOLDS = {"funding_hi_abs": 0.001}


def _emitted_labels(taxonomy: str) -> set[str]:
    """All labels the classifier actually emits, from a synthetic frame
    engineered to cover every state of the taxonomy."""
    if taxonomy == "TA":
        df = pd.DataFrame(
            {
                # calm / stressed (funding hi) / extreme (funding hi + oi surge)
                "funding_rate_8h": [0.0001, 0.0006, 0.0006],
                "oi_chg_24h": [0.01, 0.01, 0.06],
                "fg": [50.0, 50.0, 50.0],
            }
        )
        cfg = TaxonomyConfig(name="TA", thresholds=TA_THRESHOLDS)
    elif taxonomy == "TB":
        df = pd.DataFrame(
            {
                "funding_rate_8h": [0.0001, 0.0001, 0.0006, 0.0006],
                "oi_chg_24h": [0.01] * 4,
                "fg": [50.0] * 4,
                "close_vs_sma30_1d": [0.02, -0.02, 0.02, -0.02],
            }
        )
        cfg = TaxonomyConfig(name="TB", thresholds=TA_THRESHOLDS)
    elif taxonomy == "TC":
        df = pd.DataFrame(
            {
                "funding_rate_8h": [0.0002, 0.0015, -0.0002, -0.0020],
                "oi_chg_24h": [0.0] * 4,
                "fg": [50.0] * 4,
            }
        )
        cfg = TaxonomyConfig(name="TC", thresholds=TC_THRESHOLDS)
    else:  # pragma: no cover
        raise ValueError(taxonomy)
    return set(label(df, cfg))


EXPECTED_LABEL_SETS = {
    "TA": {"calm", "stressed", "extreme"},
    "TB": {"calm-up", "calm-down", "stressed-up", "stressed-down"},
    "TC": {"pos-mild", "pos-extreme", "neg-mild", "neg-extreme"},
}


def test_synthetic_frames_cover_all_states():
    for tax, expected in EXPECTED_LABEL_SETS.items():
        assert _emitted_labels(tax) == expected


def test_action_maps_reference_only_their_taxonomys_labels():
    emitted = {tax: _emitted_labels(tax) for tax in EXPECTED_LABEL_SETS}
    for v in enumerate_all():
        keys = set(v.action_dict())
        assert keys == emitted[v.taxonomy], (
            f"{v.id}: action map keys {sorted(keys)} != classifier emissions "
            f"{sorted(emitted[v.taxonomy])} for taxonomy {v.taxonomy}"
        )


def test_variant_fields():
    for v in enumerate_all():
        assert isinstance(v, Variant)
        assert isinstance(v.id, str) and v.id
        assert v.family in {"direction", "risk"}
        assert v.taxonomy in {"TA", "TB", "TC"}
        assert isinstance(v.action_map, tuple)
        for pair in v.action_map:
            assert isinstance(pair, tuple) and len(pair) == 2
            lbl, size = pair
            assert isinstance(lbl, str)
            assert isinstance(size, float)
