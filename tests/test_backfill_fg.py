"""Tests for the committed Fear & Greed backfill CSV (plan Task 0.4).

Runs on data/backfill/fear_greed.csv only — no network.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

CSV = Path(__file__).resolve().parents[1] / "data" / "backfill" / "fear_greed.csv"
FULL_STACK_START = date(2025, 4, 3)  # PR-1
FULL_STACK_END = date(2026, 6, 9)  # PR-1 (last full-stack day)


@pytest.fixture(scope="module")
def fg() -> pd.DataFrame:
    df = pd.read_csv(CSV)
    df["date_utc"] = pd.to_datetime(df["date_utc"]).dt.date
    return df


def test_columns(fg: pd.DataFrame) -> None:
    assert list(fg.columns) == ["date_utc", "value", "source"]


def test_values_in_0_100(fg: pd.DataFrame) -> None:
    assert fg["value"].between(0, 100).all()


def test_no_duplicate_dates(fg: pd.DataFrame) -> None:
    assert not fg["date_utc"].duplicated().any()


def test_source_values_known(fg: pd.DataFrame) -> None:
    assert set(fg["source"].unique()) <= {"cmc", "alternative.me"}


def test_span_covers_full_stack_window(fg: pd.DataFrame) -> None:
    assert fg["date_utc"].min() <= FULL_STACK_START
    assert fg["date_utc"].max() >= FULL_STACK_END


def test_daily_continuity_ge_99pct_over_full_stack_window(fg: pd.DataFrame) -> None:
    window_days = (FULL_STACK_END - FULL_STACK_START).days + 1
    present = fg.loc[
        (fg["date_utc"] >= FULL_STACK_START) & (fg["date_utc"] <= FULL_STACK_END),
        "date_utc",
    ].nunique()
    assert present / window_days >= 0.99
