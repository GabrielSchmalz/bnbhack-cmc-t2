"""Layer-1 bit-equality battery for lab/null_fast.py (the fast null kernel).

Design of record: docs/plans/2026-06-12-null-fast-design.md; grill verdicts:
docs/plans/2026-06-12-null-fast-grill.md. The kernel is an opt-in
(`W_NULL_FAST=1`) numpy re-derivation of the pooled-null path
(`sweep_w._null_sharpes_w` -> `shuffle_null_pooled_w`); its acceptance bar
is BIT-IDENTITY — every comparison here is `.tobytes()` equality on
float64 output, zero tolerance, never approx.

Three layers of pinning:
  - kernel vs frozen `_null_sharpes_w` on synthetic toys (plain / ts / vb /
    combined variants; na-frozen episodes; genuine-NaN and unknown labels;
    length-1 episodes; empty-OOS and all-na folds; zero-std segments;
    randomized property sweeps across seeds);
  - the time-stop int-code port vs frozen `rules_w.apply_time_stop`
    branch-for-branch (boundary convention, k=1 degenerate, all-na,
    randomized);
  - the integration seam: a full toy `run_w_sweep` artifact must be
    byte-identical with the flag on vs off (and on+fork-pool), and with
    the flag UNSET the kernel module must never even be imported.

Synthetic frames only — never data/ CSVs (the env-gated real-panel spot
check in scripts/prove_null_fast.sh is Layer 2's job). Fixtures mirror
tests/test_sweep_w.py's toy conventions.
"""

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

import lab.null_fast as null_fast  # noqa: E402
from lab.hooks_w import episode_shuffles_w  # noqa: E402
from lab.rules import apply as rules_apply  # noqa: E402
from lab.rules_w import apply_time_stop  # noqa: E402
from lab.sweep_w import GATE_COST_BPS, _null_sharpes_w, run_w_sweep  # noqa: E402
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


def _labels(idx, seed, nan_share=0.0, pool=LABEL_POOL):
    """Random episode-y labels: short runs from the pool, optional genuine
    NaN bars (length-1 episodes by construction of `episodes`)."""
    rng = np.random.default_rng(seed)
    vals = []
    while len(vals) < len(idx):
        vals.extend([rng.choice(pool)] * int(rng.integers(1, 6)))
    arr = np.array(vals[:len(idx)], dtype=object)
    if nan_share:
        arr[rng.random(len(idx)) < nan_share] = np.nan
    return pd.Series(arr, index=idx, dtype=object)


def _ctx(idx, oos_spans, labels_by_fold, na_set, draws, hots=None,
         hot_default=False):
    """(fold_ctx, shuffles) exactly as run_w_sweep wires them."""
    fold_ctx, shuffles = [], {}
    for i, (a, b) in enumerate(oos_spans):
        name = f"F{i + 1:02d}"
        fold = Fold(train_idx=idx[:a], oos_idx=idx[a:b], name=name)
        hot = (hots[i] if hots is not None
               else pd.Series(hot_default, index=idx))
        fold_ctx.append({"fold": fold, "labels": labels_by_fold[i],
                         "hot": hot, "ordinal": i + 1,
                         "boundary": idx[a] if a < len(idx) else idx[-1]})
        shuffles[name] = episode_shuffles_w(
            labels_by_fold[i], na_set, draws,
            panel_index=0, taxonomy_index=0, fold_ordinal=i + 1)
    return fold_ctx, shuffles


def _both(variant, fold_ctx, shuffles, bars, funding, draws, monkeypatch):
    """Run frozen and fast paths; assert bit-identity; return the vector."""
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    frozen = _null_sharpes_w(variant, fold_ctx, shuffles, bars, funding,
                             draws)
    fast = null_fast.pooled_null_sharpes(variant, fold_ctx, shuffles, bars,
                                         funding, GATE_COST_BPS, draws)
    assert isinstance(fast, np.ndarray)
    assert frozen.dtype == np.float64 and fast.dtype == np.float64
    assert frozen.shape == fast.shape
    assert frozen.tobytes() == fast.tobytes()
    return frozen


OOS_3 = ((120, 180), (240, 320), (380, 420))


# -------------------------------------------------- kernel vs frozen path


def test_plain_direction_variant_bit_identical(monkeypatch):
    idx, bars, funding = _panel()
    labs = [_labels(idx, s) for s in (11, 12, 13)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, set(), draws=25)
    out = _both(_variant(), fold_ctx, shuffles, bars, funding, 25,
                monkeypatch)
    assert np.ptp(out) > 0.0          # non-degenerate toy (real dispersion)


def test_unknown_and_genuine_nan_labels_act_flat(monkeypatch):
    # Labels outside the action map + genuine np.nan bars (length-1
    # episodes): both act 0.0 through the frozen map/fillna path; the
    # kernel's reserved-NaN code must reproduce it bit-for-bit.
    idx, bars, funding = _panel(seed=4)
    pool = np.append(LABEL_POOL, np.array(["ghost-label"], dtype=object))
    labs = [_labels(idx, s, nan_share=0.07, pool=pool) for s in (21, 22, 23)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, set(), draws=20)
    _both(_variant(), fold_ctx, shuffles, bars, funding, 20, monkeypatch)


def test_na_labels_frozen_in_place(monkeypatch):
    # §7 na-freeze: "na" episodes keep their bar positions in every draw.
    idx, bars, funding = _panel(seed=5)
    labs = [_labels(idx, s) for s in (31, 32, 33)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=20)
    _both(_variant(), fold_ctx, shuffles, bars, funding, 20, monkeypatch)


@pytest.mark.parametrize("k", [1, 2, 6])
def test_time_stop_variant_bit_identical(monkeypatch, k):
    idx, bars, funding = _panel(seed=6)
    labs = [_labels(idx, s, nan_share=0.03) for s in (41, 42, 43)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=20)
    _both(_variant(time_stop=k), fold_ctx, shuffles, bars, funding, 20,
          monkeypatch)


def test_vol_band_variant_with_distinct_per_fold_hot_masks(monkeypatch):
    # Distinct hot masks per fold pin the itertools.cycle alignment of the
    # frozen path; one mask carries NaN bars (D4.3: NaN -> cold).
    idx, bars, funding = _panel(seed=7)
    rng = np.random.default_rng(99)
    hots = []
    for i in range(3):
        h = pd.Series(rng.random(len(idx)) < 0.25 * (i + 1), index=idx)
        if i == 1:
            h = h.astype(object)
            h.iloc[:50] = np.nan
        hots.append(h)
    labs = [_labels(idx, s) for s in (51, 52, 53)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=20, hots=hots)
    _both(_variant(vol_band=True), fold_ctx, shuffles, bars, funding, 20,
          monkeypatch)


def test_time_stop_plus_vol_band_combined(monkeypatch):
    # The registered §5 grids never combine them, but _strategy_w composes
    # them sequentially when a Variant carries both — the kernel must too.
    idx, bars, funding = _panel(seed=8)
    rng = np.random.default_rng(199)
    hots = [pd.Series(rng.random(len(idx)) < 0.3, index=idx)
            for _ in range(3)]
    labs = [_labels(idx, s) for s in (61, 62, 63)]
    fold_ctx, shuffles = _ctx(idx, OOS_3, labs, {"na"}, draws=15, hots=hots)
    _both(_variant(time_stop=6, vol_band=True), fold_ctx, shuffles, bars,
          funding, 15, monkeypatch)


def test_empty_oos_fold_is_inactive_and_all_empty_returns_zeros(monkeypatch):
    idx, bars, funding = _panel(seed=9)
    labs = [_labels(idx, s) for s in (71, 72)]
    # F01 has an EMPTY OOS slice -> inactive in both paths.
    fold_ctx, shuffles = _ctx(idx, ((150, 150), (250, 330)), labs, set(),
                              draws=15)
    _both(_variant(), fold_ctx, shuffles, bars, funding, 15, monkeypatch)
    # ALL folds empty -> np.zeros(draws), frozen behavior.
    fold_ctx2, shuffles2 = _ctx(idx, ((150, 150), (250, 250)), labs, set(),
                                draws=15)
    out = _both(_variant(), fold_ctx2, shuffles2, bars, funding, 15,
                monkeypatch)
    assert out.tobytes() == np.zeros(15).tobytes()


def test_all_na_fold_every_draw_identical(monkeypatch):
    # One fold entirely na-labeled: every draw equals the original series
    # (hooks_w degenerate case) — pooled with a live fold, bit-identical.
    idx, bars, funding = _panel(seed=10)
    all_na = pd.Series(np.array(["na"] * len(idx), dtype=object), index=idx)
    labs = [all_na, _labels(idx, 82)]
    fold_ctx, shuffles = _ctx(idx, ((120, 200), (280, 360)), labs, {"na"},
                              draws=15)
    _both(_variant(), fold_ctx, shuffles, bars, funding, 15, monkeypatch)


def test_zero_std_pooled_segment_sharpe_zero(monkeypatch):
    # Flat prices + zero funding + all-zero actions -> every pooled draw
    # has zero std -> the frozen sharpe's 0.0 guard fires in both paths.
    idx, _, _ = _panel(seed=11)
    bars = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0,
                         "close": 100.0, "volume": 1.0}, index=idx)
    funding = pd.Series(0.0, index=idx)
    labs = [_labels(idx, 91), _labels(idx, 92)]
    amap = {lab: 0.0 for lab in LABEL_POOL}
    fold_ctx, shuffles = _ctx(idx, ((120, 200), (280, 360)), labs, set(),
                              draws=10)
    out = _both(_variant(amap=amap), fold_ctx, shuffles, bars, funding, 10,
                monkeypatch)
    assert out.tobytes() == np.zeros(10).tobytes()


def test_mismatched_draw_lists_raise_the_frozen_valueerror(monkeypatch):
    idx, bars, funding = _panel(seed=12)
    labs = [_labels(idx, 101), _labels(idx, 102)]
    fold_ctx, shuffles = _ctx(idx, ((120, 200), (280, 360)), labs, set(),
                              draws=10)
    shuffles["F02"] = episode_shuffles_w(labs[1], set(), 7, 0, 0, 2)
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    with pytest.raises(ValueError, match="fold shuffle lists differ"):
        _null_sharpes_w(_variant(), fold_ctx, shuffles, bars, funding, 10)
    with pytest.raises(ValueError, match="fold shuffle lists differ"):
        null_fast.pooled_null_sharpes(_variant(), fold_ctx, shuffles, bars,
                                      funding, GATE_COST_BPS, 10)


def test_kernel_refuses_index_mismatch():
    # A3 (grill): the kernel CHECKS the design's index invariant instead of
    # trusting it — shuffles built on a different index must raise, never
    # silently misalign.
    idx, bars, funding = _panel(seed=13)
    other_idx = idx + pd.Timedelta(hours=2)
    labels = _labels(other_idx, 111)
    fold = Fold(train_idx=other_idx[:120], oos_idx=other_idx[120:200],
                name="F01")
    fold_ctx = [{"fold": fold, "labels": labels,
                 "hot": pd.Series(False, index=other_idx), "ordinal": 1,
                 "boundary": other_idx[120]}]
    shuffles = {"F01": episode_shuffles_w(labels, set(), 5, 0, 0, 1)}
    with pytest.raises(ValueError, match="index"):
        null_fast.pooled_null_sharpes(_variant(), fold_ctx, shuffles, bars,
                                      funding, GATE_COST_BPS, 5)


@pytest.mark.parametrize("seed", [201, 202, 203, 204, 205])
def test_randomized_property_sweep(monkeypatch, seed):
    # Property-style: random panel, random fold geometry, random Variant
    # dressing (ts/vb), random na set, genuine NaN bars — bit-identical.
    rng = np.random.default_rng(seed)
    idx, bars, funding = _panel(n=360, seed=seed)
    spans, lo = [], 80
    for _ in range(int(rng.integers(2, 5))):
        a = lo + int(rng.integers(0, 30))
        b = min(a + int(rng.integers(0, 70)), 360)
        spans.append((a, b))
        lo = b + 10
    labs = [_labels(idx, int(rng.integers(0, 2 ** 31)),
                    nan_share=float(rng.choice([0.0, 0.05])))
            for _ in spans]
    na_set = set() if rng.random() < 0.5 else {"na"}
    ts = [None, 1, 6][int(rng.integers(0, 3))]
    vb = bool(rng.integers(0, 2))
    hots = [pd.Series(rng.random(len(idx)) < 0.3, index=idx) for _ in spans]
    fold_ctx, shuffles = _ctx(idx, spans, labs, na_set, draws=12, hots=hots)
    _both(_variant(time_stop=ts, vol_band=vb), fold_ctx, shuffles, bars,
          funding, 12, monkeypatch)


# ------------------------------------ time-stop int-code port, branch level


def _lagged_codes(lagged_labels: pd.Series, amap: dict):
    """Equality-faithful factorization of a lagged-label series: every NA
    value -> the reserved NAN_CODE; act flags via the frozen `_act` rule."""
    acts = [0.0]                       # NAN_CODE acts 0.0
    lookup = {}
    codes = np.empty(len(lagged_labels), dtype=np.intp)
    for i, v in enumerate(lagged_labels.to_numpy()):
        if pd.isna(v):
            codes[i] = null_fast.NAN_CODE
            continue
        c = lookup.get(v)
        if c is None:
            c = len(acts)
            lookup[v] = c
            acts.append(float(amap.get(v, 0.0)))
        codes[i] = c
    return codes, np.asarray(acts) != 0.0


def _ts_both(raw_labels, amap, k, index=None):
    labels = pd.Series(raw_labels, index=index, dtype=object)
    w = rules_apply(labels, amap)
    lagged = labels.shift(1)
    frozen = apply_time_stop(w, lagged, amap, k)
    codes, act_nonzero = _lagged_codes(lagged, amap)
    fast = null_fast._time_stop_codes(
        w.astype(float).to_numpy(), codes, act_nonzero, k)
    assert frozen.to_numpy().tobytes() == fast.tobytes()
    return frozen


TS_MAP = {"A": 1.0, "B": -1.0, "H": 0.5, "Z": 0.0}


@pytest.mark.parametrize("seq,k", [
    # boundary convention: transition at the first forced-flat bar
    # re-enters immediately (rules_w test-pinned case)
    (["A", "A", "A", "B", "B"], 2),
    # re-entry collides with the stop bar exactly
    (["A"] * 6 + ["B"] * 6, 3),
    # label change mid-run without a flat bar continues the run
    (["A", "A", "B", "B", "A", "A"], 4),
    # k=1 degenerate: every isolated entry stops at its first bar
    (["A", "Z", "A", "A", "B"], 1),
    # zero-action transition does not re-enter; later nonzero does
    (["A", "A", "A", "Z", "Z", "B", "B"], 2),
    # all-na: nothing ever enters
    ([np.nan] * 6, 2),
    # NaN -> NaN is no transition; NaN -> A is
    (["A", "A", "A", np.nan, np.nan, "A", "B"], 2),
    # unknown labels act 0.0
    (["A", "A", "A", "ghost", "A", "A"], 2),
])
def test_time_stop_port_pinned_branches(seq, k):
    _ts_both(seq, TS_MAP, k)


def test_time_stop_port_rejects_bad_k_like_frozen():
    with pytest.raises(ValueError, match="positive integer"):
        null_fast._time_stop_codes(np.zeros(3), np.zeros(3, dtype=np.intp),
                                   np.array([False]), 0)
    with pytest.raises(ValueError, match="positive integer"):
        null_fast._time_stop_codes(np.zeros(3), np.zeros(3, dtype=np.intp),
                                   np.array([False]), 2.5)


@pytest.mark.parametrize("seed", range(301, 309))
def test_time_stop_port_randomized(seed):
    rng = np.random.default_rng(seed)
    pool = np.array(["A", "B", "H", "Z", "ghost"], dtype=object)
    vals = []
    while len(vals) < 200:
        vals.extend([rng.choice(pool)] * int(rng.integers(1, 7)))
    arr = np.array(vals[:200], dtype=object)
    arr[rng.random(200) < 0.06] = np.nan
    k = int(rng.choice([1, 2, 3, 6]))
    _ts_both(list(arr), TS_MAP, k)


# ----------------------------------------------------- integration seam


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


def _toy_sweep(out_dir, workers=1):
    idx = pd.date_range("2025-03-01 00:00", periods=300, freq="4h")
    return run_w_sweep(
        panels=("BTC",), draws=8, out_dir=str(out_dir),
        panel_loader=lambda asset: _toy_w_panel(),
        boundaries={"BTC": [idx[120], idx[180], idx[240]]},
        taxonomies={"BTC": TOY_TAXONOMIES}, workers=workers)


def test_full_sweep_artifact_byte_identical_flag_on_vs_off(monkeypatch,
                                                           tmp_path, capfd):
    monkeypatch.delenv("W_NULL_FAST", raising=False)
    _toy_sweep(tmp_path / "off")
    assert "null path: fast" not in capfd.readouterr().out
    monkeypatch.setenv("W_NULL_FAST", "1")
    monkeypatch.setattr(null_fast, "_announced", False)
    _toy_sweep(tmp_path / "on")
    # provenance disclosed on stdout — and proof the kernel actually ran
    assert "null path: fast" in capfd.readouterr().out
    monkeypatch.setattr(null_fast, "_announced", False)
    _toy_sweep(tmp_path / "on_par", workers=4)   # fork-pool seam too
    assert "null path: fast" in capfd.readouterr().out
    text_off = (tmp_path / "off" / "sweep_results_w.json").read_text()
    text_on = (tmp_path / "on" / "sweep_results_w.json").read_text()
    text_par = (tmp_path / "on_par" / "sweep_results_w.json").read_text()
    assert text_off == text_on               # byte-identical artifact
    assert text_off == text_par              # and under the fork pool


def test_flag_unset_never_imports_kernel():
    # Layer-3 standing guard: with the flag unset the frozen path must not
    # even import lab.null_fast (a kernel bug cannot perturb it).
    code = (
        "import sys; sys.path.insert(0, '.');\n"
        "import lab.sweep_w\n"
        "assert 'lab.null_fast' not in sys.modules, 'kernel imported'\n"
        "print('clean')\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "W_NULL_FAST"}
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True,
        text=True, cwd=str(Path(__file__).resolve().parent.parent))
    assert out.returncode == 0, out.stderr
    assert "clean" in out.stdout


@pytest.mark.skipif(os.environ.get("W_NULL_FAST_REALPANEL") != "1",
                    reason="real-panel spot check: slow, reads data/ CSVs; "
                           "set W_NULL_FAST_REALPANEL=1 (proof battery)")
def test_real_panel_spot_check_all_variants_first_draws(monkeypatch):
    """Design §5 Layer-1 real-panel spot check: every registered Variant
    on P-BTC / P-ETH / P-SOL, first 5 common draws (the episode_shuffles_w
    prefix), frozen vs fast bit-identical. Read-only on data/ CSVs; the
    registered OOS-contact event already happened (committed sweep), this
    replays the same mechanics and writes nothing."""
    import lab.sweep_w as sweep_w
    from lab.hooks_w import PANEL_INDEX_W, TAXONOMY_INDEX_W
    from lab.panels_w import ASSETS_W, W_BOUNDARIES, load_w_panel
    from lab.sweep import OHLCV
    from lab.sweep_w import _build_fold_ctx, _na_set, _tax_key, compute_embargo
    from lab.variants_w import PANEL_TAXONOMIES_W, enumerate_all_w

    monkeypatch.delenv("W_NULL_FAST", raising=False)
    draws = 5
    all_w = enumerate_all_w()
    checked = 0
    for asset in ASSETS_W:
        panel_id = f"P-{asset}"
        panel = load_w_panel(asset)
        bars, funding = panel[OHLCV], panel["funding_rate"]
        bnds = [pd.Timestamp(b) for b in W_BOUNDARIES[asset]]
        for tax in PANEL_TAXONOMIES_W[panel_id]:
            embargo = compute_embargo(panel, tax, bnds)
            fold_ctx = _build_fold_ctx(panel, tax, bnds, embargo)
            shuffles = {
                fc["fold"].name: episode_shuffles_w(
                    fc["labels"], _na_set(tax), draws,
                    PANEL_INDEX_W[panel_id],
                    TAXONOMY_INDEX_W[_tax_key(tax)], fc["ordinal"])
                for fc in fold_ctx}
            for v in (v for v in all_w
                      if v.panel == panel_id and v.taxonomy == tax):
                frozen = sweep_w._null_sharpes_w(
                    v, fold_ctx, shuffles, bars, funding, draws)
                fast = null_fast.pooled_null_sharpes(
                    v, fold_ctx, shuffles, bars, funding, GATE_COST_BPS,
                    draws)
                assert frozen.tobytes() == fast.tobytes(), v.id
                checked += 1
    assert checked == 183                       # every registered Variant


def test_provenance_line_printed_once_per_process(monkeypatch, capsys):
    idx, bars, funding = _panel(n=200, seed=14)
    labs = [_labels(idx, 121)]
    fold_ctx, shuffles = _ctx(idx, ((100, 160),), labs, set(), draws=3)
    monkeypatch.setattr(null_fast, "_announced", False)
    for _ in range(2):
        null_fast.pooled_null_sharpes(_variant(), fold_ctx, shuffles, bars,
                                      funding, GATE_COST_BPS, 3)
    out = capsys.readouterr().out
    assert out.count("null path: fast") == 1
    assert "2026-06-12-null-fast-design.md" in out
