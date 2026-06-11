"""Tests for lab/calibration_w.py — planted-edge power calibration (lane W-B).

Toy frames only — never a real-data row, never the committed artifact
(adversarial lane W-B builds the §9 planted-edge calibration; the heavy
real-panel runs happen out-of-band via scripts/run_w_calibration.sh).

Pinned behavior (docs/report/adversarial/lane2_gate_calibration.md §1,
replicated for the registered T-D D1 graded map):
  - injection mask from the DECISION bar: bar t carries drift iff
    label[t-1] is hot — pos-hi/pos-x -> downward drift (the D1 short leg
    earns), neg-hi/neg-x -> upward drift (the D1 long leg earns);
  - drift magnitude m_t ~ Normal(edge, edge), default_rng(99), one draw
    per masked bar in index order (noise sd = mean, lane-2 verbatim);
  - multiplicative self-consistent price path:
    M_open[t] = prod_{s<t}(1-d_s), M_close[t] = M_open[t]*(1-d_t);
    open' = open*M_open, close' = close*M_close, high/low scaled by
    M_close then enveloped to contain open'/close';
  - labels and funding untouched: the planted panel is rebuilt from the
    perturbed RAW bars through the unmodified build_w_panel assembly, so
    every price-derived Feature is recomputed consistently while funding
    /fg/oi sources are byte-identical;
  - the runner drives the UNMODIFIED run_w_sweep through its documented
    panel_loader injection point, one panel per run, into an isolated
    out dir — NEVER artifacts/w (the committed sweep artifact).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lab.calibration_w as calibration_w  # noqa: E402
from lab import rules  # noqa: E402
from lab.calibration_w import (  # noqa: E402
    CAL_OUT_ROOT_W,
    DRIFT_SEED_W,
    HOT_NEG_W,
    HOT_POS_W,
    RUNGS_BPS_W,
    _assert_isolated_out_dir,
    build_planted_panel_from_sources,
    drift_series,
    injection_masks,
    perturb_prices,
    plant_bars,
    run_calibration_cell,
)
from lab.classifiers_w import derive_thresholds_w, label_w  # noqa: E402
from lab.engine import run_backtest  # noqa: E402

FOUR_H = pd.Timedelta(hours=4)

# The registered D1 map (variants_w §5 vector), action dict form.
D1_MAP = {"pos-mid": 0.0, "pos-hi": -0.5, "pos-x": -1.0,
          "neg-mid": 0.0, "neg-hi": 0.5, "neg-x": 1.0}
D3_MAP = {k: -v for k, v in D1_MAP.items()}      # anti-aligned mirror


def _idx(n, start="2025-03-01 00:00"):
    return pd.date_range(start, periods=n, freq="4h")


# ------------------------------------------------------ registered constants


def test_registered_constants_pinned():
    assert RUNGS_BPS_W == (5, 10, 25)        # §9: >= 3 rungs, 5/10/25
    assert DRIFT_SEED_W == 99                # lane-2 drift seed, verbatim
    assert set(HOT_POS_W) == {"pos-hi", "pos-x"}
    assert set(HOT_NEG_W) == {"neg-hi", "neg-x"}
    assert CAL_OUT_ROOT_W == "artifacts/w/calibration"


# --------------------------------------------------------- injection masks


def test_injection_masks_decision_bar_lag():
    labels = pd.Series(
        ["pos-x", "pos-mid", "pos-hi", "neg-x", "neg-hi", "neg-mid"],
        index=_idx(6))
    pos, neg = injection_masks(labels)
    # bar t is masked iff label[t-1] is hot; bar 0 has no decision bar
    assert pos.tolist() == [False, True, False, True, False, False]
    assert neg.tolist() == [False, False, False, False, True, True]
    assert pos.index.equals(labels.index)
    assert neg.index.equals(labels.index)


def test_injection_masks_disjoint():
    labels = pd.Series(["pos-x", "neg-x", "pos-hi", "neg-hi"], index=_idx(4))
    pos, neg = injection_masks(labels)
    assert not (pos & neg).any()


# ------------------------------------------------------------ drift series


def test_drift_series_matches_registered_stream():
    idx = _idx(8)
    pos = pd.Series([False, True, False, True, False, False, False, False],
                    index=idx)
    neg = pd.Series([False, False, False, False, True, False, True, False],
                    index=idx)
    edge = 10 / 1e4
    d = drift_series(pos, neg, 10)
    # one Normal(edge, edge) draw per masked bar in index order (seed 99);
    # pos bars carry +m (downward price drift), neg bars carry -m (upward)
    m = np.random.default_rng(DRIFT_SEED_W).normal(edge, edge, 4)
    expected = np.zeros(8)
    expected[1], expected[3] = m[0], m[1]
    expected[4], expected[6] = -m[2], -m[3]
    np.testing.assert_array_equal(d.to_numpy(), expected)
    # deterministic: a second call is byte-identical
    np.testing.assert_array_equal(
        d.to_numpy(), drift_series(pos, neg, 10).to_numpy())


def test_drift_series_zero_off_mask_and_scales_with_rung():
    idx = _idx(6)
    pos = pd.Series([False, True, True, False, False, False], index=idx)
    neg = pd.Series(False, index=idx)
    d5 = drift_series(pos, neg, 5)
    d25 = drift_series(pos, neg, 25)
    assert (d5[~pos] == 0.0).all()
    # same seed, same mask: the draws are the rung scaled by 5x
    np.testing.assert_allclose(d25[pos].to_numpy(),
                               5.0 * d5[pos].to_numpy(), rtol=1e-12)


# ------------------------------------------------------------- price path


def _ohlc(n, seed=3):
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, 0.01, n)
    opens = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + r[:-1])))
    closes = np.empty(n)
    closes[:-1] = opens[1:]
    closes[-1] = opens[-1] * (1.0 + r[-1])
    high = np.maximum(opens, closes) * 1.005
    low = np.minimum(opens, closes) * 0.995
    return pd.DataFrame({"open": opens, "high": high, "low": low,
                         "close": closes, "volume": 1.0}, index=_idx(n))


def test_perturb_prices_lane2_multiplier_mechanics():
    bars = _ohlc(4)
    d = pd.Series([0.0, 0.01, 0.0, -0.02], index=bars.index)
    o, h, lo, c = perturb_prices(bars["open"], bars["high"], bars["low"],
                                 bars["close"], d)
    m_close = (1.0 - d).cumprod()
    m_open = m_close.shift(1).fillna(1.0)     # prod over s < t
    np.testing.assert_allclose(o.to_numpy(),
                               (bars["open"] * m_open).to_numpy())
    np.testing.assert_allclose(c.to_numpy(),
                               (bars["close"] * m_close).to_numpy())
    # continuity: bar-t drift lands inside bar t (close mult == next open mult)
    np.testing.assert_allclose(m_close.to_numpy()[:-1],
                               m_open.to_numpy()[1:])
    # envelope: high/low contain the perturbed open/close
    assert (h >= np.maximum(o, c) - 1e-12).all()
    assert (lo <= np.minimum(o, c) + 1e-12).all()


def test_perturb_prices_zero_drift_identity():
    bars = _ohlc(6)
    d = pd.Series(0.0, index=bars.index)
    o, h, lo, c = perturb_prices(bars["open"], bars["high"], bars["low"],
                                 bars["close"], d)
    pd.testing.assert_series_equal(o, bars["open"], check_names=False)
    pd.testing.assert_series_equal(h, bars["high"], check_names=False)
    pd.testing.assert_series_equal(lo, bars["low"], check_names=False)
    pd.testing.assert_series_equal(c, bars["close"], check_names=False)


def test_perturbed_engine_return_identity():
    # r'[t] = (1+r[t])(1-d_t)-1 on BOTH return conventions: the engine's
    # open-to-open r[t] = open[t+1]/open[t]-1 and close-to-close.
    bars = _ohlc(50, seed=11)
    rng = np.random.default_rng(5)
    d = pd.Series(np.where(rng.random(50) < 0.3,
                           rng.normal(0.002, 0.002, 50), 0.0),
                  index=bars.index)
    o, _, _, c = perturb_prices(bars["open"], bars["high"], bars["low"],
                                bars["close"], d)
    r = (bars["open"].shift(-1) / bars["open"] - 1.0).to_numpy()[:-1]
    rp = (o.shift(-1) / o - 1.0).to_numpy()[:-1]
    np.testing.assert_allclose(rp, (1.0 + r) * (1.0 - d.to_numpy()[:-1]) - 1.0,
                               rtol=1e-12, atol=1e-15)
    rc = (bars["close"] / bars["close"].shift(1) - 1.0).to_numpy()[1:]
    rcp = (c / c.shift(1) - 1.0).to_numpy()[1:]
    np.testing.assert_allclose(rcp, (1.0 + rc) * (1.0 - d.to_numpy()[1:]) - 1.0,
                               rtol=1e-12, atol=1e-15)


# ------------------------------------------------------------- plant_bars


def _csv_bars(idx):
    ohlc = _ohlc(len(idx))
    return pd.DataFrame({
        "open_time": idx,
        "open": ohlc["open"].to_numpy(),
        "high": ohlc["high"].to_numpy(),
        "low": ohlc["low"].to_numpy(),
        "close": ohlc["close"].to_numpy(),
        "volume": 1.0,
    })


def test_plant_bars_warmup_untouched_span_perturbed_tail_carried():
    idx = _idx(12)
    bars = _csv_bars(idx)
    span = idx[4:10]                           # the "panel grid"
    d = pd.Series(0.0, index=span)
    d.iloc[1] = 0.01
    d.iloc[4] = -0.02
    out = plant_bars(bars, d)
    assert list(out.columns) == list(bars.columns)
    # warmup rows (before the span) are byte-identical
    pd.testing.assert_frame_equal(out.iloc[:4], bars.iloc[:4])
    # volume is never touched
    pd.testing.assert_series_equal(out["volume"], bars["volume"])
    # span rows match perturb_prices on the span slice
    o, h, lo, c = perturb_prices(
        bars["open"].iloc[4:10].set_axis(span),
        bars["high"].iloc[4:10].set_axis(span),
        bars["low"].iloc[4:10].set_axis(span),
        bars["close"].iloc[4:10].set_axis(span), d)
    np.testing.assert_allclose(out["open"].iloc[4:10].to_numpy(),
                               o.to_numpy())
    np.testing.assert_allclose(out["close"].iloc[4:10].to_numpy(),
                               c.to_numpy())
    np.testing.assert_allclose(out["high"].iloc[4:10].to_numpy(),
                               h.to_numpy())
    np.testing.assert_allclose(out["low"].iloc[4:10].to_numpy(),
                               lo.to_numpy())
    # post-span rows carry the FULL accumulated multiplier on every price
    # column (drift is zero there: open and close multipliers coincide)
    final = float((1.0 - d).cumprod().iloc[-1])
    for col in ("open", "high", "low", "close"):
        np.testing.assert_allclose(out[col].iloc[10:].to_numpy(),
                                   (bars[col].iloc[10:] * final).to_numpy())


def test_plant_bars_duplicate_open_time_rows_supported():
    # D4.1: the committed CSV holds byte-identical duplicate rows; both
    # copies must receive the same multiplier (dedup happens downstream).
    idx = _idx(6)
    bars = _csv_bars(idx)
    dup = pd.concat([bars, bars.iloc[[3]]], ignore_index=True)
    d = pd.Series([0.0, 0.01, 0.0, 0.0, -0.01, 0.0], index=idx)
    out = plant_bars(dup, d)
    a, b = out.iloc[3], out.iloc[6]
    assert a["open"] == b["open"] and a["close"] == b["close"]


def test_plant_bars_off_grid_span_row_raises():
    idx = _idx(6)
    bars = _csv_bars(idx)
    bars.loc[3, "open_time"] = idx[3] + pd.Timedelta(hours=1)  # off-grid
    d = pd.Series(0.001, index=idx)
    with pytest.raises(ValueError):
        plant_bars(bars, d)


# ------------------------------------- planted panel through the assembly


def _toy_sources():
    """CSV-schema toy sources: warmup March + span April-May 2020."""
    idx = pd.date_range("2020-03-01 00:00", "2020-05-31 20:00", freq="4h")
    bars = _csv_bars(idx)
    stamps = pd.date_range("2020-03-01 00:00", "2020-05-31 16:00", freq="8h")
    mag = np.tile([1e-5, 5e-5, 9e-5], len(stamps) // 3 + 1)[:len(stamps)]
    sign = np.where((np.arange(len(stamps)) // 6) % 2 == 0, 1.0, -1.0)
    funding = pd.DataFrame({
        "funding_time_utc": stamps.strftime("%Y-%m-%d %H:%M:%S"),
        "funding_rate": mag * sign,
    })
    fg = pd.DataFrame(columns=["date_utc", "value"])
    start = pd.Timestamp("2020-04-01 00:00")
    end = pd.Timestamp("2020-05-31 20:00")
    return bars, funding, fg, start, end


def test_planted_panel_labels_and_funding_invariant():
    bars, funding, fg, start, end = _toy_sources()
    planted, meta = build_planted_panel_from_sources(
        bars, funding, fg, start, end, 25)
    base = meta["base_panel"]
    assert planted.index.equals(base.index)
    assert list(planted.columns) == list(base.columns)
    # the plant has bars to act on
    assert int(meta["pos_mask"].sum()) > 0
    assert int(meta["neg_mask"].sum()) > 0
    # funding / fg / volume byte-identical (labels and funding untouched)
    for col in ("funding_rate", "funding_rate_8h", "fg", "volume"):
        pd.testing.assert_series_equal(planted[col], base[col])
    # T-D labels (full-window cuts) are invariant under the injection
    thr_b = derive_thresholds_w(base, "TD")
    thr_p = derive_thresholds_w(planted, "TD")
    assert thr_b == thr_p
    pd.testing.assert_series_equal(label_w(planted, "TD", thr_p),
                                   label_w(base, "TD", thr_b))
    # prices actually moved somewhere
    assert (planted["close"] != base["close"]).any()


def test_planted_panel_features_recomputed_consistently():
    bars, funding, fg, start, end = _toy_sources()
    planted, meta = build_planted_panel_from_sources(
        bars, funding, fg, start, end, 25)
    # pc_24h is recomputed FROM THE PERTURBED closes by the assembly
    expected = planted["close"] / planted["close"].shift(6) - 1.0
    drifted = meta["d"] != 0.0
    np.testing.assert_allclose(
        planted["pc_24h"].iloc[6:].to_numpy(),
        expected.iloc[6:].to_numpy(), rtol=1e-12)
    assert not np.allclose(
        planted["pc_24h"].iloc[6:][drifted.iloc[6:]].to_numpy(),
        meta["base_panel"]["pc_24h"].iloc[6:][drifted.iloc[6:]].to_numpy())
    # OHLC stays a valid candle set
    assert (planted["high"] >= planted[["open", "close"]].max(axis=1)
            - 1e-12).all()
    assert (planted["low"] <= planted[["open", "close"]].min(axis=1)
            + 1e-12).all()


def test_planted_drift_lands_on_the_lagged_d1_position():
    # End-to-end sign alignment: rules.apply's 1-bar lag puts the D1
    # position on exactly the drift-carrying bars, so D1 gains and the
    # anti-aligned mirror D3 loses (frozen engine, zero costs).
    bars, funding, fg, start, end = _toy_sources()
    planted, meta = build_planted_panel_from_sources(
        bars, funding, fg, start, end, 25)
    base = meta["base_panel"]
    thr = derive_thresholds_w(base, "TD")
    labels = label_w(base, "TD", thr)
    zero_funding = pd.Series(0.0, index=base.index)

    def net(panel, amap):
        w = rules.apply(labels, amap)
        res = run_backtest(panel[["open", "high", "low", "close", "volume"]],
                           w, zero_funding, 0.0)
        return float((1.0 + res.bar_returns).prod() - 1.0)

    assert net(planted, D1_MAP) > net(base, D1_MAP)
    assert net(planted, D3_MAP) < net(base, D3_MAP)


# ------------------------------------------------------------- the runner


def _toy_panel_300() -> pd.DataFrame:
    """test_sweep_w-style toy panel (5-bar T-D episodes, fg all-NaN)."""
    n = 300
    idx = _idx(n)
    mag = np.tile(np.repeat([1e-5, 5e-5, 9e-5], 5), n // 15 + 1)[:n]
    sign = np.where((np.arange(n) // 15) % 2 == 0, 1.0, -1.0)
    f8 = mag * sign
    ohlc = _ohlc(n, seed=7)
    panel = ohlc.copy()
    panel["funding_rate"] = f8
    panel["funding_rate_8h"] = f8
    panel["fg"] = np.nan
    panel["rsi14_1d"] = 50.0
    panel["close_vs_sma200_1d"] = 1.0
    panel["pc_24h"] = panel["close"] / panel["close"].shift(6) - 1.0
    return panel


def test_run_calibration_cell_isolated_artifact(tmp_path):
    toy = _toy_panel_300()
    built = []

    def builder(asset, rung_bps):
        built.append((asset, rung_bps))
        return toy

    idx = toy.index
    results = run_calibration_cell(
        "BTC", 10, draws=8, jobs=1, out_root=str(tmp_path),
        panel_builder=builder,
        boundaries={"BTC": [idx[120], idx[180], idx[240]]},
        taxonomies={"BTC": ("TD",)},
    )
    assert built == [("BTC", 10)]
    cell = tmp_path / "P-BTC_10bps"
    on_disk = json.loads((cell / "sweep_results_w.json").read_text())
    assert on_disk == json.loads(json.dumps(results))
    # the T-D cell: 24 gated variants + the 8 P-BTC annex riders
    assert len(results["variants"]) == 32
    assert sum(r["annex"] for r in results["variants"]) == 8
    assert results["globals"]["n_draws"] == 8


def test_out_dir_guard_rejects_production_artifact_dir(tmp_path):
    repo = Path(__file__).resolve().parent.parent
    with pytest.raises(ValueError):
        _assert_isolated_out_dir(repo / "artifacts" / "w")
    # the registered calibration root passes
    _assert_isolated_out_dir(repo / "artifacts" / "w" / "calibration"
                             / "P-BTC_10bps")
    _assert_isolated_out_dir(tmp_path / "P-BTC_10bps")


def test_runner_guard_is_wired(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(calibration_w, "_assert_isolated_out_dir",
                        lambda p: calls.append(Path(p)))
    monkeypatch.setattr(calibration_w, "run_w_sweep",
                        lambda **kw: {"variants": [], "globals": {}})
    run_calibration_cell("BTC", 5, out_root=str(tmp_path),
                         panel_builder=lambda a, r: None)
    assert calls == [tmp_path / "P-BTC_5bps"]


def test_runner_loader_rejects_wrong_asset(tmp_path):
    seen = {}

    def fake_sweep(**kw):
        seen.update(kw)
        return {"variants": [], "globals": {}}

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(calibration_w, "run_w_sweep", fake_sweep)
        run_calibration_cell("ETH", 25, out_root=str(tmp_path),
                             panel_builder=lambda a, r: "PANEL")
    assert seen["panels"] == ("ETH",)
    assert seen["workers"] == 1
    assert seen["panel_loader"]("ETH") == "PANEL"
    with pytest.raises(ValueError):
        seen["panel_loader"]("BTC")


# ------------------------------------------------------------------- CLI


def test_cli_forwards_args(monkeypatch, tmp_path):
    seen = {}

    def stub(asset, rung_bps, **kwargs):
        seen.update({"asset": asset, "rung_bps": rung_bps, **kwargs})
        return {"variants": [], "globals": {}}

    monkeypatch.setattr(calibration_w, "run_calibration_cell", stub)
    calibration_w.main(["--asset", "SOL", "--rung", "25", "--jobs", "6",
                        "--out-root", str(tmp_path)])
    assert seen["asset"] == "SOL"
    assert seen["rung_bps"] == 25
    assert seen["jobs"] == 6
    assert seen["draws"] == 1000                     # registered default
    assert seen["out_root"] == str(tmp_path)


def test_cli_rejects_nonpositive_rung(monkeypatch):
    monkeypatch.setattr(calibration_w, "run_calibration_cell",
                        lambda *a, **k: {"variants": [], "globals": {}})
    with pytest.raises(SystemExit):
        calibration_w.main(["--asset", "BTC", "--rung", "0"])


def test_cli_rejects_unknown_asset():
    with pytest.raises(SystemExit):
        calibration_w.main(["--asset", "DOGE", "--rung", "10"])
