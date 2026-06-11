"""ETH/SOL backfill tests — W-sweep registration §1 panels, §2 Bars + funding.

Two layers, mirroring tests/test_backfill_funding.py:

  1. Pure-helper unit tests on the backfill scripts (synthetic inputs, no
     network): SOL's +3..11 ms stamp jitter snaps to the exact 8h grid
     (recon §1), kline numeric strings trim like the committed bars_4h.csv,
     duplicate open_time stamps drop keep-first (D4.1 precedent).
  2. Sanity tests on the COMMITTED CSVs as written by the scripts — spans
     pinned to the recon §1 probe (ETH funding earliest 2019-11-27 08:00,
     SOL funding earliest 2020-09-13 16:00, ETH bars 2019-11-27 04:00, SOL
     bars 2020-09-14 04:00), contiguous 4h grid, panel end 2026-06-09 20:00.

No network: layer 2 runs on the committed files only.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.backfill_funding_eth_sol import snap_to_8h_grid_ms  # noqa: E402
from scripts.backfill_klines_eth_sol import (  # noqa: E402
    dedupe_klines,
    format_open_time,
    trim_number,
)

EIGHT_H_MS = 8 * 3600 * 1000
FOUR_H_MS = 4 * 3600 * 1000

FUNDING_ETH = REPO_ROOT / "data" / "backfill" / "funding_ethusdt_binance.csv"
FUNDING_SOL = REPO_ROOT / "data" / "backfill" / "funding_solusdt_binance.csv"
BARS_ETH = REPO_ROOT / "data" / "lab" / "bars_4h_eth.csv"
BARS_SOL = REPO_ROOT / "data" / "lab" / "bars_4h_sol.csv"


# ------------------------------------------------------------- pure helpers


def test_snap_handles_sol_millisecond_jitter():
    # Recon §1: SOL fundingTime stamps carry +3..11 ms jitter on the
    # 00/08/16 UTC boundaries. Snapping must land them exactly on the grid.
    boundary = 1600041600000  # 2020-09-14 00:00:00 UTC, a true 8h boundary
    for jitter in (0, 3, 7, 11, -11):
        assert snap_to_8h_grid_ms(boundary + jitter) == boundary


def test_snap_is_identity_on_grid_stamps():
    for k in range(5):
        ts = 1546300800000 + k * EIGHT_H_MS  # 2019-01-01 00:00 UTC + k*8h
        assert snap_to_8h_grid_ms(ts) == ts


def test_trim_number_matches_bars_csv_format():
    # data/lab/bars_4h.csv stores 7189.43 / 60755 / 12055.759 — no trailing
    # zeros, no trailing dot. Binance returns zero-padded strings.
    assert trim_number("7189.43000000") == "7189.43"
    assert trim_number("60755.00000000") == "60755"
    assert trim_number("12055.759") == "12055.759"
    assert trim_number("0.00000000") == "0"
    assert trim_number("150") == "150"


def test_format_open_time_matches_bars_csv_format():
    # bars_4h.csv open_time format: 2020-01-01 00:00:00.000
    assert format_open_time(1577836800000) == "2020-01-01 00:00:00.000"


def test_dedupe_klines_keeps_first_occurrence():
    # D4.1 precedent (lab/dataset.py): drop duplicate open_time, keep first.
    rows = [
        [FOUR_H_MS * 0, "1", "2", "0.5", "1.5", "10"],
        [FOUR_H_MS * 1, "1.5", "2", "1", "1.8", "11"],
        [FOUR_H_MS * 1, "9", "9", "9", "9", "99"],  # duplicate stamp
        [FOUR_H_MS * 2, "1.8", "2", "1.7", "1.9", "12"],
    ]
    kept, n_dropped = dedupe_klines(rows)
    assert n_dropped == 1
    assert [r[0] for r in kept] == [0, FOUR_H_MS, 2 * FOUR_H_MS]
    assert kept[1][1] == "1.5"  # first occurrence wins


# ------------------------------------------------- committed funding CSVs


@pytest.fixture(scope="module")
def funding_eth() -> pd.DataFrame:
    df = pd.read_csv(FUNDING_ETH, parse_dates=["funding_time_utc"])
    df["funding_time_utc"] = df["funding_time_utc"].dt.tz_localize("UTC")
    return df


@pytest.fixture(scope="module")
def funding_sol() -> pd.DataFrame:
    df = pd.read_csv(FUNDING_SOL, parse_dates=["funding_time_utc"])
    df["funding_time_utc"] = df["funding_time_utc"].dt.tz_localize("UTC")
    return df


@pytest.mark.parametrize("fix", ["funding_eth", "funding_sol"])
def test_funding_csv_columns_and_volume(fix, request):
    df = request.getfixturevalue(fix)
    assert list(df.columns) == ["funding_time_utc", "funding_rate"]
    assert df["funding_rate"].notna().all()


@pytest.mark.parametrize("fix", ["funding_eth", "funding_sol"])
def test_funding_stamps_8h_aligned(fix, request):
    ts = request.getfixturevalue(fix)["funding_time_utc"].dt
    assert (ts.hour % 8 == 0).all(), "hours must be 00/08/16 UTC"
    assert (ts.minute == 0).all()
    assert (ts.second == 0).all()


@pytest.mark.parametrize("fix", ["funding_eth", "funding_sol"])
def test_funding_sorted_no_duplicates(fix, request):
    ts = request.getfixturevalue(fix)["funding_time_utc"]
    assert ts.is_monotonic_increasing
    assert not ts.duplicated().any()


def test_funding_eth_span(funding_eth: pd.DataFrame):
    # Recon §1: ETHUSDT funding earliest = 2019-11-27 08:00 UTC, live tail.
    assert funding_eth["funding_time_utc"].iloc[0] == pd.Timestamp(
        "2019-11-27 08:00", tz="UTC"
    )
    assert funding_eth["funding_time_utc"].iloc[-1] >= pd.Timestamp(
        "2026-06-09", tz="UTC"
    )
    assert len(funding_eth) > 7000  # ~3/day since 2019-11-27


def test_funding_sol_span(funding_sol: pd.DataFrame):
    # Recon §1: SOLUSDT funding earliest = 2020-09-13 16:00 UTC, live tail.
    assert funding_sol["funding_time_utc"].iloc[0] == pd.Timestamp(
        "2020-09-13 16:00", tz="UTC"
    )
    assert funding_sol["funding_time_utc"].iloc[-1] >= pd.Timestamp(
        "2026-06-09", tz="UTC"
    )
    assert len(funding_sol) > 6100  # ~3/day since 2020-09-13


def test_funding_eth_rates_within_sanity_bounds(funding_eth: pd.DataFrame):
    # ETH history stays strictly inside the BTC-style (-0.0075, 0.0075) band.
    rates = funding_eth["funding_rate"]
    assert (rates > -0.0075).all()
    assert (rates < 0.0075).all()


def test_funding_sol_rates_within_sanity_bounds(funding_sol: pd.DataFrame):
    # SOL needs a wider band than BTC/ETH: its Binance funding cap is
    # dynamic and the committed series holds genuine cap prints — -0.0075
    # (2021-01-06/07), -0.02 during the FTX crash week (2022-11-09/10),
    # ~-0.0093 (2023-01-03/04). Bound = the widest observed cap, inclusive.
    rates = funding_sol["funding_rate"]
    assert (rates >= -0.02).all()
    assert (rates <= 0.02).all()


# ---------------------------------------------------- committed bars CSVs


@pytest.fixture(scope="module")
def bars_eth() -> pd.DataFrame:
    df = pd.read_csv(BARS_ETH, parse_dates=["open_time"])
    df["open_time"] = df["open_time"].dt.tz_localize("UTC")
    return df


@pytest.fixture(scope="module")
def bars_sol() -> pd.DataFrame:
    df = pd.read_csv(BARS_SOL, parse_dates=["open_time"])
    df["open_time"] = df["open_time"].dt.tz_localize("UTC")
    return df


@pytest.mark.parametrize("fix", ["bars_eth", "bars_sol"])
def test_bars_csv_columns_match_frozen_format(fix, request):
    # Identical column set/order to the committed data/lab/bars_4h.csv.
    df = request.getfixturevalue(fix)
    assert list(df.columns) == ["open_time", "open", "high", "low", "close", "volume"]
    assert df.notna().all().all()


@pytest.mark.parametrize("fix", ["bars_eth", "bars_sol"])
def test_bars_contiguous_4h_grid_no_duplicates(fix, request):
    ts = request.getfixturevalue(fix)["open_time"]
    assert ts.is_monotonic_increasing
    assert not ts.duplicated().any(), "duplicate open_time must be dropped (D4.1)"
    # resolution-independent grid check (pandas parses the .000 stamps as us)
    on_grid = (
        (ts.dt.hour % 4 == 0)
        & (ts.dt.minute == 0)
        & (ts.dt.second == 0)
        & (ts.dt.microsecond == 0)
    )
    assert on_grid.all(), "open_time must sit on the 4h UTC grid"
    diffs = ts.diff().dropna()
    assert (diffs == pd.Timedelta(hours=4)).all(), "4h grid must be contiguous"


def test_bars_eth_span_and_count(bars_eth: pd.DataFrame):
    # Recon §1: ETHUSDT 4h futures klines earliest = 2019-11-27 04:00 UTC;
    # panel end (registration §1) = 2026-06-09 20:00 open_time.
    assert bars_eth["open_time"].iloc[0] == pd.Timestamp(
        "2019-11-27 04:00", tz="UTC"
    )
    assert bars_eth["open_time"].iloc[-1] == pd.Timestamp(
        "2026-06-09 20:00", tz="UTC"
    )
    # contiguous grid between those stamps = 14,315 bars (~14k sanity)
    assert 14200 <= len(bars_eth) <= 14400


def test_bars_sol_span_and_count(bars_sol: pd.DataFrame):
    # Recon §1: SOLUSDT 4h futures klines earliest = 2020-09-14 04:00 UTC.
    assert bars_sol["open_time"].iloc[0] == pd.Timestamp(
        "2020-09-14 04:00", tz="UTC"
    )
    assert bars_sol["open_time"].iloc[-1] == pd.Timestamp(
        "2026-06-09 20:00", tz="UTC"
    )
    # contiguous grid between those stamps = 12,563 bars (~12.6k sanity)
    assert 12450 <= len(bars_sol) <= 12650


@pytest.mark.parametrize("fix", ["bars_eth", "bars_sol"])
def test_bars_ohlc_sane(fix, request):
    df = request.getfixturevalue(fix)
    assert (df[["open", "high", "low", "close"]] > 0).all().all()
    assert (df["high"] >= df[["open", "close", "low"]].max(axis=1)).all()
    assert (df["low"] <= df[["open", "close", "high"]].min(axis=1)).all()
    assert (df["volume"] >= 0).all()
