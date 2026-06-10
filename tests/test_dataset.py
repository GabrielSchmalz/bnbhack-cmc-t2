"""Task 1.1 tests — lab/dataset.py causal 4h panel assembly.

All tests drive build_panel with small hand-constructed frames and
hand-computed expectations. The committed data/lab CSVs are NEVER read here;
the one load_panel plumbing test writes tiny synthetic CSVs to tmp_path.

Policies under test (plan Task 1.1 (a)-(d) + addendum D4.1-D4.5):
  (a) as-of join takes the LAST value <= bar open, never after
  (b) dvol staleness > 24h -> NaN
  (c) F&G stamped day D is first visible on the D 04:00 bar
  (d) funding lands only on 00/08/16 UTC bars, 0.0 elsewhere
  D4.1 duplicate bar stamps dropped
  D4.2 OI/LS resampled to daily 00:00 snapshots first (no intraday leak),
       then as-of joined with 36h staleness cap (holes -> NaN)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package and pytest
# only inserts tests/ (rootdir-wide fix belongs in shared config, not here)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.dataset import DATA_DIR, WINDOWS, build_panel, load_panel

EXPECTED_COLUMNS = [
    "open", "high", "low", "close", "volume",
    "funding_rate", "oi", "ls_ratio", "dvol", "fg", "band",
]


# ---------------------------------------------------------------- helpers

def make_bars(start: str, n: int) -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="4h")
    return pd.DataFrame({
        "open_time": idx,
        "open": [100.0 + i for i in range(n)],
        "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)],
        "close": [100.5 + i for i in range(n)],
        "volume": [1.0] * n,
    })


def empty(cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=cols)


EMPTY_FUNDING = empty(["funding_time_utc", "funding_rate"])
EMPTY_OI = empty(["ts", "open_interest"])
EMPTY_LS = empty(["ts", "long_short_ratio"])
EMPTY_DVOL = empty(["ts", "close"])
EMPTY_FG = empty(["date_utc", "value"])
EMPTY_BANDS = empty(["bar_ts", "region_id"])


def build(bars, *, funding=None, oi=None, ls=None, dvol=None, fg=None,
          bands=None, window_start=None, window_end=None) -> pd.DataFrame:
    ot = pd.to_datetime(bars["open_time"])
    return build_panel(
        bars,
        funding if funding is not None else EMPTY_FUNDING,
        oi if oi is not None else EMPTY_OI,
        ls if ls is not None else EMPTY_LS,
        dvol if dvol is not None else EMPTY_DVOL,
        fg if fg is not None else EMPTY_FG,
        bands if bands is not None else EMPTY_BANDS,
        window_start if window_start is not None else ot.min(),
        window_end if window_end is not None else ot.max(),
    )


# ------------------------------------------------------- shape / windowing

def test_columns_index_and_window_clipping():
    bars = make_bars("2025-05-01 00:00", 12)  # through 2025-05-02 20:00
    panel = build(bars, window_start="2025-05-01 04:00",
                  window_end="2025-05-02 00:00")
    assert list(panel.columns) == EXPECTED_COLUMNS
    assert panel.index.name == "open_time"
    assert panel.index.tz is None
    # inclusive bounds on both ends
    assert panel.index[0] == pd.Timestamp("2025-05-01 04:00")
    assert panel.index[-1] == pd.Timestamp("2025-05-02 00:00")
    assert len(panel) == 6
    # OHLCV passthrough (bar at 04:00 was row i=1 -> open 101.0)
    assert panel.loc[pd.Timestamp("2025-05-01 04:00"), "open"] == 101.0


def test_window_constants():
    assert WINDOWS["full"] == (pd.Timestamp("2025-04-03 00:00"),
                               pd.Timestamp("2026-06-09 20:00"))
    assert WINDOWS["deep"] == (pd.Timestamp("2021-03-24 00:00"),
                               pd.Timestamp("2026-05-18 20:00"))


def test_load_panel_rejects_unknown_window():
    with pytest.raises(ValueError):
        load_panel("bogus")


# -------------------------------------------------- (a) as-of causal join

def test_asof_takes_last_value_at_or_before_bar_open():
    bars = make_bars("2025-05-01 00:00", 3)  # 00:00, 04:00, 08:00
    dvol = pd.DataFrame({
        "ts": pd.to_datetime(["2025-05-01 03:00", "2025-05-01 05:00",
                              "2025-05-01 08:00"]),
        "close": [10.0, 20.0, 30.0],
    })
    panel = build(bars, dvol=dvol)
    assert np.isnan(panel["dvol"].iloc[0])          # nothing <= 00:00
    assert panel["dvol"].iloc[1] == 10.0            # last <= 04:00, NOT 20.0
    assert panel["dvol"].iloc[2] == 30.0            # value AT open is usable


# --------------------------------------------- (b) dvol staleness cap 24h

def test_dvol_staleness_cap_24h():
    bars = make_bars("2025-05-01 00:00", 8)  # through 2025-05-02 04:00
    dvol = pd.DataFrame({"ts": pd.to_datetime(["2025-05-01 00:00"]),
                         "close": [50.0]})
    panel = build(bars, dvol=dvol)
    assert panel["dvol"].iloc[0] == 50.0   # 0h
    assert panel["dvol"].iloc[5] == 50.0   # 20h
    assert panel["dvol"].iloc[6] == 50.0   # exactly 24h: still fresh
    assert np.isnan(panel["dvol"].iloc[7])  # 28h: stale -> NaN


# ----------------------------------------------- (c) F&G D 04:00 timing

def test_fg_available_from_d_0400_bar_never_d_0000():
    fg = pd.DataFrame({
        "date_utc": ["2025-05-01", "2025-05-02", "2025-05-03"],
        "value": [25, 40, 60],
    })
    bars = make_bars("2025-05-02 00:00", 8)  # 05-02 00:00 .. 05-03 04:00
    panel = build(bars, fg=fg)
    assert panel["fg"].iloc[0] == 25.0   # 05-02 00:00 still sees day 05-01
    assert panel["fg"].iloc[1] == 40.0   # 05-02 04:00 first bar with day-D value
    assert panel["fg"].iloc[6] == 40.0   # 05-03 00:00 still previous day
    assert panel["fg"].iloc[7] == 60.0   # 05-03 04:00 flips to day 05-03


def test_fg_nan_before_first_publication():
    fg = pd.DataFrame({"date_utc": ["2025-05-02"], "value": [40]})
    bars = make_bars("2025-05-01 00:00", 6)  # all of 05-01
    panel = build(bars, fg=fg)
    assert panel["fg"].isna().all()


# -------------------------------------- (d) funding only on 8h-stamp bars

def test_funding_lands_on_8h_stamps_else_zero():
    bars = make_bars("2025-05-01 00:00", 6)  # 00,04,08,12,16,20
    funding = pd.DataFrame({
        "funding_time_utc": pd.to_datetime(
            ["2025-05-01 00:00", "2025-05-01 08:00", "2025-05-01 16:00"]),
        "funding_rate": [0.0001, 0.0002, -0.0003],
    })
    panel = build(bars, funding=funding)
    assert panel["funding_rate"].tolist() == [
        0.0001, 0.0, 0.0002, 0.0, -0.0003, 0.0]


def test_funding_missing_stamp_is_zero_not_nan():
    bars = make_bars("2025-05-01 00:00", 6)
    funding = pd.DataFrame({
        "funding_time_utc": pd.to_datetime(["2025-05-01 08:00"]),
        "funding_rate": [0.0005],
    })
    panel = build(bars, funding=funding)
    assert panel["funding_rate"].tolist() == [0.0, 0.0, 0.0005, 0.0, 0.0, 0.0]
    assert not panel["funding_rate"].isna().any()


# --------------------------------------------------- D4.1 duplicate bars

def test_bars_drop_duplicates_on_open_time():
    bars = make_bars("2025-05-01 00:00", 3)
    dup = pd.concat([bars, bars.iloc[[1]]], ignore_index=True)  # dupe 04:00
    dup = dup.sample(frac=1, random_state=7)  # also scramble row order
    panel = build(dup, window_start="2025-05-01 00:00",
                  window_end="2025-05-01 08:00")
    assert panel.index.is_unique
    assert len(panel) == 3
    assert panel.index.is_monotonic_increasing
    assert panel.loc[pd.Timestamp("2025-05-01 04:00"), "open"] == 101.0


# ------------------------------ D4.2 OI/LS daily-snapshot cadence + cap

def test_oi_ls_daily_snapshot_no_intraday_leak():
    bars = make_bars("2025-05-01 00:00", 12)  # 05-01 00:00 .. 05-02 20:00
    oi = pd.DataFrame({
        "ts": pd.to_datetime(["2025-05-01 00:00", "2025-05-01 13:00",
                              "2025-05-02 00:00"]),
        "open_interest": [100.0, 999.0, 110.0],
    })
    ls = pd.DataFrame({
        "ts": pd.to_datetime(["2025-05-01 00:00", "2025-05-01 13:00",
                              "2025-05-02 00:00"]),
        "long_short_ratio": [1.5, 9.9, 1.8],
    })
    panel = build(bars, oi=oi, ls=ls)
    # all six 05-01 bars hold the 05-01 00:00 snapshot; 5-min-era intraday
    # prints (13:00) never reach any bar
    assert panel["oi"].iloc[:6].tolist() == [100.0] * 6
    assert panel["oi"].iloc[6:].tolist() == [110.0] * 6
    assert 999.0 not in panel["oi"].tolist()
    assert panel["ls_ratio"].iloc[:6].tolist() == [1.5] * 6
    assert panel["ls_ratio"].iloc[6:].tolist() == [1.8] * 6
    assert 9.9 not in panel["ls_ratio"].tolist()


def test_oi_staleness_cap_36h_hole_becomes_nan():
    bars = make_bars("2025-05-01 00:00", 13)  # 05-01 00:00 .. 05-03 00:00
    oi = pd.DataFrame({"ts": pd.to_datetime(["2025-05-01 00:00"]),
                       "open_interest": [100.0]})
    panel = build(bars, oi=oi)
    # staleness vs the 05-01 00:00 daily snapshot:
    # idx 0..8 -> 0..32h fresh; idx 9 = 36h exactly (still fresh); idx 10+ NaN
    assert panel["oi"].iloc[:10].tolist() == [100.0] * 10
    assert panel["oi"].iloc[10:].isna().all()


# ----------------------------------------------------- band exact join

def test_band_exact_join_on_bar_open_time():
    bars = make_bars("2025-05-01 00:00", 6)
    bands = pd.DataFrame({
        "bar_ts": pd.to_datetime(["2025-05-01 04:00", "2025-05-01 08:00"]),
        "region_id": ["4h::region01", "4h::region02"],
    })
    panel = build(bars, bands=bands)
    assert pd.isna(panel["band"].iloc[0])
    assert panel["band"].iloc[1] == "4h::region01"
    assert panel["band"].iloc[2] == "4h::region02"
    assert panel["band"].iloc[3:].isna().all()


# ------------------------------------- deep window: late sources -> NaN

def test_deep_window_oi_ls_band_all_nan_other_sources_populated():
    # bars inside the deep-history window, before OI/LS/bands exist
    bars = make_bars("2021-03-24 00:00", 6)
    funding = pd.DataFrame({
        "funding_time_utc": pd.to_datetime(
            ["2021-03-24 00:00", "2021-03-24 08:00", "2021-03-24 16:00"]),
        "funding_rate": [0.0001, 0.0002, 0.0003],
    })
    dvol = pd.DataFrame({"ts": pd.to_datetime(["2021-03-24 00:00"]),
                         "close": [84.88]})
    oi = pd.DataFrame({"ts": pd.to_datetime(["2025-04-03 00:00"]),
                       "open_interest": [49369.163]})
    ls = pd.DataFrame({"ts": pd.to_datetime(["2025-04-03 00:00"]),
                       "long_short_ratio": [1.72]})
    fg = pd.DataFrame({"date_utc": ["2023-06-29"], "value": [59]})
    panel = build(bars, funding=funding, oi=oi, ls=ls, dvol=dvol, fg=fg,
                  bands=EMPTY_BANDS)
    assert panel["oi"].isna().all()
    assert panel["ls_ratio"].isna().all()
    assert panel["band"].isna().all()
    assert panel["fg"].isna().all()           # F&G history starts 2023-06-29
    assert (panel["dvol"] == 84.88).all()     # within 24h cap all day
    assert panel["funding_rate"].tolist() == [
        0.0001, 0.0, 0.0002, 0.0, 0.0003, 0.0]


# -------------------------------------- load_panel plumbing (tmp CSVs)

def test_load_panel_reads_csvs_relative_to_data_dir(tmp_path, monkeypatch):
    import lab.dataset as dataset_mod

    # DATA_DIR default must point at <repo>/data via pathlib parents
    assert DATA_DIR.name == "data"
    assert DATA_DIR.parent.name == "bnbhack-cmc-t2"

    lab_dir = tmp_path / "data" / "lab"
    bf_dir = tmp_path / "data" / "backfill"
    lab_dir.mkdir(parents=True)
    bf_dir.mkdir(parents=True)

    stamps = [f"2025-04-03 {h:02d}:00:00.000" for h in (0, 4, 8, 12, 16, 20)]
    bars_rows = "\n".join(
        f"{s},{100 + i},{101 + i},{99 + i},{100.5 + i},1.0"
        for i, s in enumerate(stamps))
    (lab_dir / "bars_4h.csv").write_text(
        "open_time,open,high,low,close,volume\n" + bars_rows + "\n")
    (lab_dir / "oi_bybit.csv").write_text(
        "ts,open_interest\n2025-04-03 00:00:00.000,50000.0\n")
    (lab_dir / "ls_bybit.csv").write_text(
        "ts,long_short_ratio\n2025-04-03 00:00:00.000,1.7\n")
    (lab_dir / "dvol.csv").write_text(
        "ts,close\n2025-04-03 00:00:00.000,50.0\n")
    (lab_dir / "bands_rm17.csv").write_text(
        "bar_ts,region_id\n2025-04-03 00:00:00.000,4h::region01\n")
    (bf_dir / "funding_btcusdt_binance.csv").write_text(
        "funding_time_utc,funding_rate\n2025-04-03 00:00:00,0.0001\n")
    (bf_dir / "fear_greed.csv").write_text(
        "date_utc,value,source\n2025-04-02,40,cmc\n2025-04-03,55,cmc\n")

    monkeypatch.setattr(dataset_mod, "DATA_DIR", tmp_path / "data")
    panel = load_panel("full")

    assert list(panel.columns) == EXPECTED_COLUMNS
    assert len(panel) == 6
    assert panel.index[0] == pd.Timestamp("2025-04-03 00:00")
    assert panel["funding_rate"].tolist() == [0.0001, 0, 0, 0, 0, 0]
    assert (panel["oi"] == 50000.0).all()      # <= 20h staleness all day
    assert (panel["ls_ratio"] == 1.7).all()
    assert (panel["dvol"] == 50.0).all()
    assert panel["fg"].iloc[0] == 40.0         # 00:00 bar: prior day's value
    assert (panel["fg"].iloc[1:] == 55.0).all()  # from 04:00 bar onward
    assert panel["band"].iloc[0] == "4h::region01"
    assert panel["band"].iloc[1:].isna().all()
