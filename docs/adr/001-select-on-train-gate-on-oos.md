# Select on train, gate on OOS

The variant sweep ranks all variants by train-period Sharpe (at 10 bps RT,
tiebreak: lower max-DD). The Winner is the highest-ranked variant that passes
the shipping gate — OOS is used ONLY as a binary pass/fail, never as a ranking
key. Consequence we accept: the Winner may have a lower OOS Sharpe than a
discarded survivor. Rationale: ranking by OOS across dozens of variants turns
the ~3-month OOS window into a validation set we optimized over, and with that
little data, max-OOS-Sharpe selection crowns noise. Pre-committing to the best
in-sample candidate and asking "did it survive?" keeps the OOS claim honest and
is the stronger story in front of a judging panel probing for cherry-picking.
The report discloses total variant count and this rule.

Rejected alternative: rank survivors by OOS Sharpe and ship the top
(disclosed). Rejected because disclosure does not undo selection bias — it only
documents it.

## Refinements (2026-06-10 review)

These close leakage/validity holes that the base rule above does not, by itself,
cover. They are binding on the Lab.

### R1 — Distillation thresholds fit on train only (anti-leakage)

The percentile→absolute mapping that produces the distilled classifier's frozen
thresholds MUST be computed on the **train partition only**. It must NOT inherit
the `regime_matrix_labels` full-sample cuts: the rm17-derivs run window
(2025-10→2026-05-18) **overlaps the prospective OOS** (~2026-03→06), so any cut
derived from that full sample has already seen OOS data. Bands may seed
*discovery*, but every threshold that survives into the shipped/validated
classifier is re-derived on train only. Reference-table percentiles likewise:
train-fit, with the refresh procedure documenting that re-derivation is
train-window-scoped.

### R2 — Walk-forward over a single 3-month holdout (honest N)

A single ~3-month OOS tail of the 14-month full-stack window yields only a
handful of regime episodes (order ~4–6) — too few to validate a regime-*switching*
edge; trades and bars overstate N (see CONTEXT "Regime episode"). The gate is
therefore evaluated on a **purged/embargoed walk-forward** across the full-stack
window (rolling train→OOS folds, embargo ≥ one regime episode at each boundary),
not one tail. This multiplies OOS episodes under the same select-on-train,
gate-on-OOS posture, and reads as *more* rigorous to the panel. **The report's
headline honest-N is the OOS regime-episode count**, stated explicitly alongside
trade/bar counts.

### R3 — Gate multiple-testing is disclosed, not waved away

Select-on-train fixes *which* survivor wins. It does NOT fix that the OOS
pass/fail gate is applied across every swept variant, so P(≥1 false pass) grows
with the variant count — the survivor set is itself OOS-filtered. The report
therefore discloses: total variants swept, variants that passed the gate, and
the **expected pass-rate under the regime-shuffle null** (already computed by the
honesty hooks). A pass-count near the null expectation is reported as such, not
spun as signal.
