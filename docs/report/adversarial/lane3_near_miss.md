# Lane 3 — Near-miss stability: DIR-TC-H8-fade_pos_extreme_only-{0.5,1.0}

**Scope.** Adversarial characterization of the sweep's only 4-of-5-clause near-miss
(fails only `top5_pass`). Question: is the R-NULL result knife-edge or robust around
this variant?

**Binding caveat (ADR-001 / PR-7 / PR-10).** Every number below is post-hoc
exploration of a pre-registered, already-failed gate. NOTHING here re-opens the
shipping decision: the gate parameters (q=(0.2,0.8), E=max(42, median episode),
PR-6 boundaries, top-N=5, n_null=1000, seed 17) were frozen before the sweep, the
variant failed, and the R-NULL branch ships regardless of what any perturbation
shows. This file is fragility/robustness evidence for the falsification chapter only.

**Verdict in one line.** The near-miss is knife-edge in BOTH directions — one
analyst degree of freedom (quantile width, or removal count N) flips it to a full
PASS, and a 2-week fold-boundary shift in the other direction collapses it to a
2-clause fail — and a single 4-of-5 near-miss in a 36-variant null sweep is an
expected-order outcome (P ≈ 1/3 under the global null). The null result stands;
the gate's `top5_pass` clause did exactly what it was registered to do.

All scripts: `/tmp/lane3/` (scratch, not committed). Pipeline slices reassembled
from the committed `lab/` functions only (`features.derive_thresholds`,
`classifier.label`, `walkforward.folds` semantics, `rules.apply`,
`dd_guard.apply_dd_guard`, `engine.run_backtest`, `hooks.*`, `gate.shipping_gate`)
— no harness code modified.

---

## 1. Top-5 clause recomputed by hand

Pipeline slice (TC taxonomy, base config) reproduces the artifact **exactly, to 10
decimals**, for both sizes:

| quantity | hand recompute (0.5) | artifact (0.5) | hand (1.0) | artifact (1.0) |
|---|---|---|---|---|
| pooled OOS Sharpe | 2.3763096001 | 2.3763096001 | 2.3760903552 | 2.3760903552 |
| pooled OOS net @10bps | +0.0755766843 | +0.0755766843 | +0.1550451700 | +0.1550451700 |
| OOS trades | 30 | 30 | 30 | 30 |
| top5_net | −0.0103253019 | −0.0103253019 | −0.0212602144 | −0.0212602144 |

`lab.hooks.top_n_removal` semantics verified: pooled GUARDED OOS trades
(`entry_ts ∈ pooled OOS index`), remove the 5 largest positive `pnl_pct`,
`removed_gain = Π(1+pnl)−1`, `top5_net = (1+total)/(1+removed_gain)−1`.
The DD guard never fired in any OOS segment (guarded ≡ unguarded w).

**The 5 removed trades (size 0.5; size 1.0 is the identical set at ~2× pnl):**

| fold | entry | exit | w | pnl_pct |
|---|---|---|---|---|
| F1 | 2025-11-20 12:00 | 2025-11-20 20:00 | −0.5 | +0.02762 |
| F2 | 2025-12-29 04:00 | 2025-12-29 20:00 | −0.5 | +0.01530 |
| F4 | 2026-06-01 20:00 | 2026-06-02 12:00 | −0.5 | +0.01502 |
| F4 | 2026-05-27 04:00 | 2026-05-28 12:00 | −0.5 | +0.01433 |
| F1 | 2025-11-04 04:00 | 2025-11-04 12:00 | −0.5 | +0.01174 |

**Concentration (size 0.5; size 1.0 analogous):**

- Top-5 compounded gain = **+8.68%** vs total pooled-OOS net **+7.56%** → the top 5
  trades carry **114.8% of the entire OOS gain** (116.2% for size 1.0). The
  remaining 25 trades compound to **−1.03%**.
- Top 5 = 5/30 trades (17%) but 61.9% of all positive-trade gain.
- Hit rate 50% (15/30); median trade **+0.03%**; the single best trade (Nov 20
  2025, an 8h hold) is 36.5% of the net gain.
- Per-fold OOS net: F1 +3.34%, F2 +0.87%, **F3 +0.00% (zero trades — structurally
  flat all of Feb–Mar 2026)**, F4 +3.18%. In position only **92 of 1,344 pooled OOS
  bars (6.8%)**. Two of four folds carry essentially everything, and the two F4
  monsters sit in the final two weeks of the data window.

**Accounting-semantics check (anti-"hook is rigged" angle).** Trade `pnl_pct`
excludes the exit fill cost (charged on the bar after the run), which IS inside the
pooled total — so `removed_gain` is slightly overstated and the hook is marginally
harsher than a perfectly-symmetric removal. Crediting the exit costs back:
top5_net = **−0.0091** (0.5) / **−0.0188** (1.0). Still clearly negative — no
accounting artifact explains the failure. Trades whose pnl extends past the fold
OOS boundary: **0**.

## 2. Perturbation grid (TC slice reassembled; n_null=300, seed base 17, per-fold seed 17+fold#)

Both sizes behave identically at clause level in every scenario; table shows size 0.5
(size 1.0 in `/tmp/lane3/part2_results.json`).

| scenario | E | OOS Sharpe | net@10 | null_p95 | top5_net | trades (F1/F2/F3/F4) | gate @N=5 | @N=3 | @N=8 |
|---|---|---|---|---|---|---|---|---|---|
| base (control) | 42 | 2.376 | +0.0756 | 2.089¹ | −0.0103 | 10/15/0/5 | fail: top5 | **PASS** | fail |
| E=63 | 63 | 2.708 | +0.0788 | 2.058 | −0.0073 | 8/15/0/5 | fail: top5 | **PASS** | fail |
| q=(0.15,0.85) | 42 | 2.656 | +0.0798 | 2.332 | −0.0024 | 10/10/0/5 | fail: top5 | **PASS** | fail |
| q=(0.25,0.75) | 42 | 2.999 | +0.1296 | 2.610 | **+0.0175** | 14/21/0/8 | **PASS (all 5)** | **PASS** | fail |
| boundaries +14d | 42 | 2.445 | +0.0766 | 2.413² | −0.0050 | 9/15/0/6 | fail: top5 | **PASS** | fail |
| boundaries −14d | 42 | **1.329** | +0.0375 | 2.107 | −0.0269 | 12/11/2/5 | **fail: null + top5** | fail | fail |

¹ 300-draw p95 vs 2.259 at the production 1000 draws — the null clause passes either way at base.
² null margin shrinks to 0.03 Sharpe (2.445 vs 2.413) — the null clause itself is near its own knife edge here.

**Flip analysis:**

- **Toward PASS:** widening the trade set — q=(0.25,0.75) lowers `funding_hi_abs`
  (≈8.4e-5 → ≈7.5–8.4e-5), trades 30→43, and the variant passes ALL FIVE clauses
  (top5 +1.75%, Sharpe 3.00 > null_p95 2.61). Likewise, top-N=3 passes in **5 of 6**
  scenarios. At q=(0.15,0.85) top5_net is −0.24% — within a quarter of a percent of
  flipping.
- **Toward clear fail:** boundaries −14d **halves the Sharpe (2.38→1.33)** and fails
  the null clause outright on the same data with the same rule. N=8 fails in **all**
  scenarios including the q25-75 pass.
- The pre-registered configuration sits between a one-knob PASS and a one-knob
  collapse. That is the definition of a knife-edge result, not a robust edge.

**Threshold knife-edge context.** The TC "pos-extreme" cut is q80 of |8h funding| ≈
**8.4e-5–9.8e-5** per fold — i.e. just BELOW Binance's 1e-4 baseline funding rate;
at q85 the quantile lands exactly ON the 1e-4 clump for F1–F3. OOS max |funding| is
only 1.1–1.2e-4. The entire "extremity" axis spans a microstructure-thin band
around the default funding rate, which is why ±0.05 of quantile moves the trade
count by ±40%, and why F3's OOS (funding never ≥ +cut) is structurally empty.

## 3. Size-pair sanity (0.5 vs 1.0)

- **Label series:** identical by construction (labels depend on taxonomy +
  thresholds only, not the action map) — confirmed.
- **Trade set:** identical 30 entry/exit timestamps; w exactly halved; pnl ratio
  0.436–0.508 per trade (≈0.5, not exactly — bar growth is multiplicative,
  `(1−|Δw|c)(1−wf)(1+wr)`, so halving w does not exactly halve compounded pnl;
  deviation largest on near-zero-pnl trades where cross-terms dominate).
- **null_p95:** common shuffles by construction, but values are NOT bit-identical
  (2.258935541611618 vs 2.2588581392110862): the null draw's bar-return series is
  not exactly scale-invariant in w for the same compounding reason, so each size's
  Sharpe (and hence p95) differs in the 4th decimal. Expected behavior, not a bug.
- Consequence: the pair is ONE effective hypothesis appearing as two records; its
  clause outcomes agree in every base and perturbed scenario tested.

## 4. Base rate: how surprising is one 4-of-5 near-miss in 36 variants?

Not surprising at all.

- **Null-clause pass count is exactly at expectation.** The clause is calibrated at
  5% per variant by construction (`expected_null_pass_rate` = 0.0500). Expected
  variants passing it: 36 × 0.05 = **1.8**. Observed: **2** — the H8 pair, i.e. one
  effective hypothesis.
- **Empirical near-miss rate under the global null** (200 common null draws pushed
  through the FULL gate with H8-0.5's own machinery, `/tmp/lane3/part3_baserate.py`):
  full-gate pass 2/200 = **1.0%**; fails-ONLY-top5 near-miss 3/200 = **1.5%**.
  Per-clause null pass rates: beats_hodl **98%** (HODL at −2.10 makes this clause
  nearly vacuous), beats_flat 63%, ladder 47%, null_pass 2.5%, top5_pass **5%**.
- With ~26 effective independent variants (10 direction hypotheses + 16 ladders;
  size pairs are duplicates), P(≥1 fails-only-top5 near-miss somewhere in a fully
  null sweep) ≈ 1 − (1−0.015)^26 ≈ **32%** (≈42% if the null clause runs at its
  5% design rate). Roughly **one in three fully-null sweeps of this design shows
  exactly what we observed.**
- Corroborating: of the 5 null draws that cleared the 95th-percentile null clause,
  3 still failed top5 — concentration is the DEFAULT shape of a lucky draw here,
  which is precisely why the clause was registered.

## 5. Both-ways adversarial conclusions

**(a) Did the pipeline destroy a real edge?** The top-5 clause is brutal in this
setting: removing 5 of ~30 trades, only 5% of even the null draws pass it, and a
true rare-event fade edge would be concentrated by construction — so the clause has
low power to admit a genuinely concentrated edge, and the q25-75 full pass shows a
plausibly-real wider version of the same hypothesis clears everything. AGAINST
that: the breadth evidence is genuinely absent (25 remaining trades net −1.0%, hit
rate 50%, median trade +3bp, zero exposure for one entire fold, 6.8% of OOS bars in
position), the exit-cost accounting check above rules out a mechanical artifact,
the shift−14d collapse (Sharpe 1.33, null fail) shows the OOS performance itself is
boundary-placement luck to a substantial degree, and the variant is short-only in a
window where HODL's Sharpe is −2.10 (its beats_hodl clause is near-vacuous, 98%
null pass rate). No pipeline bug was found in this lane; the hand recompute matched
the artifact to 10 decimals.

**(b) Can the near-miss be talked past the gate?** Every route to a PASS found here
(q25-75, N=3) is an un-registered analyst degree of freedom exercised AFTER seeing
the OOS — exactly the move ADR-001 exists to forbid, and exactly how a false
survivor would be manufactured: among the 6 single-knob settings tested, at least
one flips to PASS, which on ~26 effective variants would mint survivors from noise
at well above the gate's designed 1–1.5% false-pass rate.

**Recommendation for the falsification chapter.** Report H8 as: "one near-miss, at
the base rate expected from a null sweep (P≈1/3 of sweeps), with >100% of its OOS
gain in its top-5 trades, flippable to PASS by a single un-registered parameter
change and to a 2-clause fail by a 2-week boundary shift." If the hypothesis family
(fade positive funding extremes) is pursued post-contest, it requires a NEW
pre-registration on data after 2026-06-09 — q=(0.25,0.75) and N=3 cannot be adopted
retroactively.

---
*Lane 3 scratch artifacts: `/tmp/lane3/part1.py` (top-5 recompute),
`/tmp/lane3/part2.py` + `part2_results.json` (perturbation grid),
`/tmp/lane3/part3_baserate.py` (null clause tally), `/tmp/lane3/occupancy.py`,
`/tmp/lane3/perfold.py`. Run with `uv run --no-sync python <script>`.*
