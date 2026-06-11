"""W-sweep taxonomy classifiers T-D…T-H (registration §4) + coverage floor (§2).

Registered spec: docs/plans/2026-06-10-widening-preregistration.md (build
phase §12.1). Taxonomy ids follow the frozen lab convention: "TD" ≡ the
registration's "T-D", …, "TH" ≡ "T-H" (same mapping as "TA"/"TB"/"TC" in
lab/classifier.py). Canonical order TD, TE, TF, TG, TH matches the §7 RNG
taxonomy_index map (T-D=0 … T-H=4).

Feature columns (§2 R-SRC): funding_rate_8h, oi_chg_24h_daily, fg,
close_vs_sma200_1d, rsi14_1d.

derive_thresholds_w(df_train, taxonomy) — train-only absolute cuts (R1; the
caller passes fold-train rows exclusively, as in lab/features.py):
  TD: c_hi = q60(|funding_rate_8h|), c_x = q90(|funding_rate_8h|)
  TF: fg_lo = q20(fg), fg_hi = q80(fg)
  TE / TG: no train-derived cuts
  TH: fixed canonical constants rsi_os = 30.0 / rsi_ob = 70.0, returned
      as-is (never data-derived)
plus the §2 coverage floor for the taxonomy's non-funding Feature axis:
axis_na is True iff df_train holds < 90 distinct UTC calendar days each
containing >= 1 non-NaN observation of that Feature. Funding axes are
exempt (TD returns no sentinel). Cuts are still derived on a floored fold;
the sentinel, not the cuts, governs labeling.

label_w(df, taxonomy, thresholds) — label Series in §4's canonical label
spaces. NaN policy (§4): funding NaN keeps the frozen D4.3 semantics (a NaN
clause evaluates FALSE, so pos requires f >= 0 -> neg branch, NaN extremity
-> mid). A NaN non-funding Feature bar maps to the taxonomy's explicit na
label; a floored axis (thresholds["axis_na"] is True) maps EVERY bar of the
fold to the na label. Band membership is inclusive (|f| >= cut, fg <= / >=
cut, rsi <= 30 / >= 70), matching frozen T-C and the §6 reference-extremity
convention.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TAXONOMIES_W = ["TD", "TE", "TF", "TG", "TH"]

# §4 table, canonical order verbatim. The non-na prefix of each list is the
# §5 direction-vector zip order; na labels (and, for T-F direction maps,
# fg-mid) always act 0.
LABELS_W = {
    "TD": ["pos-mid", "pos-hi", "pos-x", "neg-mid", "neg-hi", "neg-x"],
    "TE": ["pos-build", "pos-unwind", "neg-build", "neg-unwind", "oi-na"],
    "TF": ["pos-fear", "pos-greed", "neg-fear", "neg-greed", "fg-mid",
           "fg-na"],
    "TG": ["pos-above", "neg-above", "pos-below", "neg-below", "sma-na"],
    "TH": ["pos-os", "pos-mid", "pos-ob", "neg-os", "neg-mid", "neg-ob",
           "rsi-na"],
}

# The explicit na label per taxonomy (None for funding-only T-D, §4).
NA_LABEL_W = {
    "TD": None, "TE": "oi-na", "TF": "fg-na", "TG": "sma-na", "TH": "rsi-na",
}

# The non-funding Feature axis per taxonomy (§2 coverage floor; None = the
# taxonomy is funding-only and exempt).
AXIS_FEATURE_W = {
    "TD": None,
    "TE": "oi_chg_24h_daily",
    "TF": "fg",
    "TG": "close_vs_sma200_1d",
    "TH": "rsi14_1d",
}

COVERAGE_FLOOR_DAYS = 90  # §2: distinct UTC calendar days with >= 1 obs
RSI_OS = 30.0             # §4 T-H canonical constants, not data-derived
RSI_OB = 70.0


def _check_taxonomy(taxonomy: str) -> None:
    if taxonomy not in AXIS_FEATURE_W:
        raise ValueError(
            f"unknown W taxonomy {taxonomy!r}; expected one of {TAXONOMIES_W}"
        )


def _covered_days(feature: pd.Series) -> int:
    """Distinct UTC calendar days holding >= 1 non-NaN observation (§2)."""
    obs = feature.dropna()
    if obs.empty:
        return 0
    return int(pd.DatetimeIndex(obs.index).normalize().nunique())


def derive_thresholds_w(df_train: pd.DataFrame, taxonomy: str) -> dict:
    """Train-only absolute cuts + §2 coverage-floor sentinel (R1).

    Quantiles are computed over the rows of df_train and nothing else — the
    caller is responsible for passing exactly the fold-train slice. NaNs are
    excluded (pandas quantile semantics); cut values are plain floats.
    """
    _check_taxonomy(taxonomy)
    out: dict = {}
    if taxonomy == "TD":
        # Funding axis only — exempt from the coverage floor (§2).
        abs_f = df_train["funding_rate_8h"].abs()
        out["c_hi"] = float(abs_f.quantile(0.60))
        out["c_x"] = float(abs_f.quantile(0.90))
        return out
    if taxonomy == "TF":
        fg = df_train["fg"]
        out["fg_lo"] = float(fg.quantile(0.20))
        out["fg_hi"] = float(fg.quantile(0.80))
    elif taxonomy == "TH":
        out["rsi_os"] = RSI_OS
        out["rsi_ob"] = RSI_OB
    axis = AXIS_FEATURE_W[taxonomy]
    out["axis_na"] = bool(
        _covered_days(df_train[axis]) < COVERAGE_FLOOR_DAYS
    )
    return out


def _funding_prefix(df: pd.DataFrame) -> np.ndarray:
    """pos ⇔ f >= 0 (D4.3: NaN funding -> FALSE -> neg branch)."""
    return np.where(df["funding_rate_8h"] >= 0, "pos", "neg")


def _label_td(df: pd.DataFrame, t: dict) -> pd.Series:
    abs_f = df["funding_rate_8h"].abs()
    # Inclusive bands, x checked first (q90 >= q60); NaN -> mid (D4.3).
    band = np.select(
        [abs_f >= t["c_x"], abs_f >= t["c_hi"]], ["x", "hi"], default="mid"
    )
    out = np.char.add(np.char.add(_funding_prefix(df), "-"), band)
    return pd.Series(out, index=df.index)


def _label_te(df: pd.DataFrame, t: dict) -> pd.Series:
    oi = df["oi_chg_24h_daily"]
    side = np.where(oi >= 0, "build", "unwind")  # build ⇔ oi >= 0
    out = np.char.add(np.char.add(_funding_prefix(df), "-"), side)
    return pd.Series(np.where(oi.isna(), "oi-na", out), index=df.index)


def _label_tf(df: pd.DataFrame, t: dict) -> pd.Series:
    fg = df["fg"]
    corner = np.select(
        [fg <= t["fg_lo"], fg >= t["fg_hi"]], ["fear", "greed"], default=""
    )
    out = np.char.add(np.char.add(_funding_prefix(df), "-"), corner)
    out = np.where(corner == "", "fg-mid", out)  # mid is funding-free (§4)
    return pd.Series(np.where(fg.isna(), "fg-na", out), index=df.index)


def _label_tg(df: pd.DataFrame, t: dict) -> pd.Series:
    sma = df["close_vs_sma200_1d"]
    side = np.where(sma > 0, "above", "below")  # above ⇔ strictly > 0
    out = np.char.add(np.char.add(_funding_prefix(df), "-"), side)
    return pd.Series(np.where(sma.isna(), "sma-na", out), index=df.index)


def _label_th(df: pd.DataFrame, t: dict) -> pd.Series:
    rsi = df["rsi14_1d"]
    band = np.select(
        [rsi <= t["rsi_os"], rsi >= t["rsi_ob"]], ["os", "ob"], default="mid"
    )
    out = np.char.add(np.char.add(_funding_prefix(df), "-"), band)
    return pd.Series(np.where(rsi.isna(), "rsi-na", out), index=df.index)


_LABELERS_W = {
    "TD": _label_td, "TE": _label_te, "TF": _label_tf, "TG": _label_tg,
    "TH": _label_th,
}


def label_w(df: pd.DataFrame, taxonomy: str, thresholds: dict) -> pd.Series:
    """Regime label per bar under a W taxonomy; index = df.index.

    thresholds is the derive_thresholds_w output (or any dict of absolute
    numbers with the same keys, R1). An axis-floored fold (axis_na True)
    short-circuits to the taxonomy's na label on every bar (§2).
    """
    _check_taxonomy(taxonomy)
    na_label = NA_LABEL_W[taxonomy]
    if na_label is not None and thresholds.get("axis_na", False):
        return pd.Series(na_label, index=df.index, dtype=object)
    return _LABELERS_W[taxonomy](df, thresholds)
