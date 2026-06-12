"""Layer-1 equality battery for the draw-parallel §8 cell calibration.

Design of record: docs/plans/2026-06-12-cal-fast-sketch.md (Phase 1,
grilled 2026-06-12, amendments B1-B13); grill verdicts:
docs/plans/2026-06-12-cal-fast-grill.md. The flag (`W_CAL_JOBS`, env,
default OFF) routes `sweep_w._cell_calibration`'s 200 registered draws
through a fork pool of per-draw workers; its acceptance bar is EXACT
equality with the serial path — the same dict (plain Python types,
mc_se float bits included) and, on fixtures where `verdict.passed`
varies, the same ORDERED per-draw verdict vector (B7 — a 0==0 equality
is not evidence).

Shapes (B7/B8):
  - direct `_cell_calibration` serial-vs-parallel dict equality on toys
    (plain / ts6 / vol-band; degenerate early-return cells; jobs <= 1);
  - the ordered per-draw verdict vector on a varying-verdict fixture,
    through the worker body AND the real fork pool;
  - the cold-vs-warm pandas `DatetimeIndex._cache` seam (B11 — the one
    observable side effect of the draw body on shared state);
  - toy `run_w_sweep` artifact byte-identity: flag off vs on vs
    on+workers=4 vs on+W_NULL_FAST=1 (+ the B6 provenance line);
  - the `run_calibration_cell` seam: env propagation with zero plumbing;
  - a flag-unset standing guard (subprocess, `W_CAL_JOBS` scrubbed: no
    calibration pool dispatch, no provenance line);
  - an env-gated real-cell prefix check (`W_CAL_FAST_REALPANEL=1`).

Every case monkeypatches `W_CAL_JOBS` explicitly (B8 — no ambient-env
exposure). Synthetic frames only, except the env-gated real-panel case.
Fixtures mirror tests/test_null_fast.py / tests/test_sweep_w.py's toy
conventions (mirrored, never cross-imported).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lab.sweep_w as sweep_w  # noqa: E402
from lab.benchmarks import hodl  # noqa: E402
from lab.gate_w import GateVerdictW  # noqa: E402
from lab.hooks import _restrict  # noqa: E402
from lab.hooks_w import episode_shuffles_w  # noqa: E402
from lab.sweep_w import _cell_calibration, _null_sharpes_w, run_w_sweep  # noqa: E402
from lab.variants_w import VariantW  # noqa: E402
from lab.walkforward import Fold  # noqa: E402

# Toy action map: graded symmetric fade plus a mapped-zero label ("mid")
# and an na placeholder label ("na") — unknown labels stay OUT of the map.
AMAP = {"pos-x": -1.0, "pos-hi": -0.5, "neg-x": 1.0, "neg-hi": 0.5,
        "mid": 0.0, "na": 0.0}
LABEL_POOL = np.array(["pos-x", "pos-hi", "neg-x", "neg-hi", "mid", "na"],
                      dtype=object)


def _variant(time_stop=None, vol_band=False, amap=AMAP):
    suffix = ("-ts" + str(time_stop) if time_stop else "") + \
        ("-vb" if vol_band else "")
    return VariantW(
        id=f"TOY-DIR-TD-X1-toy-1.0{suffix}",
        panel="P-BTC", family="direction", taxonomy="TD",
        action_map=tuple(amap.items()),
        time_stop=time_stop, vol_band=vol_band)


def _panel(n=420, seed=3):
    """Toy bars + funding on a 4h grid (synthetic, deterministic)."""
    idx = pd.date_range("2025-01-01 00:00", periods=n, freq="4h")
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, 0.01, n)
    opens = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + r[:-1])))
    closes = np.empty(n)
    closes[:-1] = opens[1:]
    closes[-1] = opens[-1] * (1.0 + r[-1])
    bars = pd.DataFrame({"open": opens,
                         "high": np.maximum(opens, closes),
                         "low": np.minimum(opens, closes),
                         "close": closes, "volume": 1.0}, index=idx)
    funding = pd.Series(rng.normal(0.0, 1e-4, n), index=idx)
    return idx, bars, funding


def _labels(idx, seed, pool=LABEL_POOL):
    """Random episode-y labels: short runs from the pool."""
    rng = np.random.default_rng(seed)
    vals = []
    while len(vals) < len(idx):
        vals.extend([rng.choice(pool)] * int(rng.integers(1, 6)))
    arr = np.array(vals[:len(idx)], dtype=object)
    return pd.Series(arr, index=idx, dtype=object)


def _ctx(idx, oos_spans, labels_by_fold, na_set, draws, hots=None):
    """(fold_ctx, shuffles) exactly as run_w_sweep wires them."""
    fold_ctx, shuffles = [], {}
    for i, (a, b) in enumerate(oos_spans):
        name = f"F{i + 1:02d}"
        fold = Fold(train_idx=idx[:a], oos_idx=idx[a:b], name=name)
        hot = (hots[i] if hots is not None
               else pd.Series(False, index=idx))
        fold_ctx.append({"fold": fold, "labels": labels_by_fold[i],
                         "hot": hot, "ordinal": i + 1,
                         "boundary": idx[a] if a < len(idx) else idx[-1]})
        shuffles[name] = episode_shuffles_w(
            labels_by_fold[i], na_set, draws,
            panel_index=0, taxonomy_index=0, fold_ordinal=i + 1)
    return fold_ctx, shuffles


def _cal_args(fold_ctx, bars, funding):
    """(pooled_oos_idx, fold_oos_idx, covered_folds, hodl_r10) as
    run_w_sweep wires them into _cell_calibration (covered = folds with
    a non-empty OOS — sufficient for the toy gate inputs)."""
    pooled = pd.DatetimeIndex([])
    for fc in fold_ctx:
        pooled = pooled.append(fc["fold"].oos_idx)
    pooled = pooled.unique().sort_values()
    fold_oos_idx = {fc["fold"].name: fc["fold"].oos_idx for fc in fold_ctx}
    covered = [fc["fold"].name for fc in fold_ctx
               if len(fc["fold"].oos_idx)]
    hodl_r10 = _restrict(hodl(bars, funding, 10.0).bar_returns, pooled)
    return pooled, fold_oos_idx, covered, hodl_r10


def _cell(variant, fold_ctx, shuffles, bars, funding, null_sharpes, n_cal):
    pooled, fold_oos, covered, hodl_r10 = _cal_args(fold_ctx, bars, funding)
    return _cell_calibration(variant, fold_ctx, shuffles, bars, funding,
                             hodl_r10, pooled, fold_oos, covered,
                             null_sharpes, n_cal)


def _both(variant, fold_ctx, shuffles, bars, funding, n_cal, monkeypatch,
          jobs=3):
    """Serial (flag scrubbed) vs parallel (W_CAL_JOBS=jobs): exact dict
    equality incl. float bits (json repr) and plain Python types (B12).
    The null vector is REAL (frozen `_null_sharpes_w`), never zeroed
    (B7)."""
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    null = _null_sharpes_w(variant, fold_ctx, shuffles, bars, funding,
                           n_cal)
    serial = _cell(variant, fold_ctx, shuffles, bars, funding, null, n_cal)
    monkeypatch.setenv("W_CAL_JOBS", str(jobs))
    par = _cell(variant, fold_ctx, shuffles, bars, funding, null, n_cal)
    assert par == serial
    assert json.dumps(par, sort_keys=True) == json.dumps(serial,
                                                         sort_keys=True)
    assert type(par["draws"]) is int                      # B12: plain types
    assert type(par["full_gate_pass_rate"]) is float
    assert type(par["mc_se"]) is float
    assert sweep_w._CAL_CTX_W == {}                       # B4: reset
    return serial


OOS_3 = ((120, 180), (240, 320), (380, 420))


# --------------------------------------- direct serial-vs-parallel equality


def test_plain_variant_dict_equality(monkeypatch):
    idx, bars, funding = _panel()
    labs = [_labels(idx, s) for s in (11, 12, 13)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=8)
    _both(_variant(), fold_ctx, shuffles, bars, funding, 8, monkeypatch)


def test_ts6_variant_dict_equality(monkeypatch):
    idx, bars, funding = _panel(seed=4)
    labs = [_labels(idx, s) for s in (21, 22, 23)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=8)
    _both(_variant(time_stop=6), fold_ctx, shuffles, bars, funding, 8,
          monkeypatch)


def test_vol_band_variant_dict_equality(monkeypatch):
    # Distinct per-fold hot masks pin the per-fold fc["hot"] consumption.
    idx, bars, funding = _panel(seed=5)
    rng = np.random.default_rng(99)
    hots = [pd.Series(rng.random(len(idx)) < 0.25 * (i + 1), index=idx)
            for i in range(3)]
    labs = [_labels(idx, s) for s in (31, 32, 33)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=8, hots=hots)
    _both(_variant(vol_band=True), fold_ctx, shuffles, bars, funding, 8,
          monkeypatch)


def test_jobs_exceeding_n_cal_dict_equality(monkeypatch):
    # pool size min(jobs, n_cal) (B3): more workers than draws is fine.
    idx, bars, funding = _panel(seed=6)
    labs = [_labels(idx, s) for s in (41, 42, 43)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=3)
    _both(_variant(), fold_ctx, shuffles, bars, funding, 3, monkeypatch,
          jobs=8)


# ------------------------------------------- flag posture + early returns


def _boom(*args, **kwargs):
    raise AssertionError("parallel calibration twin dispatched")


def test_degenerate_cells_return_frozen_dict_and_never_pool(monkeypatch):
    # B5: the frozen early return (n_cal <= 0 / no active folds) wins
    # before any flag parse or pool creation, even with the flag set.
    idx, bars, funding = _panel(seed=7)
    labs = [_labels(idx, s) for s in (51, 52)]
    monkeypatch.setenv("W_CAL_JOBS", "4")
    monkeypatch.setattr(sweep_w, "_cell_calibration_parallel", _boom)
    frozen = {"draws": 0, "full_gate_pass_rate": None, "mc_se": None}
    # n_cal = 0
    fold_ctx, shuffles = _ctx(idx, ((120, 180), (240, 320)), labs, set(),
                              draws=5)
    out = _cell(_variant(), fold_ctx, shuffles, bars, funding,
                np.zeros(5), 0)
    assert out == frozen
    # no active folds (every OOS slice empty)
    fold_ctx2, shuffles2 = _ctx(idx, ((150, 150), (250, 250)), labs, set(),
                                draws=5)
    out2 = _cell(_variant(), fold_ctx2, shuffles2, bars, funding,
                 np.zeros(5), 5)
    assert out2 == frozen


@pytest.mark.parametrize("flag", [None, "0", "1", "-3", ""])
def test_jobs_leq_one_takes_serial_path(monkeypatch, flag):
    # B2: unset / "" / integers <= 1 are a meaningful OFF — the serial
    # loop runs and the twin is never dispatched.
    idx, bars, funding = _panel(seed=8)
    labs = [_labels(idx, s) for s in (61, 62, 63)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=4)
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    null = _null_sharpes_w(_variant(), fold_ctx, shuffles, bars, funding, 4)
    serial = _cell(_variant(), fold_ctx, shuffles, bars, funding, null, 4)
    if flag is None:
        monkeypatch.delenv("W_CAL_JOBS", raising=False)
    else:
        monkeypatch.setenv("W_CAL_JOBS", flag)
    monkeypatch.setattr(sweep_w, "_cell_calibration_parallel", _boom)
    out = _cell(_variant(), fold_ctx, shuffles, bars, funding, null, 4)
    assert out == serial


def test_n_cal_one_takes_serial_path(monkeypatch):
    # B2: the parallel branch engages iff jobs > 1 AND n_cal > 1.
    idx, bars, funding = _panel(seed=9)
    labs = [_labels(idx, s) for s in (71, 72, 73)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=4)
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    null = _null_sharpes_w(_variant(), fold_ctx, shuffles, bars, funding, 4)
    serial = _cell(_variant(), fold_ctx, shuffles, bars, funding, null, 1)
    monkeypatch.setenv("W_CAL_JOBS", "4")
    monkeypatch.setattr(sweep_w, "_cell_calibration_parallel", _boom)
    out = _cell(_variant(), fold_ctx, shuffles, bars, funding, null, 1)
    assert out == serial


@pytest.mark.parametrize("bad", ["six", "2.5", " "])
def test_malformed_flag_raises_loudly(monkeypatch, bad):
    # B2 (A3 spirit): non-integer values raise, never a silent fallback.
    idx, bars, funding = _panel(seed=10)
    labs = [_labels(idx, s) for s in (81, 82, 83)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=3)
    monkeypatch.setenv("W_CAL_JOBS", bad)
    with pytest.raises(ValueError):
        _cell(_variant(), fold_ctx, shuffles, bars, funding, np.zeros(3), 3)


# ------------------------------------- ordered per-draw verdict vector (B7)


def test_per_draw_verdict_vector_ordered_and_varying(monkeypatch):
    """B7: on a fixture where verdict.passed VARIES across draws, the
    parallel worker body must reproduce the serial path's ORDERED
    per-draw verdict vector — a 0==0 equality is not evidence. No toy
    clears the real gate's clause-7 floor, so the gate is substituted
    with a deterministic surrogate of the draw's pooled@10 returns
    (both paths run the same surrogate; fork workers inherit it)."""
    idx, bars, funding = _panel(seed=21)
    labs = [_labels(idx, s) for s in (211, 212, 213)]
    n_cal = 24
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=n_cal)
    variant = _variant()
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    null = _null_sharpes_w(variant, fold_ctx, shuffles, bars, funding,
                           n_cal)

    calls = []

    def surrogate(pooled10, hodl_r10, null_sharpes, ladder, trades, w,
                  oos_idx, fold_oos_idx, covered_folds):
        passed = bool(float(pooled10.sum()) > 0.0)
        calls.append(passed)
        return GateVerdictW(passed=passed, reasons={"toy": passed},
                            stats={})

    monkeypatch.setattr(sweep_w, "shipping_gate_w", surrogate)
    serial = _cell(variant, fold_ctx, shuffles, bars, funding, null, n_cal)
    serial_vec = list(calls)
    assert len(serial_vec) == n_cal
    assert 0 < sum(serial_vec) < n_cal        # non-constant pass pattern

    # the worker body, in-process, ordered over draw indices
    pooled, fold_oos, covered, hodl_r10 = _cal_args(fold_ctx, bars, funding)
    active = [fc for fc in fold_ctx if len(fc["fold"].oos_idx)]
    monkeypatch.setattr(sweep_w, "_CAL_CTX_W", {
        "variant": variant, "active": active, "shuffles": shuffles,
        "bars": bars, "funding": funding, "hodl_r10": hodl_r10,
        "pooled_oos_idx": pooled, "fold_oos_idx": fold_oos,
        "covered_folds": covered, "null_sharpes": null})
    calls.clear()
    par_vec = [bool(sweep_w._mp_cal_draw(i)) for i in range(n_cal)]
    assert par_vec == serial_vec
    assert calls == serial_vec

    # and through the real fork pool (the workers inherit the surrogate)
    monkeypatch.setattr(sweep_w, "_CAL_CTX_W", {})
    monkeypatch.setenv("W_CAL_JOBS", "3")
    par = _cell(variant, fold_ctx, shuffles, bars, funding, null, n_cal)
    assert par == serial
    assert par["full_gate_pass_rate"] == sum(serial_vec) / n_cal


def test_cold_vs_warm_index_cache_seam(monkeypatch):
    """B11: the one observable side effect of the draw body on shared
    state is pandas lazily populating `DatetimeIndex._cache` on the fold
    OOS indexes — value-transparent. Draw k computed FIRST-THING on
    freshly built (cold) indexes must equal draw k computed after a warm
    prefix, exactly (reasons + stats blob)."""
    k = 5

    def fresh():
        idx, bars, funding = _panel(seed=31)
        labs = [_labels(idx, s) for s in (311, 312, 313)]
        fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=k + 1)
        return bars, funding, fold_ctx, shuffles

    monkeypatch.delenv("W_NULL_FAST", raising=False)
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    bars0, funding0, fold_ctx0, shuffles0 = fresh()
    null = _null_sharpes_w(_variant(), fold_ctx0, shuffles0, bars0,
                           funding0, k + 1)

    records = []
    real_gate = sweep_w.shipping_gate_w

    def spy(*args):
        v = real_gate(*args)
        records.append((dict(v.reasons), repr(sorted(v.stats.items()))))
        return v

    monkeypatch.setattr(sweep_w, "shipping_gate_w", spy)

    # cold: fresh objects, draw k first-thing through the worker body
    bars, funding, fold_ctx, shuffles = fresh()
    pooled, fold_oos, covered, hodl_r10 = _cal_args(fold_ctx, bars, funding)
    active = [fc for fc in fold_ctx if len(fc["fold"].oos_idx)]
    monkeypatch.setattr(sweep_w, "_CAL_CTX_W", {
        "variant": _variant(), "active": active, "shuffles": shuffles,
        "bars": bars, "funding": funding, "hodl_r10": hodl_r10,
        "pooled_oos_idx": pooled, "fold_oos_idx": fold_oos,
        "covered_folds": covered, "null_sharpes": null})
    sweep_w._mp_cal_draw(k)
    cold = records[-1]

    # warm: fresh objects again, serial draws 0..k — draw k is the last
    records.clear()
    bars, funding, fold_ctx, shuffles = fresh()
    _cell(_variant(), fold_ctx, shuffles, bars, funding, null, k + 1)
    assert len(records) == k + 1
    assert records[-1] == cold


# ----------------------------------------------------- integration seams


TOY_TAXONOMIES = ("TD", "TF")


def _toy_w_panel() -> pd.DataFrame:
    """test_sweep_w's toy panel, reproduced (synthetic, no data/ CSVs)."""
    n = 300
    idx = pd.date_range("2025-03-01 00:00", periods=n, freq="4h")
    mag = np.tile(np.repeat([1e-5, 5e-5, 9e-5], 5), n // 15 + 1)[:n]
    sign = np.where((np.arange(n) // 15) % 2 == 0, 1.0, -1.0)
    f8 = mag * sign
    rng = np.random.default_rng(7)
    r = rng.normal(0.0, 0.01, n)
    opens = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + r[:-1])))
    closes = np.empty(n)
    closes[:-1] = opens[1:]
    closes[-1] = opens[-1] * (1.0 + r[-1])
    panel = pd.DataFrame(
        {"open": opens, "high": np.maximum(opens, closes),
         "low": np.minimum(opens, closes), "close": closes, "volume": 1.0,
         "funding_rate": f8, "funding_rate_8h": f8, "fg": np.nan,
         "rsi14_1d": 50.0, "close_vs_sma200_1d": 1.0}, index=idx)
    panel["pc_24h"] = panel["close"] / panel["close"].shift(6) - 1.0
    return panel


_TOY_IDX = pd.date_range("2025-03-01 00:00", periods=300, freq="4h")
TOY_BOUNDARIES = [_TOY_IDX[120], _TOY_IDX[180], _TOY_IDX[240]]


def _toy_sweep(out_dir, workers=1):
    return run_w_sweep(
        panels=("BTC",), draws=8, out_dir=str(out_dir),
        panel_loader=lambda asset: _toy_w_panel(),
        boundaries={"BTC": TOY_BOUNDARIES},
        taxonomies={"BTC": TOY_TAXONOMIES}, workers=workers)


def test_full_sweep_artifact_byte_identical_flag_off_vs_on(monkeypatch,
                                                           tmp_path, capfd):
    # B8(b): toy run_w_sweep artifact byte-identity — off vs on vs
    # on+workers=4 (29(g) variant-pool seam) vs on+W_NULL_FAST=1; the B6
    # provenance line is stdout-only, once per parent process, and only
    # when the parallel path engages.
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    _toy_sweep(tmp_path / "off")
    assert "calibration path: parallel" not in capfd.readouterr().out
    monkeypatch.setenv("W_CAL_JOBS", "3")
    monkeypatch.setattr(sweep_w, "_cal_announced", False)
    _toy_sweep(tmp_path / "on")
    assert capfd.readouterr().out.count("calibration path: parallel") == 1
    monkeypatch.setattr(sweep_w, "_cal_announced", False)
    _toy_sweep(tmp_path / "on_par", workers=4)
    assert "calibration path: parallel" in capfd.readouterr().out
    monkeypatch.setenv("W_NULL_FAST", "1")
    monkeypatch.setattr(sweep_w, "_cal_announced", False)
    _toy_sweep(tmp_path / "on_null")
    text_off = (tmp_path / "off" / "sweep_results_w.json").read_text()
    text_on = (tmp_path / "on" / "sweep_results_w.json").read_text()
    text_par = (tmp_path / "on_par" / "sweep_results_w.json").read_text()
    text_null = (tmp_path / "on_null" / "sweep_results_w.json").read_text()
    assert text_off == text_on               # byte-identical artifact
    assert text_off == text_par              # and under the variant pool
    assert text_off == text_null             # and combined with null-fast


def test_run_calibration_cell_env_propagation(monkeypatch, tmp_path, capfd):
    # B8(c)/B2: the flag MUST reach _cell_calibration through
    # lab.calibration_w with ZERO plumbing (run_calibration_cell is
    # off-limits to edits) — env propagation, byte-identical artifact.
    from lab.calibration_w import run_calibration_cell
    kw = dict(draws=8, jobs=1,
              panel_builder=lambda asset, rung: _toy_w_panel(),
              boundaries={"BTC": TOY_BOUNDARIES},
              taxonomies={"BTC": TOY_TAXONOMIES})
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    run_calibration_cell("BTC", 5, out_root=str(tmp_path / "off"), **kw)
    assert "calibration path: parallel" not in capfd.readouterr().out
    monkeypatch.setenv("W_CAL_JOBS", "3")
    monkeypatch.setattr(sweep_w, "_cal_announced", False)
    run_calibration_cell("BTC", 5, out_root=str(tmp_path / "on"), **kw)
    # the pool actually engaged — proven by the provenance line
    assert "calibration path: parallel" in capfd.readouterr().out
    text_off = (tmp_path / "off" / "P-BTC_5bps"
                / "sweep_results_w.json").read_text()
    text_on = (tmp_path / "on" / "P-BTC_5bps"
               / "sweep_results_w.json").read_text()
    assert text_off == text_on


def test_flag_unset_standing_guard_subprocess():
    # B8/B6 standing guard (mirrors test_null_fast's flag-unset guard):
    # subprocess with W_CAL_JOBS scrubbed — the serial path runs, the
    # parallel twin is never dispatched, no provenance line is printed.
    # The zeroed null vector is fine HERE: this is a path guard, not an
    # equality test (the B7 prohibition binds equality tests only).
    code = (
        "import sys; sys.path.insert(0, '.')\n"
        "import numpy as np, pandas as pd\n"
        "import lab.sweep_w as sweep_w\n"
        "from lab.benchmarks import hodl\n"
        "from lab.hooks import _restrict\n"
        "from lab.hooks_w import episode_shuffles_w\n"
        "from lab.variants_w import VariantW\n"
        "from lab.walkforward import Fold\n"
        "def boom(*a, **k):\n"
        "    raise SystemExit('calibration twin dispatched, flag unset')\n"
        "sweep_w._cell_calibration_parallel = boom\n"
        "idx = pd.date_range('2025-01-01', periods=80, freq='4h')\n"
        "rng = np.random.default_rng(5)\n"
        "r = rng.normal(0.0, 0.01, 80)\n"
        "opens = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + r[:-1])))\n"
        "closes = np.empty(80)\n"
        "closes[:-1] = opens[1:]; closes[-1] = opens[-1]\n"
        "bars = pd.DataFrame({'open': opens,\n"
        "                     'high': np.maximum(opens, closes),\n"
        "                     'low': np.minimum(opens, closes),\n"
        "                     'close': closes, 'volume': 1.0}, index=idx)\n"
        "funding = pd.Series(0.0, index=idx)\n"
        "labels = pd.Series((['pos-x'] * 4 + ['mid'] * 4) * 10, index=idx,\n"
        "                   dtype=object)\n"
        "fold = Fold(train_idx=idx[:50], oos_idx=idx[50:], name='F01')\n"
        "fold_ctx = [{'fold': fold, 'labels': labels,\n"
        "             'hot': pd.Series(False, index=idx), 'ordinal': 1,\n"
        "             'boundary': idx[50]}]\n"
        "shuffles = {'F01': episode_shuffles_w(labels, set(), 4, 0, 0, 1)}\n"
        "variant = VariantW(id='TOY', panel='P-BTC', family='direction',\n"
        "                   taxonomy='TD',\n"
        "                   action_map=(('pos-x', -1.0), ('mid', 0.0)),\n"
        "                   time_stop=None, vol_band=False)\n"
        "hodl_r10 = _restrict(hodl(bars, funding, 10.0).bar_returns,\n"
        "                     fold.oos_idx)\n"
        "out = sweep_w._cell_calibration(\n"
        "    variant, fold_ctx, shuffles, bars, funding, hodl_r10,\n"
        "    fold.oos_idx, {'F01': fold.oos_idx}, ['F01'], np.zeros(4), 4)\n"
        "assert out['draws'] == 4\n"
        "print('clean')\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "W_CAL_JOBS"}
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True,
        text=True, cwd=str(Path(__file__).resolve().parent.parent))
    assert out.returncode == 0, out.stderr
    assert "clean" in out.stdout
    assert "calibration path: parallel" not in out.stdout


# ------------------------------------------ real-cell prefix (env-gated)


@pytest.mark.skipif(os.environ.get("W_CAL_FAST_REALPANEL") != "1",
                    reason="real-cell prefix check: slow, reads data/ "
                           "CSVs; set W_CAL_FAST_REALPANEL=1 (proof "
                           "battery)")
def test_real_cell_prefix_serial_vs_parallel(monkeypatch):
    """B8(d): the committed P-BTC_5bps TD calibration pick
    (P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0) on the real planted
    panel, REAL null vector (the W_NULL_FAST kernel — proven
    bit-identical by tests/test_null_fast.py + scripts/prove_null_fast.sh
    — never the zeroed §4 probe stand-in), first 6 calibration draws:
    serial vs parallel dict equality plus the ordered per-draw verdict
    vector and exact per-draw stats blobs. Read-only on data/ CSVs;
    writes nothing."""
    from lab.calibration_w import build_planted_panel
    from lab.hooks_w import PANEL_INDEX_W, TAXONOMY_INDEX_W
    from lab.panels_w import W_BOUNDARIES
    from lab.sweep import OHLCV
    from lab.sweep_w import (
        _build_fold_ctx,
        _na_set,
        _tax_key,
        compute_embargo,
    )
    from lab.variants_w import enumerate_all_w

    pick = "P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0"
    variant = next(v for v in enumerate_all_w() if v.id == pick)
    panel = build_planted_panel("BTC", 5)
    bars, funding = panel[OHLCV], panel["funding_rate"]
    bnds = [pd.Timestamp(b) for b in W_BOUNDARIES["BTC"]]
    embargo = compute_embargo(panel, "TD", bnds)
    fold_ctx = _build_fold_ctx(panel, "TD", bnds, embargo)
    n_cal = 6
    shuffles = {
        fc["fold"].name: episode_shuffles_w(
            fc["labels"], _na_set("TD"), n_cal, PANEL_INDEX_W["P-BTC"],
            TAXONOMY_INDEX_W[_tax_key("TD")], fc["ordinal"])
        for fc in fold_ctx}
    monkeypatch.setenv("W_NULL_FAST", "1")    # proven-identical REAL values
    null = _null_sharpes_w(variant, fold_ctx, shuffles, bars, funding,
                           n_cal)
    monkeypatch.delenv("W_NULL_FAST", raising=False)

    records = []
    real_gate = sweep_w.shipping_gate_w

    def spy(*args):
        v = real_gate(*args)
        records.append((bool(v.passed), repr(sorted(v.stats.items()))))
        return v

    monkeypatch.setattr(sweep_w, "shipping_gate_w", spy)
    monkeypatch.delenv("W_CAL_JOBS", raising=False)
    serial = _cell(variant, fold_ctx, shuffles, bars, funding, null, n_cal)
    serial_records = list(records)
    assert len(serial_records) == n_cal

    records.clear()
    monkeypatch.setenv("W_CAL_JOBS", "4")
    par = _cell(variant, fold_ctx, shuffles, bars, funding, null, n_cal)
    assert par == serial
    assert json.dumps(par, sort_keys=True) == json.dumps(serial,
                                                         sort_keys=True)

    # ordered per-draw verdict vector + stats blobs via the worker body
    pooled, fold_oos, covered, hodl_r10 = _cal_args(fold_ctx, bars, funding)
    active = [fc for fc in fold_ctx if len(fc["fold"].oos_idx)]
    monkeypatch.setattr(sweep_w, "_CAL_CTX_W", {
        "variant": variant, "active": active, "shuffles": shuffles,
        "bars": bars, "funding": funding, "hodl_r10": hodl_r10,
        "pooled_oos_idx": pooled, "fold_oos_idx": fold_oos,
        "covered_folds": covered, "null_sharpes": null})
    records.clear()
    vec = [bool(sweep_w._mp_cal_draw(i)) for i in range(n_cal)]
    assert records == serial_records
    assert vec == [p for p, _ in serial_records]
