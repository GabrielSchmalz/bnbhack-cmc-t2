# Lane W-B — planted-edge power calibration: READOUT

**This document is the readout AGAINST the pre-registered §5 protocol of
the launch note** (`docs/report/adversarial/w_lane2_launch_note.md`,
written and committed before any calibration result existed). Every
extraction below is one of the seven numbered §5 items, executed over the
nine completed cells
`artifacts/w/calibration/P-{BTC,ETH,SOL}_{5,10,25}bps/sweep_results_w.json`
against the committed 0-rung anchor `artifacts/w/sweep_results_w.json`
(183 evaluated, 4 gate passes, all four
`P-BTC-DIR-TD-D1-fade_extremes_graded_sym` dressings, all family-locked,
ship_eligible_count = 0). Readout run by adversarial lane W-B (fresh
context, no involvement in the launch), 2026-06-12. Unfavorable findings
are reported with the same prominence as favorable ones; the single
red-flag finding is in §5.

**Headline (read this first).**

- P-BTC: the unmodified W machinery detects the planted aligned edge
  **robustly at every rung including 5 bps/bar** — all four D1 dressings
  pass all 8 clauses and the aligned family holds train rank #1 in all
  three cells.
- P-ETH and P-SOL: detection only at **25 bps/bar, and only marginally**
  (gate passes, but the aligned family never reaches train rank #1 —
  a T-G trend confound outranks it). ETH 10 bps is a near-miss (7/8
  clauses); SOL 10 bps and both 5 bps cells are clean non-detections.
  **The production ETH/SOL nulls therefore cannot exclude conditional
  edges of this shape at ≤ 10 bps/bar on those panels.**
- The §3 falsifiable prediction is **split**: all 20 aligned planted
  passers stayed family-locked with ship_eligible = False (held), but
  the predicted mechanism — layer 2 — failed to lock 7 of the 12 aligned
  passers at 25 bps, leaving layer 3 as the only binding lock, once with
  a share margin of 0.000943 over the 0.5 rule. And the cell-level claim
  "ship_eligible must remain 0 in every cell" is **VIOLATED**: P-ETH
  10 bps produced one ship-eligible passer (a T-G confound, §5 red flag).

## 0. Hygiene block (execution record, restated verbatim where pre-verified)

- First invocation on 2026-06-11 (hygiene brief: ~07:05; the surviving
  run log records a chain start at 07:12:48Z) self-skipped all nine cells
  on stale dry-test dummy result files and exited `fail=0` without
  computing anything; the dummies were removed and the chain relaunched
  CLEAN at **2026-06-11T07:14:04Z** (matching the launch note's recorded
  invocation `34319f5e…`).
- All nine result-file mtimes lie between **2026-06-11 09:40:46Z**
  (P-BTC_5bps) and **2026-06-12 01:18:26Z** (P-SOL_25bps) — every file
  post-dates the clean relaunch, so no dummy contamination.
- systemd unit `bnbhack-wcal`: **NRestarts=0** over the whole ≈18.1 h
  chain (re-verified at readout: `NRestarts=0`, `ExecMainStatus=0`),
  log line `[w-cal] chain end 2026-06-12T01:18:26Z fail=0`, peak memory
  ≈ 0.87 GB as recorded during the run. Zero unit restarts, zero failed
  cells.
- Per-cell wall times (log): BTC 8,802 / 9,912 / 12,435 s; ETH 5,690 /
  7,103 / 5,925 s; SOL 4,894 / 5,094 / 5,196 s — total ≈ 18.07 h,
  inside the 15–18 h launch budget.
- Globals confirmed in every artifact: n_draws = 1000,
  calibration_draws = 200, gate cost 10 bps, registered seed map
  ([17, panel, taxonomy, fold]), era split 2025-04-01, embargo TD = 42.
- Pass-count census recomputed from the artifacts matches the run log
  AND each artifact's own `r3.swept` block exactly:
  **BTC 12/81, 16/81, 23/81; ETH 0/51, 2/51, 8/51; SOL 0/51, 0/51,
  6/51** at 5/10/25 bps. ship_eligible_count = 0 in eight cells and
  **1 in P-ETH_10bps** (see §5). ETH/SOL cells have 51 variants because
  T-E is not a registered taxonomy on those panels.
- Plant stats from the log: BTC 6,558 pos + 246 neg masked of 13,566
  bars (cuts c_hi = 1.000e-4, c_x = 2.223e-4); ETH 6,860 pos + 322 neg
  of 13,566 (c_x = 3.006e-4); SOL 6,082 pos + 1,374 neg of 12,468
  (c_x = 3.691e-4). Net log drift at 5/10/25 bps: BTC −3.184 / −6.371 /
  −15.952; ETH −3.292 / −6.588 / −16.497; SOL −2.364 / −4.731 /
  −11.856.

## 1. Aligned-variant train rank (§5.1)

Rank key per §7: rank_key (mean per-fold train Sharpe @10 bps)
descending, tiebreak lower mean train max-DD, then lexicographic id,
among GATED variants (annex excluded; pool = 73 on BTC, 51 on ETH/SOL).
The four committed P-BTC passer ids are exactly the four local D1
dressings, so one table covers both halves of item 1. Dressing suffixes
abbreviate `P-<A>-DIR-TD-D1-fade_extremes_graded_sym-<suffix>`.

**P-BTC** (0-rung ranks from the committed artifact in parentheses):

| dressing | 0-rung | 5 bps | 10 bps | 25 bps |
|---|---|---|---|---|
| 1.0 | #43 (rk −0.0746501) | **#1** (1.11953) | **#1** (2.18619) | **#1** (5.52890) |
| 0.5 | #42 (−0.0511580) | #4 (1.00569) | #2 (2.12329) | #2 (5.44491) |
| 0.5-ts6 | #23 (0.417354) | #2 (1.04064) | #6 (1.65940) | #11 (3.47496) |
| 1.0-ts6 | #24 (0.411927) | #3 (1.03323) | #7 (1.65617) | #10 (3.47499) |

The aligned family takes ranks 1–4 outright at 5 bps and rank #1 at
every rung. Detection is credible by the lane-2 standard at all three
rungs on P-BTC.

**P-ETH:**

| dressing | 0-rung | 5 bps | 10 bps | 25 bps |
|---|---|---|---|---|
| 1.0 | #51 (−1.42594) | #45 (−0.580622) | #7 (0.256501) | #2 (2.98537) |
| 0.5 | #49 (−1.28899) | #40 (−0.351873) | #3 (0.496116) | #3 (2.96216) |
| 0.5-ts6 | #50 (−1.30836) | #50 (−0.780794) | #30 (−0.257429) | #8 (1.20158) |
| 1.0-ts6 | #48 (−1.27543) | #49 (−0.771562) | #32 (−0.261867) | #7 (1.23374) |

Top overall at 5 bps: `P-ETH-RISK-TD-ladder-1_0.5_0_1_1_0.5-vb`
(0.548068, fails gate); at 10 and 25 bps:
`P-ETH-DIR-TG-G2-trend_crowding_filtered-0.5` (0.652075 / 3.24250, both
gate PASSES). **The aligned family never reaches #1 on P-ETH, even at
25 bps** — the trend confound outranks it (3.24250 vs 2.98537).

**P-SOL:**

| dressing | 0-rung | 5 bps | 10 bps | 25 bps |
|---|---|---|---|---|
| 1.0 | #49 (−0.523767) | #30 (−0.0340496) | #15 (0.347763) | #2 (1.93017) |
| 0.5 | #51 (−0.669419) | #33 (−0.149329) | #18 (0.320906) | #3 (1.83625) |
| 0.5-ts6 | #29 (−0.0472621) | #17 (0.261215) | #5 (0.563659) | #5 (1.47053) |
| 1.0-ts6 | #31 (−0.0772148) | #19 (0.174023) | #6 (0.524324) | #6 (1.44646) |

Top overall at 5 bps: `P-SOL-RISK-TH-ladder-1_1_0.5_1_1_0.5` (0.761027,
fails gate); at 10 bps: `P-SOL-DIR-TG-G1-follow_trend-1.0` (0.710408,
fails gate); at 25 bps: `P-SOL-DIR-TG-G2-trend_crowding_filtered-0.5`
(1.98208, gate PASS). **Aligned family never #1 on P-SOL either.**

## 2. All-8-clause margins for the top D1 dressing per cell (§5.2)

Margins as pre-specified: c1 = net@10; c2 = Sharpe − HODL Sharpe;
c3/c6 = unguarded Sharpe − null p95/p99; c4 = top5 net; c5 = net@20;
c7 = trades / nonzero bars / covered-fold trade fraction / max fold
contribution; c8 = topK net (K). Failing margins in **bold**.

| cell | top D1 (rank) | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 |
|---|---|---|---|---|---|---|---|---|---|
| BTC 5 | 1.0 (#1) PASS | 5.04367 | 2.53086 | +0.983622 | 3.03086 | 3.92676 | +0.748482 | 382 tr / 4482 nz / 21/21 / 0.2147 | 2.34561 (K=8) |
| BTC 10 | 1.0 (#1) PASS | 18.6953 | 4.37710 | +1.57487 | 10.0243 | 14.8471 | +1.32947 | 381 / 4492 / 21/21 / 0.1714 | 7.81195 (K=8) |
| BTC 25 | 1.0 (#1) PASS | 692.445 | 9.88995 | +3.22840 | 146.162 | 564.858 | +2.94461 | 381 / 4492 / 21/21 / 0.1351 | 83.8210 (K=8) |
| ETH 5 | 0.5 (#40) fail | 0.119277 | 0.613902 | **−0.394844** | **−0.0606631** | 0.00795434 | **−0.646523** | 398 / 3504 / 21/21 / **1.274** | **−0.130098** (K=8) |
| ETH 10 | 0.5 (#3) fail | 0.758552 | 2.01651 | +0.134566 | 0.301971 | 0.579873 | **−0.0849085** | 398 / 3504 / 21/21 / 0.2953 | 0.171408 (K=8) |
| ETH 25 | 1.0 (#2) PASS | 42.5893 | 6.15786 | +1.66115 | 7.22764 | 33.9187 | +1.44975 | 398 / 3504 / 21/21 / 0.1236 | 4.71822 (K=8) |
| SOL 5 | 0.5-ts6 (#17) fail | **−0.198114** | **−0.196001** | **−0.828942** | **−0.379435** | **−0.332606** | **−1.13962** | 619 / 2166 / 19/19 / n/a (not evaluated, pooled R ≤ 0) | **−0.507872** (K=13) |
| SOL 10 | 0.5-ts6 (#5) fail | 0.0486329 | 0.511083 | **−0.449390** | **−0.198232** | **−0.108977** | **−0.734558** | 619 / 2167 / 19/19 / **3.210** | **−0.367507** (K=13) |
| SOL 25 | 1.0 (#2) PASS | 89.7138 | 4.19325 | +1.48058 | 15.3519 | 64.7150 | +1.24517 | 601 / 4218 / 19/19 / 0.1574 | 4.96214 (K=13) |

The single most informative marginal cell is **ETH 10 bps**: the best
aligned dressing passes 7 of 8 clauses and misses ONLY clause 6
(unguarded Sharpe 1.09429 vs null p99 1.17920, margin −0.0849085). The
single-seed caveat (launch note §3.5) applies with full force: this is
the edge of detectability, not reliable power.

## 3. Detection verdict and power statements (§5.3)

Per protocol: PASS iff ≥ 1 D1-aligned variant passes all 8 clauses.

| panel | 5 bps | 10 bps | 25 bps |
|---|---|---|---|
| P-BTC | PASS, 4/4 dressings, top rank | PASS, 4/4, top rank | PASS, 4/4, top rank |
| P-ETH | FAIL (0 D1 pass) | FAIL (best D1 7/8, clause 6 by −0.0849) | PASS, 4/4, NOT top rank (#2) |
| P-SOL | FAIL (0 D1 pass) | FAIL (best D1 2/8) | PASS, 4/4, NOT top rank (#2) |

Lane-2-form power statements:

- **P-BTC: the W gate detects ≥ 5 bps/bar robustly** (all dressings, all
  clauses, #1 train rank, smallest 5 bps clause margin +0.748 on
  clause 6).
- **P-ETH: the W gate detects 25 bps/bar marginally** (passes but never
  top-ranked; 10 bps is a one-clause near-miss; 5 bps undetected).
- **P-SOL: the W gate detects 25 bps/bar marginally** (passes but never
  top-ranked; 10 and 5 bps undetected).

**Consequence for the production nulls (pre-stated framing, stated
plainly):** ETH produced 0 gate passes at 5 bps and SOL produced 0 at
both 5 AND 10 bps. An edge size the machinery cannot detect cannot be
excluded by a null result. The committed sweep's zero passes on P-ETH
and P-SOL therefore constrain only edges ≳ 25 bps/bar of this
conditional shape on those panels; a true 5–10 bps/bar ETH or SOL edge
of exactly the planted form would have produced the same null. Only the
P-BTC null is informative down to ≈ 5 bps/bar.

## 4. Confound census (§5.4) — every non-D1 gate passer, all nine cells

67 total gate passes across the nine cells decompose as: **20 aligned
D1**, **12 in-family annex (all A2 `fade_pos_graded`, all P-BTC,
reported separately per §6 — annex variants are never in the gated
survivor pool)**, and **35 out-of-family confound passers**. Counts the
protocol asks for separately: **T-D risk-ladder passers: 0** (no RISK
variant passed anywhere — ladders are long-only by design and lose in
the planted downtrend, even though RISK ladders top the train rank in
the undetected ETH-5 and SOL-5 cells); **T-G trend passers: 11** (all
`G2 trend_crowding_filtered`, no G1/G3).

Full census of the 35 out-of-family confounds (`P-<panel>-DIR-` and map
abbreviated; all sizes/dressings listed; lock layer in brackets):

- **P-BTC 5 bps (4):** TE-E2-follow_unwind_sym-0.5 [L3],
  TE-E3-fade_pos_long_neg-0.5 [L3], TE-E2-follow_unwind_sym-1.0 [L3],
  TG-G2-trend_crowding_filtered-0.5 [L3].
- **P-BTC 10 bps (8):** TE-E3-0.5 [L3], TE-E3-1.0 [L3], TG-G2-0.5 [L3],
  TE-E2-0.5 [L3], TE-E2-1.0 [L3], TE-E2-0.5-ts6 [L3], TG-G2-1.0 [L3],
  TE-E2-1.0-ts6 [L3].
- **P-BTC 25 bps (15):** TE-E3-1.0 [L3], TE-E3-0.5 [L3], TG-G2-0.5
  [L3], TG-G2-1.0 [L3], TE-E2-1.0 [L3], TE-E2-0.5 [L3], TE-E3-1.0-ts6
  [L3], TE-E3-0.5-ts6 [L3], TE-E1-fade_build_sym-0.5 [L3], TE-E1-1.0
  [L3], TE-E2-1.0-ts6 [L3], TE-E2-0.5-ts6 [L3],
  TF-F1-capitulation_euphoria-1.0 [L2+L3], TF-F1-0.5 [L2+L3],
  TH-H1-fade_ob_pos_buy_os_neg-0.5 [L2].
- **P-ETH 10 bps (2):** TG-G2-0.5 [L3], **TG-G2-1.0 [UNLOCKED —
  SHIP-ELIGIBLE, see §5]**.
- **P-ETH 25 bps (4):** TG-G2-0.5 [L3], TG-G2-1.0 [L3], TF-F1-0.5
  [L2+L3], TF-F1-1.0 [L2+L3].
- **P-SOL 25 bps (2):** TG-G2-0.5 [L3], TG-G2-1.0 [L3].

By taxonomy: T-E 19 (E2 ×10, E3 ×7, E1 ×2 — all P-BTC, the only panel
carrying T-E), T-G 11, T-F 4, T-H 1. The 12 A2 annex passers (4 per BTC
rung) all carry locks [L1+L2+L3] at 5/10 bps and [L1+L3] at 25 bps.

**Interpretation against §3 caveat 3 (secular-downtrend capture).** The
census confirms the pre-stated confound channel, stronger than frozen
lane-2's: the planted drift pools to a −3.2 to −16.5 net log downtrend,
and follow-the-trend shapes legitimately capture it — G2 passes in all
six cells that have any passes and OUTRANKS the aligned family on
ETH/SOL at every detected rung. T-E confounds are label-correlated
captures (OI labels correlate with funding extremity; E3
`fade_pos_long_neg` is the planted direction map expressed in T-E label
space), all locked by layer 3 precisely because their PnL concentrates
on the reference extremity bars where the drift lives. Confound count
grows with rung on BTC (4 → 8 → 15). The pre-stated expectation that
"short-side ladders" might also capture the trend did NOT materialize —
zero RISK passers; the gated direction maps were the only confound
carriers.

## 5. Lock behavior on planted passers (§5.5) — including the red-flag finding

All **20 aligned D1 passers are family-locked with ship_eligible =
False**. Layer 1 never fires (the symmetric D1 map is outside the
pure-map predicate by design). Layer-by-layer:

- **Layer 2 locks 13/20:** all eight BTC passers at 5 and 10 bps, BTC-25
  0.5 and 1.0, ETH-25 0.5 and 1.0, SOL-25 0.5.
- **Layer 2 FAILS to lock 7/20 — all at 25 bps:** BTC 0.5-ts6 and
  1.0-ts6 (twin Sharpe 1.99173/1.99182 vs their null p95 1.4842), ETH
  0.5-ts6 and 1.0-ts6 (twin 1.55571/1.55559 vs p95 1.1671), SOL
  0.5-ts6, 1.0 and 1.0-ts6 (twins 0.684511 / 1.41349 / 1.23247 vs p95
  0.65186 / 0.95397 / 0.65184). The twins pass because neutralizing the
  reference positive-extremity bars leaves the long neg-extremity leg
  and residual trend exposure, which at 25 bps is itself enough to clear
  beats_flat and null_p95 — most visibly on SOL, whose neg leg is 1,374
  bars (5.6× BTC's 246).
- **Layer 3 locks 20/20** (share range 0.5009–0.8958). For the seven
  layer-2 escapees layer 3 was the ONLY binding lock, and for
  `P-SOL-DIR-TD-D1-fade_extremes_graded_sym-1.0-ts6` at 25 bps the share
  was **0.500943 — a margin of 0.000943 over the 0.5 majority rule**.
  Had its locked-leg share been 0.1% lower, a planted ALIGNED passer
  would have been ship-eligible and the prediction falsified outright.
  The quarantine held, but on SOL-at-25 it held by a coin's edge.

Twin deltas across the 20 aligned passers: Sharpe deltas **+0.670046 to
+3.33651**, net deltas **+0.575728 to +690.272** (the extreme is BTC-25
1.0: net 692.445 vs twin 2.17334). At the 0-rung anchor the four
committed passers' twins are net-NEGATIVE (−0.0377 to −0.0982, twin
Sharpe −0.230/−0.159); the planted twins turn progressively positive
with rung — exactly the residual-drift signature described above.

**RED FLAG — pre-stated prediction violated at the cell level.** The
launch-note instruction "ship_eligible must remain 0 in every cell" is
violated by **P-ETH_10bps: ship_eligible_count = 1**. The escapee is
**`P-ETH-DIR-TG-G2-trend_crowding_filtered-1.0`** — not an aligned
variant but a T-G trend confound: passes all 8 clauses (net@10 11.1759,
Sharpe 1.25986, unguarded 1.33914 vs p95 1.09888 / p99 1.25147, top5
1.98842, net@20 5.34617, 448 trades, topK 0.550344 at K=9), and **no
lock layer fires**: layer 1 False (it is not a funding-extremity map),
layer 2 twin passes (twin Sharpe 1.33002 > p95 — neutralizing funding
extremity bars barely touches a trend variant), layer 3 share 0.459060
< 0.5. Its sister dressing G2-0.5 (train rank #1 in the cell) passed
the gate identically but was locked by layer 3 at share 0.547397 —
ship-eligibility flipped between two dressings of the same map on an
0.088 swing in locked-leg share. Under §7 selection, in this planted
world **G2-1.0 would have been the cycle Winner on P-ETH**. Its §8 era
split shows the classic confound signature: pre-2025-04 net 7.18860
(314 trades, all clauses pass) vs post net 0.486935 (134 trades;
null_pass, top5, null_p99, min_active_sample, topk all FAIL post-era);
at the 0-rung anchor the same variant fails the gate (top5
−0.468209, topk −0.674496, max fold contribution 1.51025). Per the §3
pre-statement this must be read as a **defect finding, not a success**:
the §6 lock is a family quarantine and by design does not quarantine
out-of-family trend capture, so in any world containing a multi-year
secular drift the gate-plus-lock stack can emit a ship-eligible Survivor
whose edge is the drift, not its own conditional hypothesis. The era
split and 0-rung counterfactual would have disclosed it, but nothing in
the pipeline would have BLOCKED it.

## 6. R3 stability (§5.6)

- `observed_null_p95_rate` / `observed_null_p99_rate` are 0.0500 /
  0.0100 in all nine cells and in the committed run. Inspection of
  `lab/sweep_w.py` shows these measure each variant's own null draws
  against their own pooled quantiles, so they are a tautological
  self-consistency check of the quantile mechanics (which passed), not
  evidence about planting. Recorded as such, no more.
- **Per-cell full-gate null calibration (200 draws through all 8
  clauses)** stays at committed levels at every rung — no
  false-positive inflation anywhere. Committed: 9 of 13 cells at 0.000,
  max 0.0200 ± 0.0099 (P-ETH/TG). Planted cells: max 0.0250 ± 0.0110
  (P-ETH/TG at 5 bps); the T-D cells read BTC 0.000 / 0.005 / 0.005,
  ETH 0.000 / 0.005 / 0.015, SOL 0.000 / 0.015 / 0.010 (mc_se 0.005 –
  0.0086) across 5/10/25 bps — all within ~1–2 Monte-Carlo SE of the
  committed values. Caveat: the calibration slot follows the cell's top
  train-ranked gated variant, whose identity changes between the
  committed run (RISK ladders) and most planted cells (DIR variants),
  so the comparison is rate-level, not variant-identical.
- **Null quantiles rise monotonically with rung for every D1 dressing
  on every panel**, e.g. p95 for the 1.0 dressing: BTC 0.28684 →
  0.80772 → 1.32120 → 2.85970; ETH 0.36254 → 0.65891 → 0.95974 →
  1.87400; SOL 0.36711 → 0.48072 → 0.59858 → 0.95397 (0-rung → 5 → 10
  → 25). This confirms the pre-stated expectation: the episode-shuffle
  null inherits part of a window-wide edge, biasing the machine toward
  FALSE NEGATIVES at higher rungs, never false positives. It is also a
  second power-loss mechanism on ETH/SOL — the detection bar itself
  rises as the plant grows.

## 7. Per-fold sanity for the aligned variant (§5.7)

Top D1 dressing per cell (same as §2):

- **Train-Sharpe flatness.** BTC: flat ex-F01 (5 bps: mean 1.1961, sd
  0.2114 across F02–F21; F01 −0.41185 is the one cold fold, fading with
  rung: F01 = 0.52291 at 10 bps, 4.34280 at 25 bps). ETH 25: mean
  3.0620, sd 0.7287 ex-F01 (F02 = 1.11100 the laggard). SOL 25: mean
  1.9928, sd 0.6042 ex-F01 (F02 = −0.27900 still negative — SOL's early
  folds never see the edge cleanly). At the undetected rungs the
  profiles are NOT flat (ETH 5: all-negative trains, mean −0.35187; SOL
  5: mean 0.26121, sd 0.4651) — consistent with the plant being below
  the noise floor there, not with a pipeline fault.
- **OOS capture fold coverage.** Folds with net > 0: BTC 18/21 → 20/21
  → 21/21 across rungs (trades in 21/21 folds everywhere, max fold
  contribution 0.2147 → 0.1351). ETH: 11/21 → 17/21 → 19/21 (max
  contribution 1.274 at 5 bps — concentration FAIL — then 0.2953,
  0.1236). SOL: 11/19 → 12/19 → 18/19 (5 bps concentration not
  evaluated, pooled R ≤ 0; 10 bps max contribution 3.210 —
  concentration FAIL; 25 bps 0.1574). Window-wide capture appears
  exactly where detection passes.
- **Threshold-mismatch haircut.** Not stored in the artifacts; per-fold
  T-D train cuts were recomputed at readout from the committed panels
  via `lab.panels_w`/`w_folds` (valid because funding_rate_8h is
  injection-invariant; nothing was re-run or written). Result —
  **P-BTC: zero haircut.** Every fold's train c_hi equals the
  full-window mask cut exactly (1.000e-4 — the q60 cut sits on the
  Binance default rate in every train window); hot-set agreement on
  fold-OOS bars is 1.0000 in all 21 folds (0/10,494 bars mismatched).
  Per-fold c_x ranges [2.321e-4, 7.803e-4] vs mask 2.223e-4, so some
  bars the mask drifted as "x" are traded at hi-grade (0.5×) weight —
  a graded-weight haircut only, invisible in the hot set.
  **P-ETH: 11.11% pooled hot-set mismatch** (1,166/10,494 OOS bars);
  per-fold c_hi up to 2.069e-4 (F01), agreement as low as 0.2941 (F02)
  / 0.4216 (F03) / 0.4266 (F01) in the early high-funding folds.
  **P-SOL: 7.27% pooled mismatch** (689/9,480); c_hi up to 2.186e-4,
  worst agreement 0.2216 (F01), 0.4137 (F02). This is a real,
  quantified power-loss channel specific to ETH/SOL: in the 2021-era
  folds the variant's per-fold hot set diverges sharply from the
  full-window mask that placed the drift, so the variant misses planted
  bars and trades unplanted ones — compounding the rising-null effect
  (§6) and ETH/SOL's weaker per-bar drift-to-vol ratio. It is a
  property of the CALIBRATION CONSTRUCTION (lane-2's full-window mask
  convention), not of the production pipeline; but it means the ETH/SOL
  power statements above are, if anything, slightly pessimistic for an
  edge that tracked per-fold cuts, and exactly right for an edge fixed
  in absolute funding terms.

## Power statement table

| panel | rung (bps/bar) | cell passes | D1 passers | best D1 rank | aligned top rank? | detection verdict |
|---|---|---|---|---|---|---|
| P-BTC | 5 | 12/81 | 4 | 1 | yes | **PASS — robust** |
| P-BTC | 10 | 16/81 | 4 | 1 | yes | **PASS — robust** |
| P-BTC | 25 | 23/81 | 4 | 1 | yes | **PASS — robust** |
| P-ETH | 5 | 0/51 | 0 | 40 | no | FAIL |
| P-ETH | 10 | 2/51 | 0 | 3 | no | FAIL (near-miss: 7/8, clause 6 by −0.0849) |
| P-ETH | 25 | 8/51 | 4 | 2 | no | **PASS — marginal** (confound outranks) |
| P-SOL | 5 | 0/51 | 0 | 17 | no | FAIL |
| P-SOL | 10 | 0/51 | 0 | 5 | no | FAIL |
| P-SOL | 25 | 6/51 | 4 | 2 | no | **PASS — marginal** (confound outranks) |

## §3 pre-stated prediction — verdict

Three components, judged separately:

1. **"Any aligned passer should remain family-locked" — HELD.** 20/20
   aligned passers locked, 0 ship-eligible, twin Sharpe deltas +0.670
   to +3.337.
2. **"…by §6 layer 2" — FAILED at 25 bps.** Layer 2 locked only 13/20;
   at 25 bps it caught 5/12, and the quarantine survived solely on the
   layer-3 majority rule, once by share 0.500943 (SOL 1.0-ts6). The
   predicted mechanism is not the one that held at the top rung; layer
   3 is doing unbudgeted work and its 0.5 Schelling threshold has
   essentially zero margin on SOL at 25 bps.
3. **"ship_eligible must remain 0 in every cell" — VIOLATED.**
   P-ETH_10bps emitted one ship-eligible passer
   (`P-ETH-DIR-TG-G2-trend_crowding_filtered-1.0`, out-of-family trend
   confound, no lock layer fires, would have been the cycle Winner in
   that world). Per the pre-statement this is recorded as a lock-scope
   defect finding (§5 red flag), not celebrated as detection.

## What this means for the production null

The committed W-sweep's wider-null narrative — 183 evaluated, 4 passes,
all family-locked, nothing ship-eligible — is now power-qualified as
follows. On **P-BTC** the null is strong: the unmodified machinery
detects a 5 bps/bar conditional edge of the registered shape with all
four dressings at train rank #1, so the absence of any unlocked P-BTC
survivor genuinely excludes in-family edges down to roughly the 5
bps/bar scale (single drift seed caveat stands). On **P-ETH** the null
constrains only edges ≳ 25 bps/bar, with 10 bps a single-clause
near-miss — a true 10 bps/bar ETH edge of this shape would more likely
than not have produced the same zero. On **P-SOL** the null constrains
only ≳ 25 bps/bar and nothing below — 5 and 10 bps are clean
non-detections. The production zero-pass results on ETH/SOL must
therefore be reported as "no detectable edge at the ≥ 25 bps/bar
scale", never as the absence of smaller edges. Two further
qualifications travel with any use of the null: (i) at higher edge
sizes the episode-shuffle null rises with the signal, so the gate's
errors run toward false negatives — conservative for shipping, but it
means wide nulls get LESS informative exactly when edges get bigger;
and (ii) the P-ETH_10bps escapee shows that ship-eligibility is not by
itself proof of a real conditional edge in worlds with secular drift —
the era-split and 0-rung counterfactual disclosures, which did flag the
escapee's profile here, are load-bearing parts of any future Winner
claim and should be treated as blocking checks, not footnotes.

---
*Lane W-B readout, 2026-06-12. Inputs: nine calibration artifacts (mtimes
09:40:46Z–01:18:26Z), committed anchor, run log `/tmp/w_cal_run.log`,
`systemctl --user show bnbhack-wcal`. Fields not present in the
artifacts and how they were handled: per-fold threshold cuts (recomputed
read-only from committed panels, §7); bar-level planted-vs-realized PnL
attribution (not stored — fold-coverage proxy used, §7); lock/era blocks
for non-passers are null in all artifacts, so 0-rung confound
comparisons use gate stats only (§5). No artifact was modified, no sweep
re-run, no git command issued.*
