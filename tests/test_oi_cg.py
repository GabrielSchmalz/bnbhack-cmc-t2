"""Tests for lab/oi_cg.py — registered CG daily-OI loader (widening §2).

Hand-constructed synthetic frames with hand-computed expectations; the one
committed-CSV test checks export METADATA only (row counts, span, dtype) —
it never evaluates OOS data.

Registered semantics under test (pre-registration §2 "Daily-OI loader";
determination committed in docs/gate0/OI-CG-STAMP-SEMANTICS.md):
  - load_oi_cg_daily: dedupe to the LAST stamp per UTC day, stamps kept;
  - oi_chg_24h_daily: snap(D)/snap(D-1) - 1, NaN when day D-1 has no
    snapshot (first row included);
  - join_to_bars: day-D value usable at the first 4h bar opening STRICTLY
    AFTER the day-D stamp (00:00 stamp -> D 04:00 bar; a bar opening
    exactly at the stamp must NOT see it); staleness > 48h -> NaN
    (exactly 48h is still fresh); frozen tail 2026-05-18 -> NaN beyond
    2026-05-20 00:00.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.oi_cg import (  # noqa: E402
    join_to_bars,
    load_oi_cg_daily,
    oi_chg_24h_daily,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORT_CSV = REPO_ROOT / "data" / "lab" / "oi_cg_daily_btc.csv"


def _write_csv(tmp_path, rows):
    p = tmp_path / "oi.csv"
    p.write_text("ts,oi\n" + "\n".join(f"{ts},{v}" for ts, v in rows) + "\n")
    return p


def _series(stamps, values):
    return pd.Series(
        np.asarray(values, dtype=float),
        index=pd.DatetimeIndex(pd.to_datetime(stamps)),
    )


# ------------------------------------------------------------ load_oi_cg_daily


def test_load_dedupes_to_last_stamp_per_day(tmp_path):
    # day 2 carries 00:00 AND 16:00 stamps (the 2026-04 pattern): the LAST
    # stamp per UTC day wins and its actual stamp time is preserved.
    p = _write_csv(tmp_path, [
        ("2026-04-02 00:00:00", 100.0),
        ("2026-04-03 00:00:00", 110.0),
        ("2026-04-03 16:00:00", 120.0),
        ("2026-04-04 00:00:00", 130.0),
    ])
    s = load_oi_cg_daily(p)
    assert len(s) == 3
    assert s.index.tolist() == [
        pd.Timestamp("2026-04-02 00:00:00"),
        pd.Timestamp("2026-04-03 16:00:00"),
        pd.Timestamp("2026-04-04 00:00:00"),
    ]
    assert s.tolist() == [100.0, 120.0, 130.0]
    assert s.dtype == float


def test_load_sorts_unordered_rows(tmp_path):
    p = _write_csv(tmp_path, [
        ("2025-01-03 00:00:00", 3.0),
        ("2025-01-01 00:00:00", 1.0),
        ("2025-01-02 00:00:00", 2.0),
    ])
    s = load_oi_cg_daily(p)
    assert s.index.is_monotonic_increasing
    assert s.tolist() == [1.0, 2.0, 3.0]


# ------------------------------------------------------------ oi_chg_24h_daily


def test_chg_adjacent_days_hand_computed():
    daily = _series(
        ["2025-01-01 00:00", "2025-01-02 00:00", "2025-01-03 00:00"],
        [100.0, 110.0, 99.0],
    )
    chg = oi_chg_24h_daily(daily)
    assert chg.index.equals(daily.index)
    assert np.isnan(chg.iloc[0])  # no day D-1 snapshot
    assert chg.iloc[1] == (110.0 / 100.0 - 1)
    assert chg.iloc[2] == (99.0 / 110.0 - 1)


def test_chg_missing_previous_day_is_nan():
    # day 2025-01-04 has no 2025-01-03 snapshot -> NaN, not a 2-day change.
    daily = _series(
        ["2025-01-01 00:00", "2025-01-02 00:00", "2025-01-04 00:00"],
        [100.0, 110.0, 121.0],
    )
    chg = oi_chg_24h_daily(daily)
    assert chg.iloc[1] == (110.0 / 100.0 - 1)
    assert np.isnan(chg.iloc[2])


def test_chg_keeps_actual_stamps_and_spans_16h_stamp():
    # registered formula is snap(D)/snap(D-1) - 1 verbatim, even when the
    # deduped day-D stamp is 16:00 (the 2026-04 double-stamp days).
    daily = _series(["2026-04-02 00:00", "2026-04-03 16:00"], [100.0, 120.0])
    chg = oi_chg_24h_daily(daily)
    assert chg.index.tolist() == daily.index.tolist()
    assert chg.iloc[1] == (120.0 / 100.0 - 1)


# ----------------------------------------------------------------- join_to_bars


def test_join_bar_at_stamp_hour_does_not_see_that_day():
    # THE availability boundary: a bar opening exactly at the day-D stamp
    # must NOT see the day-D value (first bar opening strictly after the
    # stamp does: 00:00 stamp -> D 04:00 bar).
    chg = _series(["2025-01-01 00:00", "2025-01-02 00:00"], [0.10, 0.20])
    bars = pd.DatetimeIndex(pd.to_datetime([
        "2025-01-01 20:00",   # after day-1 stamp -> 0.10
        "2025-01-02 00:00",   # AT day-2 stamp -> still 0.10
        "2025-01-02 04:00",   # first bar after day-2 stamp -> 0.20
    ]))
    out = join_to_bars(chg, bars)
    assert out.index.equals(bars)
    assert out.tolist() == [0.10, 0.10, 0.20]


def test_join_16h_stamp_usable_from_20h_bar():
    chg = _series(["2026-04-02 00:00", "2026-04-03 16:00"], [0.10, 0.20])
    bars = pd.DatetimeIndex(pd.to_datetime([
        "2026-04-03 12:00",   # before the 16:00 stamp -> 0.10
        "2026-04-03 16:00",   # AT the stamp -> still 0.10
        "2026-04-03 20:00",   # first bar after -> 0.20
    ]))
    assert join_to_bars(chg, bars).tolist() == [0.10, 0.10, 0.20]


def test_join_staleness_exactly_48h_fresh_beyond_nan():
    chg = _series(["2025-01-01 00:00"], [0.10])
    bars = pd.DatetimeIndex(pd.to_datetime([
        "2025-01-03 00:00",   # age exactly 48h -> still fresh
        "2025-01-03 04:00",   # age 52h -> NaN
    ]))
    out = join_to_bars(chg, bars)
    assert out.iloc[0] == 0.10
    assert np.isnan(out.iloc[1])


def test_join_before_first_stamp_is_nan():
    chg = _series(["2025-01-02 00:00"], [0.10])
    bars = pd.DatetimeIndex(pd.to_datetime(
        ["2025-01-01 20:00", "2025-01-02 00:00"]))
    out = join_to_bars(chg, bars)
    assert np.isnan(out.iloc[0])
    assert np.isnan(out.iloc[1])


def test_join_nan_change_value_propagates():
    # the first chg row is NaN by construction (no D-1 snapshot): bars that
    # match it carry NaN, they do not fall back to an older stamp.
    chg = _series(["2025-01-01 00:00", "2025-01-02 00:00"], [np.nan, 0.20])
    bars = pd.DatetimeIndex(pd.to_datetime(["2025-01-01 04:00"]))
    assert np.isnan(join_to_bars(chg, bars).iloc[0])


def test_join_frozen_tail_2026_05_18_goes_nan():
    # last CG stamp is 2026-05-18 00:00 (frozen mirror). Registered §2:
    # the day's value serves bars opening in (2026-05-18 00:00,
    # 2026-05-20 00:00] and every later bar is NaN -> `oi-na`
    # (first NaN bar: 2026-05-20 04:00).
    daily = _series(
        ["2026-05-16 00:00", "2026-05-17 00:00", "2026-05-18 00:00"],
        [100.0, 110.0, 121.0],
    )
    chg = oi_chg_24h_daily(daily)
    bars = pd.date_range("2026-05-18 00:00", "2026-05-21 00:00", freq="4h")
    out = join_to_bars(chg, bars)
    # bar at the 05-18 stamp still sees the 05-17 change
    assert out.loc[pd.Timestamp("2026-05-18 00:00")] == (110.0 / 100.0 - 1)
    served = out.loc["2026-05-18 04:00":"2026-05-20 00:00"]
    assert (served == (121.0 / 110.0 - 1)).all()
    tail = out.loc["2026-05-20 04:00":]
    assert len(tail) == 6 and tail.isna().all()


# ------------------------------------------------------- committed export file


def test_committed_export_metadata_only():
    # Metadata pins for data/lab/oi_cg_daily_btc.csv (no OOS evaluation):
    # raw rows, dedupe count, span endpoints, clean positive floats.
    raw = pd.read_csv(EXPORT_CSV)
    assert list(raw.columns) == ["ts", "oi"]
    assert len(raw) == 2286
    s = load_oi_cg_daily(EXPORT_CSV)
    assert len(s) == 2273                      # 13 double-stamp days deduped
    assert s.index[0] == pd.Timestamp("2020-02-27 00:00:00")
    assert s.index[-1] == pd.Timestamp("2026-05-18 00:00:00")
    assert s.index.is_monotonic_increasing
    assert s.index.normalize().is_unique
    assert s.notna().all() and (s > 0).all()
