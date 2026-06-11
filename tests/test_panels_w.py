"""W-sweep tests — lab/panels_w.py (widening registration §1 panels/folds/embargo, §2 sources).

Synthetic frames drive the assembly and geometry through build_w_panel /
w_folds / compute_embargo with hand-computed expectations. The REAL-data
tests at the bottom load the committed panels but assert ONLY on TRAIN-era
rows (every row-level assertion sits strictly before 2021-04-01 for P-BTC /
P-ETH and before 2021-10-01 only via the first-fold train slice for P-SOL;
no OOS index or value is ever asserted on) — Phase 1 has a hard
no-OOS-contact rule.

Pinned behavior (docs/plans/2026-06-10-widening-preregistration.md):
  §1  spans P-BTC/P-ETH 2020-04-01 00:00 -> 2026-06-09 20:00, P-SOL
      2020-10-01 00:00 ->; quarterly boundary lists 2021-04-01..2026-04-01
      (21) and 2021-10-01..2026-04-01 (19) — fold counts test-pinned;
      expanding train strictly before each boundary; OOS = [boundary + E
      bars .. next boundary) on the grid, final OOS to panel end;
      E = max(42, ceil(median NON-na episode bars)) on the FIRST fold's
      train slice labeled with that fold's train-derived cuts — na
      episodes excluded per §13 amendment 27, the floor binding when no
      non-na episode exists; warmup rows before the span start feed
      feature construction only, then the panel is trimmed to the span.
  §2  bars/funding/fg per asset through the frozen build_panel +
      add_features code paths (D4.4/D4.5 conventions reused, never
      duplicated); oi_chg_24h_daily via the registered lab.oi_cg loader,
      P-BTC only — P-ETH/P-SOL panels omit the column.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.panels_w import (  # noqa: E402
    ASSETS_W,
    OI_CG_CSV,
    W_BOUNDARIES,
    W_PANEL_COLUMNS,
    W_SPANS,
    build_w_panel,
    compute_embargo,
    load_w_panel,
    w_folds,
)

FOUR_H = pd.Timedelta(hours=4)


# ---------------------------------------------------------------- helpers

def _bars_frame(start, end, close=100.0):
    """Bars frame in the committed CSV schema on a complete 4h grid."""
    idx = pd.date_range(start, end, freq="4h")
    return pd.DataFrame({
        "open_time": idx,
        "open": close,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": 1.0,
    })


def _funding_frame(rows=()):
    return pd.DataFrame(list(rows), columns=["funding_time_utc", "funding_rate"])


def _fg_frame(rows=()):
    return pd.DataFrame(list(rows), columns=["date_utc", "value"])


def _td_panel(run_lengths, start="2024-01-01 00:00", abs_f=1e-4):
    """Synthetic W-panel frame whose T-D label episodes have the given
    lengths: |funding| is constant (q60 == q90 == abs_f, every bar is an
    extremity band) and the SIGN alternates per run, so episodes == runs."""
    vals = []
    sign = 1.0
    for n in run_lengths:
        vals.extend([sign * abs_f] * n)
        sign = -sign
    idx = pd.date_range(start, periods=len(vals), freq="4h")
    return pd.DataFrame({"funding_rate_8h": vals}, index=idx)


# ------------------------------------------------- registered constants (§1)

def test_boundary_lists_pinned():
    assert len(W_BOUNDARIES["BTC"]) == 21
    assert len(W_BOUNDARIES["ETH"]) == 21
    assert len(W_BOUNDARIES["SOL"]) == 19
    assert W_BOUNDARIES["ETH"] == W_BOUNDARIES["BTC"]  # P-ETH aligned (§1)
    assert W_BOUNDARIES["BTC"][0] == pd.Timestamp("2021-04-01")
    assert W_BOUNDARIES["BTC"][-1] == pd.Timestamp("2026-04-01")
    assert W_BOUNDARIES["SOL"][0] == pd.Timestamp("2021-10-01")
    assert W_BOUNDARIES["SOL"][-1] == pd.Timestamp("2026-04-01")


def test_boundaries_are_quarterly_calendar_utc():
    for asset in ASSETS_W:
        bs = W_BOUNDARIES[asset]
        for b in bs:
            assert b.month in (1, 4, 7, 10)
            assert b.day == 1 and b.hour == 0 and b.minute == 0
        # consecutive boundaries are exactly one quarter apart
        for a, b in zip(bs, bs[1:]):
            assert b == a + pd.DateOffset(months=3)


def test_spans_pinned():
    end = pd.Timestamp("2026-06-09 20:00")
    assert W_SPANS["BTC"] == (pd.Timestamp("2020-04-01 00:00"), end)
    assert W_SPANS["ETH"] == (pd.Timestamp("2020-04-01 00:00"), end)
    assert W_SPANS["SOL"] == (pd.Timestamp("2020-10-01 00:00"), end)
    assert ASSETS_W == ("BTC", "ETH", "SOL")  # §7 RNG panel order 0/1/2


# ------------------------------------------------------- w_folds geometry (§1)

def test_w_folds_counts_pinned_on_registered_grids():
    expected = {"BTC": 21, "ETH": 21, "SOL": 19}
    for asset in ASSETS_W:
        start, end = W_SPANS[asset]
        grid = pd.date_range(start, end, freq="4h")
        fs = w_folds(grid, W_BOUNDARIES[asset], 42)
        assert len(fs) == expected[asset]
        assert fs[0].name == "F01"
        assert fs[-1].name == f"F{expected[asset]:02d}"
        # final fold's OOS runs to the panel end (synthetic grid)
        assert fs[-1].oos_idx[-1] == grid[-1]


def test_w_folds_hand_computed_geometry():
    grid = pd.date_range("2025-01-01 00:00", periods=20, freq="4h")
    fs = w_folds(grid, [grid[8], grid[14]], 2)
    assert len(fs) == 2
    # F01: train strictly before boundary; OOS = [boundary + E .. next)
    assert fs[0].train_idx.equals(grid[:8])
    assert fs[0].oos_idx.equals(grid[10:14])
    # F02 (last): expanding train; OOS to panel end
    assert fs[1].train_idx.equals(grid[:14])
    assert fs[1].oos_idx.equals(grid[16:20])


def test_w_folds_zero_embargo_oos_starts_at_boundary():
    grid = pd.date_range("2025-01-01 00:00", periods=12, freq="4h")
    fs = w_folds(grid, [grid[6]], 0)
    assert fs[0].oos_idx[0] == grid[6]
    assert fs[0].oos_idx[-1] == grid[-1]


def test_w_folds_boundary_between_bars_uses_strictly_before():
    grid = pd.date_range("2025-01-01 00:00", periods=12, freq="4h")
    boundary = grid[6] + pd.Timedelta(hours=2)  # off-grid timestamp
    fs = w_folds(grid, [boundary], 1)
    # train = every grid bar strictly before the boundary (grid[6] included)
    assert fs[0].train_idx.equals(grid[:7])
    # OOS starts E bars after the first bar at-or-after the boundary
    assert fs[0].oos_idx[0] == grid[8]


def test_w_folds_first_fold_on_btc_grid_pinned():
    start, end = W_SPANS["BTC"]
    grid = pd.date_range(start, end, freq="4h")
    fs = w_folds(grid, W_BOUNDARIES["BTC"], 42)
    f01 = fs[0]
    # first train = exactly one year of 4h bars (§1: first train = 1 year)
    assert len(f01.train_idx) == 2190
    assert f01.train_idx[0] == pd.Timestamp("2020-04-01 00:00")
    assert f01.train_idx[-1] == pd.Timestamp("2021-03-31 20:00")
    # E = 42 bars = 7 days on the 4h grid
    assert f01.oos_idx[0] == pd.Timestamp("2021-04-08 00:00")
    # OOS ends strictly before the next boundary
    assert f01.oos_idx[-1] == pd.Timestamp("2021-06-30 20:00")


def test_w_folds_unsorted_index_raises():
    grid = pd.DatetimeIndex(
        ["2025-01-01 04:00", "2025-01-01 00:00", "2025-01-01 08:00"])
    with pytest.raises(ValueError):
        w_folds(grid, [pd.Timestamp("2025-01-01 04:00")], 0)


# ---------------------------------------------------- compute_embargo (§1)

def test_embargo_floor_binds_on_short_episodes():
    panel = _td_panel([3] * 10)  # median episode length 3
    boundary = panel.index[-1] + FOUR_H  # whole frame is first-fold train
    assert compute_embargo(panel, "TD", [boundary]) == 42


def test_embargo_median_above_floor():
    panel = _td_panel([100, 100, 100, 100])
    boundary = panel.index[-1] + FOUR_H
    assert compute_embargo(panel, "TD", [boundary]) == 100


def test_embargo_ceils_fractional_median():
    # episode lengths 100, 101, 100, 101 -> median 100.5 -> ceil -> 101
    panel = _td_panel([100, 101, 100, 101])
    boundary = panel.index[-1] + FOUR_H
    assert compute_embargo(panel, "TD", [boundary]) == 101


def test_embargo_uses_only_first_fold_train_slice():
    # train (before boundaries[0]): runs of 3 -> floor binds (E = 42).
    # post-boundary rows hold runs of 200 that would push the median to 200
    # if the slice leaked — §1 pins the FIRST fold's train slice.
    panel = _td_panel([3, 3, 3, 3] + [200] * 6)
    boundary = panel.index[12]  # first 12 bars are the train slice
    assert compute_embargo(panel, "TD", [boundary]) == 42


def test_embargo_tf_all_na_train_slice_floor_binds():
    # §13 amendment 27: na episodes are EXCLUDED from the embargo median —
    # they are missing-feature placeholders, not regime episodes (frozen
    # in the null, excluded from honest-N). A T-F train slice with zero fg
    # coverage labels EVERY bar fg-na (one 300-bar episode here; on the
    # real panel ONE 2,190-bar episode -> E = 2,190, structurally voiding
    # every T-F OOS slice — the formula artifact the amendment repairs).
    # With no non-na episodes the 42-bar floor binds.
    idx = pd.date_range("2024-01-01", periods=300, freq="4h")
    panel = pd.DataFrame(
        {"funding_rate_8h": 1e-4, "fg": np.nan}, index=idx)
    boundary = idx[-1] + FOUR_H
    assert compute_embargo(panel, "TF", [boundary]) == 42


def test_embargo_non_na_median_binds_above_floor():
    # Amendment 27 keeps the non-na median binding when it exceeds the
    # floor. T-G slice: five 108-bar labeled episodes separated/flanked by
    # six 3-bar sma-na episodes. Non-na median = 108 -> E = 108; the
    # all-episode median would be 3 (the 42-bar floor would bind), so this
    # pins that na EXCLUSION, not the floor, drives E. Coverage: 558 bars
    # = 93 UTC days, every day holds >= 3 non-NaN sma observations, so the
    # §2 coverage floor (90 days) does not trip.
    sma: list[float] = []
    sign = 1.0
    for _ in range(5):
        sma.extend([np.nan] * 3)
        sma.extend([sign] * 108)
        sign = -sign
    sma.extend([np.nan] * 3)
    idx = pd.date_range("2024-01-01", periods=len(sma), freq="4h")
    panel = pd.DataFrame(
        {"funding_rate_8h": 1e-4, "close_vs_sma200_1d": sma}, index=idx)
    boundary = idx[-1] + FOUR_H
    assert compute_embargo(panel, "TG", [boundary]) == 108


def test_embargo_empty_train_slice_returns_floor():
    panel = _td_panel([3, 3, 3])
    boundary = panel.index[0]  # nothing strictly before -> empty train
    assert compute_embargo(panel, "TD", [boundary]) == 42


# ------------------------------------------------ build_w_panel assembly (§2)

def test_span_trim_and_column_set():
    bars = _bars_frame("2020-03-01 00:00", "2020-05-10 20:00")
    start = pd.Timestamp("2020-04-01 00:00")
    end = pd.Timestamp("2020-05-01 20:00")
    panel = build_w_panel(bars, _funding_frame(), _fg_frame(), start, end)
    assert panel.index[0] == start
    assert panel.index[-1] == end
    assert len(panel) == len(pd.date_range(start, end, freq="4h"))
    # non-BTC column set: oi_chg_24h_daily omitted, order pinned
    expected = [c for c in W_PANEL_COLUMNS if c != "oi_chg_24h_daily"]
    assert list(panel.columns) == expected


def test_funding_stamp_join_and_ffill_convention_reused():
    # one true stamp at 08:00; the frozen D4.5 + add_features convention:
    # stamp-hour bars without a row carry filler 0.0 (treated as a true
    # 0.0 rate), non-stamp bars ffill from the last stamp-hour bar.
    bars = _bars_frame("2020-04-01 00:00", "2020-04-01 20:00")
    funding = _funding_frame([("2020-04-01 08:00:00", 5e-4)])
    panel = build_w_panel(
        bars, funding, _fg_frame(),
        pd.Timestamp("2020-04-01 00:00"), pd.Timestamp("2020-04-01 20:00"))
    assert panel["funding_rate"].tolist() == [0.0, 0.0, 5e-4, 0.0, 0.0, 0.0]
    assert panel["funding_rate_8h"].tolist() == [0.0, 0.0, 5e-4, 5e-4, 0.0, 0.0]


def test_fg_d44_availability_rule_reused():
    # day-D F&G becomes available at the D 04:00 bar (frozen D4.4), then
    # carries with no staleness cap.
    bars = _bars_frame("2020-04-01 00:00", "2020-04-03 20:00")
    fg = _fg_frame([("2020-04-01", 40.0), ("2020-04-02", 55.0)])
    panel = build_w_panel(
        bars, _funding_frame(), fg,
        pd.Timestamp("2020-04-01 00:00"), pd.Timestamp("2020-04-03 20:00"))
    assert np.isnan(panel.loc[pd.Timestamp("2020-04-01 00:00"), "fg"])
    assert panel.loc[pd.Timestamp("2020-04-01 04:00"), "fg"] == 40.0
    assert panel.loc[pd.Timestamp("2020-04-02 00:00"), "fg"] == 40.0
    assert panel.loc[pd.Timestamp("2020-04-02 04:00"), "fg"] == 55.0
    assert panel.loc[pd.Timestamp("2020-04-03 20:00"), "fg"] == 55.0  # no cap


def test_oi_cg_column_btc_availability_rule():
    bars = _bars_frame("2020-04-01 00:00", "2020-04-03 20:00")
    daily = pd.Series(
        [100.0, 110.0, 132.0],
        index=pd.DatetimeIndex(
            ["2020-04-01 00:00", "2020-04-02 00:00", "2020-04-03 00:00"]),
    )
    panel = build_w_panel(
        bars, _funding_frame(), _fg_frame(),
        pd.Timestamp("2020-04-01 00:00"), pd.Timestamp("2020-04-03 20:00"),
        oi_cg_daily=daily)
    assert list(panel.columns) == W_PANEL_COLUMNS
    col = panel["oi_chg_24h_daily"]
    # Apr-1 chg is NaN (no Mar-31 snapshot) and serves through Apr-2 00:00
    assert col.loc[:"2020-04-02 00:00"].isna().all()
    # Apr-2 chg = 0.10 usable from the first bar strictly after its stamp
    assert col.loc[pd.Timestamp("2020-04-02 04:00")] == pytest.approx(0.10)
    assert col.loc[pd.Timestamp("2020-04-03 00:00")] == pytest.approx(0.10)
    # Apr-3 chg = 0.20 from the 04:00 bar onward
    assert np.allclose(col.loc["2020-04-03 04:00":], 0.20)


def test_oi_cg_column_omitted_without_series():
    bars = _bars_frame("2020-04-01 00:00", "2020-04-01 20:00")
    panel = build_w_panel(
        bars, _funding_frame(), _fg_frame(),
        pd.Timestamp("2020-04-01 00:00"), pd.Timestamp("2020-04-01 20:00"))
    assert "oi_chg_24h_daily" not in panel.columns


def test_warmup_rows_feed_features_then_trim():
    # bars from 2020-01-01 with span start 2020-04-01: daily close #200
    # (counting the WARMUP days) is 2020-07-18, available D+1 -> the
    # 2020-07-19 00:00 bar is the FIRST non-NaN SMA200 bar. Without warmup
    # the first valid bar would sit at/after span_start + 200 days
    # (2020-10-18) — the assertion below proves warmup rows counted.
    bars = _bars_frame("2020-01-01 00:00", "2020-08-31 20:00")
    start = pd.Timestamp("2020-04-01 00:00")
    end = pd.Timestamp("2020-08-31 20:00")
    panel = build_w_panel(bars, _funding_frame(), _fg_frame(), start, end)
    assert panel.index[0] == start  # warmup rows trimmed from the panel
    sma = panel["close_vs_sma200_1d"]
    assert sma.first_valid_index() == pd.Timestamp("2020-07-19 00:00")
    assert sma.first_valid_index() < start + pd.Timedelta(days=200)
    assert sma.loc[:"2020-07-18 20:00"].isna().all()
    # constant closes: close - SMA200 == 0.0 once defined
    assert (sma.loc["2020-07-19 00:00":] == 0.0).all()
    # RSI(14) and pc_24h are warmup-seeded long before the span start:
    # non-NaN from the very first panel bar (flat closes -> RSI 50, pc 0)
    assert panel["rsi14_1d"].iloc[0] == 50.0
    assert panel["pc_24h"].iloc[0] == 0.0


def test_load_w_panel_unknown_asset_raises():
    with pytest.raises(ValueError):
        load_w_panel("DOGE")


# ----------------------------------------- REAL data, TRAIN-era rows ONLY
#
# Every row-level assertion below is restricted to rows strictly before
# the panel's FIRST fold boundary (P-BTC/P-ETH 2021-04-01, P-SOL
# 2021-10-01) — first-fold TRAIN rows, never OOS. No assertion reads an
# index entry or value beyond that boundary.

BTC_TRAIN_END = "2021-03-31 20:00"      # last bar before 2021-04-01
SOL_TRAIN_END = "2021-09-30 20:00"      # last bar before 2021-10-01


@pytest.fixture(scope="module")
def btc_panel():
    return load_w_panel("BTC")


@pytest.fixture(scope="module")
def eth_panel():
    return load_w_panel("ETH")


@pytest.fixture(scope="module")
def sol_panel():
    return load_w_panel("SOL")


def test_real_btc_span_start_and_train_grid(btc_panel):
    assert btc_panel.index[0] == pd.Timestamp("2020-04-01 00:00")
    assert list(btc_panel.columns) == W_PANEL_COLUMNS
    train = btc_panel.loc[:BTC_TRAIN_END]
    assert len(train) == 2190  # one year of complete 4h bars
    assert (train.index.to_series().diff().dropna() == FOUR_H).all()


def test_real_btc_train_era_features(btc_panel):
    train = btc_panel.loc[:BTC_TRAIN_END]
    first = train.index[0]
    # funding warmup-seeded: the 2020-04-01 00:00 stamp is a true CSV row
    assert train.loc[first, "funding_rate_8h"] == pytest.approx(-9.237e-05)
    # RSI/pc_24h warmup-seeded -> non-NaN from the first panel bar
    assert not np.isnan(train.loc[first, "rsi14_1d"])
    assert not np.isnan(train.loc[first, "pc_24h"])
    # SMA200: sma-na on early-panel bars (§1 — no panel has 200 daily
    # closes before its start); first valid bar counts the 91 warmup days
    # (bars_4h.csv starts 2020-01-01), so it lands in July 2020, well
    # before span_start + 200 days (2020-10-18)
    sma_first = train["close_vs_sma200_1d"].first_valid_index()
    assert np.isnan(train.loc[first, "close_vs_sma200_1d"])
    assert pd.Timestamp("2020-07-01") < sma_first < pd.Timestamp("2020-08-01")
    # CMC F&G history starts 2023-06-29: the whole first-fold train is NaN
    assert train["fg"].isna().all()


def test_real_btc_oi_cg_value_hand_computed(btc_panel):
    # 2020-04-01 00:00 bar sees the last stamp strictly before its open
    # (2020-03-31 00:00): chg = oi(03-31)/oi(03-30) - 1. TRAIN-era CSV
    # rows only.
    raw = pd.read_csv(OI_CG_CSV)
    raw["ts"] = pd.to_datetime(raw["ts"])
    raw = raw[raw["ts"] < pd.Timestamp("2020-04-01")]
    snap = raw.set_index("ts")["oi"].astype(float)
    expected = (snap.loc[pd.Timestamp("2020-03-31")]
                / snap.loc[pd.Timestamp("2020-03-30")] - 1.0)
    got = btc_panel.loc[pd.Timestamp("2020-04-01 00:00"), "oi_chg_24h_daily"]
    assert got == pytest.approx(expected)


def test_real_eth_panel_train_era(eth_panel):
    assert eth_panel.index[0] == pd.Timestamp("2020-04-01 00:00")
    assert "oi_chg_24h_daily" not in eth_panel.columns  # §2: BTC only
    train = eth_panel.loc[:BTC_TRAIN_END]
    assert len(train) == 2190
    first = train.index[0]
    assert not np.isnan(train.loc[first, "funding_rate_8h"])
    # ETH bars start 2019-11-27 -> 200th daily close 2020-06-13, available
    # 2020-06-14 (in-span, train era)
    sma_first = train["close_vs_sma200_1d"].first_valid_index()
    assert np.isnan(train.loc[first, "close_vs_sma200_1d"])
    assert pd.Timestamp("2020-06-01") < sma_first < pd.Timestamp("2020-07-01")


def test_real_sol_panel_train_era(sol_panel):
    assert sol_panel.index[0] == pd.Timestamp("2020-10-01 00:00")
    assert "oi_chg_24h_daily" not in sol_panel.columns  # §2: BTC only
    train = sol_panel.loc[:SOL_TRAIN_END]
    assert len(train) == 2190
    first = train.index[0]
    assert not np.isnan(train.loc[first, "funding_rate_8h"])
    # SOL warmup is 17 days (bars start 2020-09-14): enough for RSI(14)
    # at the span start, nowhere near 200 daily closes for the SMA
    assert not np.isnan(train.loc[first, "rsi14_1d"])
    assert train.loc[:"2021-03-31", "close_vs_sma200_1d"].isna().all()


def test_real_fold_counts_pinned(btc_panel, eth_panel, sol_panel):
    fs_btc = w_folds(btc_panel.index, W_BOUNDARIES["BTC"], 42)
    fs_eth = w_folds(eth_panel.index, W_BOUNDARIES["ETH"], 42)
    fs_sol = w_folds(sol_panel.index, W_BOUNDARIES["SOL"], 42)
    assert len(fs_btc) == 21
    assert len(fs_eth) == 21
    assert len(fs_sol) == 19
    assert [f.name for f in fs_btc] == [f"F{i:02d}" for i in range(1, 22)]
    # first-fold train slices (TRAIN-era assertions only)
    assert fs_btc[0].train_idx[-1] == pd.Timestamp(BTC_TRAIN_END)
    assert len(fs_btc[0].train_idx) == 2190
    assert fs_sol[0].train_idx[-1] == pd.Timestamp(SOL_TRAIN_END)
    assert len(fs_sol[0].train_idx) == 2190
