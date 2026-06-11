# W-sweep evidence supplement — clause-6 marginality CIs, §8 transfer correlations, era-restricted honest-N

Date: 2026-06-11 · Author: builder agent (report-stage evidence supplement,
lane W-C issue discharge) · Status: **report-ready** — the REPORT W chapter
cites this file directly · Inputs of record:
`artifacts/w/sweep_results_w.json` (committed `74e6417`), binding
registration `docs/plans/2026-06-10-widening-preregistration.md` (§6, §7,
§8, §13 amendments 14 and 29),
`docs/report/adversarial/w_lane1_reproduction.md` (lane W-A),
`docs/report/adversarial/w_lane3_r3_audit.md` (lane W-C),
`docs/report/adversarial/w_lane2_launch_note.md` (lane W-B — readout
**PENDING**, §4 below) · Scratch code: `~/.cache/wr3sup/wr3sup.py`, raw
outputs `~/.cache/wr3sup/{out.json, run.log}` (not committed; single
process, production lab code path).

---

## 0. Scope, method, and verification anchors

This supplement discharges the two **medium** issues of the lane W-C R3
audit — **I2** (the §8/amendment-14 clause-6 marginality bootstrap CI,
absent from the artifact because per-variant null-Sharpe arrays are not
stored) and **I2b** (the §8 pairwise pooled-OOS return correlations for
the transfer disclosure) — plus the era-restricted honest-N table for the
four passers' context. Nothing here re-opens any verdict: the artifact's
bottom line (183 evaluated, 4 gate passes, all four family-locked,
`ship_eligible_count = 0`) is unchanged by everything below.

**Method status.** This is *recomputation bookkeeping at report stage*
(exactly what W-C §7 prescribes for I2/I2b), not a second independent
reproduction — the independence proof already exists: lane W-A rebuilt the
passers from the registration text with zero load-bearing lab imports and
matched 731 scalars at max |diff| = 0.0, including all eight stored null
quantiles regenerated from the registered seed map at full D = 1000. This
supplement therefore deliberately reuses the production code path
(`lab.hooks_w.episode_shuffles_w` — the lane-W-A-verified draw generator —
and `lab.sweep_w`'s evaluation internals).

**Verification anchors of this recomputation** (every check bit-for-bit,
max |diff| = 0.0, against the committed artifact):

- 12/12 pooled-OOS Sharpes **and** net returns (the D1 map in all four
  dressings on all three panels — §2's correlation inputs);
- 8/8 null quantiles (q95/q99 × the four passers — §1's CI inputs) and
  4/4 unguarded pooled-OOS Sharpes (the clause-6 numerators);
- 21/21 per-fold OOS bar counts and regime-episode counts for P-BTC/T-D
  (§3's honest-N inputs), summing to the artifact's honest_N = 1502.

All recomputation runs from the committed CSVs through the registered
pipeline at the gate rung (10 bps RT). Shared conventions used throughout
(frozen definitions, pinned here once):

- **Sharpe** (lab/metrics.py): annualized, `mean(r) / std(r, ddof=0) ×
  √2190` over per-bar net returns; degenerate inputs → 0.0.
- **Net return** (lab/hooks.py): `Π(1 + r_t) − 1` over the restricted
  bar-return series.
- **Pooled OOS series**: per fold, the engine's per-bar net returns
  (next-bar-open fills, per-side cost on |Δw|, R-FUND funding accrual)
  restricted to that fold's OOS index, then concatenated across folds and
  sorted by timestamp (`_pool`).
- **Quantiles**: `np.quantile(·, q)` with numpy's default linear
  interpolation — the same call as the frozen p95 path (§7).

## 1. Clause-6 marginality bootstrap CIs (§8, amendment 14 — lane W-C I2)

**Registered disclosure rule (§8):** "for any Variant whose clause-6
margin lies inside the bootstrap CI of its cell's pooled q99 (D = 1000),
that CI is disclosed next to the verdict." The artifact stores the
quantiles but not the 1000-draw arrays, so the CI is recomputed here from
the registered seed map.

**Mechanics, in full:**

1. **Common null draws** (registration §7; regenerated, not simulated
   anew): per fold F01…F21 of P-BTC/T-D, a fresh
   `numpy.random.default_rng([17, 0, 0, fold_ordinal])` (panel_index 0,
   taxonomy_index 0, fold_ordinal 1-based) yields D = 1000 sequential
   `rng.permutation` orders over the fold's labeled episodes (frozen
   episode segmentation; episode lengths preserved; T-D has no `na`
   label, so the registered `na`-freeze is vacuous and the draw is the
   plain frozen episode shuffle). Generator: `lab.hooks_w.
   episode_shuffles_w` — verified bit-for-bit by lane W-A §3.
2. **Pooled null Sharpe per draw** (§7 + §13.29a): for draw i, each
   fold's permuted label series runs the passer's FULL registered rule
   surface (D1 graded action map via the frozen 1-bar-lag `rules.apply`,
   × size, §3 time-stop k=6 where dressed; vol-band off for direction
   maps) **unguarded** at 10 bps over the full panel; bar returns are
   restricted to the fold's OOS, concatenated across the 21 folds, and
   the frozen Sharpe is taken. This yields the passer's 1000-entry pooled
   null Sharpe array `ns`.
3. **Point quantiles**: `q95 = np.quantile(ns, 0.95)`,
   `q99 = np.quantile(ns, 0.99)`. Recomputed values match the artifact's
   stored `null_p95` / `null_p99` **bit-for-bit (diff 0.0) for all four
   passers** — same result lane W-A obtained independently.
4. **Clause-6 margin**: `m = S_u − q99`, where `S_u` is the variant's
   UNGUARDED pooled-OOS Sharpe — the registered sweep-level substitution
   (§13.29a; the null draws are unguarded, so the numerator is too).
   `S_u` was likewise recomputed (diff 0.0 vs the artifact).
5. **Bootstrap CI of q99** (this supplement's added instrument; D stays
   1000 per amendment 14): per passer, a fresh
   `numpy.random.default_rng(20260611)` (one generator per passer —
   passer-order-independent by construction) draws the index matrix
   `idx = rng.integers(0, 1000, size=(10000, 1000))` in a single call;
   `boot_q99[b] = np.quantile(ns[idx[b]], 0.99)` for each of the
   B = 10,000 resamples-with-replacement;
   `CI = np.quantile(boot_q99, [0.025, 0.975])`.
6. **Marginality determination**: the §8 condition "margin lies inside
   the CI" is operationalized in margin space as
   `m ∈ [CI_lo − q99, CI_hi − q99]` — equivalently, the pass is marginal
   iff `S_u ≤ CI_hi` (every margin below is positive, so the binding edge
   is the upper one): a marginal passer's Sharpe could be cleared by a
   resampling-plausible q99.

**Result table** (all q95/q99 and S_u values reproduced the artifact at
diff 0.0 before bootstrapping; CIs at full precision in
`~/.cache/wr3sup/out.json`, which also stores the four 1000-entry null
arrays):

| passer (P-BTC-DIR-TD-D1-fade_extremes_graded_sym-…) | null q99 (D=1000) | bootstrap 95% CI of q99 | unguarded OOS Sharpe S_u | clause-6 margin m | S_u inside CI? |
|---|---|---|---|---|---|
| -0.5 | 0.522578 | [0.455764, 0.614627] | 0.676895 | **0.154317** | no — above CI_hi |
| -1.0 | 0.522619 | [0.455820, 0.614630] | 0.676998 | **0.154379** | no — above CI_hi |
| -0.5-ts6 | 0.570949 | [0.485446, 0.722774] | 0.810830 | **0.239882** | no — above CI_hi |
| -1.0-ts6 | 0.570950 | [0.485563, 0.722769] | 0.810991 | **0.240041** | no — above CI_hi |

Null-distribution context per passer (mean / sd of the 1000 pooled null
Sharpes; bootstrap sd of q99): plain dressings −0.298 / 0.365 (q99 sd
0.0379); ts6 dressings −0.447 / 0.437 (q99 sd 0.0770). Each passer's S_u
sits at the 99.8th (plain) / 99.6th (ts6) percentile of its own null —
matching lane W-A §3's independent readout.

**Verdict.** The margins lane W-C quoted from the artifact (~0.154 and
~0.240 annualized-Sharpe units) are **confirmed** at full precision
(0.154317 / 0.154379 / 0.239882 / 0.240041). For **all four passers** the
unguarded Sharpe clears even the upper end of its q99 bootstrap CI
(margin m exceeds CI_hi − q99 = 0.092 plain / 0.152 ts6), so the §8
registered disclosure condition — margin inside the CI — is **not
triggered for any passer**: the clause-6 passes are not knife-edge
artifacts of q99 estimation noise at D = 1000. The CIs are nonetheless
disclosed here in full — the q99 point estimate carries an asymmetric
resampling band of −0.067/+0.092 (plain) and −0.086/+0.152 (ts6) around
itself, which is worth seeing next to any quoted margin.
Marginality was the last open mechanical question about these passes;
what remains against them is the substantive one — the §6 family lock
(layers 2+3, twin Sharpe collapse to −0.16/−0.23, 88–92% burned-leg PnL
share), which this supplement leaves exactly where lanes W-A/W-C left
it.

## 2. §8 pairwise transfer correlations (lane W-C I2b)

**Registered framing (§8):** "Cross-panel agreement is expected under
both signal and null because the assets are correlated; transfer evidence
is reported as correlation-discounted consistency, never independent
confirmation, with measured pairwise pooled-OOS return correlations
disclosed next to it." Those correlations are computed here for the D1
map (the passers' structure) at every dressing.

**Mechanics:**

- **Strategy return series**: for each (panel, dressing), the D1 Variant
  is evaluated exactly as in the sweep — per-fold train-derived T-D cuts
  (R1), full rule surface, PR-4 DD guard at the 10 bps gate rung (the
  registered evaluation path; the same series whose pooled Sharpe/net
  matches the artifact at diff 0.0) — giving per-bar pooled-OOS net
  returns (costs and funding included; bars with no position carry 0 and
  are **included** — exposure overlap is part of the transfer question).
- **Correlation**: Pearson r between two panels' series on the
  **intersection of their pooled-OOS timestamps** (P-BTC ∩ P-ETH =
  10,494 bars — identical fold geometry; pairs with P-SOL = 9,480 bars —
  P-SOL's 19-fold OOS is a subset, and its embargo gaps coincide because
  E = 42 binds at the same quarterly boundaries).
- **Market context**: Pearson r of raw close-to-close bar returns
  (`close_t/close_{t−1} − 1`, full-grid, NaN first bar dropped) over the
  same pooled-OOS intersections.

**Strategy-level: per-bar pooled-OOS net returns of the same D1 dressing
across panels (Pearson r):**

| dressing | P-BTC ↔ P-ETH (n=10,494) | P-BTC ↔ P-SOL (n=9,480) | P-ETH ↔ P-SOL (n=9,480) |
|---|---|---|---|
| D1-0.5 | 0.495 | 0.310 | 0.367 |
| D1-1.0 | 0.435 | 0.314 | 0.322 |
| D1-0.5-ts6 | 0.259 | 0.136 | 0.230 |
| D1-1.0-ts6 | 0.261 | 0.150 | 0.217 |

**Market-level context: raw close-to-close return correlations over the
same pooled-OOS windows:**

| pair | overlapping OOS bars | Pearson r |
|---|---|---|
| P-BTC ↔ P-ETH | 10,494 | 0.843 |
| P-BTC ↔ P-SOL | 9,480 | 0.729 |
| P-ETH ↔ P-SOL | 9,480 | 0.747 |

**Reading, under the §8 discount.** The underlying markets are highly
correlated over these OOS windows (r = 0.73–0.84), so cross-panel
*agreement* would have carried little independent evidence — that is
exactly why §8 pre-framed transfer as correlation-discounted consistency.
What the data shows is the reverse pattern: the same strategy applied to
panels this correlated still co-moves only modestly (r = 0.14–0.49 —
positive, via the shared funding-fade exposure on correlated prices, and
visibly weaker for the ts6 dressings, whose forced exits desynchronize
positions), **and the map loses money on both sibling panels anyway**
(net@10 −1.0%…−53.6% on P-ETH, −41.7%…−45.2% on P-SOL; 7 of 8 clauses
fail in every dressing — artifact records, audited in lane W-C §4).
Transfer *failure* across markets this correlated is evidence **against**
a cross-asset funding-fade mechanism and consistent with the lock's
attribution: a P-BTC-specific echo of the burned 2021–22
fade-positive-extremes signal (88–92% of the passers' PnL sits on the
quarantined leg, lane W-A §4). The correlation table is disclosed so that
nobody can later present P-ETH/P-SOL *or* any cross-panel agreement as
independent confirmation — and so the observed disagreement carries its
honest weight.

## 3. Era-restricted honest-N (P-BTC/T-D — the four passers' context)

**Mechanics.** Honest-N is the pooled-OOS **regime-episode** count per
(panel, taxonomy) (§7; FREEZE §3 amendment 4 carried forward): per fold,
the frozen episode segmentation (`lab.classifier.episodes`) runs on that
fold's OOS label slice (labels from that fold's train-derived cuts), and
non-`na` episodes are counted — for T-D there is no `na` label, so every
episode counts. The §8 era split at **2025-04-01** partitions cleanly on
fold boundaries (verified: every fold's OOS lies entirely on one side):
F01–F16 pre, F17–F21 post. Per-fold counts match the artifact 21/21;
no episode straddles the split (episodes are per-fold maximal runs).

| era | folds | OOS bars | **honest-N (episodes)** | passer OOS trades (0.5 / 1.0 / 0.5-ts6 / 1.0-ts6) |
|---|---|---|---|---|
| pre 2025-04-01 | F01–F16 (16) | 8,094 | **1,153** | 324 / 327 / 348 / 348 |
| post 2025-04-01 (frozen-window-overlap era) | F17–F21 (5) | 2,400 | **349** | 57 / 57 / 57 / 57 |
| pooled | F01–F21 (21) | 10,494 | **1,502** | 381 / 384 / 405 / 405 |

(Trade counts from the artifact's audited era_split blocks; quoted here
because any candidate statement must cite its ACTIVE sample — trades /
nonzero-position bars / folds-with-trades — never the taxonomy-level
honest-N. The four passers' nonzero-position pooled-OOS bars are
4,492 / 4,482 / 1,541 / 1,541 respectively.)

Context the table carries: the post era — the only era that overlaps the
frozen build's window, era framing per §8 and prior-contact item 11 —
holds 23% of the episodes and ~15% of the passers' trades, and it is the
era where their top-trade-removal clauses fail (W-C §4: the pass is
*driven* by the pre era, which for this hypothesis family is the
evaluation-contaminated 2021–22 window). The pre-era honest-N of 1,153
episodes is a real, large sample — the issue with the pre era is
contamination (§10 item 1), not sample size.

## 4. Pending input — explicitly NOT consumed here

The lane W-B planted-edge power calibration (`bnbhack-wcal`, launched
2026-06-11 07:14 UTC, 9 (panel, rung) cells) was **still running** when
this supplement was produced; its readout is **PENDING** and no number in
this file depends on it. Until that readout lands against the launch
note's §5 protocol, the W-panels have **no measured gate-power
statement** — the frozen floor's lane-2 power numbers (≥10 bps/bar
robust on the 14-month panel) do **not** transfer and must not be quoted
for W-panel detection power. The REPORT W chapter must fill its power
slot from the W-B readout when it exists, or carry it as pending.

## 5. Bottom line

- The §8/amendment-14 marginality disclosure obligation (W-C I2) is
  discharged: no passer's clause-6 margin lies inside its q99 bootstrap
  CI — margins 0.154/0.154/0.240/0.240 vs CI upper-edge distances
  0.092/0.092/0.152/0.152; the registered disclosure condition does not
  trigger, and the CIs are published above anyway.
- The §8 transfer-correlation disclosure (W-C I2b) is discharged: market
  correlation 0.73–0.84 across panels, same-map strategy correlation
  0.14–0.49 — and the map still fails 7/8 clauses on both non-BTC panels;
  transfer evidence is negative *after* the registered correlation
  discount.
- Era-restricted honest-N: 1,153 pre / 349 post of 1,502 pooled episodes;
  the pass lives in the pre era, which is precisely the era the §6
  quarantine exists for.
- Nothing here moves any verdict: 4 gate passes, all family-locked
  (layers 2+3), `ship_eligible_count = 0`, wider-null narrative intact.
