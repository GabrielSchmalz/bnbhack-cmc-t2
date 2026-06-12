# W-freeze — family-locked-Survivors branch (registration §11, Phase-3 → Phase-4 handoff)

Date: 2026-06-11 · Author: critic lane (freeze decision-of-record for the
widening outcome; the Phase-4 re-authoring executes this document)
Inputs of record: `docs/plans/2026-06-10-widening-preregistration.md`
(frozen registration, esp. §5–§8, §11, §13),
`artifacts/w/sweep_results_w.json` (committed `74e6417`),
`artifacts/w/structural_feasibility.json` (committed `6df12bb`,
**pre-OOS-contact** — commit order verified by lane W-C),
`docs/report/adversarial/w_lane1_reproduction.md` (lane W-A),
`w_lane2_launch_note.md` (lane W-B, readout PENDING),
`w_lane3_r3_audit.md` (lane W-C), the frozen floor's `docs/FREEZE.md` +
`docs/report/REPORT.md`, CONTEXT.md vocabulary. HEAD at decision: `3ff8f27`.

---

## 1. Verdict on the W-sweep outcome: THE §11 "ONLY FAMILY-LOCKED SURVIVORS" BRANCH HOLDS — NO WINNER

**4 of 183 evaluated Variants passed the 8-clause gate; all four are one
effective hypothesis; all four are family-locked; `ship_eligible_count = 0`.**
The four passers are
`P-BTC-DIR-TD-D1-fade_extremes_graded_sym-{0.5, 1.0, 0.5-ts6, 1.0-ts6}` —
four dressings (size × time-stop) of the single structure (T-D, D1) on
P-BTC. Sharpe is nearly size-invariant (0.6769/0.6791 plain,
0.8108/0.8110 ts6): under the registered §8 convention this is **one
effective hypothesis, not four successes**.

**The lock held, and it held substantively:**

- **Layer 1** (pure-map predicate) correctly does not fire — D1 is
  symmetric (long on negative-funding extremes). All 8 annex variants DO
  satisfy layer 1 (test-pinned; lane W-C recomputation) — the standing
  reason A1/A2 can never ship regardless of outcome.
- **Layer 2** (extremity-neutralized twin, the binding test): every twin
  goes **net-negative** — twin net −3.8%/−8.3% (plain), **−4.7%/−9.8%**
  (ts6); twin Sharpe −0.159/−0.230, below even the null q95
  (0.287/0.296). Both §6 lock conditions fail independently. Locked.
- **Layer 3** (share backstop): the short-leg on reference
  positive-extremity bars carries **88.3–92.4%** of pooled-OOS arithmetic
  PnL (0.5-ts6: leg 0.26233 of total 0.28389 = **0.9241**) vs the 0.5
  majority line. Locked.

**Lane W-A reproduced every compared number bit-for-bit**: max |diff| =
0.0 over **731 scalars** (demanded ≤ 1e-9) — train Sharpes, rank keys,
per-fold and pooled OOS at every cost rung, top-5/top-K removals, fold
contributions, era splits, crash-day counts, feasibility projections,
panel globals; all 42 per-fold cuts re-derived from boundary-truncated
raw CSVs with zero lab imports (R1 proven); all eight stored null
quantiles regenerated bit-identically from the registered seed map at
full D = 1000; all three lock layers independently rebuilt and confirmed.
Lane W-A's adversarial reading is adopted verbatim: the symmetric map is,
on this panel, "economically the locked fade-positive-extremes hypothesis
wearing its registered mirror as a coat; the twin instrument caught it
exactly as designed."

**The pure-fade annex (A1/A2, 8 variants) failed the gate outright** —
every one of the 8 fails at least one concentration clause: all four A1
dressings fail top5 AND topK (top5 net −0.0344 … −0.1851) plus
min_active_sample; A2-1.0 fails top5/topK; A2-{0.5,1.0,1.0-ts6} fail
topK and/or the fold-concentration sub-part of min_active_sample
(A2-0.5: max fold contribution 0.5374 > 0.5); the closest annex miss,
A2-0.5-ts6, fails only topk_pass (topk_net −0.0538).

**Both directions of the lane W-C statistics, stated honestly:**

- **One effective full-gate pass is unsurprising under the null.**
  Applying the per-cell calibration rates to the 82 panel-level
  structures: point estimates give P(≥1 effective pass somewhere) ≈
  **22%**; replacing the nine 0/200 cells by their Clopper-Pearson 95%
  upper bound (1.83%) gives ≈ **72%**; a blanket 2% gives ≈ **81%**. A
  single effective pass is NOT evidence of shippable signal. (Caveat
  honored both ways: the calibration slot landed on a risk ladder in all
  13 cells, so ≤ 2% is not a strict bound on the D1 shape's false-pass
  rate — §3 amendment 3.)
- **AND the clause-6 cluster is exactly the registered H8 contamination
  signature.** Observed clause-6 (null_p99) exceedance among the 175
  gated: **8 nominal = 3 effective** (D1 on T-D; E2 `follow_unwind_sym`
  and E3 `fade_pos_long_neg` on T-E) vs **1.75 expected nominal / 0.32
  effective** — all P-BTC, all funding-fade-flavored (E3 is the
  axis-collapse control that ignores OI, i.e. a pure symmetric funding
  fade; E2 shorts positive funding on the unwind subset). The defensible
  surprise band runs from ≈ 27.5% (cluster as one event) down to ≈ 0.4%
  (treating the three correlated structures as independent, which they
  are not). E2-{1.0,0.5} and E3-0.5 failed the full gate on topk_pass
  alone; E3-1.0 failed top5/ladder/min_active_sample/topk.

**Why the locked verdict is substantive, not technical** — three
independent quarantine confirmations beyond the lock arithmetic:

1. **The failed transfer.** The same D1 map fails **7 of 8 clauses** in
   every dressing on BOTH other panels, with negative nets: P-ETH net@10
   −1.0% … −53.6% (Sharpe −0.649 … +0.016 vs null q95 0.363–0.413);
   P-SOL net@10 −41.7% … −45.2% (Sharpe −0.690 … −0.169 vs q95
   0.367–0.476). Under §8's own framing, disagreement across correlated
   panels is evidence against a cross-asset mechanism and consistent
   with a BTC-specific burned-signal echo.
2. **The era split.** The PnL lives in the replay-contaminated
   pre-2025-04 era (net +25.8% … +67.0% pre vs +4.3% … +9.6% post; §10
   item 1 — the H8 deep replay burned 2021-22 fade-positive-extremes PnL
   into exactly this panel-era for exactly this family). The
   frozen-window-overlap era fails concentration on its own: top5_pass
   AND topk_pass fail post-era for all four passers (the mechanical
   57-trades-< 60 min_active_sample fail is disclosed as mechanical).
3. **The economic profile.** Max fold contribution 0.42–0.49 (cap 0.50),
   driven by F05 — the 2022-Q2 Luna quarter; 7 of each passer's 381–405
   OOS trades overlap the five published near-miss crash days. Crash-quarter shorts
   plus carry: the profile the lock exists to quarantine.

**Frozen outcome: NO Winner. The §11 locked-Survivors branch ships** —
the upgraded monitor + the locked candidates published in the
falsification chapter (with the §6 layer that locked each) + the active
forward registration. The story, verbatim from the registration: "the
gate found something it refuses to ship until its own published protocol
is satisfiable."

Recorded, non-blocking (lane W-A): two semantic determinations — the
time-stop cap-bar immediate-re-entry reading (text-consistent and
passer-UNfavorable) and the sequential guard/time-stop composition
(train-only effect, rank-key 3rd decimal) — must be test-pinned before
any future re-run of this family.

---

## 2. The wider null: 31 of 32 effective hypotheses cleared nothing on any panel

Registered denominator: 175 gated Variants (73/51/51 across
P-BTC/P-ETH/P-SOL) ≈ **32 effective hypotheses** (T-D 8, T-E 7, T-F 6,
T-G 6, T-H 5); 8 locked-annex Variants reported separately; 24 forward
Variants recorded, never evaluated; total evaluated 183. **31 of the 32
effective hypotheses produced zero full-gate passes on any panel, in any
dressing** (clause-level exceedances disclosed in §1; the only full-gate
passer is the quarantined family's symmetric sibling).

**Effective denominator = 110**, after the 65 structural-feasibility
flags. Cross-reference: `artifacts/w/structural_feasibility.json` was
committed at `6df12bb` BEFORE the sweep artifact (`74e6417`) — train-side
flags, pre-OOS in the strong order; lane W-C verified 183/183 ids and
bit-identical flags between the standalone artifact and the sweep's
embedded copies. Flag breakdown (recomputed from the committed artifact):
the **entire T-F taxonomy — 30/30 variants on all panels** (F&G history
starts 2023-06-29 ⇒ 11/21 covered folds ⇒ projected trades < 60), T-G 18
(G1/G3 12 + ladders 6), T-H 10 (H2/H3 4 + ladders 6), T-D R2 ladders 6,
T-E L1 1. The §5 expectation prose ("all G1/G3/L1-type") under-predicted
this set; the report must say so rather than echo it (lane W-C I3). None
of the 4 passers is flagged (projected trades 403.8/518.7 ≫ 60).

Honest-N (pooled-OOS regime episodes per (panel, taxonomy), from the
artifact; embargo E = 42 in all 13 cells — the floor binds everywhere):

| panel | T-D | T-E | T-F | T-G | T-H |
|---|---|---|---|---|---|
| P-BTC (21 folds) | **1,502** | 1,754 | 292 (11 covered folds) | 871 | 915 |
| P-ETH (21 folds) | 1,587 | — | 342 (11) | 884 | 940 |
| P-SOL (19 folds) | 1,941 | — | 383 (11) | 1,036 | 1,092 |

P-BTC/T-D's 1,502 pooled-OOS episodes vs the floor's TC = 225: the
widened null is evaluated on ~6.7× the floor's episode count, three
assets, ~5–6-year multi-regime OOS, under a strictly harder gate
(8 clauses vs 5). Cumulative-contact disclosure carried forward (§8): 36
frozen Variants (≈ 26 effective hypotheses) were already evaluated on the
overlapping 2025-04 → 2026-06 window, plus the lane-3 perturbation grid
and the H8 deep replay.

---

## 3. Confirmed ship shape: regime MONITOR, frozen floor classifier UNTOUCHED, upgraded per §11

**The Skill remains a regime monitor.** The W-sweep validated nothing
shippable, so the floor's frozen classifier stands untouched: taxonomy
**TC** (funding-sign × extremity), threshold
`funding_hi_abs = 8.385600000000002e-05` (F4-train), enum
`pos-mild · pos-extreme · neg-mild · neg-extreme`, emission schema per
floor FREEZE §2–§3 — all UNCHANGED from the floor freeze. No G7
re-validation is triggered.

**Upgrades, per the registration's §11 every-outcome commitments:**
≥ 7 verified CMC tools with honest roles (classifier inputs are only
Gate-0-verified Features; derivatives/narratives/macro-events appear as
labeled display context only), F&G CMC-end-to-end, and the D1/D3 basis
disclosures in every emission.

**Amendments (binding on the Phase-4 re-authoring):**

1. **The W chapter is added to REPORT.md as falsification evidence.** The
   locked candidates are published in full — rule surface, gate numbers,
   and the lock-layer numbers (twin nets/Sharpes, layer-3 shares, the
   layer that locked each) — never as tradable specs, each carrying
   `"validated": false`.
2. **The forward registration is stated in SKILL.md provenance and in
   REPORT**: 24 Variants (A1/A2 × 2 sizes × time-stop {none, 6} × 3
   assets), OOS = 2026-06-11 00:00 UTC onward, quarterly folds, this
   cycle's 8-clause gate; evaluation when ≥ 4 post-freeze quarterly folds
   exist (earliest 2027-07-01); any earlier readout is underpowered and
   non-shippable. This cycle reports the registration itself, not a
   result.
3. **Lane W-C report-stage items I1/I2 must appear in the R3
   disclosure.** I1: `r3.swept.observed_null_p95_rate /
   observed_null_p99_rate` (0.05/0.01) are draw-bookkeeping identities,
   NEVER quotable as observed clause rates — the real observed rates are
   clause-3 **23/175 = 13.1%** and clause-6 **8/175 = 4.6%** (3 effective
   vs 0.32 expected). I2: the clause-6 bootstrap CIs (cell pooled q99,
   D = 1000) and the §8 pairwise pooled-OOS return correlations for the
   transfer table come from the companion evidence file
   `docs/report/w_r3_supplement.md` (in production in a parallel lane) —
   the R3 disclosure cites it; the §8 "indicative calibration, never the
   headline" framing is kept verbatim (I4).
4. **Lane W-A marginality disclosures are quoted wherever the passers are
   described**: 1.0-ts6's clause-8 margin is
   **topk_net = +0.000608205257158767** — six basis points of net after
   removing its K = 9 best trades (0.5-ts6: +0.0096; plain sizes +0.1040
   / +0.0276); max fold concentration **0.4898** (1.0-ts6) / 0.4713
   (0.5-ts6) vs the 0.50 fail line, driven by F05, the 2022-Q2 Luna
   quarter.
5. **The lane W-B power statement section ships only after the
   `bnbhack-wcal` readout.** Status at this freeze: **PENDING** — the
   calibration unit (9 cells: 3 panels × rungs 5/10/25 bps/bar) was
   launched 2026-06-11 07:14:04 UTC and is still running; no readout
   exists; the readout protocol is pinned in `w_lane2_launch_note.md` §5.
   A placeholder power statement is FORBIDDEN in the final submission;
   the readout is a **Phase-4 completion gate**.
   *[Discharged 2026-06-12 — additive note, freeze text above unchanged:
   the readout landed against the §5 protocol
   (`docs/report/adversarial/w_lane2_power_readout.md`, 9/9 cells) and
   the power slots in REPORT §7.5, README, SKILL.md and SUBMISSION are
   filled from it. Headline: P-BTC ≥ 5 bps/bar robust; P-ETH/P-SOL
   25 bps/bar marginal only; one disclosed lock-scope defect finding
   (planted-world out-of-family ship-eligible escapee, P-ETH 10 bps).]*
6. **Monitor emission schema, threshold, and enum are unchanged from
   floor FREEZE §2–§3 amendments 1–6** (train-stat provenance, no
   active_ruleset in runtime emissions, failed-candidate publication
   rules, active-sample quoting rule, Band framing, funding-basis
   disclaimer). No re-validation is triggered; any post-freeze change to
   them still triggers full re-validation (G7).
7. **The README/SUBMISSION headline becomes the two-layer story**: floor
   null (0/36) → widened search (175 gated Variants, 3 panels,
   ~5–6-year OOS, 8-clause gate) → one effective passer, quarantined by
   pre-registered locks → wider null everywhere else.

---

## 4. Numbers block (report headline inputs — all values from `74e6417` / lane reports)

- **R3 triple (W-sweep):** variants evaluated = **183** (175 gated + 8
  annex; 24 forward recorded-not-evaluated) · gate passes = **4 = 1
  effective hypothesis** (family-locked; `ship_eligible_count = 0`) ·
  expected clause-6 null pass-rate = **0.01** ⇒ 1.75 expected nominal
  across 175 (0.32 effective across 32); observed **8 nominal / 3
  effective** clause-6, **23/175 = 13.1%** clause-3.
- **Per-cell full-gate calibration (200 common draws on the cell's top
  train-ranked GATED Variant — a risk ladder in all 13 cells, I4):**
  P-BTC/TD 0.0 · P-BTC/TE 0.005 · P-BTC/TF 0.0 · P-BTC/TG 0.01 ·
  P-BTC/TH 0.0 · P-ETH/TD 0.0 · P-ETH/TF 0.0 · P-ETH/TG 0.02 ·
  P-ETH/TH 0.0 · P-SOL/TD 0.0 · P-SOL/TF 0.0 · P-SOL/TG 0.005 ·
  P-SOL/TH 0.0 (MC SE ≤ 0.0099 everywhere; nine cells 0/200).
- **Honest-N table:** §2 above (headline: P-BTC/T-D **1,502** pooled-OOS
  episodes vs the floor's 225; E = 42 in all 13 cells).
- **The four passers (pooled OOS @10 bps, guarded):**

| dressing | Sharpe | net | trades | nz bars | top5 net | topK net (K) | max fold contrib | null q95 / q99 |
|---|---|---|---|---|---|---|---|---|
| 0.5 | 0.6769 | +39.21% | 381 | 4,492 | +0.1924 | +0.1040 (8) | 0.4202 | 0.2868 / 0.5226 |
| 1.0 | 0.6791 (unguarded 0.6770) | +83.09% | 384 | 4,482 | +0.2005 | +0.0276 (8) | 0.4326 | 0.2868 / 0.5226 |
| 0.5-ts6 | 0.8108 | +31.15% | 405 | 1,541 | +0.1056 | +0.0096 (9) | 0.4713 | 0.2959 / 0.5709 |
| 1.0-ts6 | 0.8110 | +67.71% | 405 | 1,541 | +0.1986 | **+0.000608** (9) | **0.4898** | 0.2958 / 0.5710 |

- **Lock numbers:** layer-2 twin net/Sharpe — 0.5: −0.0377/−0.1593 ·
  1.0: −0.0826/−0.1593 · 0.5-ts6: −0.0468/−0.2302 · 1.0-ts6:
  −0.0982/−0.2302 (every twin below null q95 AND net-negative); layer-3
  locked-leg shares 0.8832 / 0.8845 / 0.9241 / 0.9241.
- **Era split (2025-04-01; pre 8,094 / post 2,400 OOS bars):** nets pre →
  post — 0.5: +32.85% → +4.79% (324/57 trades) · 1.0: +66.98% → +9.65%
  (327/57) · 0.5-ts6: +25.77% → +4.28% (348/57) · 1.0-ts6: +54.41% →
  +8.62% (348/57). Era clause status (per the artifact; lane W-A verified
  64/64 booleans): pre-era — 0.5 passes all 8; 0.5-ts6 and 1.0-ts6 fail
  only min_active_sample; 1.0 fails min_active_sample + topk_pass (in
  all three, the failing min_active_sample sub-part is the
  fold-concentration rule on era-restricted nets, max contribution
  0.51–0.58 per lane W-C recomputation). Post-era — ALL FOUR fail
  top5_pass AND topk_pass (plus min_active_sample, partly mechanical:
  57 trades < 60).
- **Crash-day coincidence (identical for all four):** 7 trades overlap
  the five published near-miss crash-day groups — 1 / 1 / 1 / 3 / 1
  (2025-11-04, 2025-11-20, 2025-12-29, 2026-05-27/28, 2026-06-01/02).
- **Transfer failures (same D1 map, all dressings, 7 of 8 clauses fail —
  only min_active_sample passes):** P-ETH net@10 −1.04% … −53.64%,
  Sharpe −0.649 … +0.016 vs q95 0.363–0.413, 401–424 trades; P-SOL
  net@10 −41.66% … −45.23%, Sharpe −0.690 … −0.169 vs q95 0.367–0.476,
  601–620 trades. Pairwise pooled-OOS return correlations: report-stage,
  from `w_r3_supplement.md` (amendment 3).
- **Benchmarks (HODL pooled-OOS, rung-invariant):** P-BTC Sharpe
  0.10295621564420757 / net −0.3765801752030906 · P-ETH
  0.22331754249315747 / −0.4153609785298228 · P-SOL 0.2839134924454298 /
  −0.574538690194161.
- **Null context (lane W-A):** null means are negative (≈ −0.30 plain /
  −0.45 ts6); each passer's unguarded Sharpe sits at the 99.6th–99.8th
  percentile of its own 1000-draw null; clause-6 margins 0.154 (plain) /
  0.240 (ts6) in annualized-Sharpe units — whether they sit inside the
  cell's bootstrap q99 CI is discharged by the supplement (amendment 3).
- **Gate power statement (lane W-B):** **PENDING** — `bnbhack-wcal`
  running since 2026-06-11 07:14:04 UTC; this slot is intentionally
  empty and is a Phase-4 completion gate (amendment 5). No number may be
  written here except from the readout against the launch note's §5
  protocol.
  *[2026-06-12, additive: readout landed — P-BTC ≥ 5 bps/bar robust
  (aligned family rank #1 at every rung), P-ETH/P-SOL 25 bps/bar
  marginal only; see `docs/report/adversarial/w_lane2_power_readout.md`.]*

---

## 5. Sign-off

**W-freeze approved by critic lane.**
Frozen: the §11 family-locked branch (no Winner; `ship_eligible_count =
0`; the locked candidates publish as falsification evidence with their
lock layers, `"validated": false`) · the wider null over the effective
denominator 110 (31/32 effective hypotheses cleared nothing on any
panel) · Skill shape = regime monitor with the floor's TC classifier,
threshold, enum, and emission schema untouched, upgraded per §11 ·
amendments 1–7 binding on the Phase-4 re-authoring · the lane W-B power
readout as a Phase-4 completion gate. Any post-freeze change to the
monitor's frozen surface triggers full re-validation (G7); any change to
a W verdict (gate, lock, era, R3) requires reopening through the
adversarial lanes — never an edit to this document.
