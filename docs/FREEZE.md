# Threshold freeze — R-NULL branch (plan Task 2.6, PR-10)

Date: 2026-06-10 · Author: critic lane (freeze decision, plan §W phase-F sign-off)
Inputs of record: `artifacts/sweep_results.json`, `artifacts/sweep_summary.md`,
`docs/report/adversarial/lane1_reproduction.md`, `lane2_gate_calibration.md`,
`lane3_near_miss.md`, `docs/report/band_recon.md`, ADR-001, CONTEXT.md,
`docs/gate0/GATE0-FREEZE.md` + `FREEZE-ADDENDUM-decisions.md` (D1–D4).

---

## 1. Verdict on the null result: THE NULL STANDS

0/36 variants passed the shipping gate. Both adversarial failure directions were
attacked and neither holds:

**(a) "A pipeline bug destroyed real edges" — refuted.**
- Lane 1 re-wired the fold pipeline independently (own fold loop, own
  metrics/shuffle/top-5; `lab.sweep/hooks/walkforward/gate/metrics` not in the
  load-bearing path) and reproduced every compared scalar in
  `artifacts/sweep_results.json` with **max |diff| = 0.0** (tolerance 1e-9).
  R1 threshold hygiene was proven the strong way: all 6 thresholds × 4 folds
  recomputed **from raw CSVs truncated strictly before each fold boundary, zero
  lab imports** — exact match, so no OOS row influences any threshold, including
  through feature construction. Trade PnL, cost sides, and the R-FUND sign were
  hand-verified on raw rows to 1e-16.
- Lane 2 planted a known regime-conditional edge into the real panel and ran the
  **unmodified** `lab.sweep`: the gate passes a true edge of **≥ 10 bps/bar
  robustly** (aligned variant ranks #1 on train, all five clauses pass with
  margin) and **5 bps/bar marginally**; drift-sign, cost-wiring, and 1-bar-lag
  probes all behave correctly (rank-key tent peaks exactly at the rules lag).
  The machinery can pass a real edge; nothing real cleared it.
- The bear OOS is the market, not the engine: raw-bar OOS segments compound to
  ≈ −46%, matching HODL's −45.9% net.

**(b) "Talk the near-miss past the gate" — refused.**
DIR-TC-H8-fade_pos_extreme_only-{0.5,1.0} fails the pre-registered top-5-removal
clause for a substantive reason: its 5 best trades (all crash-day shorts) carry
**114.8%/116.2% of the entire OOS gain**; the remaining 25 trades net −1.03%.
Hand recompute matched the artifact to 10 decimals; crediting exit costs back
(the only accounting asymmetry found) leaves top5_net at −0.91%/−1.88% — still
negative. The null-clause margin (p ≈ 0.036) is fully absorbed by 36-variant
selection (expected null-clause passers ≈ 1.8; observed 2, and they are one
strategy at two sizes). Lane 3 shows the result is knife-edge in BOTH
directions — one un-registered knob (q=(0.25,0.75) or top-N=3) flips it to PASS,
a −14d boundary shift collapses it to a 2-clause fail (Sharpe 1.33) — and a
fails-only-top5 near-miss is expected in ~1 of 3 fully-null sweeps of this
design. Every route to a PASS is a post-hoc analyst degree of freedom; ADR-001
exists to forbid exactly that move.

**Frozen outcome: no Winner. The null result ships (R-NULL, PR-10).**
No REOPEN items. The disclosure obligations in §6 are binding on the report and
the Skill but are not reopen-grade.

---

## 2. Frozen taxonomy: T-C (funding-sign × extremity, 4-state)

The Skill ships as a regime **monitor** (§3); it still needs one frozen
taxonomy for its regime classification. Selection basis is pre-stated:
classification stability, episode structure, live-computability — **not** OOS
performance of any variant (no variant validated; performance is not available
as a criterion even in principle).

| criterion | TA (stress 3-state) | TB (stress×trend 4-state) | **TC (funding sign×extremity)** |
|---|---|---|---|
| label stability when thresholds re-derive F1-train → F4-train (full window, bars relabeled) | 48.0% | 28.4% | **5.2%** |
| threshold drift F1→F4 of consumed cuts | funding_lo **−89.9%**, fg_lo −42.9%, fg_hi −16.7%, funding_hi −15.5%, oi_surge +13.7% | same as TA + trend | **funding_hi_abs −14.3%** (single cut) |
| pooled-OOS episodes per fold (uniformity) | 54/71/50/75 | 11/32/19/43 | **52/48/60/65** |
| state occupancy shape (full window @F4 thresholds) | near-uniform 34/36/29% — "extreme" is 29% of bars (semantically inflated) | 12–35% per state | mild states 82%, extremes rare (16.6%/1.5%) — extremity means extremity |
| Features needed live | funding + OI Δ24h + F&G (3 fields; OI live field is a global aggregate, D3; OI lab history has two 12.5-day holes) | TA's 3 + SMA30 trend (4 fields) | **funding only — 1 field, in exactly the D1-sanctioned scale-free form (sign + extremity band)** |
| funding_lo = +1.458e-06 semantics hazard (Lane 1 §4) | consumed | consumed | **not consumed** |

TC dominates on every pre-stated criterion. Recorded counterpoints (disclosed,
not disqualifying): the q80 |funding| cut sits in a microstructure-thin band
just below Binance's 1e-4 baseline funding clump (Lane 3 §2 — the
pos-extreme/pos-mild boundary is sensitive to quantile choice); F3's OOS had
zero pos-extreme bars (extended quiet periods where an extreme state never
fires are normal monitor behavior and must be presented as such); the
neg-extreme state is thin everywhere (1.2% of F4-train bars).

### 2.1 Frozen regime enum (public names = classifier strings, G7)

`pos-mild` · `pos-extreme` · `neg-mild` · `neg-extreme`
(gloss: long-crowding mild/extreme, short-crowding mild/extreme — funding sign
proxies which side pays). The enum ships verbatim as emitted by
`lab/classifier.py::_label_tc`; no rename layer between validated and shipped.

### 2.2 Frozen thresholds (F4-train, verbatim full precision)

Derived by `lab.features.derive_thresholds` on the F4-train slice
(2025-04-03 00:00 ≤ t < 2026-04-01, 2178 bars), exactly the numbers the sweep
gated on F4 OOS (PR-6: shipped frozen thresholds ≡ F4-train numbers).
Recomputed this session via the committed pipeline; matches Lane 1's
boundary-truncated raw recomputation (0.0 diff at its printed precision).

**Binding threshold (the only cut TC consumes):**

| key | value | definition |
|---|---|---|
| `funding_hi_abs` | **8.385600000000002e-05** | q80 of \|funding_rate_8h\| on F4-train |

Classification rule (frozen): `pos` ⇔ funding_rate_8h ≥ 0; `extreme` ⇔
|funding_rate_8h| ≥ 8.3856e-05; NaN clause ⇒ FALSE (D4.3: NaN funding → neg
branch, NaN extremity → mild).

**Full F4-train tuple for the reference table** (recorded for the refresh
procedure; NOT consumed by the TC classifier):
`funding_hi = 8.186200000000001e-05`, `funding_lo = 1.458000000000004e-06`,
`funding_hi_abs = 8.385600000000002e-05`, `oi_surge = 0.05107445682896805`,
`fg_lo = 24.0`, `fg_hi = 55.0`.
Reference-table prose MUST carry Lane 1's caveat: `funding_lo` is
bottom-quintile-RELATIVE and **positive** — it is not a negative-funding
extreme, and any "short-crowded" gloss on it is wrong.

### 2.3 Per-regime expected-behavior notes (F4-train statistics — `"validated": false`)

Descriptive statistics of the F4-train slice only, aligned to the PR-3
convention (label known at close t → described return is bar t+1, open-to-open).
These are the ONLY numbers the monitor's expected-behavior notes may cite, each
carrying `"validated": false`. They are train-period descriptions, not validated
edges — the gate found NO variant on this taxonomy (or any other) shippable.

| regime | bars (share) | episodes | med ep len | next-bar mean r | median r | %neg | ann. vol | train funding range |
|---|---|---|---|---|---|---|---|---|
| pos-mild | 1356 (62.3%) | 184 | 4 | −0.005% | +0.019% | 48.8% | 0.41 | +3.2e-07 .. +8.379e-05 |
| pos-extreme | 410 (18.8%) | 88 | 2 | −0.066% | −0.041% | 53.4% | 0.38 | +8.39e-05 .. +1.0e-04 |
| neg-mild | 386 (17.7%) | 100 | 2 | +0.067% | +0.032% | 48.7% | 0.47 | −8.326e-05 .. −6e-08 |
| neg-extreme | 26 (1.2%) | 9 | 2 | −0.159% | −0.256% | 69.2% | 0.63 | −1.518e-04 .. −8.417e-05 |

Mandatory framing rules for these notes: (i) neg-extreme is 26 bars / 9
episodes — the note must say "insufficient sample to characterize"; (ii) the
pos-extreme negative drift is precisely the pattern whose tradable form FAILED
the gate (§4) — the note must cross-reference the falsification chapter, never
imply an actionable fade.

---

## 3. Skill shape ruling (PR-10): regime MONITOR — confirmed, with amendments

**Confirmed shape.** The Skill ships as a regime monitor emitting:
`{regime (frozen TC enum), as_of_utc, signal_snapshot (live-fetched Feature
values echoed verbatim), per-regime expected-behavior notes derived from
F4-train statistics (§2.3), each labeled "validated": false}` — plus the
near-miss variant published in the report's falsification chapter as a
**FAILED candidate** (gate-caught concentration), never as a tradable spec.

**Amendments (binding):**
1. **Train-stat provenance is pinned**: expected-behavior notes derive from the
   F4-train slice ONLY (§2.3) — the same slice as the frozen thresholds. No
   OOS-derived number may appear in a note.
2. **No active_ruleset in the runtime emission.** The G9 strategy spec block's
   `active_ruleset / entry / exit / sizing` fields are NOT emitted as live
   output. The monitor's JSON block replaces them with the expected-behavior
   note for the current regime plus `validated_metrics_ref` pointing at the
   falsification chapter. Emitting an entry/exit/sizing recommendation that the
   gate refused to validate would be the exact dishonesty the gate exists to
   prevent.
3. **The failed-candidate spec is published in full** (§4) in the falsification
   chapter and referenced (not inlined as actionable) from SKILL.md provenance,
   always headed FAILED + `"validated": false`.
4. **Sample-size quoting rule** (Lane 1 §3): any mention of the failed candidate
   quotes its ACTIVE sample — 30 OOS trades / 92 nonzero-position OOS bars /
   3 of 4 folds — never the taxonomy-level honest_N of 225.
5. **Band framing** (band_recon): TC's NMI vs rm17 Bands is 0.0228 — near
   independence. All prose is "Band-inspired, independently gated on its own
   walk-forward"; the Skill and report claim NO Band distillation for the
   shipped taxonomy. (TB's 0.211 is trend/calendar-mediated and Bands are
   direction-less — also not distillation evidence.)
6. **Funding basis disclaimer** (D1/D3): the live field is
   `get_global_metrics_latest → leverage.funding_rate.average.current` (global
   average, %-units, decimal = value/100); the frozen cut derives from
   Binance-BTC 8h history. The monitor compares sign + extremity band only and
   states the basis difference in every emission; the D1 paired-sample
   calibration result goes in `reference_table.md`.

**How this still satisfies the Track-2 brief ("a backtestable strategy spec
authored as an LLM Skill"), honestly:**
- **Backtestable**: the published failed-candidate spec (§4) is a complete,
  frozen strategy spec — taxonomy, exact thresholds, action map, sizing,
  execution model (PR-3), DD guard (PR-4), costs — reproducible end-to-end by
  anyone via `uv run python -m lab.sweep` from committed CSVs. It is not merely
  backtestable; it WAS backtested, under a pre-registered gate, and the result
  is disclosed.
- **Strategy spec**: the spec exists in full fidelity; what changed is its
  label — FAILED, with the precise clause and reason — instead of an implied
  endorsement.
- **Authored as an LLM Skill**: SKILL.md drives Gate-0-verified CMC MCP tools
  to compute the same frozen classifier live, emits the regime + snapshot +
  disclaimed notes, and carries the validation provenance. The deliverable's
  honest content is: a reproducible gate, a frozen live classifier, and a fully
  specified candidate that the gate caught — which is the submission's rigor
  story, not its failure.

The alternative PR-10 branch (drop the Skill, ship report+demo of the gate
only) is REJECTED: the monitor is live-computable from one verified field, adds
a working MCP integration to the demo, and gives the falsification chapter a
runtime artifact — provided amendments 1–6 hold.

---

## 4. The failed candidate (falsification-chapter exhibit — NOT a tradable spec)

**`DIR-TC-H8-fade_pos_extreme_only` (sizes 0.5 / 1.0) — FAILED, `"validated": false`**

- Rule: at each bar close, if the prior bar's TC label is `pos-extreme`, hold
  w = −size next bar (next-bar-open fill); flat otherwise. Thresholds per-fold
  train-derived (F4-train cut: §2.2). Execution PR-3, DD guard PR-4 (never
  fired in OOS), 10 bps RT gate rung.
- Train rank #4/#5 of 36 (rank key 0.96) — not the top train pick.
- Pooled OOS: Sharpe 2.3763/2.3761, net +7.56%/+15.50%, 30 trades,
  92/1344 OOS bars in position (6.8%), F3 = zero trades (funding never reached
  the positive cut Feb–Mar 2026).
- Gate: PASSES beats_flat, beats_hodl, shuffle-null (2.376 > null_p95 2.259,
  p ≈ 0.036 — within 36-variant selection noise), cost ladder.
  **FAILS top-5 removal: top5_net −1.03%/−2.13%** (exit-cost-credited:
  −0.91%/−1.88%). The 5 removed trades (size-0.5 pnl: F1 2025-11-20 +2.76%,
  F2 2025-12-29 +1.53%, F4 2026-06-01 +1.50%, F4 2026-05-27 +1.43%,
  F1 2025-11-04 +1.17%; identical trade set at size 1.0 at ~2× pnl; all
  shorts, 8–32h holds) carry >100% of the OOS gain (114.8%/116.2%); remaining 25 trades
  net −1.03%; hit rate 50%, median trade +3 bp.
- Fragility (Lane 3): flips to full PASS under un-registered q=(0.25,0.75) or
  top-N=3; collapses to a 2-clause fail (Sharpe 1.33 < null_p95) at fold
  boundaries −14d. A fails-only-top5 near-miss arises in ~1 of 3 fully-null
  sweeps of this design (P ≈ 32% over ~26 effective hypotheses).
- Lane 2 calibration: its shortfall is < ~5 bps/bar of true per-bar edge; the
  top-5 clause is the gate's binding detection margin for this concentrated
  shape.
- If the hypothesis family (fade positive funding extremes) is pursued
  post-contest, it requires a NEW pre-registration on data after 2026-06-09;
  q=(0.25,0.75) and N=3 cannot be adopted retroactively.

---

## 5. R-NAME: skill folder

**`skills/btc-funding-regime-monitor/`**

Family-true: it is a monitor (not a strategy), of BTC funding-derived regimes.
No momentum/fade/winner prejudice in the name; "derivatives-regime" was
rejected as overclaiming (the frozen classifier consumes funding only — OI/LS
are not in it), as was any name carrying the failed candidate's direction.

---

## 6. Numbers block (report headline inputs)

- **honest_N (pooled-OOS regime episodes, R2):** TA = 250, TB = 105,
  **TC = 225** (52/48/60/65 by fold); embargo E = 42 bars for all three
  (median episode 4 bars → floor binds). Caveat: taxonomy-level counts; the
  failed candidate's active sample is 30 trades / 92 bars / 3 of 4 folds.
- **R3 disclosure triple:** variants swept = **36** · gate passes = **0** ·
  expected null-clause pass-rate = **0.0500**. Supplementary calibration:
  full-gate pass rate of the top train-ranked variant over 200 null draws =
  **1.5%**; observed null-clause passers 2/36 vs 1.8 expected (one effective
  hypothesis); fails-only-top5 near-miss rate under the global null ≈ 1.5%
  per variant (~1-in-3 sweeps).
- **HODL pooled-OOS (benchmark):** Sharpe **−2.0963135337153442**, net
  **−0.45901858600522905** — identical at 5/10/20 bps (single entry fill at
  window start, outside every OOS segment). The beats_hodl clause was
  near-vacuous this window (98% null pass rate) — disclose in the report.
- **Near-miss summary:** §4.
- **Gate power statement (Lane 2):** on the real panel at 10 bps RT, the
  unmodified pre-registered pipeline passes a planted regime-conditional edge
  of **≥ 10 bps/bar robustly** (train rank #1, all five clauses with margin)
  and **5 bps/bar marginally** (single seed; treat as edge of detectability);
  the episode-shuffle null is conservative against real edges (biases to false
  negatives only); R3 calibration is stable in planted worlds (5.0% / 1.5–2.0%).
  The null result is evidence about the data, not the machinery.

---

## 7. Sign-off

**Freeze approved by critic lane.**
Frozen: R-NULL outcome (no Winner) · taxonomy TC with F4-train
`funding_hi_abs = 8.385600000000002e-05` and enum
{pos-mild, pos-extreme, neg-mild, neg-extreme} · Skill shape = regime monitor
per §3 amendments 1–6 · folder `skills/btc-funding-regime-monitor/`.
Any post-freeze change to thresholds, enum, taxonomy, or the monitor's emitted
schema triggers full re-validation (G7).
