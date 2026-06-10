"""Action-map rules: regime labels -> pre-lagged position series (Task 2.3).

apply(labels, action_map) is the ONLY place the 1-bar lag lives: a regime
known at the close of bar t may affect the position from bar t+1 onward
(signal at close, next-bar-open fill — PR-3). lab/engine.run_backtest
expects w ALREADY LAGGED; do not lag again downstream.

Unknown labels and NaN labels map to 0.0 (flat) — deterministic, mirroring
the classifier's NaN-clause-is-FALSE semantics (FREEZE-ADDENDUM D4.3).
"""

from __future__ import annotations

import pandas as pd


def apply(labels: pd.Series, action_map: dict[str, float]) -> pd.Series:
    """Map regime labels to a position series w, lagged by one bar.

    w_raw[t] = action_map[labels[t]] (unknown or NaN label -> 0.0), then
    w = w_raw.shift(1).fillna(0.0): the regime at bar t affects w at bar
    t+1 only; bar 0 is always flat.
    """
    w_raw = labels.map(action_map).astype(float).fillna(0.0)
    return w_raw.shift(1).fillna(0.0)
