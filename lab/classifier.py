"""Taxonomy classifiers (plan Task 1.6, PR-8 candidates T-A/T-B/T-C).

label(df, cfg) maps a feature frame to a regime-label Series under one of the
pre-registered taxonomies. Thresholds are passed in as ABSOLUTE numbers
(derivation lives in features.py, R1); this module only consumes them.

Canonical feature columns: funding_rate_8h, oi_chg_24h, fg, close_vs_sma30_1d.
Canonical threshold keys: funding_hi, funding_lo, funding_hi_abs, oi_surge,
fg_lo, fg_hi.

NaN semantics (FREEZE-ADDENDUM D4.3): any clause referencing a NaN Feature
evaluates FALSE. Pandas elementwise comparisons against NaN already yield
False, so the boolean ops below are deliberately fillna-free — the behavior
is pinned by tests, not patched in.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

EPISODE_COLUMNS = ["label", "start", "end", "n_bars"]


@dataclass(frozen=True)
class TaxonomyConfig:
    """One taxonomy + its frozen absolute thresholds."""

    name: str  # "TA" | "TB" | "TC"
    thresholds: dict[str, float]


def _stress_score(df: pd.DataFrame, t: dict[str, float]) -> pd.Series:
    """T-A stress score: count of firing clauses (0..3). NaN clause -> 0."""
    funding = df["funding_rate_8h"]
    funding_clause = (funding >= t["funding_hi"]) | (funding <= t["funding_lo"])
    oi_clause = df["oi_chg_24h"].abs() >= t["oi_surge"]
    fg = df["fg"]
    fg_clause = (fg <= t["fg_lo"]) | (fg >= t["fg_hi"])
    return funding_clause.astype(int) + oi_clause.astype(int) + fg_clause.astype(int)


def _label_ta(df: pd.DataFrame, t: dict[str, float]) -> pd.Series:
    score = _stress_score(df, t)
    out = np.select([score >= 2, score == 1], ["extreme", "stressed"], default="calm")
    return pd.Series(out, index=df.index)


def _label_tb(df: pd.DataFrame, t: dict[str, float]) -> pd.Series:
    stress = _stress_score(df, t) >= 1
    up = df["close_vs_sma30_1d"] > 0  # NaN trend -> False -> "down" branch
    prefix = np.where(stress, "stressed", "calm")
    suffix = np.where(up, "up", "down")
    return pd.Series(np.char.add(np.char.add(prefix, "-"), suffix), index=df.index)


def _label_tc(df: pd.DataFrame, t: dict[str, float]) -> pd.Series:
    funding = df["funding_rate_8h"]
    pos = funding >= 0  # NaN funding -> False -> "neg" branch
    extreme = funding.abs() >= t["funding_hi_abs"]  # NaN -> False -> "mild"
    prefix = np.where(pos, "pos", "neg")
    suffix = np.where(extreme, "extreme", "mild")
    return pd.Series(np.char.add(np.char.add(prefix, "-"), suffix), index=df.index)


_TAXONOMIES = {"TA": _label_ta, "TB": _label_tb, "TC": _label_tc}


def label(df: pd.DataFrame, cfg: TaxonomyConfig) -> pd.Series:
    """Regime label per bar under taxonomy cfg.name; index = df.index."""
    try:
        fn = _TAXONOMIES[cfg.name]
    except KeyError:
        raise ValueError(
            f"unknown taxonomy {cfg.name!r}; expected one of {sorted(_TAXONOMIES)}"
        ) from None
    return fn(df, cfg.thresholds)


def episodes(labels: pd.Series) -> pd.DataFrame:
    """Maximal runs of equal label -> DataFrame[label, start, end, n_bars].

    start/end are the index values of the first/last bar of each run, in
    original order. Regime episodes are the honest sample-size unit (R2).
    """
    if labels.empty:
        return pd.DataFrame(columns=EPISODE_COLUMNS)
    run_id = (labels != labels.shift()).cumsum()
    rows = [
        {
            "label": grp.iloc[0],
            "start": grp.index[0],
            "end": grp.index[-1],
            "n_bars": len(grp),
        }
        for _, grp in labels.groupby(run_id, sort=False)
    ]
    return pd.DataFrame(rows, columns=EPISODE_COLUMNS)
