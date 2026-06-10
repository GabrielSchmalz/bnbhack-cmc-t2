"""Tests for lab/walkforward.py — Task 1.7 (PR-6, ADR-001 R2).

Hand-constructed dense 4h index + synthetic label series with hand-computed
median episode lengths. Never lab CSVs.

PR-6 boundaries (calendar UTC), expanding train, embargo E bars on the index
grid between each boundary bar and the OOS start:
  F1 train [start..2025-10-01)  OOS [2025-10-01 + E bars .. 2025-12-01)
  F2 train [start..2025-12-01)  OOS [2025-12-01 + E bars .. 2026-02-01)
  F3 train [start..2026-02-01)  OOS [2026-02-01 + E bars .. 2026-04-01)
  F4 train [start..2026-04-01)  OOS [2026-04-01 + E bars .. index end]
E = max(42, median episode n_bars from episodes(labels)) — BARS, not wall time.

Overlap semantics under EXPANDING folds: a fold's train must never overlap its
own or any LATER fold's OOS, and OOS segments are mutually disjoint. (An
earlier fold's OOS lies inside a later fold's train by construction — that is
the expanding design, not leakage; thresholds are re-derived per fold, R1.)
"""

import dataclasses
import sys
from pathlib import Path

import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.walkforward import Fold, folds, pooled_oos  # noqa: E402

# Dense 4h grid spanning the full-stack window (PR-1), tz-naive UTC like
# dataset.py output: 2025-04-03 00:00 .. 2026-06-09 20:00 = 2598 bars.
IDX = pd.date_range("2025-04-03 00:00", "2026-06-09 20:00", freq="4h")


def _labels_median_60() -> pd.Series:
    """Label series on IDX with median episode length exactly 60 bars.

    Repeating cycle A*50, B*60, C*70 (180 bars). 2598 = 14*180 + 78, so the
    tail is A*50 + B*28. Episode lengths: 15x50, 14x60, 14x70, 1x28
    (44 episodes; sorted, the 22nd and 23rd are both 60 -> median 60).
    """
    pattern = ["A"] * 50 + ["B"] * 60 + ["C"] * 70
    values = (pattern * 15)[: len(IDX)]
    return pd.Series(values, index=IDX)


def _labels_short_episodes() -> pd.Series:
    """Every episode exactly 5 bars (A*5, B*5 alternating) -> median 5 < 42."""
    pattern = ["A"] * 5 + ["B"] * 5
    values = (pattern * (len(IDX) // 10 + 1))[: len(IDX)]
    return pd.Series(values, index=IDX)


# ------------------------------------------------------------------- Fold shape


def test_fold_is_frozen_dataclass():
    f = Fold(train_idx=IDX[:5], oos_idx=IDX[10:15], name="F1")
    assert f.name == "F1"
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.name = "F2"


def test_folds_returns_four_named_folds():
    fs = folds(IDX, _labels_median_60())
    assert [f.name for f in fs] == ["F1", "F2", "F3", "F4"]


# ------------------------------------------------- (a) exact PR-6 boundaries


def test_fold_boundaries_exact_with_median_60():
    # E = max(42, 60) = 60 bars = 60*4h = 10 calendar days on a dense grid.
    fs = folds(IDX, _labels_median_60())
    f1, f2, f3, f4 = fs

    # Expanding train: every fold's train starts at the index start.
    for f in fs:
        assert f.train_idx[0] == pd.Timestamp("2025-04-03 00:00")

    # Train ends: last bar strictly before the calendar boundary.
    assert f1.train_idx[-1] == pd.Timestamp("2025-09-30 20:00")
    assert f2.train_idx[-1] == pd.Timestamp("2025-11-30 20:00")
    assert f3.train_idx[-1] == pd.Timestamp("2026-01-31 20:00")
    assert f4.train_idx[-1] == pd.Timestamp("2026-03-31 20:00")

    # OOS starts: boundary bar position + 60 bars on the grid (= +10 days).
    assert f1.oos_idx[0] == pd.Timestamp("2025-10-11 00:00")
    assert f2.oos_idx[0] == pd.Timestamp("2025-12-11 00:00")
    assert f3.oos_idx[0] == pd.Timestamp("2026-02-11 00:00")
    assert f4.oos_idx[0] == pd.Timestamp("2026-04-11 00:00")

    # OOS ends: last bar strictly before the next boundary; F4 runs to index end.
    assert f1.oos_idx[-1] == pd.Timestamp("2025-11-30 20:00")
    assert f2.oos_idx[-1] == pd.Timestamp("2026-01-31 20:00")
    assert f3.oos_idx[-1] == pd.Timestamp("2026-03-31 20:00")
    assert f4.oos_idx[-1] == pd.Timestamp("2026-06-09 20:00")

    # Train is exactly every grid bar before the boundary (no holes).
    assert f1.train_idx.equals(IDX[IDX < pd.Timestamp("2025-10-01")])
    assert f4.train_idx.equals(IDX[IDX < pd.Timestamp("2026-04-01")])


def test_folds_work_on_tz_aware_utc_index():
    idx = IDX.tz_localize("UTC")
    labels = pd.Series(_labels_median_60().to_numpy(), index=idx)
    f1 = folds(idx, labels)[0]
    assert f1.train_idx[-1] == pd.Timestamp("2025-09-30 20:00", tz="UTC")
    assert f1.oos_idx[0] == pd.Timestamp("2025-10-11 00:00", tz="UTC")


# ------------------------------------------- (b) embargo gap in BARS per fold


def test_embargo_gap_at_least_E_bars_every_fold():
    E = 60  # median episode length of the synthetic labels
    for f in folds(IDX, _labels_median_60()):
        gap_bars = IDX.get_loc(f.oos_idx[0]) - IDX.get_loc(f.train_idx[-1])
        assert gap_bars >= E
        # Exact construction: train ends at boundary-1 bar, OOS starts at
        # boundary bar + E -> position gap is E+1 (E bars dropped between).
        assert gap_bars == E + 1


# -------------------------------------------------------- (c) zero overlap


def test_no_leakage_overlap_between_train_and_oos():
    fs = folds(IDX, _labels_median_60())
    # Within each fold and against every LATER fold's OOS: train sees no OOS.
    for i, fi in enumerate(fs):
        for fj in fs[i:]:
            assert len(fi.train_idx.intersection(fj.oos_idx)) == 0
    # OOS segments are mutually disjoint.
    for i, fi in enumerate(fs):
        for fj in fs[i + 1 :]:
            assert len(fi.oos_idx.intersection(fj.oos_idx)) == 0


# ------------------------------------------------- (d) pooled OOS helper


def test_pooled_oos_sorted_unique_equals_union():
    fs = folds(IDX, _labels_median_60())
    pooled = pooled_oos(fs)
    assert isinstance(pooled, pd.DatetimeIndex)
    assert pooled.is_monotonic_increasing
    assert pooled.is_unique
    expected_n = sum(len(f.oos_idx) for f in fs)  # fold OOS are disjoint
    assert len(pooled) == expected_n
    assert pooled[0] == fs[0].oos_idx[0]
    assert pooled[-1] == fs[-1].oos_idx[-1]


def test_pooled_oos_dedupes_duplicate_segments():
    fs = folds(IDX, _labels_median_60())
    pooled = pooled_oos([fs[0], fs[0], fs[1]])
    assert pooled.is_unique
    assert len(pooled) == len(fs[0].oos_idx) + len(fs[1].oos_idx)


# ------------------------------------------------- (e) 42-bar embargo floor


def test_embargo_floor_42_bars_when_episodes_short():
    # Median episode length 5 << 42 -> E = 42 bars = 7 calendar days.
    f1 = folds(IDX, _labels_short_episodes())[0]
    assert f1.oos_idx[0] == pd.Timestamp("2025-10-08 00:00")
    gap_bars = IDX.get_loc(f1.oos_idx[0]) - IDX.get_loc(f1.train_idx[-1])
    assert gap_bars == 43  # 42 embargoed bars between train end and OOS start
