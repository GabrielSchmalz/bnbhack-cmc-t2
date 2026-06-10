# Lane 1 — Independent reproduction of the Task 2.4 sweep (adversarial verification)

Date: 2026-06-10 · Agent: lane-1 reproduction critic · Scope: plan Task 2.5, ADR-001 R1–R3
Scratch code: `/tmp/lane1/{lane1_repro.py, check1_thresholds_raw.py, check4_spot_trades.py, check_extra_diagnostics.py}`
Raw outputs: `/tmp/lane1/lane1_repro_out.json`, `/tmp/lane1/check1_out.json`, `/tmp/lane1/h8_oos_trades.csv`

## 0. What was rebuilt independently vs. reused

Rebuilt from the plan text (no `lab.sweep`, `lab.hooks`, `lab.walkforward`, `lab.gate`,
`lab.metrics` in the load-bearing path):

- the PR-6 fold loop (calendar boundaries, embargo sizing from my own run-length
  episode encoder, `train = bars < boundary`, `oos = grid[boundary_pos + E : next_boundary)`),
- per-fold R1 threshold derivation calls and label generation per fold,
- pooled-OOS concatenation, PR-7 rank key, Sharpe (`mean/std(ddof=0)·√2190`), net
  return, max-DD, turnover — all re-implemented inline,
- the episode-block shuffle null (my own RLE → `default_rng(17+fold#)` permutation →
  reassembly; 1000 draws/fold, unguarded @10 bps, pooled across folds, p95),
- top-5 removal formula `(1+total)/(1+removed_gain)−1`,
- the variants' action maps, transcribed from PR-8.

Reused as building blocks (allowed by the assignment; each independently spot-verified
below): `lab.dataset.load_panel`, `lab.features.add_features/derive_thresholds`,
`lab.classifier.label`, `lab.rules.apply`, `lab.engine.run_backtest`, `lab.dd_guard`.
Check 1 additionally rebuilds the three threshold features **straight from the raw CSVs
with zero lab imports**, and check 4 re-derives trade PnL by hand arithmetic from raw
bars + funding rows, so the reused modules' semantics are not taken on faith.

## 1. Reproduction result: exact match, 0 divergence

For the top-3 rank-ranked variants (`DIR-TC-H10-short_crowded_long-0.5`,
`DIR-TC-H10-short_crowded_long-1.0`, `RISK-TC-ladder-0.5_0_1_0.5`) and both near-misses
(`DIR-TC-H8-fade_pos_extreme_only-{0.5,1.0}`), every compared field matches
`artifacts/sweep_results.json`:

- per-fold train Sharpes (F1–F4), rank key, mean train max-DD
- pooled OOS Sharpe / net / max-DD / n_trades / turnover (guarded @10 bps)
- unguarded pooled OOS Sharpe (the gate's null-clause numerator)
- `null_p95` (re-derived from my own shuffle implementation, 1000 draws/fold)
- `top5_net`, full cost ladder {5, 10, 20} bps (net + Sharpe)

**Max |difference| across all ~100 compared scalars: 0.0** (tolerance demanded: 1e-9).
Globals also match exactly: embargo E=42 for TA/TB/TC (median episode length 4 bars →
the 42-bar floor binds), TC per-fold OOS bars 324/330/312/378, HODL pooled-OOS Sharpe
−2.0963135337153442 / net −0.45901858600522905.

There is no divergence to chase to root cause. The artifact is what the pre-registered
pipeline produces.

Fold geometry reproduced: F1 OOS 2025-10-08→2025-11-30 20:00, F2 2025-12-08→2026-01-31
20:00, F3 2026-02-08→2026-03-31 20:00, F4 2026-04-08→2026-06-09 20:00; embargo gap = 42
bars (7 days) at every boundary; train always strictly pre-boundary. The 4h grid is
complete: 2598 bars, all 2597 deltas exactly 4h, no holes.

## 2. Check 1 — R1 threshold hygiene (train-only, provably)

Method: rebuilt `funding_rate_8h` (stamp join + ffill), `oi_chg_24h` (daily-midnight
snapshot → 36h-cap as-of → 6-bar change) and `fg` (D 00:00 + 4h availability as-of)
**from the raw committed CSVs with no lab imports**, with every source frame
**truncated strictly before the fold boundary** before any computation, then took
pandas q20/q80 quantiles.

Result: all 6 thresholds × 4 folds match the pipeline values **exactly (0.0 diff)**:

| fold | funding_hi | funding_lo | funding_hi_abs | oi_surge | fg_lo | fg_hi |
|---|---|---|---|---|---|---|
| F1 | 9.693e-05 | 1.439e-05 | 9.782e-05 | 0.0449112490 | 42 | 66 |
| F2 | 9.321e-05 | 1.250e-05 | 9.543e-05 | 0.0465693710 | 31 | 61 |
| F3 | 8.850e-05 | 1.439e-05 | 8.909e-05 | 0.0471881599 | 28 | 58 |
| F4 | 8.18620e-05 | 1.458e-06 | 8.38560e-05 | 0.0510744568 | 24 | 55 |

Because the entire raw recomputation never saw a single row stamped at or after the
boundary, an exact match **proves no OOS row influences any fold's thresholds** — this
is stronger than a slice-only argument (it also rules out leakage hidden inside feature
construction, e.g. full-window resampling effects).

Label implication: TC labels rebuilt from raw funding alone (`pos/neg` by sign,
`extreme` by `|f| ≥ funding_hi_abs`) match the pipeline's label series for all 4 folds
on all 2598 bars — **0 mismatches**. The thresholds are exactly what the labeling uses.

## 3. Check 2 — honest_N (TC)

My own run-length count of each fold's label series restricted to that fold's OOS:
F1=52, F2=48, F3=60, F4=65 → pooled **225**, matching the artifact exactly.

Adversarial caveat on its meaning: honest_N is a **taxonomy-level** episode count over
all four TC labels. For the H8 near-miss the *active* OOS evidence is far smaller —
**30 trades over 92 nonzero-position bars** (F1: 34, F2: 38, F3: **0**, F4: 20). Any
ship-side argument quoting N=225 for an H8-style variant would overstate its sample by
~7×. F3 contributes zero trades: under F3-train thresholds, not one OOS bar in
Feb–Mar 2026 labels pos-extreme — the variant's OOS evidence effectively spans 3 of 4
folds.

## 4. Check 3 — the funding_lo = +1.458e-6 oddity

Confirmed: q20 of `funding_rate_8h` on F4-train is **+1.458e-06 — positive** (and
positive on every fold: F1 +1.439e-05, F2 +1.250e-05, F3 +1.439e-05). On F4-train,
18.92% of bars carry negative funding, median +4.0e-05, min −1.5178e-04; the 20th
percentile therefore lands just above zero.

Semantics: the TA/TB `funding ≤ funding_lo` clause is **bottom-quintile-relative**, not
negative-extreme. It fires on mildly *positive* near-zero funding as well as on negative
funding. "Low funding" in those taxonomies means "bottom 20% of the train distribution"
(≈ absence of long-crowding), and any prose describing it as "negative/short-crowded
extreme" would be wrong. Note also the regime drift it exposes: funding_lo collapsed an
order of magnitude from F1–F3 (≈+1.4e-05) to F4 (+1.5e-06) as 2026's negative-funding
bars entered train. The TC taxonomy (all five target variants) does not consume
funding_lo, so the near-misses are unaffected; the caveat binds any TA/TB-based claims
and any reference-table prose.

## 5. Check 4 — hand spot-check of 3 DIR-TC-H8-1.0 OOS trades

Recomputed from raw `bars_4h.csv` + `funding_btcusdt_binance.csv` with plain arithmetic
(per-side 5 bps on |Δw|, funding only at 00/08/16 UTC stamps, r = next open / open − 1):

| trade | trigger bar funding vs threshold | bars | hand pnl | engine pnl | diff |
|---|---|---|---|---|---|
| 2025-10-08 12:00 → 10-08 20:00 (first OOS) | +1.000e-4 ≥ 9.782e-5 ✓ | 2 | −0.0050842431 | −0.0050842431 | 1.7e-16 |
| 2025-11-20 12:00 → 11-20 20:00 (best, +5.56%) | +1.000e-4 ≥ 9.782e-5 ✓ | 2 | +0.0555872078 | +0.0555872078 | 1.5e-16 |
| 2025-11-18 04:00 → 11-18 20:00 (worst, −2.58%) | +1.000e-4 ≥ 9.782e-5 ✓ | 4 | −0.0257508950 | −0.0257508950 | 1.3e-16 |

Verified on real data: next-bar-open fill after a pos-extreme close, the one-side entry
cost in the first bar's growth factor, and the **R-FUND sign** — the short *earns*
positive funding at the 16:00 stamps (e.g. growth factor 1.03298975 on 2025-11-20 16:00
= (1+8.999e-5)·(1+0.032897)). Funding correctly accrues 0 on non-stamp (04/12/20) bars.
Trade-coverage probe: every nonzero-position OOS bar of H8-1.0 belongs to a trade whose
entry is inside the same fold's OOS — the top-5-removal hook sees the variant's complete
OOS PnL; nothing leaks around it via embargo-straddling entries. The DD guard never
activates for H8 (guarded ≡ unguarded, consistent with the artifact's equal Sharpes).

## 6. Adversarial reading — direction (a): is the null result an artifact of a bug that destroys real edges?

No evidence of that. Specifically:

1. **Zero numeric divergence** between an independently wired pipeline and the artifact.
2. **The bear OOS is real market path, not mis-accounting**: from raw bars, the four OOS
   segments are −25.5% (F1), −12.9% (F2), −1.5% (F3), −14.2% (F4); pooled ≈ −46%,
   matching HODL's −45.9% net. HODL's −2.10 Sharpe is the market, not the engine.
   (HODL's identical metrics across cost rungs are correct: its single entry fill is at
   the window start, outside every OOS segment.)
3. Sign conventions (funding, fill timing, costs) verified by hand on raw rows (§5).
4. Thresholds provably train-only (§2) — the anti-leakage direction also can't be
   *destroying* edges via contaminated thresholds.
5. The direction near-misses **passed** beats_flat/beats_hodl/null/ladder; the failing
   clauses (top5 for H8; null+top5+ladder for H10) measure edge robustness, not
   accounting.
6. The one structural property that genuinely *raises* the bar for sparse short
   variants: the episode-shuffle null permutes episodes over the **whole index**, so
   null draws hold the global share of short-labeled bars (~12–17% pos-extreme) inside
   the OOS, while the real variant's OOS share is much lower (F1 10.5%, F2 11.5%,
   F3 0%, F4 5.3%). In a monotonically falling OOS, the null therefore carries *more*
   short exposure than the variant and its Sharpe distribution shifts up —
   `null_p95 = 2.26` is a **conservative** hurdle for H8-type variants (and plausibly
   what killed H7's 1.42 vs 2.16). This is pre-registered behavior (plan PR-7,
   sweep.py adaptation (a)), disclosed here for the report; changing it post-sweep
   would be re-validation territory. It did not cause the H8 gate failure — H8 passed
   the null clause.

## 7. Adversarial reading — direction (b): should the H8 near-miss be talked past the gate? No.

1. **The top5 failure is substantive, not technical.** H8-1.0: 30 OOS trades, 15
   winners/15 losers, median trade +0.06%. The top-5 winners (2025-11-20 +5.6%,
   2025-12-29 +3.1%, 2026-06-01 +3.0%, 2026-05-27 +2.9%, 2025-11-04 +2.3%) carry
   **63.4% of total log-gains**; removing them flips +15.50% to −2.13%. The entire OOS
   profit is five crash-day shorts. With a 30-trade sample this is exactly the
   concentration failure mode the pre-registered clause exists to catch.
2. **The null margin is thin and unadjusted for selection.** The unguarded pooled OOS
   Sharpe 2.376 sits at the **96.4th percentile** of the variant's own 1000-draw null
   (one-sided p ≈ 0.036). 36 variants were swept; the expected count of variants
   clearing their own null p95 by chance ≈ 1.8. Observed: 2 — and they are the H8 pair,
   i.e. **one strategy at two sizes** (Sharpe is nearly scale-invariant; the pairs'
   rank keys differ only at 1e-5). The near-miss is statistically indistinguishable
   from the multiple-testing background it would have to clear (R3).
3. **Effective sample is 30 trades / 3 folds**, not honest_N=225 (§3).
4. The fade-positive-extreme edge is confounded with the OOS direction: shorting
   *anything* in this OOS made money (null p95 of 2.26 is itself evidence — randomly
   placed short episodes reach Sharpe 2.26 at the 95th percentile). What would
   distinguish timing skill from bear-market beta — profits surviving top-5 removal —
   is precisely what failed.

## 8. Verdict

- **Reproduction: CONFIRMED, bit-for-bit (max |diff| = 0.0; required tolerance 1e-9)**
  for all five target variants, all gate inputs, and all taxonomy globals.
- **R1: CONFIRMED** — thresholds re-derived from boundary-truncated raw CSVs match
  exactly; no OOS row can influence them; labels match what the thresholds imply.
- **honest_N: CONFIRMED** (225 = 52+48+60+65), with the disclosed caveat that it is a
  taxonomy-level count, ~7× the H8 variant's active sample.
- **funding_lo: CONFIRMED positive (+1.458e-06 on F4-train)**; the TA/TB clause is
  bottom-quintile-relative, not negative-extreme; not consumed by the TC near-misses.
- **Trades: CONFIRMED** against raw bars/funding at 1e-16, including the R-FUND sign.
- **The R-NULL outcome stands.** No pipeline defect was found that could have destroyed
  a real edge, and the DIR-TC-H8 near-miss fails the pre-registered top-5 clause for a
  substantive reason (5 trades = the entire OOS profit) while clearing its null clause
  by a margin (p ≈ 0.036) that 36-variant selection fully accounts for. The shipping
  decision is the operator's; this lane found no grounds to overturn the gate in either
  direction.
