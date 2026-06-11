"""Hypothesis-family quarantine — registration §6 lock layers, in full.

Registered spec: docs/plans/2026-06-10-widening-preregistration.md §6
(the fade-positive-funding-extremes family quarantine; amendment 1) plus
prior-contact item 1 (H8 deep replay — why the family is locked on every
panel); build phase §12.1. The quarantine travels with the HYPOTHESIS,
not the ticker: every layer below applies to Survivors on all panels.

Reference extremity labeling (taxonomy-independent, §6): per-fold
TRAIN-ONLY cuts c_hi = q60(|funding_rate_8h|), c_x = q90(|f|) — identical
quantile calls to T-D in lab/classifiers_w.derive_thresholds_w (R1; the
caller passes exactly the fold-train funding slice). A pooled-OOS bar is
a reference positive-extremity bar iff f >= 0 AND |f| >= c_hi (inclusive,
matching T-D band membership); a reference positive-MILD bar iff f >= 0
AND |f| < c_hi. NaN funding: every clause evaluates FALSE (D4.3), so NaN
bars are neither. Masks are per-fold; the caller assembles pooled masks
fold by fold (cuts differ across folds).

Layer 1 — pure-map predicate (layer1_pure_map_locked). Locked iff the
action map (i) is short in >= 1 positive-funding extremity band of its
own label space (T-D: pos-hi / pos-x) or, for taxonomies without
funding-extremity bands (T-E/T-F/T-G/T-H), is short on EVERY
positive-funding label, AND (ii) takes no nonzero action in any
negative-funding label, AND (iii) is long nowhere. A1/A2 satisfy it; the
registered symmetric maps do not. na labels (and fg-mid) are funding-
unsigned: they count only for clause (iii).

Layer 2 — counterfactual extremity-neutralized twin (layer2_twin, the
binding test). w' = w-bar_mild(fold) — the Survivor's mean signed w over
the reference positive-MILD bars of that fold's OOS (fallback 0 if that
fold has none) — on every reference positive-extremity OOS bar; w' = w
elsewhere. This module returns the twin series ONLY; the caller re-runs
the pooled OOS pipeline on w' (same fills, costs, funding, common null
draws) and the Survivor is family-locked unless the twin still passes
beats_flat@10bps AND null_p95. The §6 sketch passes (w, mask,
fold_assignment); the positive-MILD set is not derivable from the
extremity mask alone, so the mild mask is an explicit keyword argument,
built with reference_mild_mask from the SAME per-fold cuts.

Layer 3 — share backstop (layer3_share, majority rule). The caller
decomposes pooled-OOS net PnL into bar-level net return contributions
(each bar's return including that bar's |dw| cost and any funding
accrual). Locked-leg bars = reference positive-extremity bars with
w < 0. Evaluated only when the ARITHMETIC total > 0: family-locked iff
leg_sum / total_sum > 0.5 (a Schelling point chosen for defensibility,
not tuned to any observed share).

A family-locked Survivor is published in the falsification chapter with
the specific layer that locked it; it cannot be the Winner this cycle,
on any panel.
"""

from __future__ import annotations

import pandas as pd

REFERENCE_Q_HI = 0.60  # §6: c_hi = q60(|funding_rate_8h|), train-only
REFERENCE_Q_X = 0.90   # §6: c_x = q90(|funding_rate_8h|), train-only
LAYER3_MAJORITY = 0.5  # §6: locked iff leg share > 0.5 (strict)

# §6 layer-1 clause (i): positive-funding extremity bands per W taxonomy
# label space. Only T-D has them; the other taxonomies take the
# short-on-every-positive-funding-label branch.
POS_EXTREMITY_BANDS_W: dict[str, tuple[str, ...]] = {
    "TD": ("pos-hi", "pos-x"),
    "TE": (),
    "TF": (),
    "TG": (),
    "TH": (),
}


def reference_cuts(fold_train_funding: pd.Series) -> dict:
    """Per-fold train-only reference cuts (§6; identical to T-D §4)."""
    abs_f = fold_train_funding.abs()
    return {
        "c_hi": float(abs_f.quantile(REFERENCE_Q_HI)),
        "c_x": float(abs_f.quantile(REFERENCE_Q_X)),
    }


def reference_extremity_mask(funding: pd.Series,
                             fold_train_funding: pd.Series) -> pd.Series:
    """Reference positive-extremity bars: f >= 0 AND |f| >= c_hi (§6).

    funding is the fold's bar series to label (e.g. its OOS slice);
    fold_train_funding is that fold's train funding slice (R1). NaN
    funding -> both clauses FALSE (D4.3) -> never an extremity bar.
    """
    c_hi = reference_cuts(fold_train_funding)["c_hi"]
    return (funding >= 0) & (funding.abs() >= c_hi)


def reference_mild_mask(funding: pd.Series,
                        fold_train_funding: pd.Series) -> pd.Series:
    """Reference positive-MILD bars: f >= 0 AND |f| < c_hi (§6 layer 2)."""
    c_hi = reference_cuts(fold_train_funding)["c_hi"]
    return (funding >= 0) & (funding.abs() < c_hi)


def layer1_pure_map_locked(variant) -> bool:
    """§6 lock layer 1 — pure-map predicate on a VariantW's action map.

    Locked iff (i) short in >= 1 positive-funding extremity band (or, for
    taxonomies without them, short on EVERY positive-funding label), AND
    (ii) zero action in every negative-funding label, AND (iii) long
    nowhere (any label, na included).
    """
    if variant.taxonomy not in POS_EXTREMITY_BANDS_W:
        raise ValueError(
            f"unknown W taxonomy {variant.taxonomy!r}; the §6 lock predicate "
            f"is defined on {sorted(POS_EXTREMITY_BANDS_W)}")
    actions = variant.action_dict()
    if any(a > 0.0 for a in actions.values()):
        return False  # (iii) long somewhere
    if any(a != 0.0 for lab, a in actions.items() if lab.startswith("neg-")):
        return False  # (ii) nonzero action in a negative-funding label
    bands = POS_EXTREMITY_BANDS_W[variant.taxonomy]
    if bands:
        return any(actions.get(b, 0.0) < 0.0 for b in bands)  # (i)
    pos = [a for lab, a in actions.items() if lab.startswith("pos-")]
    return bool(pos) and all(a < 0.0 for a in pos)  # (i) no-band branch


def layer2_twin(w: pd.Series, mask: pd.Series, fold_assignment: pd.Series,
                *, mild_mask: pd.Series) -> pd.Series:
    """§6 lock layer 2 — the extremity-neutralized twin w' (binding test).

    Args:
      w: the Survivor's pooled-OOS position series (final w, post every
         rule-surface transform — what the engine actually held).
      mask: reference positive-extremity mask on w's bars (per-fold cuts,
         assembled by the caller via reference_extremity_mask).
      fold_assignment: fold id per bar of w (panel-local fold names).
      mild_mask: reference positive-MILD mask on w's bars, from the SAME
         per-fold cuts (reference_mild_mask); keyword-only — see module
         docstring.

    Returns the twin series w' on w's index: on every masked bar,
    w-bar_mild(fold) — the mean signed w over that fold's mild bars
    (fallback 0 if the fold has none) — and w elsewhere. The twin zeroes
    a short-fade coat and RE-RISKS a long-only de-risk coat with one
    instrument; the caller re-runs the pooled OOS pipeline on it. Never
    mutates inputs.
    """
    wf = w.astype(float).copy()
    ext = mask.reindex(wf.index).eq(True)        # NaN/missing -> False
    mild = mild_mask.reindex(wf.index).eq(True)  # NaN/missing -> False
    folds = fold_assignment.reindex(wf.index)
    twin = wf.copy()
    for fold in pd.unique(folds):
        in_fold = folds == fold
        mild_w = wf[in_fold & mild]
        fill = float(mild_w.mean()) if len(mild_w) else 0.0  # fallback 0
        twin.loc[in_fold & ext] = fill
    return twin


def layer3_share(bar_net_contributions: pd.Series, mask: pd.Series,
                 w: pd.Series) -> dict:
    """§6 lock layer 3 — share backstop (majority rule), arithmetic.

    Args:
      bar_net_contributions: bar-level net return contributions of the
         pooled-OOS PnL decomposition (each bar's return including that
         bar's |dw| cost and any funding accrual), summed ARITHMETICALLY.
      mask: reference positive-extremity mask on the same bars.
      w: the Survivor's position series on the same bars.

    Locked-leg bars = mask AND w < 0. Returns a dict:
      total: arithmetic sum over all bars;
      leg_sum: arithmetic sum over locked-leg bars;
      evaluated: total > 0 (§6: evaluated only then);
      share: leg_sum / total when evaluated, else NaN;
      locked: evaluated AND share > 0.5 (strict majority).
    """
    contrib = bar_net_contributions.astype(float)
    ext = mask.reindex(contrib.index).eq(True)
    wf = w.reindex(contrib.index).astype(float)
    leg = ext & (wf < 0.0)
    total = float(contrib.sum())
    leg_sum = float(contrib[leg].sum())
    evaluated = total > 0.0
    share = leg_sum / total if evaluated else float("nan")
    locked = bool(evaluated and share > LAYER3_MAJORITY)
    return {
        "total": total,
        "leg_sum": leg_sum,
        "evaluated": evaluated,
        "share": share,
        "locked": locked,
    }
