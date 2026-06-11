"""W-sweep tests — lab/hooks_w.py (widening registration §7 null mechanics).

Hand-constructed label series with hand-computed expectations; the
committed data/ CSVs are NEVER read here (no OOS contact).

Pinned behavior (docs/plans/2026-06-10-widening-preregistration.md §7
"Null mechanics (pinned)"; amendment log items 2 (M2) and 9 (M10, W7)):
  - episode_shuffles_w: episodes via lab.classifier.episodes; episodes
    whose label is in na_labels are FROZEN IN PLACE — their bar positions
    are identical in every draw; the remaining episodes' ORDER is permuted
    and they fill the non-na bar positions in sequence, lengths preserved
  - RNG map: a fresh numpy.random.default_rng([17, panel_index,
    taxonomy_index, fold_ordinal]) per (panel, taxonomy, fold); draws come
    sequentially from that one rng, so episode_shuffles_w(.., m, ..) is a
    PREFIX of episode_shuffles_w(.., n, ..) for m <= n
  - registered index tables: panel P-BTC=0 / P-ETH=1 / P-SOL=2; taxonomy
    T-D=0 / T-E=1 / T-F=2 / T-G=3 / T-H=4; fold_ordinal panel-local 1-based
  - pooled null: lab.hooks.shuffle_null_pooled is reused UNCHANGED (it
    takes pre-generated shuffles); hooks_w re-exports it byte-identically
    as shuffle_null_pooled_w
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# repo root on sys.path: the project is not installed as a package (same
# convention as the other test modules).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.classifier import episodes  # noqa: E402
import lab.hooks  # noqa: E402
from lab.hooks_w import (  # noqa: E402
    NULL_SEED_W,
    PANEL_INDEX_W,
    TAXONOMY_INDEX_W,
    episode_shuffles_w,
    shuffle_null_pooled_w,
)

NA = "sma-na"


# ---------------------------------------------------------------- helpers


def make_bars(opens, closes, start="2025-01-01 00:00"):
    """Tiny 4h-bar frame indexed by open_time (same shape as engine tests)."""
    idx = pd.date_range(start, periods=len(opens), freq="4h")
    opens = np.asarray(opens, dtype=float)
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes),
            "low": np.minimum(opens, closes),
            "close": closes,
            "volume": 1.0,
        },
        index=idx,
    )


def zero_funding(index):
    return pd.Series(0.0, index=index)


def labels_from_blocks(blocks, start="2025-01-01 00:00"):
    vals = [lab for lab, k in blocks for _ in range(k)]
    idx = pd.date_range(start, periods=len(vals), freq="4h")
    return pd.Series(vals, index=idx)


def na_holes_labels():
    """Leading na mega-block + interior na holes; non-na labels distinct so
    the run decomposition of every draw's non-na substream is unambiguous."""
    return labels_from_blocks(
        [(NA, 5), ("A", 3), (NA, 2), ("B", 4), (NA, 1), ("C", 2), ("D", 3)])


def runs(seq):
    """[(value, run_length), ...] decomposition of a flat sequence."""
    out: list[list] = []
    for v in seq:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return [(v, c) for v, c in out]


def reference_draws(labels, na_labels, n, panel_index, taxonomy_index,
                    fold_ordinal):
    """Independent reconstruction of the registered mechanics (§7): one
    rng.permutation over the non-na episode count per draw, permuted
    episodes repeated to length and written into the non-na bar positions
    in sequence; na bar positions carry their original labels."""
    eps = episodes(labels)
    keep = ~eps["label"].isin(list(na_labels)).to_numpy()
    ep_labels = eps["label"].to_numpy(dtype=object)[keep]
    ep_lengths = eps["n_bars"].to_numpy()[keep]
    na_mask = labels.isin(list(na_labels)).to_numpy()
    base = labels.to_numpy(dtype=object)
    rng = np.random.default_rng(
        [17, panel_index, taxonomy_index, fold_ordinal])
    out = []
    for _ in range(n):
        order = rng.permutation(len(ep_labels))
        vals = base.copy()
        if len(ep_labels):
            vals[~na_mask] = np.concatenate(
                [np.repeat(ep_labels[j], ep_lengths[j]) for j in order])
        out.append(pd.Series(vals, index=labels.index))
    return out


def assert_series_list_equal(got, expected):
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        assert g.index.equals(e.index)
        assert g.tolist() == e.tolist()


# ----------------------------------------------- na-freeze draw mechanics


def test_na_positions_invariant_across_draws():
    labels = na_holes_labels()
    na_mask = (labels == NA).to_numpy()
    draws = episode_shuffles_w(labels, {NA}, 10, 0, 3, 1)

    assert len(draws) == 10
    for d in draws:
        assert isinstance(d, pd.Series)
        assert d.index.equals(labels.index)
        vals = d.to_numpy(dtype=object)
        # na bar positions invariant: exactly the original na holes
        assert (vals[na_mask] == NA).all()
        assert (vals[~na_mask] != NA).all()


def test_non_na_episode_blocks_preserved_per_draw():
    labels = na_holes_labels()
    na_mask = (labels == NA).to_numpy()
    draws = episode_shuffles_w(labels, {NA}, 10, 0, 3, 1)

    for d in draws:
        substream = d.to_numpy(dtype=object)[~na_mask]
        # permuted order, lengths preserved: the non-na substream decomposes
        # into exactly the original (label, length) episode blocks
        assert sorted(runs(substream)) == sorted(
            [("A", 3), ("B", 4), ("C", 2), ("D", 3)])

    # the permutation actually acts: not every draw is the identity
    assert any(not d.equals(labels) for d in draws)


def test_non_na_value_multiset_preserved_with_repeated_labels():
    # two "A" episodes split by a na hole: bar-value multiset still exact
    labels = labels_from_blocks(
        [("A", 2), (NA, 3), ("A", 4), ("B", 1), (NA, 1)])
    na_mask = (labels == NA).to_numpy()
    original = sorted(labels.to_numpy(dtype=object)[~na_mask].tolist())

    for d in episode_shuffles_w(labels, {NA}, 8, 2, 0, 4):
        vals = d.to_numpy(dtype=object)
        assert (vals[na_mask] == NA).all()
        assert sorted(vals[~na_mask].tolist()) == original


def test_two_na_labels_both_frozen():
    labels = labels_from_blocks(
        [("oi-na", 2), ("A", 3), (NA, 2), ("B", 2), ("oi-na", 1)])
    na_labels = {NA, "oi-na"}
    frozen_mask = labels.isin(list(na_labels)).to_numpy()

    for d in episode_shuffles_w(labels, na_labels, 6, 0, 1, 2):
        vals = d.to_numpy(dtype=object)
        # every frozen bar keeps ITS OWN original na label, in place
        assert (vals[frozen_mask]
                == labels.to_numpy(dtype=object)[frozen_mask]).all()
        assert sorted(runs(vals[~frozen_mask])) == sorted(
            [("A", 3), ("B", 2)])


# ------------------------------------------------- registered RNG map


def test_seed_map_pinned_by_reference_reconstruction():
    # pins the base seed 17 AND the [17, panel, taxonomy, fold] order
    labels = na_holes_labels()
    got = episode_shuffles_w(labels, {NA}, 7, 1, 3, 2)
    expected = reference_draws(labels, {NA}, 7, 1, 3, 2)
    assert_series_list_equal(got, expected)
    assert NULL_SEED_W == 17


def test_prefix_property():
    labels = na_holes_labels()
    short = episode_shuffles_w(labels, {NA}, 3, 0, 0, 1)
    long = episode_shuffles_w(labels, {NA}, 9, 0, 0, 1)
    assert_series_list_equal(short, long[:3])


def test_same_index_tuple_reproducible():
    labels = na_holes_labels()
    a = episode_shuffles_w(labels, {NA}, 6, 2, 4, 19)
    b = episode_shuffles_w(labels, {NA}, 6, 2, 4, 19)
    assert_series_list_equal(a, b)


def test_distinct_index_tuples_give_distinct_draws():
    labels = na_holes_labels()
    base = episode_shuffles_w(labels, {NA}, 6, 0, 0, 1)
    for p, t, f in [(1, 0, 1), (0, 1, 1), (0, 0, 2)]:
        other = episode_shuffles_w(labels, {NA}, 6, p, t, f)
        assert any(not a.equals(b) for a, b in zip(base, other))


def test_registered_index_tables():
    assert PANEL_INDEX_W == {"P-BTC": 0, "P-ETH": 1, "P-SOL": 2}
    assert TAXONOMY_INDEX_W == {
        "T-D": 0, "T-E": 1, "T-F": 2, "T-G": 3, "T-H": 4}


# ------------------------------------------------------ degenerate cases


def test_all_na_every_draw_identical_to_original():
    labels = labels_from_blocks([(NA, 4), ("oi-na", 3), (NA, 2)])
    draws = episode_shuffles_w(labels, {NA, "oi-na"}, 5, 0, 2, 3)
    assert len(draws) == 5
    for d in draws:
        assert d.index.equals(labels.index)
        assert d.tolist() == labels.tolist()


def test_zero_na_reduces_to_plain_episode_shuffle():
    # no na episodes -> the permutation acts on ALL episodes (frozen
    # episode_shuffles mechanics under the new seed map)
    labels = labels_from_blocks([("A", 3), ("B", 4), ("C", 5)])
    empty = episode_shuffles_w(labels, set(), 6, 0, 0, 1)
    absent = episode_shuffles_w(labels, {"zz-na"}, 6, 0, 0, 1)
    expected = reference_draws(labels, set(), 6, 0, 0, 1)
    assert_series_list_equal(empty, expected)
    assert_series_list_equal(absent, expected)
    for d in empty:
        assert sorted(runs(d.to_numpy(dtype=object))) == sorted(
            [("A", 3), ("B", 4), ("C", 5)])


# --------------------------------------------------------- pooled null


def test_shuffle_null_pooled_w_is_frozen_function_unchanged():
    # §7: clause mechanics byte-identical to lab/hooks.py — the pooled
    # null is the frozen function itself, re-exported, never reimplemented
    assert shuffle_null_pooled_w is lab.hooks.shuffle_null_pooled


def test_pooled_null_consumes_w_draws():
    n_bars = 12
    opens = [100.0, 101.0, 103.0, 102.0, 105.0, 108.0,
             107.0, 110.0, 112.0, 111.0, 115.0, 118.0]
    closes = opens[1:] + [120.0]
    bars = make_bars(opens, closes)
    idx = bars.index

    labels_f1 = pd.Series([NA] * 3 + ["A"] * 4 + ["B"] * 5, index=idx)
    labels_f2 = pd.Series(["A"] * 4 + [NA] * 2 + ["B"] * 6, index=idx)
    assert len(labels_f1) == len(labels_f2) == n_bars
    sh1 = episode_shuffles_w(labels_f1, {NA}, 4, 0, 3, 1)
    sh2 = episode_shuffles_w(labels_f2, {NA}, 4, 0, 3, 2)

    captured: list[pd.Series] = []

    def strategy_fn(labs: pd.Series) -> pd.Series:
        captured.append(labs.copy())
        return (labs == "A").astype(float)

    out = shuffle_null_pooled_w(
        strategy_fn, [(sh1, idx[6:9]), (sh2, idx[9:])],
        bars, zero_funding(idx), 10.0)

    assert set(out) == {"p95", "null_sharpes"}
    assert isinstance(out["null_sharpes"], np.ndarray)
    assert len(out["null_sharpes"]) == 4
    assert out["p95"] == pytest.approx(
        float(np.quantile(out["null_sharpes"], 0.95)))

    # draw-major, fold-minor order; na holes intact in every series the
    # strategy consumed
    assert len(captured) == 8
    for k, labs in enumerate(captured):
        ref = labels_f1 if k % 2 == 0 else labels_f2
        na_mask = (ref == NA).to_numpy()
        vals = labs.to_numpy(dtype=object)
        assert (vals[na_mask] == NA).all()
        assert (vals[~na_mask] != NA).all()
