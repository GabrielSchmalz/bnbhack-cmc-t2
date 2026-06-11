"""Tests for lab/sweep_w.py — the W-sweep driver (widening registration).

Synthetic frames only — never data/ CSVs, never a real-panel OOS row
(Phase 1 hard no-OOS-contact rule). The toy panel: 300 4h bars from
2025-03-01, injected through run_w_sweep's panel_loader with toy
boundary/taxonomy overrides (the documented test-injection points; the
registered defaults are untouched).

Toy design:
  - T-D machinery: |funding_rate_8h| cycles 1/5/9 e-5 in 5-bar sub-blocks
    and the sign flips every 15 bars, so every fold's train quantiles are
    c_hi = 5e-5 / c_x = 9e-5 and every T-D label episode is exactly 5
    bars (embargo floor 42 binds).
  - T-F machinery: fg is all-NaN, so the §2 coverage floor labels every
    bar fg-na on every fold. Every T-F variant is therefore ALWAYS FLAT
    (na acts 0) — the planted always-flat family — and the §13 amendment
    27 embargo repair is what gives T-F a non-empty OOS at all (no non-na
    episodes -> floor 42; pre-repair E = first-fold train length).
  - boundaries at bars 120/180/240 -> 3 folds; with E = 42 each fold's
    OOS is 18 bars; the 2025-04-01 era split lands between F01 (pre) and
    F02/F03 (post).
  - P-BTC + (TD, TF) selects 24 + 10 gated variants + the 8 annex = 42.
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

import lab.sweep_w as sweep_w  # noqa: E402
from lab.gate_w import MIN_OOS_TRADES  # noqa: E402
from lab.hooks_w import PANEL_INDEX_W, TAXONOMY_INDEX_W  # noqa: E402
from lab.sweep_w import (  # noqa: E402
    _assert_train_side,
    run_w_sweep,
    structural_feasibility_readout,
)

N_TOY = 300
TOY_START = "2025-03-01 00:00"
TOY_TAXONOMIES = ("TD", "TF")
CLAUSES_W = {"beats_flat", "beats_hodl", "null_pass", "top5_pass",
             "ladder_pass", "null_p99", "min_active_sample", "topk_pass"}


def _toy_panel() -> pd.DataFrame:
    idx = pd.date_range(TOY_START, periods=N_TOY, freq="4h")
    mag = np.tile(np.repeat([1e-5, 5e-5, 9e-5], 5), N_TOY // 15 + 1)[:N_TOY]
    sign = np.where((np.arange(N_TOY) // 15) % 2 == 0, 1.0, -1.0)
    f8 = mag * sign
    rng = np.random.default_rng(7)          # fixed seed: deterministic toy
    r = rng.normal(0.0, 0.01, N_TOY)
    opens = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + r[:-1])))
    closes = np.empty(N_TOY)
    closes[:-1] = opens[1:]
    closes[-1] = opens[-1] * (1.0 + r[-1])
    panel = pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes),
            "low": np.minimum(opens, closes),
            "close": closes,
            "volume": 1.0,
            "funding_rate": f8,
            "funding_rate_8h": f8,
            "fg": np.nan,                    # T-F: zero coverage -> fg-na
            "rsi14_1d": 50.0,
            "close_vs_sma200_1d": 1.0,
        },
        index=idx,
    )
    panel["pc_24h"] = panel["close"] / panel["close"].shift(6) - 1.0
    return panel


_TOY_IDX = pd.date_range(TOY_START, periods=N_TOY, freq="4h")
TOY_BOUNDARIES = [_TOY_IDX[120], _TOY_IDX[180], _TOY_IDX[240]]


def _loader(asset: str) -> pd.DataFrame:
    assert asset == "BTC"
    return _toy_panel()


def _run(out_dir, draws: int = 20) -> dict:
    return run_w_sweep(
        panels=("BTC",),
        draws=draws,
        out_dir=str(out_dir),
        panel_loader=_loader,
        boundaries={"BTC": TOY_BOUNDARIES},
        taxonomies={"BTC": TOY_TAXONOMIES},
    )


@pytest.fixture(scope="module")
def sweep_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("w_sweep_a")
    return _run(out), out


# ----------------------------------------------------------- determinism


def test_full_path_deterministic_twice(sweep_run, tmp_path_factory):
    _, out_a = sweep_run
    out_b = tmp_path_factory.mktemp("w_sweep_b")
    _run(out_b)
    text_a = (out_a / "sweep_results_w.json").read_text()
    text_b = (out_b / "sweep_results_w.json").read_text()
    assert text_a == text_b          # byte-identical artifacts


def test_parallel_byte_identical_to_serial(sweep_run, tmp_path_factory):
    """workers=1 and workers=4 must produce byte-identical artifact JSON.

    Amendment 29(g): fork-pool parallelism is pure scheduling over
    pre-generated common draws; output is byte-deterministic.
    """
    _, out_serial = sweep_run        # workers=1 (default)
    out_par = tmp_path_factory.mktemp("w_sweep_par")
    run_w_sweep(
        panels=("BTC",),
        draws=20,
        out_dir=str(out_par),
        panel_loader=_loader,
        boundaries={"BTC": TOY_BOUNDARIES},
        taxonomies={"BTC": TOY_TAXONOMIES},
        workers=4,
    )
    text_serial = (out_serial / "sweep_results_w.json").read_text()
    text_par = (out_par / "sweep_results_w.json").read_text()
    assert text_serial == text_par   # byte-identical: scheduling only


def test_artifact_matches_returned_dict(sweep_run):
    results, out = sweep_run
    on_disk = json.loads((out / "sweep_results_w.json").read_text())
    assert on_disk == json.loads(json.dumps(results))


# ------------------------------------------------------ records + schema


def test_variant_count_and_rank_sort(sweep_run):
    results, _ = sweep_run
    recs = results["variants"]
    assert len(recs) == 42                       # 24 TD + 10 TF + 8 annex
    assert sum(r["annex"] for r in recs) == 8
    keys = [(-r["rank_key"], r["train_max_dd_mean"], r["id"]) for r in recs]
    assert keys == sorted(keys)
    json.dumps(results)                          # serializable end-to-end


def test_record_schema(sweep_run):
    results, _ = sweep_run
    required = {"id", "panel", "family", "taxonomy", "annex", "time_stop",
                "vol_band", "rank_key", "train_sharpes", "train_max_dd_mean",
                "per_fold_oos", "oos", "hooks", "verdict",
                "structural_feasibility", "lock", "era_split",
                "crash_day_trades", "ship_eligible"}
    for r in results["variants"]:
        assert required <= set(r)
        assert r["panel"] == "P-BTC"
        assert set(r["train_sharpes"]) == {"F01", "F02", "F03"}
        assert set(r["per_fold_oos"]) == {"F01", "F02", "F03"}
        assert set(r["oos"]) == {"sharpe", "net_return", "max_dd",
                                 "n_trades", "turnover"}
        assert set(r["hooks"]) >= {"null_p95", "null_p99",
                                   "unguarded_oos_sharpe", "top5_net",
                                   "topk_net", "topk_k", "ladder"}
        assert set(r["hooks"]["ladder"]) == {"5", "10", "20"}
        assert set(r["structural_feasibility"]) == {"projected_oos_trades",
                                                    "flagged"}
        assert r["verdict"]["passed"] == all(r["verdict"]["reasons"].values())


def test_gate_reasons_keys_complete(sweep_run):
    results, _ = sweep_run
    for r in results["variants"]:
        assert set(r["verdict"]["reasons"]) == CLAUSES_W


def test_null_clauses_use_unguarded_sharpe(sweep_run):
    # Frozen-sweep adaptation (a) replicated at the W-sweep level: BOTH
    # null clauses compare the variant's UNGUARDED pooled-OOS Sharpe
    # against the (unguarded) null quantiles.
    results, _ = sweep_run
    for r in results["variants"]:
        ug = r["hooks"]["unguarded_oos_sharpe"]
        assert r["verdict"]["reasons"]["null_pass"] == (
            ug > r["hooks"]["null_p95"])
        assert r["verdict"]["reasons"]["null_p99"] == (
            ug > r["hooks"]["null_p99"])


# ------------------------------------------- planted always-flat variants


def test_tf_always_flat_fails_beats_flat(sweep_run):
    # fg all-NaN -> every T-F bar fg-na -> w == 0 -> net == 0 -> the
    # beats_flat clause (net@10 > 0) fails for every T-F variant.
    results, _ = sweep_run
    tf = [r for r in results["variants"] if r["taxonomy"] == "TF"]
    assert len(tf) == 10
    for r in tf:
        assert r["oos"]["net_return"] == 0.0
        assert r["verdict"]["reasons"]["beats_flat"] is False
        assert r["verdict"]["passed"] is False
        assert r["lock"] is None                 # lock only for passers
        assert r["era_split"] is None
        assert r["ship_eligible"] is False


# ---------------------------------------------- globals: E, honest-N, seed


def test_embargo_repair_and_honest_n_recorded(sweep_run):
    results, _ = sweep_run
    taxs = results["globals"]["panels"]["P-BTC"]["taxonomies"]
    # T-D: 5-bar episodes -> floor 42. T-F: all-na train slice -> the
    # repaired compute_embargo (amendment 27) floors at 42 (pre-repair the
    # 120-bar first-fold train would have given E = 120 and an empty OOS).
    assert taxs["TD"]["embargo_bars"] == 42
    assert taxs["TF"]["embargo_bars"] == 42
    assert results["globals"]["embargo_bars"]["P-BTC"] == {"TD": 42,
                                                           "TF": 42}
    # honest-N counts NON-na pooled-OOS episodes: T-F is all fg-na -> 0;
    # T-D OOS slices hold 4 episodes per 18-bar fold -> 12.
    assert taxs["TF"]["honest_N"] == 0
    assert taxs["TD"]["honest_N"] == 12
    for tax in TOY_TAXONOMIES:
        for meta in taxs[tax]["per_fold"].values():
            assert meta["oos_bars"] == 18
    # §7 covered folds: T-D folds are all covered, T-F none.
    assert taxs["TD"]["covered_folds"] == ["F01", "F02", "F03"]
    assert taxs["TF"]["covered_folds"] == []


def test_seed_map_tables_recorded(sweep_run):
    results, _ = sweep_run
    sm = results["globals"]["seed_map"]
    assert sm["seed_base"] == 17
    assert sm["panel_index"] == PANEL_INDEX_W
    assert sm["taxonomy_index"] == TAXONOMY_INDEX_W
    assert results["globals"]["n_draws"] == 20


def test_benchmarks_recorded(sweep_run):
    results, _ = sweep_run
    taxs = results["globals"]["panels"]["P-BTC"]["taxonomies"]
    for tax in TOY_TAXONOMIES:
        bench = taxs[tax]["benchmarks"]
        assert set(bench) == {"hodl", "flat", "vol_target"}
        for name in bench:
            assert set(bench[name]) == {"5", "10", "20"}
            for rung in bench[name].values():
                assert set(rung) == {"sharpe", "net_return"}
        # flat is zero by construction
        assert bench["flat"]["10"]["net_return"] == 0.0


# ------------------------------------------------------------- R3 block


def test_r3_registered_denominators(sweep_run):
    results, _ = sweep_run
    r3 = results["globals"]["r3"]
    reg = r3["registered"]
    assert reg["n_gated"] == 175
    assert reg["n_annex"] == 8
    assert reg["n_forward_recorded_not_evaluated"] == 24
    assert len(reg["forward_ids"]) == 24
    assert reg["effective_hypotheses"] == 32
    assert reg["expected_clause6_rate"] == 0.01
    sw = r3["swept"]
    assert sw["n_variants"] == 42
    assert sw["n_annex"] == 8
    assert sw["gate_pass_count"] == sum(
        r["verdict"]["passed"] for r in results["variants"])
    assert sw["structurally_flagged_count"] == sum(
        r["structural_feasibility"]["flagged"] for r in results["variants"])


def test_r3_per_cell_calibration(sweep_run):
    results, _ = sweep_run
    cal = results["globals"]["r3"]["per_cell_calibration"]
    assert set(cal) == {"P-BTC/TD", "P-BTC/TF"}
    by_id = {r["id"]: r for r in results["variants"]}
    for cell, c in cal.items():
        assert c["draws"] == 20                      # min(200, draws)
        assert 0.0 <= c["full_gate_pass_rate"] <= 1.0
        rate = c["full_gate_pass_rate"]
        assert c["mc_se"] == pytest.approx(
            (rate * (1.0 - rate) / c["draws"]) ** 0.5)
        # the slot holds the cell's top train-ranked GATED variant
        assert by_id[c["variant_id"]]["annex"] is False
        assert by_id[c["variant_id"]]["taxonomy"] == cell.split("/")[1]
    # T-F: every draw is the frozen all-na series -> w == 0 -> never passes
    assert cal["P-BTC/TF"]["full_gate_pass_rate"] == 0.0


# ----------------------------------------------- lock layers + era split


def test_lock_layers_and_era_split_for_passing_variant(monkeypatch,
                                                       tmp_path):
    # No toy variant can clear clause 7's floors on 54 pooled-OOS bars, so
    # force the gate verdict to PASS (synthetic toy only — no OOS-contact
    # implication) and assert the lock layers + §8 era-split/crash-day
    # disclosures run for every passer.
    real = sweep_w._verdict_w

    def forced(*args, **kwargs):
        v = real(*args, **kwargs)
        return sweep_w.GateVerdictW(
            passed=True,
            reasons={k: True for k in v.reasons},
            stats=v.stats,
        )

    monkeypatch.setattr(sweep_w, "_verdict_w", forced)
    results = _run(tmp_path, draws=8)
    by_id = {r["id"]: r for r in results["variants"]}

    for r in results["variants"]:
        lock = r["lock"]
        assert lock is not None
        assert set(lock) == {"layer1_locked", "layer2", "layer3", "locked",
                             "locked_layers"}
        assert set(lock["layer2"]) == {"twin_net_return", "twin_sharpe",
                                       "null_p95", "twin_passes", "locked"}
        assert set(lock["layer3"]) == {"total", "leg_sum", "evaluated",
                                       "share", "locked"}
        # era split (§8): pre/post 2025-04-01 with clause-by-clause status
        era = r["era_split"]
        assert era["split_at"] == "2025-04-01"
        for side in ("pre", "post"):
            assert era[side]["oos_bars"] > 0
            assert set(era[side]["reasons"]) == CLAUSES_W
            assert {"net_return", "n_trades"} <= set(era[side])
        # crash-day coincidence: five published groups, none in toy range
        cdt = r["crash_day_trades"]
        assert len(cdt) == 6 and cdt["total"] == 0
        # annex variants are never ship-eligible, even as passers
        if r["annex"]:
            assert r["ship_eligible"] is False

    # layer 1 pure-map predicate: the annex A1 map satisfies it, the
    # registered symmetric D1 map does not (§6).
    a1 = by_id["P-BTC-DIR-TD-A1-fade_pos_x_only-1.0"]
    assert a1["lock"]["layer1_locked"] is True
    assert a1["lock"]["locked"] is True
    d1 = by_id["P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0"]
    assert d1["lock"]["layer1_locked"] is False


# -------------------------------------- structural feasibility (TRAIN-side)


def test_feasibility_readout_writes_artifact_and_flags(tmp_path):
    res = structural_feasibility_readout(
        panels=("BTC",),
        panel_loader=_loader,
        boundaries={"BTC": TOY_BOUNDARIES},
        taxonomies={"BTC": TOY_TAXONOMIES},
        out_dir=str(tmp_path),
    )
    on_disk = json.loads((tmp_path / "structural_feasibility.json")
                         .read_text())
    assert on_disk == json.loads(json.dumps(res))
    assert res["clause7_trade_floor"] == MIN_OOS_TRADES
    assert res["panels"]["P-BTC"]["TD"]["embargo_bars"] == 42
    assert res["panels"]["P-BTC"]["TF"]["embargo_bars"] == 42
    assert len(res["variants"]) == 42
    for v in res["variants"]:
        assert v["flagged"] == (v["projected_oos_trades"] < MIN_OOS_TRADES)
        if v["taxonomy"] == "TF":          # always flat -> zero trades
            assert v["projected_oos_trades"] == 0.0


def test_feasibility_flags_agree_with_sweep_records(sweep_run, tmp_path):
    results, _ = sweep_run
    res = structural_feasibility_readout(
        panels=("BTC",),
        panel_loader=_loader,
        boundaries={"BTC": TOY_BOUNDARIES},
        taxonomies={"BTC": TOY_TAXONOMIES},
        out_dir=str(tmp_path),
    )
    standalone = {v["id"]: v["projected_oos_trades"]
                  for v in res["variants"]}
    for r in results["variants"]:
        assert r["structural_feasibility"]["projected_oos_trades"] == \
            standalone[r["id"]]


def test_oos_guard_assertion(monkeypatch, tmp_path):
    idx = pd.date_range("2025-01-01", periods=5, freq="4h")
    # consumed index strictly before the boundary: fine
    _assert_train_side(idx, idx[-1] + pd.Timedelta(hours=4), "F01")
    _assert_train_side(idx[:0], idx[0], "F01")        # empty: fine
    # any consumed index at/after the boundary trips the guard
    with pytest.raises(AssertionError):
        _assert_train_side(idx, idx[-1], "F01")
    with pytest.raises(AssertionError):
        _assert_train_side(idx, idx[2], "F01")
    # and the guard is wired into the feasibility path (once per fold)
    calls = []
    real = sweep_w._assert_train_side

    def spy(consumed_idx, boundary, fold_name):
        calls.append(fold_name)
        return real(consumed_idx, boundary, fold_name)

    monkeypatch.setattr(sweep_w, "_assert_train_side", spy)
    structural_feasibility_readout(
        panels=("BTC",),
        panel_loader=_loader,
        boundaries={"BTC": TOY_BOUNDARIES},
        taxonomies={"BTC": TOY_TAXONOMIES},
        out_dir=str(tmp_path),
    )
    assert len(calls) >= 6        # >= one guard call per (taxonomy, fold)


# ------------------------------------------------------------ CLI tripwire


def test_cli_tripwire_blocks_without_confirm(monkeypatch):
    monkeypatch.delenv("W_SWEEP_CONFIRM", raising=False)
    with pytest.raises(SystemExit) as ei:
        sweep_w.main([])
    assert ei.value.code == 2


def test_cli_tripwire_blocks_wrong_value(monkeypatch):
    monkeypatch.setenv("W_SWEEP_CONFIRM", "yes")
    with pytest.raises(SystemExit) as ei:
        sweep_w.main(["--draws", "5"])
    assert ei.value.code == 2


def test_cli_confirmed_runs_sweep(monkeypatch, tmp_path):
    monkeypatch.setenv("W_SWEEP_CONFIRM", "registered")
    seen = {}

    def stub(**kwargs):
        seen.update(kwargs)
        return {"globals": {}, "variants": []}

    monkeypatch.setattr(sweep_w, "run_w_sweep", stub)
    sweep_w.main(["--draws", "5", "--out-dir", str(tmp_path)])
    assert seen["draws"] == 5
    assert seen["out_dir"] == str(tmp_path)


def test_cli_feasibility_skips_tripwire(monkeypatch, tmp_path):
    monkeypatch.delenv("W_SWEEP_CONFIRM", raising=False)
    seen = {}

    def stub(**kwargs):
        seen.update(kwargs)
        return {"variants": []}

    monkeypatch.setattr(sweep_w, "structural_feasibility_readout", stub)
    sweep_w.main(["--feasibility", "--out-dir", str(tmp_path)])
    assert seen["out_dir"] == str(tmp_path)
