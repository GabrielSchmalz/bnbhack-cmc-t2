# Lane W-C — R3 / era-split / null-mechanics audit (adversarial)

Date: 2026-06-11 · Auditor: adversarial lane W-C (separate lane, never
self-approving) · Inputs of record: `artifacts/w/sweep_results_w.json`
(committed `74e6417`), `artifacts/w/structural_feasibility.json`
(committed `6df12bb`, **pre-OOS-contact** — commit order verified),
binding registration `docs/plans/2026-06-10-widening-preregistration.md`
(§5, §6, §7, §8, §13). Method: read-only artifact + registration
cross-checks, light recomputation via lab imports (`enumerate_all_w`,
`layer1_pure_map_locked`, arithmetic identities). No OOS row was
re-evaluated; no production sweep was run. Frozen floor untouched.

Pinned tests at HEAD: `test_variants_w / test_gate_w / test_lock_w /
test_hooks_w` (94 passed) and `test_sweep_w / test_panels_w` (50 passed).

**Verdict: r3 bookkeeping is sound at the artifact level — no integrity
violation found. Five issues (2 medium, 2 low, 1 nit), all of the
"report-stage disclosure trap" kind, listed in §7.**

---

## 1. Denominators — CLEAN

| check | registered (§5/§8) | artifact | match |
|---|---|---|---|
| gated N | 175 (73/51/51) | `r3.registered.n_gated` = 175; per-cell counts 24/22/10/9/8 (BTC), 24/10/9/8 (ETH, SOL) recomputed from the variant list | ✓ |
| locked annex | 8 | `n_annex` = 8; exactly the A1/A2 × size × ts ids, `annex=true` | ✓ |
| forward record | 24, never evaluated | `n_forward_recorded_not_evaluated` = 24; ids byte-equal to `enumerate_forward_registration()`; none appear in `variants` | ✓ |
| total evaluated | 183 | `swept.n_variants` = 183, no duplicate ids | ✓ |
| effective hypotheses | ≈ 32 (8/7/6/6/5) | `effective_hypotheses` = 32; map/ladder structure count recomputed = 32 | ✓ |
| expected clause-6 | 0.01 ⇒ 1.75 | `expected_clause6_rate` = 0.01, `expected_clause6_null_passers` = 1.75 | ✓ |

`enumerate_all_w()` vs the artifact: **id sets identical (183/183),
annex flags identical, panel/taxonomy/time-stop/vol-band attributes
identical.** The artifact list is ordered by the §7 rank key (rank_key
desc → mean train max-DD → id), not enumeration order — presentation
only, verified to be a pure permutation (note N1, §7).

Globals match §7 mechanics: D = 1000 common draws, gate rung 10 bps,
ladder {5, 10, 20}, seed map `[17, panel, taxonomy, fold]` with
P-BTC/ETH/SOL = 0/1/2 and T-D…T-H = 0…4, index tables printed. Embargo
table printed: **E = 42 in all 13 cells** — the floor binds everywhere,
so §1's "disclose any cell where the floor does not bind" clause is
vacuously satisfied.

## 2. Null-rate bookkeeping — CLEAN numbers, one naming trap (I1)

- `observed_null_p95_rate = 0.04999…` / `observed_null_p99_rate =
  0.00999…` are **by-construction identities, not empirical
  calibration**: per variant the driver records the fraction of its own
  1000 null draws strictly above its own q95/q99 (numpy linear
  interpolation ⇒ exactly 50/1000 and 10/1000 absent ties), then means
  over 183 variants. Recomputed: `mean([0.05]*183)` reproduces the
  stored float bit-for-bit (likewise 0.01). What these fields *do*
  verify: no degenerate/tied null cell anywhere (a tie-heavy cell would
  deviate from 0.05). What they must NOT be quoted as: "observed
  clause-3/6 pass rate matched expectation" — see I1.
- The **real** observed clause rates among the 175 gated variants
  (recomputed from per-variant `reasons`, not stored in the r3 block):
  clause 3 (`null_pass`) **23/175 = 13.1%**, clause 6 (`null_p99`)
  **8/175 = 4.6%** vs the registered 1% ⇒ **8 observed vs 1.75 expected
  nominal clause-6 passers** (annex: 2/8, both A2-ts6 dressings).
- Per-cell full-gate calibration: 13 cells ✓; draws = 200 ✓ (registered
  ≥ 200, the common-draw prefix); MC SE = sqrt(p(1−p)/200) verified
  exact in all 13 cells; rates 0.0 (9 cells), 0.005 (BTC/TE, SOL/TG),
  0.01 (BTC/TG), 0.02 (ETH/TG) — all ≤ 2%.
- **Calibration slot per §13.29(d): verified in all 13 cells** — the
  recorded `variant_id` equals the cell's top train-ranked GATED variant
  under the full §7 tiebreak (rank_key desc → train max-DD → id),
  recomputed from the artifact. In P-BTC/TD the top variant including
  the annex is the same ladder, so the gated-only restriction was not
  even load-bearing this run. Note: the top-ranked variant is a **risk
  ladder in all 13 cells**, so the full-gate false-pass rates were
  measured on long-only ladder shapes only — see I4.

## 3. The 4 gate passes — exactly one effective hypothesis; honest surprise arithmetic

The 4 passers are `P-BTC-DIR-TD-D1-fade_extremes_graded_sym-{0.5,1.0}[-ts6]`
— **all four dressings of the single structure (T-D, D1) on P-BTC**
(sizes {0.5, 1.0} × time-stop {none, 6}; vol-band does not dress
direction maps). Under the §8 convention (collapse size/time-stop/
vol-band/panel) this is **1 effective hypothesis**. No other variant,
gated or annex, passed the full gate (gate_pass_count = 4 recomputed ✓).

Two readouts the report must keep distinct:

**(a) Clause-6-only (the registered binding expectation).** Observed
**8 nominal / 3 effective** (D1 on TD; E2 `follow_unwind_sym` and E3
`fade_pos_long_neg` on TE — all P-BTC) vs expected 1.75 nominal / 0.32
effective. Naive tails: P(≥8 | Bin(175, 0.01)) ≈ 0.04% and
P(≥3 | Bin(32, 0.01)) ≈ 0.4%, but both overstate surprise — dressings
are near-duplicates and the three structures are mutually correlated
(same panel, overlapping bars, all funding-fade-flavored: E3 is the
axis-collapse control that *ignores OI*, i.e. a pure symmetric funding
fade; E2 shorts positive funding on the unwind subset). The defensible
band runs from P(≥1 effective | 32 × 1%) ≈ 27.5% (treat the cluster as
one event) down to ≈ 0.4% (treat the three as independent, which they
are not). Honest summary: **more clause-6 exceedance than a clean iid
null expects, concentrated in exactly one correlated cluster — the
fade-positive-funding direction on BTC, i.e. the §6-quarantined
hypothesis family's signature, not three independent discoveries.**
Context: E2-1.0/-0.5 and E3-0.5 failed the full gate on `topk_pass`
alone (E2-1.0: net@10 +254%, Sharpe 0.871 vs q99 0.568 — killed by
top-K trade removal); E3-1.0 failed top5/ladder/min_active_sample/topk.

**(b) Full gate (indicative calibration, never the headline — §8
verbatim).** 1 effective passer observed. Per-cell rates applied to the
82 panel-level structures: point estimates give λ ≈ 0.245 ⇒ P(≥1) ≈
22%; replacing the nine 0/200 cells by their Clopper-Pearson 95% upper
bound (1.83%) gives λ ≈ 1.29 ⇒ P(≥1) ≈ 72%; a blanket 2% gives P(≥1) ≈
81%. The observed pass sits in P-BTC/TD, whose own measured rate is
0/200 (≤ 1.83% at 95%; 8 structures ⇒ P(≥1 in-cell) ≤ 13.7%). **Both
directions, honestly:** (i) under any defensible reading of the
calibration, ≥ 1 effective full-gate pass somewhere was *likely-to-
unremarkable* under the null — a single effective pass is NOT evidence
of shippable signal; (ii) conversely the in-cell point estimate was 0,
and 4/4 dressings passing plus the clause-6 clustering is more
coherence than generic noise — but that coherence is precisely the
registered contamination mechanism (§10 item 1: the H8 deep replay
burned 2021-22 fade-positive-extremes PnL into this panel), and the §6
lock attributes the PnL accordingly (layer-3 leg share 0.88–0.92,
layer-2 twin Sharpe collapses to −0.16/−0.23, below even null q95).
Caveat either way: the per-cell ≤ 2% figures were measured on ladder
shapes (I4) and cannot be quoted as a strict bound on the D1 shape's
false-pass rate. **`ship_eligible_count = 0` is the only defensible
readout; the wider-null narrative stands.**

## 4. Era-split, crash-day, transfer — CLEAN, with required framing

Definitions match §8 exactly: split at **2025-04-01**; crash-day groups
2025-11-04, 2025-11-20, 2025-12-29, 2026-05-27/28, 2026-06-01/02;
coincidence = interval overlap of [entry_ts, exit_ts] with the UTC day
(§13.29(c)); era clause status against FULL pooled-OOS null quantiles
with the §13.29(b) note string present in every era block.

Arithmetic identities verified for all 4 passers: pre+post OOS bars =
10,494 = pooled; pre+post trades = pooled trade count;
(1+net_pre)(1+net_post)−1 = pooled net@10 to 6 dp; era nets recomputed
independently from the per-fold `fold_nets` (folds partition cleanly at
the 2025-04-01 quarterly boundary, F01–F16 pre / F17–F21 post) match
the era blocks exactly.

Substance the report must carry, with mechanics separated from
evidence:

- **The PnL lives in the pre-2025-04 era** (net +25.8%…+67.0% pre vs
  +4.3%…+9.7% post) — for THIS family that is the evaluation-
  contaminated 2021-22 window (§10 item 1). The §8 "pass disappears in
  the pre-era" framing does not apply; the opposite framing does: the
  pass is *driven* by the contaminated era.
- Pre-era clause status: the 0.5/no-ts dressing passes **all 8 clauses**
  on pre-era evidence; the other three fail only `min_active_sample`,
  and recomputation shows the failing sub-part is the fold-concentration
  rule on era-restricted nets (max contribution 0.51–0.58 > 0.5).
- Post-era failures are partly **mechanical**: 57 trades < the 60-trade
  floor (a full-sample bar applied to a 5-fold sub-era). The informative
  post-era failures are `top5_pass`/`topk_pass` — the frozen-window-era
  PnL is tail-concentrated.
- Crash-day coincidence: identical for all 4 passers — 7 of ~405 OOS
  trades overlap the five published near-miss crash days (1/1/1/3/1).
- **Transfer (correlation-discounted disclosure):** the same D1 map
  fails on both other panels, in all dressings, failing **7 of 8
  clauses** everywhere (only `min_active_sample` passes). P-ETH: net@10
  −1.0%…−53.6%, Sharpe −0.65…+0.02 vs null q95 0.36–0.41. P-SOL: net@10
  −41.7%…−45.2%, Sharpe −0.69…−0.17 vs q95 0.37–0.48. Under §8's own
  framing (cross-panel agreement expected under both signal and null
  for correlated assets), *disagreement* across correlated panels is
  evidence against a cross-asset mechanism and consistent with a
  BTC-specific burned-signal echo. The §8 pairwise pooled-OOS return
  correlations are not in the artifact and must be computed at report
  stage (I2b).

## 5. Structural-feasibility flags — CLEAN data, under-scoped §5 prose (I3)

- 65 flagged, **all gated, none annex** ⇒ effective denominator
  **175 − 65 = 110** (the §8 wider-null prose must use 110; flagged-and-
  passing is vacuously absent — none of the 4 passers is flagged;
  projected trades 404–519 ≫ 60).
- Sweep-embedded flags vs the pre-OOS committed
  `structural_feasibility.json`: **183/183 ids present, flags identical,
  projected trade counts identical to < 1e-9** — and the standalone
  artifact was committed at `6df12bb`, before the sweep artifact
  (`74e6417`), satisfying §5's commit-the-flags-with-the-sweep
  requirement in the strong (pre-OOS) order.
- §5 predicted "all G1/G3/L1-type" infeasibility. The actual flag set is
  much broader: G1/G3 + TG L1/L3 (24) as predicted, **plus the ENTIRE
  T-F taxonomy — all 30 variants on all panels** (F&G history starts
  2023-06-29 ⇒ only 11/21 covered folds ⇒ projected trades < 60), plus
  TH ladders (6) and H2/H3 on one panel (4), TD R2 ladders ±vb (6),
  TE L1 (1). Not a registration violation — the flags come from the
  registered train-side mechanism and were committed pre-OOS — but the
  §5 *expectation prose* under-predicted, and the R3 narrative must say
  so explicitly rather than echo "G1/G3/L1-type" (I3). The 90-day
  coverage floor plus the 60-trade floor structurally voided T-F as
  registered; honest-N corroborates (T-F honest_N 292–383 vs 871–1941
  elsewhere; covered folds 11 in all three T-F cells).

## 6. Lock bookkeeping — CLEAN

- All 4 passers: `lock.locked = true`, `locked_layers = ["layer2",
  "layer3"]`, `layer1_locked = false` (D1 is symmetric — long on
  negative-funding extremes — so the layer-1 predicate correctly does
  not fire; recomputed via `layer1_pure_map_locked`: **no gated variant
  satisfies layer 1; all 8 annex variants do**, matching §6's "A1/A2
  satisfy it; the registered symmetric maps do not").
- Lock fields complete per §6: layer 2 carries twin_net, twin_sharpe,
  the q95 of the variant's own common draws, twin_passes, locked
  (twin_net −0.038…−0.098 < 0 AND twin_sharpe −0.159/−0.230 < q95
  0.287/0.296 ⇒ locked, both §6 conditions failed independently);
  layer 3 carries total, leg_sum, evaluated, share, locked (shares
  0.883–0.924 > 0.5 strict majority). `family_locked_count = 4` ✓.
- `ship_eligible = false` on all 183 records; `ship_eligible_count = 0`
  ✓ (passers locked; annex never eligible by construction).
- §6 scope honored in both directions: lock evaluated for **every**
  gate-passing variant (4/4) and for **no** non-passer — all 179
  non-passers have `lock = era_split = crash_day_trades = null`,
  `ship_eligible = false`. The annex's layer-1 status is therefore not
  stored in the artifact (no annex variant passed the gate); it is
  test-pinned and reproduced here from the lab — the falsification
  chapter should cite layer 1 as the standing reason A1/A2 cannot ship
  regardless of outcome. Closest annex miss, for context: A2-0.5-ts6
  failed only `topk_pass`.

## 7. Issues

| id | severity | issue | required handling |
|---|---|---|---|
| I1 | **medium** | `r3.swept.observed_null_p95_rate/observed_null_p99_rate` are by-construction identities (own-draws-vs-own-quantile, exactly 0.05/0.01 absent ties), while the §8 expected-vs-observed comparison needs the **variant-level** clause rates, which are not stored in the r3 block. A report that quotes 0.01 as "observed matches the 1% expectation" would be wrong: the real observed clause-6 rate is **8/175 = 4.6%** (3 effective vs 0.32 expected). | Report must compute clause-level pass counts from per-variant `reasons` (numbers in §2/§3 above) and label the stored fields as draw-bookkeeping identities. |
| I2 | **medium** | §8/amendment-14 clause-6 marginality CI (bootstrap CI of the cell's pooled q99, D = 1000) is absent from the artifact, and the null draw values are not stored — so whether any passer's clause-6 margin (0.154 and 0.240 in annualized-Sharpe units) lies inside its CI is **undetermined from the artifact alone**. Same gap (I2b): §8's pairwise pooled-OOS return correlations for the transfer disclosure. | Recompute at report stage (registered seed map makes the draws reproducible deterministically); disclose the CI next to the verdict if the condition triggers; compute and disclose the pairwise correlations next to the transfer table. |
| I3 | low | §5's structural-infeasibility *expectation* ("all G1/G3/L1-type") under-predicted the committed flags: 65 flagged including the entire T-F taxonomy (30/30), TH ladders/maps, TD R2 ladders, TE L1. Data and mechanism clean and pre-OOS; prose risk only. | Wider-null narrative must use effective denominator **110**, state that the flag set exceeded the §5 prediction, and disclose that T-F was structurally voided as registered (coverage floor × trade floor). |
| I4 | low | The per-cell calibration slot (registered, §13.29(d)) landed on a **risk ladder in all 13 cells**, so full-gate false-pass rates were never measured on a direction-map shape; the P-BTC/TD 0/200 is not a direct bound on the D1 shape's false-pass rate. | Keep §8's "indicative calibration, never the headline" framing verbatim; do not quote ≤ 2% as a bound on the passer's false-pass probability (the §3(b) arithmetic above already does this). |
| N1 | nit | Artifact `variants` list is globally rank-ordered, not enumeration-ordered (verified pure permutation of `enumerate_all_w()`); `swept.gate_pass_count` sums annex records too (not triggered — no annex passed). | None required; recorded for reproducers. |

## 8. Lane verdict

**issues (2 medium, 2 low, 1 nit) — none invalidating.** Every number
checked in the artifact's r3, era-split, crash-day, structural-
feasibility, and lock blocks is internally consistent, matches the
registration's §5/§7/§8/§13 definitions, and reproduces under
independent recomputation. The 4 gate passes collapse to exactly one
effective hypothesis — the symmetric sibling of the quarantined
fade-positive-funding-extremes family, on the contaminated panel and
era, locked by layers 2+3 with 88–92% of PnL attributed to the burned
leg, and failing on both transfer panels. The medium issues are
disclosure obligations the final report must discharge (clause-level
observed rates; marginality CI + transfer correlations), not defects in
the sweep's bookkeeping. `ship_eligible_count = 0` survives this lane's
attempt to break it — and so does the wider null: the observed pass
pattern is the one outcome the registration explicitly predicted and
pre-armed against.
