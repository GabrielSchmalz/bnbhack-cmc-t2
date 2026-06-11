"""Tests for lab/variants_w.py — registration §5 grids + §6 annex/forward.

Registered spec: docs/plans/2026-06-10-widening-preregistration.md §5
(exact grids, test-pinned counts, id scheme) and §6 (locked annex A1/A2,
forward registration). Pins: 183 total = 175 gated (73/51/51 by panel;
P-BTC by taxonomy 24/22/10/9/8) + 8 locked annex; unique stable ids;
deterministic order; axis placement (time-stop only on T-D/T-E direction
maps and the annex, vol-band only on T-D ladders); §5 line-by-line action
maps (>= 1 direction map + 1 ladder per taxonomy fully asserted); na
labels (and fg-mid in T-F direction maps) act 0; registered mirrors; the
24-variant forward registration record. Never lab CSVs.
"""

import dataclasses
import sys
from collections import Counter
from pathlib import Path

import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.classifiers_w import LABELS_W, NA_LABEL_W  # noqa: E402
from lab.variants_w import (  # noqa: E402
    PANEL_TAXONOMIES_W,
    PANELS_W,
    VariantW,
    enumerate_all_w,
    enumerate_forward_registration,
)


def _gated(variants):
    return [v for v in variants if not v.annex]


def _annex(variants):
    return [v for v in variants if v.annex]


def _by_id(variants):
    return {v.id: v for v in variants}


# ------------------------------------------------------------ pinned counts


def test_total_183_gated_175_annex_8():
    vs = enumerate_all_w()
    gated, annex = _gated(vs), _annex(vs)
    print(f"W variant count (R3): {len(vs)} = {len(gated)} gated "
          f"+ {len(annex)} annex")
    assert len(vs) == 183
    assert len(gated) == 175
    assert len(annex) == 8


def test_gated_panel_split_73_51_51():
    gated = _gated(enumerate_all_w())
    assert Counter(v.panel for v in gated) == {
        "P-BTC": 73, "P-ETH": 51, "P-SOL": 51}


def test_btc_taxonomy_split_24_22_10_9_8():
    gated = _gated(enumerate_all_w())
    btc = Counter(v.taxonomy for v in gated if v.panel == "P-BTC")
    assert btc == {"TD": 24, "TE": 22, "TF": 10, "TG": 9, "TH": 8}


def test_eth_sol_taxonomy_split_24_10_9_8():
    gated = _gated(enumerate_all_w())
    for panel in ("P-ETH", "P-SOL"):
        c = Counter(v.taxonomy for v in gated if v.panel == panel)
        assert c == {"TD": 24, "TF": 10, "TG": 9, "TH": 8}


def test_te_is_p_btc_only():
    for v in enumerate_all_w():
        if v.taxonomy == "TE":
            assert v.panel == "P-BTC"
    assert PANEL_TAXONOMIES_W == {
        "P-BTC": ("TD", "TE", "TF", "TG", "TH"),
        "P-ETH": ("TD", "TF", "TG", "TH"),
        "P-SOL": ("TD", "TF", "TG", "TH"),
    }


# ------------------------------------------------------ ids + determinism


def test_ids_unique():
    ids = [v.id for v in enumerate_all_w()]
    assert len(set(ids)) == len(ids)


def test_deterministic_across_two_calls():
    a = enumerate_all_w()
    b = enumerate_all_w()
    assert a == b
    assert [v.id for v in a] == [v.id for v in b]


def test_variants_are_hashable_and_frozen():
    vs = enumerate_all_w()
    assert len(set(vs)) == 183
    with pytest.raises(dataclasses.FrozenInstanceError):
        vs[0].id = "nope"


def test_action_dict_roundtrip():
    for v in enumerate_all_w():
        d = v.action_dict()
        assert isinstance(d, dict)
        assert tuple(d.items()) == v.action_map


def test_action_maps_cover_full_label_space_in_canonical_order():
    for v in enumerate_all_w():
        assert tuple(lab for lab, _ in v.action_map) == tuple(
            LABELS_W[v.taxonomy]), v.id


# ------------------------------------------------------- axis placement (§5)


def test_time_stop_only_on_td_te_direction_and_annex():
    vs = enumerate_all_w()
    ts6 = [v for v in vs if v.time_stop == 6]
    # T-D dir: 4 maps x 2 sizes x 3 panels = 24; T-E dir (P-BTC): 5 x 2 = 10;
    # annex: 2 maps x 2 sizes = 4.
    assert len(ts6) == 38
    for v in ts6:
        assert v.family == "direction"
        assert v.taxonomy in {"TD", "TE"}
        assert v.id.endswith("-ts6")
    for v in vs:
        assert v.time_stop in (None, 6)
        if v.family == "risk":
            assert v.time_stop is None
        if v.taxonomy in {"TF", "TG", "TH"}:
            assert v.time_stop is None


def test_vol_band_only_on_td_ladders():
    vs = enumerate_all_w()
    vb = [v for v in vs if v.vol_band]
    # 4 T-D ladders x 3 panels = 12.
    assert len(vb) == 12
    for v in vb:
        assert v.family == "risk"
        assert v.taxonomy == "TD"
        assert v.id.endswith("-vb")
    for v in vs:
        if v.family == "direction" or v.taxonomy != "TD":
            assert not v.vol_band


def test_risk_family_is_long_only():
    for v in enumerate_all_w():
        if v.family == "risk":
            for _, size in v.action_map:
                assert 0.0 <= size <= 1.0


# ---------------------------------------- §5 line-by-line: T-D direction


def test_td_all_four_direction_maps_full_size_pinned():
    by_id = _by_id(enumerate_all_w())
    # §5 order (pos-mid, pos-hi, pos-x, neg-mid, neg-hi, neg-x).
    expected = {
        "P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0":
            (0.0, -0.5, -1.0, 0.0, 0.5, 1.0),
        "P-BTC-DIR-TD-D2-fade_x_only_sym-1.0":
            (0.0, 0.0, -1.0, 0.0, 0.0, 1.0),
        "P-BTC-DIR-TD-D3-follow_extremes_graded_sym-1.0":
            (0.0, 0.5, 1.0, 0.0, -0.5, -1.0),
        "P-BTC-DIR-TD-D4-follow_x_only_sym-1.0":
            (0.0, 0.0, 1.0, 0.0, 0.0, -1.0),
    }
    labels = ("pos-mid", "pos-hi", "pos-x", "neg-mid", "neg-hi", "neg-x")
    for vid, vec in expected.items():
        v = by_id[vid]
        assert v.family == "direction" and v.taxonomy == "TD"
        assert v.time_stop is None and not v.vol_band and not v.annex
        assert v.action_dict() == dict(zip(labels, vec, strict=True))


def test_td_half_size_ts6_pinned():
    by_id = _by_id(enumerate_all_w())
    v = by_id["P-SOL-DIR-TD-D2-fade_x_only_sym-0.5-ts6"]
    assert v.panel == "P-SOL"
    assert v.time_stop == 6
    assert v.action_dict() == {
        "pos-mid": 0.0, "pos-hi": 0.0, "pos-x": -0.5,
        "neg-mid": 0.0, "neg-hi": 0.0, "neg-x": 0.5,
    }


def test_td_ladders_pinned():
    by_id = _by_id(enumerate_all_w())
    # R1 vol-band off on P-BTC.
    r1 = by_id["P-BTC-RISK-TD-ladder-1_0.5_0_1_0.5_0"]
    assert r1.family == "risk" and not r1.vol_band
    assert r1.action_dict() == {
        "pos-mid": 1.0, "pos-hi": 0.5, "pos-x": 0.0,
        "neg-mid": 1.0, "neg-hi": 0.5, "neg-x": 0.0,
    }
    # R4 vol-band on, on P-ETH (the asymmetric ladder).
    r4 = by_id["P-ETH-RISK-TD-ladder-1_0.5_0_1_1_0.5-vb"]
    assert r4.vol_band and r4.time_stop is None
    assert r4.action_dict() == {
        "pos-mid": 1.0, "pos-hi": 0.5, "pos-x": 0.0,
        "neg-mid": 1.0, "neg-hi": 1.0, "neg-x": 0.5,
    }


# ---------------------------------------- §5 line-by-line: T-E (P-BTC only)


def test_te_direction_maps_pinned():
    by_id = _by_id(enumerate_all_w())
    e1 = by_id["P-BTC-DIR-TE-E1-fade_build_sym-1.0"]
    assert e1.action_dict() == {
        "pos-build": -1.0, "pos-unwind": 0.0,
        "neg-build": 1.0, "neg-unwind": 0.0, "oi-na": 0.0,
    }
    e2 = by_id["P-BTC-DIR-TE-E2-follow_unwind_sym-0.5-ts6"]
    assert e2.time_stop == 6
    assert e2.action_dict() == {
        "pos-build": 0.0, "pos-unwind": -0.5,
        "neg-build": 0.0, "neg-unwind": 0.5, "oi-na": 0.0,
    }
    e3 = by_id["P-BTC-DIR-TE-E3-fade_pos_long_neg-1.0"]
    assert e3.action_dict() == {
        "pos-build": -1.0, "pos-unwind": -1.0,
        "neg-build": 1.0, "neg-unwind": 1.0, "oi-na": 0.0,
    }


def test_te_ladders_pinned():
    by_id = _by_id(enumerate_all_w())
    l2 = by_id["P-BTC-RISK-TE-ladder-1_0_1_1"]
    assert l2.action_dict() == {
        "pos-build": 1.0, "pos-unwind": 0.0,
        "neg-build": 1.0, "neg-unwind": 1.0, "oi-na": 0.0,
    }
    assert "P-BTC-RISK-TE-ladder-1_0.5_1_0.5" in by_id


# ---------------------------------------- §5 line-by-line: T-F


def test_tf_direction_f1_pinned_fg_mid_acts_zero():
    by_id = _by_id(enumerate_all_w())
    f1 = by_id["P-BTC-DIR-TF-F1-capitulation_euphoria-1.0"]
    assert f1.time_stop is None  # no time-stop axis on T-F (§5)
    assert f1.action_dict() == {
        "pos-fear": 0.0, "pos-greed": -1.0,
        "neg-fear": 1.0, "neg-greed": 0.0,
        "fg-mid": 0.0, "fg-na": 0.0,
    }


def test_tf_ladders_pinned_fg_mid_exposure_one():
    by_id = _by_id(enumerate_all_w())
    # L2 de-risk-fear (0.5, 1, 0.5, 1 | mid 1).
    l2 = by_id["P-ETH-RISK-TF-ladder-0.5_1_0.5_1"]
    assert l2.action_dict() == {
        "pos-fear": 0.5, "pos-greed": 1.0,
        "neg-fear": 0.5, "neg-greed": 1.0,
        "fg-mid": 1.0, "fg-na": 0.0,
    }
    # L1 de-risk-greed (1, 0.5, 1, 0.5 | mid 1).
    l1 = by_id["P-BTC-RISK-TF-ladder-1_0.5_1_0.5"]
    assert l1.action_dict()["fg-mid"] == 1.0
    assert l1.action_dict()["fg-na"] == 0.0


def test_tf_direction_maps_fg_mid_always_zero():
    for v in enumerate_all_w():
        if v.taxonomy == "TF" and v.family == "direction":
            assert v.action_dict()["fg-mid"] == 0.0, v.id


# ---------------------------------------- §5 line-by-line: T-G


def test_tg_direction_g2_pinned():
    by_id = _by_id(enumerate_all_w())
    # §5 order (pos-above, neg-above, pos-below, neg-below).
    g2 = by_id["P-SOL-DIR-TG-G2-trend_crowding_filtered-1.0"]
    assert g2.action_dict() == {
        "pos-above": 0.0, "neg-above": 1.0,
        "pos-below": -1.0, "neg-below": 0.0, "sma-na": 0.0,
    }
    g1 = by_id["P-BTC-DIR-TG-G1-follow_trend-1.0"]
    assert g1.action_dict() == {
        "pos-above": 1.0, "neg-above": 1.0,
        "pos-below": -1.0, "neg-below": -1.0, "sma-na": 0.0,
    }


def test_tg_ladders_pinned():
    by_id = _by_id(enumerate_all_w())
    l3 = by_id["P-BTC-RISK-TG-ladder-0.5_1_0_0"]
    assert l3.action_dict() == {
        "pos-above": 0.5, "neg-above": 1.0,
        "pos-below": 0.0, "neg-below": 0.0, "sma-na": 0.0,
    }
    assert "P-SOL-RISK-TG-ladder-1_1_0_0" in by_id
    assert "P-SOL-RISK-TG-ladder-1_1_0.5_0" in by_id


# ---------------------------------------- §5 line-by-line: T-H


def test_th_direction_h1_pinned():
    by_id = _by_id(enumerate_all_w())
    # §5 order (pos-os, pos-mid, pos-ob, neg-os, neg-mid, neg-ob).
    h1 = by_id["P-BTC-DIR-TH-H1-fade_ob_pos_buy_os_neg-1.0"]
    assert h1.time_stop is None
    assert h1.action_dict() == {
        "pos-os": 0.0, "pos-mid": 0.0, "pos-ob": -1.0,
        "neg-os": 1.0, "neg-mid": 0.0, "neg-ob": 0.0, "rsi-na": 0.0,
    }


def test_th_ladders_pinned():
    by_id = _by_id(enumerate_all_w())
    l1 = by_id["P-BTC-RISK-TH-ladder-1_1_0.5_1_1_0.5"]
    assert l1.action_dict() == {
        "pos-os": 1.0, "pos-mid": 1.0, "pos-ob": 0.5,
        "neg-os": 1.0, "neg-mid": 1.0, "neg-ob": 0.5, "rsi-na": 0.0,
    }
    assert "P-ETH-RISK-TH-ladder-1_1_0_1_1_0" in by_id


# ----------------------------------------------------- shared §5 properties


def test_na_labels_act_zero_in_every_map():
    for v in enumerate_all_w():
        na = NA_LABEL_W[v.taxonomy]
        if na is not None:
            assert v.action_dict()[na] == 0.0, v.id


def test_every_half_size_direction_variant_is_half_its_base():
    by_id = _by_id(enumerate_all_w())
    halves = [i for i in by_id
              if "-DIR-" in i and ("-0.5" == i[-4:] or i.endswith("-0.5-ts6"))]
    # direction variants: 128 gated + 8 annex = 136 -> 68 half-size.
    assert len(halves) == 68
    for hid in halves:
        bid = hid.replace("-0.5", "-1.0", 1)
        base = by_id[bid].action_dict()
        half = by_id[hid].action_dict()
        assert set(half) == set(base)
        for k in base:
            assert half[k] == base[k] * 0.5


def test_registered_mirrors_full_size():
    """§5: every map's sign-mirror is registered except G2 (amendment M9)."""
    by_id = _by_id(enumerate_all_w())
    pairs = [
        ("P-BTC-DIR-TD-D3-follow_extremes_graded_sym-1.0",
         "P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0"),
        ("P-BTC-DIR-TD-D4-follow_x_only_sym-1.0",
         "P-BTC-DIR-TD-D2-fade_x_only_sym-1.0"),
        ("P-BTC-DIR-TE-E4-follow_build_sym-1.0",
         "P-BTC-DIR-TE-E1-fade_build_sym-1.0"),
        ("P-BTC-DIR-TE-E5-fade_unwind_sym-1.0",
         "P-BTC-DIR-TE-E2-follow_unwind_sym-1.0"),
        ("P-BTC-DIR-TF-F3-follow_fg-1.0",
         "P-BTC-DIR-TF-F2-contrarian_fg-1.0"),
        ("P-BTC-DIR-TF-F4-euphoria_follow-1.0",
         "P-BTC-DIR-TF-F1-capitulation_euphoria-1.0"),
        ("P-BTC-DIR-TG-G3-fade_trend-1.0",
         "P-BTC-DIR-TG-G1-follow_trend-1.0"),
        ("P-BTC-DIR-TH-H3-momentum_rsi-1.0",
         "P-BTC-DIR-TH-H2-contrarian_rsi-1.0"),
    ]
    for mirror_id, base_id in pairs:
        mirror = by_id[mirror_id].action_dict()
        base = by_id[base_id].action_dict()
        for k in base:
            assert mirror[k] == -base[k], (mirror_id, k)


# ------------------------------------------------------- §6 locked annex


def test_annex_8_p_btc_td_flagged():
    annex = _annex(enumerate_all_w())
    assert len(annex) == 8
    for v in annex:
        assert v.panel == "P-BTC"
        assert v.taxonomy == "TD"
        assert v.family == "direction"
        assert v.annex is True
        assert v.forward is False
        assert v.time_stop in (None, 6)
    expected_ids = {
        "P-BTC-DIR-TD-A1-fade_pos_x_only-1.0",
        "P-BTC-DIR-TD-A1-fade_pos_x_only-1.0-ts6",
        "P-BTC-DIR-TD-A1-fade_pos_x_only-0.5",
        "P-BTC-DIR-TD-A1-fade_pos_x_only-0.5-ts6",
        "P-BTC-DIR-TD-A2-fade_pos_graded-1.0",
        "P-BTC-DIR-TD-A2-fade_pos_graded-1.0-ts6",
        "P-BTC-DIR-TD-A2-fade_pos_graded-0.5",
        "P-BTC-DIR-TD-A2-fade_pos_graded-0.5-ts6",
    }
    assert {v.id for v in annex} == expected_ids


def test_annex_action_maps_pinned():
    by_id = _by_id(enumerate_all_w())
    a1 = by_id["P-BTC-DIR-TD-A1-fade_pos_x_only-1.0"]
    assert a1.action_dict() == {
        "pos-mid": 0.0, "pos-hi": 0.0, "pos-x": -1.0,
        "neg-mid": 0.0, "neg-hi": 0.0, "neg-x": 0.0,
    }
    a2 = by_id["P-BTC-DIR-TD-A2-fade_pos_graded-0.5-ts6"]
    assert a2.time_stop == 6
    assert a2.action_dict() == {
        "pos-mid": 0.0, "pos-hi": -0.25, "pos-x": -0.5,
        "neg-mid": 0.0, "neg-hi": 0.0, "neg-x": 0.0,
    }


def test_gated_variants_never_flagged():
    for v in _gated(enumerate_all_w()):
        assert v.annex is False
        assert v.forward is False


# ------------------------------------------------- §6 forward registration


def test_forward_registration_24_records():
    fwd = enumerate_forward_registration()
    assert len(fwd) == 24
    assert Counter(v.panel for v in fwd) == {
        "P-BTC": 8, "P-ETH": 8, "P-SOL": 8}
    for v in fwd:
        assert v.forward is True
        assert v.annex is False  # the forward cycle gates them per §6.2
        assert v.taxonomy == "TD"
        assert v.family == "direction"
        assert v.time_stop in (None, 6)
        assert "-DIR-TD-A" in v.id
    ids = [v.id for v in fwd]
    assert len(set(ids)) == 24
    assert "P-ETH-DIR-TD-A1-fade_pos_x_only-1.0-ts6" in ids
    assert "P-SOL-DIR-TD-A2-fade_pos_graded-0.5" in ids


def test_forward_p_btc_subset_is_the_annex_family():
    """Same registered Variants, post-freeze data: ids coincide (§6)."""
    fwd_btc = {v.id for v in enumerate_forward_registration()
               if v.panel == "P-BTC"}
    annex_ids = {v.id for v in _annex(enumerate_all_w())}
    assert fwd_btc == annex_ids


def test_forward_never_in_enumerate_all_w():
    for v in enumerate_all_w():
        assert v.forward is False


def test_forward_deterministic():
    a = enumerate_forward_registration()
    b = enumerate_forward_registration()
    assert a == b


# ----------------------------------------------------------- field hygiene


def test_variant_fields():
    for v in enumerate_all_w() + enumerate_forward_registration():
        assert isinstance(v, VariantW)
        assert isinstance(v.id, str) and v.id
        assert v.panel in PANELS_W
        assert v.family in {"direction", "risk"}
        assert v.taxonomy in {"TD", "TE", "TF", "TG", "TH"}
        assert isinstance(v.action_map, tuple)
        for pair in v.action_map:
            assert isinstance(pair, tuple) and len(pair) == 2
            lbl, size = pair
            assert isinstance(lbl, str)
            assert isinstance(size, float)
