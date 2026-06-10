"""Tests for lab/classifier.py — Task 1.6.

Hand-constructed frames with hand-computed expected labels. Never lab CSVs.

Canonical feature columns: funding_rate_8h, oi_chg_24h, fg, close_vs_sma30_1d.
Canonical threshold keys: funding_hi, funding_lo, funding_hi_abs, oi_surge,
fg_lo, fg_hi.

NaN semantics (FREEZE-ADDENDUM D4.3): any clause referencing a NaN Feature
evaluates FALSE (deterministic branch).
"""

import dataclasses
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.classifier import TaxonomyConfig, episodes, label  # noqa: E402

# Shared hand-picked thresholds (absolute numbers, as frozen thresholds are).
TA_THRESHOLDS = {
    "funding_hi": 0.0005,
    "funding_lo": -0.0003,
    "oi_surge": 0.05,
    "fg_lo": 20.0,
    "fg_hi": 80.0,
}
TC_THRESHOLDS = {"funding_hi_abs": 0.001}


def _frame(funding, oi, fg, trend=None, index=None):
    data = {
        "funding_rate_8h": funding,
        "oi_chg_24h": oi,
        "fg": fg,
    }
    if trend is not None:
        data["close_vs_sma30_1d"] = trend
    return pd.DataFrame(data, index=index)


# ---------------------------------------------------------------- TaxonomyConfig


def test_taxonomy_config_is_frozen():
    cfg = TaxonomyConfig(name="TA", thresholds=TA_THRESHOLDS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.name = "TB"


def test_unknown_taxonomy_name_raises():
    cfg = TaxonomyConfig(name="TX", thresholds={})
    with pytest.raises(ValueError):
        label(_frame([0.0], [0.0], [50.0]), cfg)


# ---------------------------------------------------------------------------- TA


def test_ta_every_label_and_every_clause():
    cfg = TaxonomyConfig(name="TA", thresholds=TA_THRESHOLDS)
    # Hand-computed stress scores:
    # r0: 0.0001 in (lo,hi), |0.01|<0.05, fg=50          -> 0 -> calm
    # r1: funding 0.0006 >= 0.0005                        -> 1 -> stressed
    # r2: funding -0.0004 <= -0.0003                      -> 1 -> stressed
    # r3: |oi -0.06| >= 0.05                              -> 1 -> stressed
    # r4: fg 15 <= 20                                     -> 1 -> stressed
    # r5: fg 85 >= 80                                     -> 1 -> stressed
    # r6: funding hi + oi surge                           -> 2 -> extreme
    # r7: funding lo + oi surge + fg hi                   -> 3 -> extreme
    df = _frame(
        funding=[0.0001, 0.0006, -0.0004, 0.0001, 0.0001, 0.0001, 0.0006, -0.0004],
        oi=[0.01, 0.01, 0.01, -0.06, 0.01, 0.01, 0.06, 0.10],
        fg=[50.0, 50.0, 50.0, 50.0, 15.0, 85.0, 50.0, 90.0],
    )
    out = label(df, cfg)
    assert out.tolist() == [
        "calm",
        "stressed",
        "stressed",
        "stressed",
        "stressed",
        "stressed",
        "extreme",
        "extreme",
    ]


def test_ta_boundaries_are_inclusive():
    cfg = TaxonomyConfig(name="TA", thresholds=TA_THRESHOLDS)
    # Exactly at each threshold -> clause fires (>= / <=).
    df = _frame(
        funding=[0.0005, -0.0003, 0.0, 0.0, 0.0],
        oi=[0.0, 0.0, 0.05, 0.0, 0.0],
        fg=[50.0, 50.0, 50.0, 20.0, 80.0],
    )
    out = label(df, cfg)
    assert out.tolist() == ["stressed"] * 5


def test_ta_index_preserved():
    cfg = TaxonomyConfig(name="TA", thresholds=TA_THRESHOLDS)
    idx = pd.date_range("2025-04-03", periods=3, freq="4h", tz="UTC")
    df = _frame([0.0, 0.0006, 0.0], [0.0, 0.06, 0.0], [50.0, 50.0, 50.0], index=idx)
    out = label(df, cfg)
    assert out.index.equals(idx)
    assert out.tolist() == ["calm", "extreme", "calm"]


def test_ta_nan_clauses_evaluate_false():
    cfg = TaxonomyConfig(name="TA", thresholds=TA_THRESHOLDS)
    # Each row NaNs exactly one Feature that would otherwise fire its clause;
    # remaining Features are quiet -> the NaN clause is FALSE -> calm.
    # Last row: all three NaN -> score 0 -> calm.
    df = _frame(
        funding=[np.nan, 0.0001, 0.0001, np.nan],
        oi=[0.01, np.nan, 0.01, np.nan],
        fg=[50.0, 50.0, np.nan, np.nan],
    )
    out = label(df, cfg)
    assert out.tolist() == ["calm"] * 4


def test_ta_nan_in_one_clause_does_not_block_others():
    cfg = TaxonomyConfig(name="TA", thresholds=TA_THRESHOLDS)
    # funding NaN (clause FALSE) but oi surge fires -> score 1 -> stressed.
    df = _frame(funding=[np.nan], oi=[0.07], fg=[50.0])
    assert label(df, cfg).tolist() == ["stressed"]


# ---------------------------------------------------------------------------- TB


def test_tb_all_four_labels():
    cfg = TaxonomyConfig(name="TB", thresholds=TA_THRESHOLDS)
    # r0: no stress, trend +0.02   -> calm-up
    # r1: no stress, trend -0.02   -> calm-down
    # r2: funding hi, trend +0.02  -> stressed-up
    # r3: funding hi, trend -0.02  -> stressed-down
    df = _frame(
        funding=[0.0001, 0.0001, 0.0006, 0.0006],
        oi=[0.01, 0.01, 0.01, 0.01],
        fg=[50.0, 50.0, 50.0, 50.0],
        trend=[0.02, -0.02, 0.02, -0.02],
    )
    out = label(df, cfg)
    assert out.tolist() == ["calm-up", "calm-down", "stressed-up", "stressed-down"]


def test_tb_zero_trend_is_down_branch():
    cfg = TaxonomyConfig(name="TB", thresholds=TA_THRESHOLDS)
    # up = (close_vs_sma30_1d > 0): strict, so 0 -> down.
    df = _frame([0.0001], [0.01], [50.0], trend=[0.0])
    assert label(df, cfg).tolist() == ["calm-down"]


def test_tb_extreme_stress_still_maps_to_stressed():
    cfg = TaxonomyConfig(name="TB", thresholds=TA_THRESHOLDS)
    # TA score 2 -> stress = (score >= 1) -> stressed-up.
    df = _frame([0.0006], [0.06], [50.0], trend=[0.02])
    assert label(df, cfg).tolist() == ["stressed-up"]


def test_tb_nan_trend_is_down_branch():
    cfg = TaxonomyConfig(name="TB", thresholds=TA_THRESHOLDS)
    # D4.3: NaN trend -> (NaN > 0) is FALSE -> down branch.
    df = _frame([0.0006], [0.01], [50.0], trend=[np.nan])
    assert label(df, cfg).tolist() == ["stressed-down"]


def test_tb_nan_stress_features_give_calm():
    cfg = TaxonomyConfig(name="TB", thresholds=TA_THRESHOLDS)
    # All stress Features NaN -> every stress clause FALSE -> calm; trend up.
    df = _frame([np.nan], [np.nan], [np.nan], trend=[0.02])
    assert label(df, cfg).tolist() == ["calm-up"]


# ---------------------------------------------------------------------------- TC


def test_tc_all_four_labels():
    cfg = TaxonomyConfig(name="TC", thresholds=TC_THRESHOLDS)
    # r0: +0.0002, |.|<0.001  -> pos-mild
    # r1: +0.0015, |.|>=0.001 -> pos-extreme
    # r2: -0.0002             -> neg-mild
    # r3: -0.0020             -> neg-extreme
    df = _frame(
        funding=[0.0002, 0.0015, -0.0002, -0.0020],
        oi=[0.0] * 4,
        fg=[50.0] * 4,
    )
    out = label(df, cfg)
    assert out.tolist() == ["pos-mild", "pos-extreme", "neg-mild", "neg-extreme"]


def test_tc_boundaries():
    cfg = TaxonomyConfig(name="TC", thresholds=TC_THRESHOLDS)
    # 0.0     -> pos (>= 0), not extreme            -> pos-mild
    # +0.001  -> pos, |.| >= 0.001                  -> pos-extreme
    # -0.001  -> neg (-0.001 < 0), |.| >= 0.001     -> neg-extreme
    df = _frame(funding=[0.0, 0.001, -0.001], oi=[0.0] * 3, fg=[50.0] * 3)
    out = label(df, cfg)
    assert out.tolist() == ["pos-mild", "pos-extreme", "neg-extreme"]


def test_tc_nan_funding_is_neg_mild():
    cfg = TaxonomyConfig(name="TC", thresholds=TC_THRESHOLDS)
    # D4.3: (NaN >= 0) FALSE -> neg branch; (|NaN| >= abs) FALSE -> mild.
    df = _frame(funding=[np.nan], oi=[0.0], fg=[50.0])
    assert label(df, cfg).tolist() == ["neg-mild"]


# ---------------------------------------------------------------------- episodes


def test_episodes_segmentation_aabbb_a():
    idx = pd.date_range("2025-04-03", periods=6, freq="4h", tz="UTC")
    labels = pd.Series(["A", "A", "B", "B", "B", "A"], index=idx)
    ep = episodes(labels)
    assert list(ep.columns) == ["label", "start", "end", "n_bars"]
    assert len(ep) == 3
    assert ep["label"].tolist() == ["A", "B", "A"]
    assert ep["start"].tolist() == [idx[0], idx[2], idx[5]]
    assert ep["end"].tolist() == [idx[1], idx[4], idx[5]]
    assert ep["n_bars"].tolist() == [2, 3, 1]


def test_episodes_single_run():
    labels = pd.Series(["calm"] * 4, index=[10, 20, 30, 40])
    ep = episodes(labels)
    assert len(ep) == 1
    assert ep.iloc[0]["label"] == "calm"
    assert ep.iloc[0]["start"] == 10
    assert ep.iloc[0]["end"] == 40
    assert ep.iloc[0]["n_bars"] == 4


def test_episodes_all_distinct():
    labels = pd.Series(["A", "B", "C"], index=[0, 1, 2])
    ep = episodes(labels)
    assert len(ep) == 3
    assert ep["n_bars"].tolist() == [1, 1, 1]


def test_episodes_empty():
    ep = episodes(pd.Series([], dtype=object))
    assert list(ep.columns) == ["label", "start", "end", "n_bars"]
    assert len(ep) == 0


def test_episodes_of_label_output_roundtrip():
    cfg = TaxonomyConfig(name="TC", thresholds=TC_THRESHOLDS)
    idx = pd.date_range("2025-04-03", periods=5, freq="4h", tz="UTC")
    # labels: pos-mild, pos-mild, neg-mild, neg-mild, pos-mild -> 3 episodes
    df = _frame(
        funding=[0.0001, 0.0002, -0.0001, -0.0002, 0.0001],
        oi=[0.0] * 5,
        fg=[50.0] * 5,
        index=idx,
    )
    ep = episodes(label(df, cfg))
    assert ep["label"].tolist() == ["pos-mild", "neg-mild", "pos-mild"]
    assert ep["n_bars"].tolist() == [2, 2, 1]
