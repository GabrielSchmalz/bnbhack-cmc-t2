"""Tests for lab/sweep.py + the pooled-null additions to lab/hooks.py
(plan Task 2.4).

Synthetic frames only — never data/ CSVs. The planted-effect panel: 200
4h bars from 2025-09-20 with calm/stressed blocks of 10 driven purely by
the |oi_chg_24h| clause (funding_rate_8h and fg are NaN so their clauses
evaluate FALSE per FREEZE-ADDENDUM D4.3), and a return pattern aligned
with the lag discipline: r[t] = +1.5% when labels[t-1] == "calm", -1.5%
when "stressed". The TA risk ladder (1, 0, 0) is long exactly on the
+1.5% bars; the misaligned ladder (1, 1, 0) is always long — the aligned
variant must out-rank it on the train-Sharpe rank key (PR-7).

Fold geometry on this panel (pins the embargo wiring): F1 train = the 66
bars before 2025-10-01; TA/TB reference episodes are 10 bars -> E = 42;
F1 OOS = bars[108:200] = 92 bars; F2-F4 OOS are empty (the index ends
2025-10-23). TC is constant ("neg-mild", funding NaN) -> one 200-bar
episode -> E = 200 -> no OOS anywhere (degenerate but valid).
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

from lab import rules  # noqa: E402
from lab.classifier import episodes  # noqa: E402
from lab.engine import run_backtest  # noqa: E402
from lab.hooks import episode_shuffles, shuffle_null_pooled  # noqa: E402
from lab.metrics import sharpe  # noqa: E402
from lab.sweep import render_summary, run_sweep  # noqa: E402

N_BARS = 200
BLOCK = 10
ALIGNED_ID = "RISK-TA-ladder-1_0_0"
MISALIGNED_ID = "RISK-TA-ladder-1_1_0"


def _planted_panel() -> tuple[pd.DataFrame, pd.Series]:
    """200-bar panel with a planted TA calm/stressed regime effect."""
    idx = pd.date_range("2025-09-20 00:00", periods=N_BARS, freq="4h")
    lab_arr = np.where((np.arange(N_BARS) // BLOCK) % 2 == 0,
                       "calm", "stressed")
    r = np.zeros(N_BARS)
    r[1:] = np.where(lab_arr[:-1] == "calm", 0.015, -0.015)
    # engine: r[t] = open[t+1]/open[t] - 1 (final bar: close/open - 1)
    opens = 100.0 * np.cumprod(np.concatenate(([1.0], 1.0 + r[:-1])))
    closes = np.empty(N_BARS)
    closes[:-1] = opens[1:]
    closes[-1] = opens[-1] * (1.0 + r[-1])
    panel = pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes),
            "low": np.minimum(opens, closes),
            "close": closes,
            "volume": 1.0,
            "funding_rate": 0.0,
            "oi": np.nan,
            "ls_ratio": np.nan,
            "dvol": np.nan,
            "fg": np.nan,
            "band": np.nan,
            # canonical Feature columns (lab/features.py)
            "funding_rate_8h": np.nan,
            "oi_chg_24h": np.where(lab_arr == "stressed", 0.10, 0.0),
            "rsi14_1d": 50.0,
            "close_vs_sma30_1d": 1.0,
        },
        index=idx,
    )
    return panel, pd.Series(lab_arr, index=idx)


@pytest.fixture(scope="module")
def sweep_results():
    panel, _ = _planted_panel()
    return run_sweep(panel, n_null=25)


# ------------------------------------------------------------ planted effect


def test_planted_alignment_outranks_misaligned(sweep_results):
    recs = {r["id"]: r for r in sweep_results["variants"]}
    assert recs[ALIGNED_ID]["rank_key"] > recs[MISALIGNED_ID]["rank_key"]
    assert recs[ALIGNED_ID]["rank_key"] > 0.0


# ------------------------------------------------------------------- schema


def test_globals_schema(sweep_results):
    g = sweep_results["globals"]
    assert g["n_variants"] == 36
    assert g["n_null"] == 25
    for tax in ("TA", "TB", "TC"):
        tg = g["taxonomies"][tax]
        assert isinstance(tg["embargo_bars"], int)
        assert set(tg["per_fold"]) == {"F1", "F2", "F3", "F4"}
        for meta in tg["per_fold"].values():
            assert set(meta) >= {"oos_bars", "oos_episodes"}
        assert tg["honest_N"] == sum(
            m["oos_episodes"] for m in tg["per_fold"].values())
        for c in ("5", "10", "20"):
            assert set(tg["hodl_oos"][c]) == {"sharpe", "net_return"}
    r3 = g["r3"]
    assert r3["n_variants"] == 36
    assert set(r3) >= {"n_variants", "gate_pass_count",
                       "expected_null_pass_rate", "top_variant_id",
                       "top_variant_null_gate_pass_rate",
                       "n_null_gate_draws"}
    assert r3["n_null_gate_draws"] == 25  # min(200, n_null)


def test_variant_record_schema_and_sort(sweep_results):
    variants = sweep_results["variants"]
    assert len(variants) == 36
    rank_keys = [v["rank_key"] for v in variants]
    assert rank_keys == sorted(rank_keys, reverse=True)
    required = {"id", "family", "taxonomy", "rank_key", "train_sharpes",
                "train_max_dd_mean", "oos", "hooks", "verdict"}
    for v in variants:
        assert required <= set(v)
        assert set(v["train_sharpes"]) == {"F1", "F2", "F3", "F4"}
        assert set(v["oos"]) == {"sharpe", "net_return", "max_dd",
                                 "n_trades", "turnover"}
        assert set(v["hooks"]) == {"null_p95", "unguarded_oos_sharpe",
                                   "top5_net", "ladder"}
        assert set(v["hooks"]["ladder"]) == {"5", "10", "20"}
        for rung in v["hooks"]["ladder"].values():
            assert set(rung) == {"net_return_oos", "sharpe_oos"}
        assert set(v["verdict"]["reasons"]) == {
            "beats_flat", "beats_hodl", "null_pass", "top5_pass",
            "ladder_pass"}
        assert v["verdict"]["passed"] == all(v["verdict"]["reasons"].values())
    json.dumps(sweep_results)  # serializable end-to-end


def test_null_clause_uses_unguarded_sharpe(sweep_results):
    # pre-registered adaptation (a): the null clause compares the variant's
    # UNGUARDED pooled-OOS Sharpe against null_p95 (null draws are unguarded)
    for v in sweep_results["variants"]:
        expected = v["hooks"]["unguarded_oos_sharpe"] > v["hooks"]["null_p95"]
        assert v["verdict"]["reasons"]["null_pass"] == expected


# ------------------------------------------------------- fold/embargo wiring


def test_embargo_and_oos_wiring(sweep_results):
    _, labels = _planted_panel()
    g = sweep_results["globals"]["taxonomies"]
    # TA/TB reference episodes are 10 bars -> E = max(42, 10) = 42
    assert g["TA"]["embargo_bars"] == 42
    assert g["TB"]["embargo_bars"] == 42
    # TC labels are constant on this panel -> one 200-bar episode -> E = 200
    assert g["TC"]["embargo_bars"] == 200
    assert g["TC"]["honest_N"] == 0
    # F1: 66 train bars before 2025-10-01, embargo 42 -> OOS = bars[108:200]
    assert g["TA"]["per_fold"]["F1"]["oos_bars"] == 92
    for f in ("F2", "F3", "F4"):
        assert g["TA"]["per_fold"][f]["oos_bars"] == 0
    expected_eps = len(episodes(labels.iloc[108:]))
    assert g["TA"]["per_fold"]["F1"]["oos_episodes"] == expected_eps
    assert g["TA"]["honest_N"] == expected_eps


# -------------------------------------------------- pooled-null hook (hooks.py)


def test_episode_shuffles_seed_reproducible_and_prefix():
    idx = pd.date_range("2025-01-01", periods=24, freq="4h")
    labels = pd.Series(["A"] * 6 + ["B"] * 6 + ["C"] * 6 + ["D"] * 6,
                       index=idx)
    a = episode_shuffles(labels, n=7, seed=18)
    b = episode_shuffles(labels, n=7, seed=18)
    assert len(a) == 7
    for s, t in zip(a, b, strict=True):
        pd.testing.assert_series_equal(s, t)
        assert list(s.index) == list(idx)
        # label multiset preserved
        assert sorted(s.tolist()) == sorted(labels.tolist())
        # episode-length multiset preserved (labels all distinct: no merges)
        assert sorted(episodes(s)["n_bars"]) == sorted(
            episodes(labels)["n_bars"])
    # prefix property: first m draws of n are the m draws (R3 regeneration)
    short = episode_shuffles(labels, n=3, seed=18)
    for s, t in zip(short, a[:3], strict=True):
        pd.testing.assert_series_equal(s, t)
    # a different seed produces a different draw sequence
    c = episode_shuffles(labels, n=7, seed=19)
    assert any(not s.equals(t) for s, t in zip(a, c, strict=True))


def test_shuffle_null_pooled_reproducible_and_hand_pooled():
    idx = pd.date_range("2025-01-01", periods=16, freq="4h")
    opens = np.linspace(100.0, 130.0, 16)
    closes = opens * 1.002
    bars = pd.DataFrame({"open": opens, "close": closes}, index=idx)
    funding = pd.Series(0.0, index=idx)
    labels = pd.Series(["A"] * 4 + ["B"] * 4 + ["C"] * 4 + ["D"] * 4,
                       index=idx)
    amap = {"A": 1.0, "B": 0.0, "C": -1.0, "D": 0.5}

    def strategy_fn(labs: pd.Series) -> pd.Series:
        return rules.apply(labs, amap)

    def make_folds():
        return [(episode_shuffles(labels, 6, seed=18), idx[8:12]),
                (episode_shuffles(labels, 6, seed=19), idx[12:16])]

    out1 = shuffle_null_pooled(strategy_fn, make_folds(), bars, funding, 10.0)
    out2 = shuffle_null_pooled(strategy_fn, make_folds(), bars, funding, 10.0)
    assert set(out1) == {"p95", "null_sharpes"}
    assert len(out1["null_sharpes"]) == 6
    np.testing.assert_array_equal(out1["null_sharpes"], out2["null_sharpes"])
    assert out1["p95"] == out2["p95"]
    assert out1["p95"] == float(np.quantile(out1["null_sharpes"], 0.95))

    # hand-pool draw 0: per fold, UNGUARDED backtest of the draw-0 shuffle,
    # restrict to the fold OOS, concat across folds, Sharpe
    segments = []
    for shuffles, oos in make_folds():
        res = run_backtest(bars, strategy_fn(shuffles[0]), funding, 10.0)
        segments.append(
            res.bar_returns.loc[res.bar_returns.index.intersection(oos)])
    expected0 = sharpe(pd.concat(segments).sort_index())
    assert out1["null_sharpes"][0] == expected0


# ------------------------------------------------------------------ summary


def test_summary_contains_top_table_survivors_r3(sweep_results):
    text = render_summary(sweep_results)
    assert "R3" in text
    assert "Survivor" in text
    assert sweep_results["variants"][0]["id"] in text
