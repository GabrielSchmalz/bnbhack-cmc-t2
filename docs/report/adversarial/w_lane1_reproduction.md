# Lane W-A — Independent reproduction + lock audit of the W-sweep passers (adversarial verification)

Date: 2026-06-11 · Agent: lane W-A reproduction critic · Scope: the four gate
passers of `artifacts/w/sweep_results_w.json` (HEAD `3702f84`), against the
binding registration `docs/plans/2026-06-10-widening-preregistration.md`
(§3, §4, §6, §7, §13) · Standard: lane-1 (max |diff| ≤ 1e-9, thresholds
re-derived from boundary-truncated raw files)
Scratch code: `~/.cache/wlane1/{repro_main.py, ts_hypo.py, repro_null.py,
repro_era.py, guard_compose.py, hand_trade.py}`
Raw outputs: `~/.cache/wlane1/{repro_main_out.json, repro_null_out.json,
repro_era_out.json, null_run.log}`

Targets: `P-BTC-DIR-TD-D1-fade_extremes_graded_sym-{0.5, 1.0, 0.5-ts6,
1.0-ts6}` — the artifact's only four `verdict.passed = true` records; all
four family-locked; `ship_eligible_count = 0`.

## 0. What was rebuilt independently vs. reused

Rebuilt from the registration text (no `lab/sweep_w`, `lab/gate_w`,
`lab/hooks_w`, `lab/lock_w`, `lab/panels_w`, `lab/classifiers_w` anywhere in
the load-bearing path — **none of those files was even read by this lane**;
the two interpretive corners below were resolved by black-box differential
testing against the artifact, not by consulting the banned code):

- panel assembly from the raw committed CSVs (`data/lab/bars_4h.csv`,
  `data/backfill/funding_btcusdt_binance.csv`): D4.1 dedupe, window clip
  2020-04-01 00:00 → 2026-06-09 20:00, exact-stamp funding join,
  stamp-masked ffill for `funding_rate_8h`;
- the 21-fold quarterly geometry (boundaries 2021-04-01 … 2026-04-01,
  train strictly pre-boundary, OOS = [boundary + 42 bars, next boundary),
  F21 to panel end) and the §1 embargo computation;
- per-fold T-D cuts c_hi = q60(|f|), c_x = q90(|f|) — twice: from the panel
  train slice AND from raw CSVs truncated strictly before each boundary
  with zero lab imports (the R1 proof, §2 below);
- T-D labeling incl. D4.3 NaN semantics (NaN → neg/mild branch), my own
  run-length episode encoder;
- the D1 action map (0, −0.5, −1, 0, +0.5, +1) × size ∈ {1.0, 0.5}, the
  1-bar lag, and the §3 time-stop state machine (k = 6);
- the PR-4 DD guard, **re-implemented inline from the PR-4 text** (the
  frozen `lab/dd_guard.py` was read for convention-pinning but not
  imported);
- pooled-OOS restriction, trade restriction by `entry_ts`, all 8 gate
  clauses per §7 including the ln-contribution fold-concentration formula
  and K = max(5, ceil(0.02 n));
- the §7 null mechanics from the registered seed map
  (`default_rng([17, 0, 0, fold_ordinal])`, fold_ordinal 1-based; T-D has
  no `na` labels so the registered `na`-freeze reduces to the plain frozen
  episode shuffle), full-panel backtest per draw with the variant's FULL
  rule surface unguarded (§13.29a), OOS restriction, pooling, numpy
  quantiles;
- the §6 lock layers 1–3, the §8 era split, the §13.29(c) crash-day
  interval-overlap rule, and the §13.29(e) structural-feasibility
  projection.

Reused as building blocks (explicitly allowed): `lab.engine.run_backtest`
and `lab.metrics.sharpe/max_dd` — frozen floor-validated primitives whose
arithmetic the frozen lane-1 already verified by hand against raw rows; a
fresh hand check is repeated here (§5). `lab.classifier` / `lab.rules`
ended up not imported (re-implemented). Frozen-floor modules
(`lab/sweep.py`, `lab/hooks.py`, `lab/dataset.py`, `lab/features.py`, …)
were READ to pin frozen conventions the registration references
("byte-identical to frozen hooks", PR-3/PR-4/PR-7 semantics) — read, not
imported.

## 1. Reproduction result: exact match, 0 divergence on 731 scalars

For all four passers, every compared field of the artifact record matches
**bit-for-bit (max |diff| = 0.0; demanded tolerance 1e-9; 731 scalars
compared, 0 violations)**:

- per-fold train Sharpes (21 × 4), rank keys, mean train max-DD;
- per-fold OOS bars / net / Sharpe (21 × 3 × 4) and fold_nets;
- pooled OOS Sharpe / net / max-DD / n_trades / turnover (guarded, gate
  rung) and the full cost ladder {5, 10, 20} bps (net + Sharpe);
- unguarded pooled OOS Sharpe (the null-clause numerator) — including the
  one passer where guarded ≠ unguarded (`-1.0`: 0.6790842413894344 vs
  0.6769979156245616, the guard flattens 10 OOS bars; both reproduced
  exactly, so the PR-4 guard path is verified inside OOS, not just train);
- top-5 and top-K removal nets, K values (8/8/9/9);
- fold contributions (ln-formula), max contribution, pooled_fold_net,
  nonzero OOS bars (4492/4482/1541/1541), folds-with-trades,
  covered_fold_count, trade counts (381/384/405/405);
- era-split bars / nets / trade counts, all 5 crash-day group counts +
  totals, structural-feasibility projections (403.7895604270752 /
  518.720338301976), lock layer-1/2/3 numbers (§4);
- panel globals: n_bars 13566, complete 4h grid (all 13565 deltas exactly
  4h), window stamps, per-fold OOS bars and episode counts (21 folds),
  honest_N = 1502, embargo E = 42 (first-fold-train median episode length
  4.0 → the floor binds, as the registration expected), HODL pooled-OOS
  Sharpe/net at all three rungs (0.10295621564420757 / −0.3765801752030906,
  rung-invariant because HODL's single entry fill predates every OOS
  segment). The `flat` benchmark is trivially zero; `vol_target` was not
  recomputed (no gate clause for these passers consumes it — disclosed).

**One interpretive corner had to be resolved, and it is the lane's main
semantic finding.** The §3 time-stop sentence "re-entry occurs at the first
label TRANSITION into any label whose mapped action is nonzero" does not
say whether that transition may occur on the bar immediately after the
k-th run bar. My first reading inserted an implicit flat bar (stop first,
re-entry only at a LATER transition); it reproduced everything except the
ts6 records (e.g. 0.5-ts6: Sharpe 0.8279 vs artifact 0.8108, 1503 vs 1541
nonzero bars). Differential testing of five §3-consistent machines
(`ts_hypo.py`) shows the implemented semantics is: **the capped run ends at
the k-th bar's close, and if that very next bar carries a transition into a
nonzero-action label, re-entry is immediate — exit and re-entry fills
coincide, no forced flat bar.** Under that machine all ts6 numbers match
bit-for-bit. Adversarial assessment: both readings are consistent with the
registered text; the implemented one is the more literal (the text never
mandates a flat bar) — and it is the LESS favorable one for the passers
(my stricter reading would have given the 0.5-ts6 passer a HIGHER OOS
Sharpe, 0.8279 vs 0.8108). No sign of opportunistic interpretation. The
corner should be pinned by a unit test if this family is ever re-run.

Candidate machines rejected by the data: one-bar-flat (M1), hold-k+1 (M3),
counter-reset-on-transition (M2), counter-reset-on-sign-flip (M2b) — none
reproduces (nz 1503/1608/1583/1515 vs artifact 1541).

## 2. R1 threshold hygiene (train-only, provably) — exact

`funding_rate_8h` was rebuilt from the raw CSVs with **zero lab imports**,
with both source frames truncated strictly before each fold boundary
before any computation (stamp filter → grid join → ffill → numpy q60/q90 of
|f|). All 42 cuts (21 folds × 2) match the panel-path pandas quantiles
**exactly (0.0 diff)**. Since the raw recomputation never saw a row stamped
at or after the boundary, no OOS row can influence any fold's cuts — and
every downstream scalar of §1 was produced from labels built on these cuts,
so the labels are exactly what the cuts imply.

Determination worth recording: **c_hi = 1.0e-4 on every one of the 21
folds** — q60(|f|) lands on the Binance default/clamped funding print in
every train slice (sample: F01 c_x 7.6207e-4, F05 5.56647e-4, F11
3.6196e-4, F21 2.3211e-4; c_hi 1.0e-4 throughout). The "hi/x" bands are
effectively "at or above the default rate" / "well above it". Train-derived
and stable, not a defect; any reference-table prose should say it.

## 3. Null reproduction from the registered seed map — exact, full D = 1000

The artifact does NOT store per-variant `null_sharpes` arrays, so the
registered 200-draw-prefix comparison route was unavailable. **What was
compared instead (stronger):** I regenerated the FULL 1000 common draws per
fold from `default_rng([17, 0, 0, fold_ordinal])` (sequential
`rng.permutation` calls; prefix property holds by construction), ran every
draw through each passer's full rule surface (D1 map × size, ts6 time-stop
where applicable) **unguarded** at 10 bps over the full panel, restricted
to fold OOS, pooled, took the frozen Sharpe, and compared
`np.quantile(·, 0.95/0.99)` against the artifact's stored `null_p95` /
`null_p99` for **all four passers** (mandate: ≥ the 0.5-ts6 one):

| variant | q95 mine = artifact | q99 mine = artifact | diff |
|---|---|---|---|
| 0.5 | 0.2868040703944894 | 0.5225776923206380 | 0.0 / 0.0 |
| 1.0 | 0.2868419359399010 | 0.5226185934683990 | 0.0 / 0.0 |
| 0.5-ts6 | 0.2958796092312639 | 0.5709485005475584 | 0.0 / 0.0 |
| 1.0-ts6 | 0.2958376365775526 | 0.5709504701348370 | 0.0 / 0.0 |

All eight quantiles bit-identical. Engine arithmetic for the 84,000 draw
backtests ran on an inlined numpy fast path proven bit-identical to
`lab.engine.run_backtest` on 24 sampled (fold, draw, variant) combinations
(max |diff| = 0.0) before use. 200-draw prefix quantiles are also recorded
in `repro_null_out.json` for any future prefix audit.

Context the quantiles carry: the null mean is **negative** (−0.30 plain,
−0.45 ts6; randomly placed episode blocks of this rule lose money on this
panel), and each passer's unguarded Sharpe sits at the 99.6th (ts6) /
99.8th (plain) percentile of its own 1000-draw null — clause-6 margins
(0.81 vs 0.57, 0.68 vs 0.52) are comfortable, not knife-edge; no §8
marginality CI is triggered.

## 4. Lock audit (§6) — all three layers independently confirmed

Reference cuts: identical to the T-D cuts (§2) — for a T-D Survivor the
reference labeling IS its own labeling; recomputed per fold from train rows
only.

**Layer 1** (pure-map predicate): D1 is long in neg-hi/neg-x, so (iii)
fails → not layer-1-locked. Matches artifact (`layer1_locked: false`) for
all four.

**Layer 2** (extremity-neutralized twin, the binding test): rebuilt per
fold from the guarded base w — w̄_mild = mean signed w over the fold's
reference positive-MILD OOS bars, written onto reference positive-extremity
OOS bars (fallback 0), twin re-run through the engine at 10 bps, pooled.
Bit-for-bit on all four (twin_net / twin_sharpe): 0.5
−0.0377240084338335 / −0.15934319193670857; 1.0
−0.08262385473062117 / −0.1592707634412158; 0.5-ts6
**−0.046757361264808894 / −0.23018398178129562** (the mandate's pinned
pair); 1.0-ts6 −0.09823313679051171 / −0.2301605106718821. Every twin
fails beats_flat AND null_p95 (its Sharpe is not merely below q95 — it is
negative), so `twin_passes = false`, locked. Confirmed.

**Layer 3** (share backstop): bar-level arithmetic decomposition (each
pooled-OOS bar's engine return, |Δw| cost and funding included), locked-leg
= reference positive-extremity bars with w < 0. Bit-for-bit on all four;
0.5-ts6: total 0.28388877134606916, leg 0.2623310743894397, share
**0.9240628755606893**; shares run 0.883–0.924 across the four. All > 0.5 →
locked. Confirmed.

Adversarial reading of what the lock numbers MEAN: 88–92% of the pooled-OOS
arithmetic PnL of these "symmetric" D1 variants is the short-leg on
reference positive-extremity bars — the exact H8/near-miss behavior §6
quarantines — and re-exposing those bars at the variant's own mild-bar
exposure flips the strategy to a negative net. The symmetric map is, on
this panel, economically the locked fade-positive-extremes hypothesis
wearing its registered mirror as a coat; the twin instrument caught it
exactly as designed. **The family-lock verdicts are substantively correct,
not a technicality. No grounds to overturn in either direction;
`ship_eligible_count = 0` stands.**

## 5. Era split, crash days, era clause status, hand trade check

- Era numbers (mandate: the 0.5 variant; verified for all four): pre/post
  2025-04-01 OOS bars 8094/2400, 0.5 nets 0.32851965436287234 /
  0.047850806033881144, trades 324/57 — all exact, likewise the other
  three.
- Crash-day coincidence (interval overlap, [entry_ts, exit_ts] vs the UTC
  day union per group): 1/1/1/3/1, total 7 — exact for all four variants.
- Era clause status (§13.29b: era-restricted evidence vs FULL pooled null
  quantiles): re-derived all 8 clauses per era under the natural reading
  (bars by timestamp, trades by entry_ts, K and ln-concentration from
  era-restricted evidence, covered folds = 21): **64/64 booleans match.**
  Notable content, pre-registered framing applies: in the post-2025-04 era
  (the frozen-window-overlap era) top5_pass and topk_pass FAIL for all
  four — the recent-era profit is again top-trade-concentrated; the gate
  pass is carried by the 2021–2025-Q1 era.
- Hand arithmetic from raw CSV rows (no lab imports in the PnL math): the
  two largest F05 OOS trades of 0.5-ts6 reproduce engine pnl_pct at
  0.0 / 2.2e-16, verifying next-bar-open fill, per-side 5 bps on |Δw|, the
  R-FUND sign (the 2022-05-12 long at w=+0.25 PAYS the negative-funding
  stamps), and the graded map (label bar f8h = +1.0e-4 ≥ c_hi=1e-4, < c_x →
  pos-hi → w = −0.25 at size 0.5).

## 6. Adversarial findings that do NOT block reproduction (disclosures)

1. **Guard/time-stop composition is sequential, and the §3
   "guard-supersedes-and-terminates-the-run" sentence binds only as a
   w-override on this data.** A genuinely composed machine (guard flat
   resets the run counter; §3 re-entry after release) differs from the
   sequential reading on 25 (0.5-ts6) / 46 (1.0-ts6) bars across the 21
   fold-labelings — all in train regions; pooled OOS is bit-identical
   under both readings, but rank_key moves in the 3rd decimal (0.5-ts6:
   0.4174 sequential vs 0.4266 composed). The artifact equals the
   SEQUENTIAL reading exactly. Materiality: zero effect on any gate
   clause, lock number, or OOS scalar of any passer; the only conceivable
   downstream contact is train-rank ordering (per-cell calibration slot
   selection, §13.29d) — flagged for the R3/calibration lanes; nothing in
   this lane's scope is affected.
2. **Clause-8 margin for 1.0-ts6 is razor-thin:** topk_net =
   +0.000608205257158767 (six basis points of net after removing its K=9
   best trades). 0.5-ts6: +0.0096. The plain-size passers have more
   headroom (+0.1040 / +0.0276). A one-trade perturbation would flip
   1.0-ts6's clause 8; the pre-registered clause held by 6 bps — worth
   stating wherever these passers are described.
3. **Fold concentration sits near the cap:** max ln-contribution 0.4898
   (1.0-ts6) / 0.4713 (0.5-ts6) vs the 0.5 fail line, driven by F05 (the
   2022-Q2 Luna quarter, net +0.288 / +0.136). Combined with §5's
   post-era top-trade failures: the economic story of these passers is
   crash-quarter shorts plus carry, exactly the profile the lock then
   disqualifies.
4. **The four passers are one effective hypothesis** (D1
   fade_extremes_graded_sym) in four dressings — Sharpe is nearly
   size-invariant (0.6769/0.6791 and 0.8108/0.8110); R3 accounting should
   (and per §8 does) count them as ≈ 1 hypothesis, not 4 successes.
5. Environment note: bit-for-bit equality was obtained under the repo
   venv (pandas 3.0.3, numpy 2.4.6, no bottleneck); reproductions on other
   stacks should expect ≤ 1e-12 float drift, not exact zeros.

## 7. Verdict

- **Reproduction: EXACT (max |diff| = 0.0 over 731 compared scalars; 
  required ≤ 1e-9)** for all four passers: train Sharpes, rank keys,
  per-fold and pooled OOS at every cost rung, top-5/top-K, fold
  contributions, trade counts, position bars, era split, crash-day counts,
  feasibility projections, and panel/taxonomy globals.
- **R1: CONFIRMED** — all 42 per-fold cuts re-derived from
  boundary-truncated raw CSVs with zero lab imports match exactly; no OOS
  row can influence any threshold.
- **Null: CONFIRMED** — all eight stored quantiles (q95/q99 × 4 passers)
  reproduced bit-for-bit from the registered seed map at full D = 1000
  (the stored-array prefix route was unavailable: no `null_sharpes` in the
  artifact; the full regeneration supersedes it).
- **Lock: CONFIRMED on all three layers**, numerically exact, and
  substantively earned: 88–92% of pooled-OOS PnL sits on the quarantined
  short-positive-extremity leg; every twin goes net-negative.
- **Era/crash audit: CONFIRMED** (and 64/64 era clause booleans match).
- One semantic determination (time-stop cap-bar immediate re-entry — the
  implemented, text-consistent, passer-unfavorable reading) and one
  composition disclosure (sequential guard, train-only, rank-key 3rd
  decimal) — neither overturns anything; both should be test-pinned before
  any future re-run of this family.
- **The artifact's bottom line stands as published: 4 gate passes, all
  family-locked, 0 ship-eligible.** This lane found no defect that
  manufactures the passes, and no defect in the lock that unfairly blocks
  them.
