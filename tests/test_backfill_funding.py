"""Task 0.3 step 4 — sanity tests on the COMMITTED funding CSV.

No network: these run on data/backfill/funding_btcusdt_binance.csv as
committed by scripts/backfill_funding.py.
"""

from pathlib import Path

import pandas as pd
import pytest

CSV_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "backfill"
    / "funding_btcusdt_binance.csv"
)


@pytest.fixture(scope="module")
def funding() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, parse_dates=["funding_time_utc"])
    df["funding_time_utc"] = df["funding_time_utc"].dt.tz_localize("UTC")
    return df


def test_csv_loads_with_expected_columns(funding: pd.DataFrame) -> None:
    assert list(funding.columns) == ["funding_time_utc", "funding_rate"]
    assert len(funding) > 7000  # ~3/day since 2019-09-10
    assert funding["funding_rate"].notna().all()


def test_stamps_8h_aligned(funding: pd.DataFrame) -> None:
    ts = funding["funding_time_utc"].dt
    assert (ts.hour % 8 == 0).all(), "hours must be 00/08/16 UTC"
    assert (ts.minute == 0).all()
    assert (ts.second == 0).all()


def test_sorted_no_duplicates(funding: pd.DataFrame) -> None:
    ts = funding["funding_time_utc"]
    assert ts.is_monotonic_increasing
    assert not ts.duplicated().any()


def test_span_covers_full_stack_window(funding: pd.DataFrame) -> None:
    # Full-stack window (PR-1): 2025-04-03 .. 2026-06-09 must be inside span.
    first = funding["funding_time_utc"].iloc[0]
    last = funding["funding_time_utc"].iloc[-1]
    assert first <= pd.Timestamp("2025-04-03", tz="UTC")
    assert last >= pd.Timestamp("2026-06-09", tz="UTC")


def test_rates_within_sanity_bounds(funding: pd.DataFrame) -> None:
    # Sanity bounds (plan Task 0.3 step 4): strictly inside (-0.0075, 0.0075).
    rates = funding["funding_rate"]
    assert (rates > -0.0075).all()
    assert (rates < 0.0075).all()
