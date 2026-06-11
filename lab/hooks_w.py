"""W-sweep null mechanics: na-freezing episode shuffles + registered RNG map.

docs/plans/2026-06-10-widening-preregistration.md §7 "Null mechanics
(pinned)" verbatim; amendment log items 2 (M2: na episodes frozen in
place) and 9 (M10/W7: seed map pinned per (panel, taxonomy, fold)).

episode_shuffles_w pre-generates the COMMON null draws for one
(panel, taxonomy, fold) cell. Per-draw mechanics:
  - episodes via lab.classifier.episodes (frozen segmentation);
  - episodes whose label is in na_labels are FROZEN IN PLACE — their bar
    positions are identical in every draw (registered because the frozen
    panel had no structurally-missing eras; freezing na blocks keeps every
    draw's activity profile inside the Variant's feature-covered eras —
    the conservative choice);
  - the permutation acts only on the non-na episodes, which fill the
    non-na bar positions in permuted order with lengths preserved.
RNG map (registered): a fresh
numpy.random.default_rng([17, panel_index, taxonomy_index, fold_ordinal])
per (panel, taxonomy, fold) — panel_index P-BTC=0 / P-ETH=1 / P-SOL=2,
taxonomy_index T-D=0 / T-E=1 / T-F=2 / T-G=3 / T-H=4, fold_ordinal the
panel-local 1-based index (tables below; printed in the sweep artifact).
Draws come sequentially from that one rng (one permutation per draw), so
episode_shuffles_w(.., m, ..) is a PREFIX of episode_shuffles_w(.., n, ..)
for m <= n — same prefix property the frozen episode_shuffles pins.

Pooled null: lab.hooks.shuffle_null_pooled is reused UNCHANGED. Confirmed
against lab/hooks.py — it consumes pre-generated per-fold draw lists
(fold_shuffles: list[tuple[list[pd.Series], pd.Index]]) and is agnostic to
how the draws were generated, so the na-freezing common draws plug
straight in. It is re-exported here as shuffle_null_pooled_w (the same
function object, never reimplemented; §7: clause mechanics byte-identical
to lab/hooks.py). Frozen-artifact byte-compatibility applies only to the
frozen 36-variant path, which keeps lab/hooks.py untouched.

Memory note: episode_shuffles_w returns a lazy _EpisodeShufflesW Sequence.
At construction it stores only the n permutation orders (n × episode-count
ints) and the shared episode/mask/base arrays. __getitem__(i) materializes
draw i as a fresh pd.Series on demand without caching, so at most one
Series is live at a time during consumer loops. fork-safe: pure numpy
state, no open file handles.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from lab.classifier import episodes
from lab.hooks import shuffle_null_pooled

NULL_SEED_W = 17  # leading entry of the registered seed list (§7)

# Registered index tables (§7 RNG map) — printed in the sweep artifact.
PANEL_INDEX_W = {"P-BTC": 0, "P-ETH": 1, "P-SOL": 2}
TAXONOMY_INDEX_W = {"T-D": 0, "T-E": 1, "T-F": 2, "T-G": 3, "T-H": 4}

# Pooled null reused unchanged from the frozen hooks (see module docstring).
shuffle_null_pooled_w = shuffle_null_pooled


class _EpisodeShufflesW(Sequence):
    """Lazy read-only Sequence of na-freezing episode-shuffled pd.Series.

    Stores n permutation orders (tiny int arrays) at construction and
    materializes each draw as a fresh pd.Series in __getitem__ without
    caching. fork-safe: pure numpy state.
    """

    __slots__ = (
        "_index", "_base", "_na_mask", "_non_na",
        "_ep_labels", "_ep_lengths", "_orders",
    )

    def __init__(
        self,
        index: pd.Index,
        base: np.ndarray,
        na_mask: np.ndarray,
        non_na: np.ndarray,
        ep_labels: np.ndarray,
        ep_lengths: np.ndarray,
        orders: list[np.ndarray],
    ) -> None:
        self._index = index
        self._base = base
        self._na_mask = na_mask
        self._non_na = non_na
        self._ep_labels = ep_labels
        self._ep_lengths = ep_lengths
        self._orders = orders

    def __len__(self) -> int:
        return len(self._orders)

    def __getitem__(self, i):  # type: ignore[override]
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(len(self)))]
        if i < 0:
            i += len(self)
        if not (0 <= i < len(self)):
            raise IndexError(i)
        order = self._orders[i]
        values = self._base.copy()
        if len(self._non_na):
            values[~self._na_mask] = np.concatenate(
                [np.repeat(self._ep_labels[j], self._ep_lengths[j])
                 for j in self._non_na[order]])
        return pd.Series(values, index=self._index)


def episode_shuffles_w(labels: pd.Series, na_labels: set[str], n: int,
                       panel_index: int, taxonomy_index: int,
                       fold_ordinal: int) -> _EpisodeShufflesW:
    """Return a lazy n-draw na-freezing episode-order-permuted Sequence (§7).

    na bar positions are invariant across draws and keep their original
    labels; the non-na episodes' ORDER is permuted (one rng.permutation
    per draw over the non-na episode count) and they fill the non-na bar
    positions in sequence, lengths preserved. Degenerate cases follow from
    the same mechanics: all-na -> every draw equals the original series;
    zero na episodes -> the plain frozen episode shuffle under this seed
    map. Each draw is a Series on labels.index, materialized on demand.

    The permutation orders are drawn sequentially from the registered rng
    at construction time (identical seed stream to the former list-based
    implementation), so the prefix property holds and draw values are
    byte-identical to the previous implementation.
    """
    eps = episodes(labels)
    ep_labels = eps["label"].to_numpy(dtype=object)
    ep_lengths = eps["n_bars"].to_numpy()
    non_na = np.flatnonzero(
        ~np.array([lab in na_labels for lab in ep_labels], dtype=bool))

    base = labels.to_numpy(dtype=object)
    na_mask = labels.isin(list(na_labels)).to_numpy()

    rng = np.random.default_rng(
        [NULL_SEED_W, panel_index, taxonomy_index, fold_ordinal])
    orders = [rng.permutation(len(non_na)) for _ in range(n)]

    return _EpisodeShufflesW(
        index=labels.index,
        base=base,
        na_mask=na_mask,
        non_na=non_na,
        ep_labels=ep_labels,
        ep_lengths=ep_lengths,
        orders=orders,
    )
