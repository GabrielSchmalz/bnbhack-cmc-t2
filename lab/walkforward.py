"""Purged/embargoed walk-forward folds (plan Task 1.7, PR-6, ADR-001 R2).

Expanding folds on fixed calendar-UTC boundaries; between each boundary bar
and the OOS start sits an embargo of E BARS counted on the index grid (not
wall time), where E = max(42, median regime-episode length in bars). The
label series passed to folds() is used ONLY to size the embargo via
classifier.episodes() — never to place boundaries.

Train is exactly every grid bar strictly before the boundary (expanding from
the index start); OOS is [boundary bar + E bars .. next boundary) on the
grid, with F4 OOS running to the index end.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lab.classifier import episodes

EMBARGO_FLOOR_BARS = 42

# PR-6 calendar-UTC fold boundaries: (name, train_end/OOS anchor, OOS end).
# OOS end None => index end (F4).
_BOUNDARIES: list[tuple[str, pd.Timestamp, pd.Timestamp | None]] = [
    ("F1", pd.Timestamp("2025-10-01"), pd.Timestamp("2025-12-01")),
    ("F2", pd.Timestamp("2025-12-01"), pd.Timestamp("2026-02-01")),
    ("F3", pd.Timestamp("2026-02-01"), pd.Timestamp("2026-04-01")),
    ("F4", pd.Timestamp("2026-04-01"), None),
]


@dataclass(frozen=True)
class Fold:
    train_idx: pd.DatetimeIndex
    oos_idx: pd.DatetimeIndex
    name: str


def embargo_bars(labels: pd.Series) -> int:
    """E = max(42, median episode n_bars). Ceil a fractional median (longer
    embargo is the conservative direction)."""
    eps = episodes(labels)
    if eps.empty:
        return EMBARGO_FLOOR_BARS
    median = float(np.median(eps["n_bars"].to_numpy()))
    return max(EMBARGO_FLOOR_BARS, math.ceil(median))


def _at(ts: pd.Timestamp, index: pd.DatetimeIndex) -> pd.Timestamp:
    return ts.tz_localize(index.tz) if index.tz is not None else ts


def folds(index: pd.DatetimeIndex, labels: pd.Series) -> list[Fold]:
    """PR-6 expanding folds over index; labels size the embargo only."""
    if not index.is_monotonic_increasing:
        raise ValueError("index must be sorted ascending")
    e = embargo_bars(labels)
    out: list[Fold] = []
    for name, boundary, oos_end in _BOUNDARIES:
        b_pos = index.searchsorted(_at(boundary, index), side="left")
        train_idx = index[:b_pos]
        oos_stop = (
            len(index)
            if oos_end is None
            else index.searchsorted(_at(oos_end, index), side="left")
        )
        oos_idx = index[b_pos + e : oos_stop]
        out.append(Fold(train_idx=train_idx, oos_idx=oos_idx, name=name))
    return out


def pooled_oos(folds_list: list[Fold]) -> pd.DatetimeIndex:
    """Concatenated, sorted, deduped OOS indices across folds (pooled OOS)."""
    if not folds_list:
        return pd.DatetimeIndex([])
    combined = folds_list[0].oos_idx
    for f in folds_list[1:]:
        combined = combined.append(f.oos_idx)
    return combined.unique().sort_values()
