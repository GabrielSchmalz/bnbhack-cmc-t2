"""Acceptance checks for the committed lab CSVs (plan Task 0.5, Step 4).

Runs on the committed files in data/lab/ ONLY — no network, no ClickHouse.
Checks: spans match the Preflight table; the 4h bar grid has no gaps > 1 bar
inside the full-stack window; OI/LS cadence has a median gap <= 2h.
"""

from pathlib import Path

import pandas as pd
import pytest

LAB = Path(__file__).resolve().parent.parent / "data" / "lab"

FULL_STACK_START = pd.Timestamp("2025-04-03 00:00:00")
FULL_STACK_END = pd.Timestamp("2026-06-09 20:00:00")  # last complete 4h bar at export
BAR = pd.Timedelta(hours=4)


def load(name: str, ts_col: str) -> pd.DataFrame:
    path = LAB / name
    assert path.exists(), f"missing committed CSV: {path}"
    df = pd.read_csv(path)
    df[ts_col] = pd.to_datetime(df[ts_col])
    return df


# ---------------------------------------------------------------- bars_4h


@pytest.fixture(scope="module")
def bars() -> pd.DataFrame:
    return load("bars_4h.csv", "open_time")


def test_bars_columns_and_span(bars):
    assert list(bars.columns) == ["open_time", "open", "high", "low", "close", "volume"]
    assert bars.open_time.min() == pd.Timestamp("2020-01-01 00:00:00")
    assert bars.open_time.max() >= FULL_STACK_END


def test_bars_duplicates_are_exact_copies(bars):
    # Known upstream anomaly: 7 bar timestamps on 2026-05-28/29 are stored twice.
    # They must be byte-identical rows (harmless under dedupe), never conflicting.
    dups = bars[bars.open_time.duplicated(keep=False)]
    if not dups.empty:
        assert dups.groupby("open_time").nunique().le(1).all().all(), (
            "conflicting duplicate bars detected"
        )


def test_bars_grid_no_gaps_in_full_stack_window(bars):
    grid = bars.drop_duplicates("open_time").set_index("open_time").sort_index()
    win = grid.loc[FULL_STACK_START:FULL_STACK_END]
    diffs = win.index.to_series().diff().dropna()
    # "no gaps > 1 bar": consecutive open_times at most 2 bar-widths apart
    assert (diffs <= 2 * BAR).all(), f"grid gap > 1 bar: max diff {diffs.max()}"
    # stronger observed property at export time: the window grid is complete
    assert (diffs == BAR).all(), f"grid not dense: {diffs[diffs != BAR]}"


def test_bars_values_sane(bars):
    for col in ["open", "high", "low", "close"]:
        assert (bars[col] > 0).all()
    assert (bars.high >= bars.low).all()
    assert (bars.volume >= 0).all()


# ---------------------------------------------------------------- oi / ls


@pytest.mark.parametrize(
    "name,value_col",
    [("oi_bybit.csv", "open_interest"), ("ls_bybit.csv", "long_short_ratio")],
)
def test_oi_ls_span_and_cadence(name, value_col):
    df = load(name, "ts")
    assert list(df.columns) == ["ts", value_col]
    assert df.ts.min() == FULL_STACK_START  # bybit series starts 2025-04-03
    assert df.ts.max() >= FULL_STACK_END
    assert df.ts.is_monotonic_increasing
    assert not df.ts.duplicated().any()
    median_gap = df.ts.diff().dropna().median()
    assert median_gap <= pd.Timedelta(hours=2), f"median cadence {median_gap} > 2h"
    assert (df[value_col] > 0).all()


# ---------------------------------------------------------------- dvol


def test_dvol_span():
    df = load("dvol.csv", "ts")
    assert list(df.columns) == ["ts", "close"]
    assert df.ts.min() == pd.Timestamp("2021-03-24 00:00:00")
    assert df.ts.max() >= FULL_STACK_END
    assert (df.close > 0).all()


# ---------------------------------------------------------------- bands


def test_bands_rm17_span_and_occupancy():
    df = load("bands_rm17.csv", "bar_ts")
    assert list(df.columns) == ["bar_ts", "region_id"]
    assert len(df) == 1357
    assert df.bar_ts.min() == pd.Timestamp("2025-10-04 20:00:00")
    assert df.bar_ts.max() == pd.Timestamp("2026-05-18 20:00:00")
    counts = df.region_id.str.extract(r"(region\d+)$")[0].value_counts().to_dict()
    assert counts == {"region01": 450, "region02": 455, "region03": 452}


# ---------------------------------------------------------------- liq events


def test_liq_events_span_and_fields():
    df = load("liq_events.csv", "ts")
    assert list(df.columns) == ["ts", "side", "usd_notional", "cascade"]
    assert df.ts.min() >= pd.Timestamp("2026-05-06")
    assert df.ts.max() >= pd.Timestamp("2026-06-09")
    assert set(df.side.unique()) <= {"buy", "sell"}
    assert (df.usd_notional > 0).all()
