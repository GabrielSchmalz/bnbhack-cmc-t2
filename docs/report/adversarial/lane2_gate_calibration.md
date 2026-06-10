# Lane 2 — Gate calibration: can this pipeline pass ANYTHING real?

**Question.** The sweep produced 0/36 survivors (R-NULL). That null is only
meaningful if a true edge would survive the machinery. This lane plants a
known regime-conditional edge into the REAL panel and runs the UNMODIFIED
`lab.sweep` pipeline (real PR-6 folds, R1 per-fold-train thresholds,
episode-shuffle null, DD guard, cost ladder, full 5-clause gate) to measure
the gate's detection threshold.

**Verdict.** The pipeline detects and passes a planted regime-conditional
drift of **10 bps/bar robustly (rank #1 on train + all 5 clauses pass), and
5 bps/bar marginally (passes the gate at train rank #3; still the ADR-001
Winner since the two higher-ranked variants fail)**. At 0 bps (the committed
real sweep) the aligned variant fails exactly one clause (top-5 removal).
The null result is therefore **not** an artifact of a pipeline that destroys
real edges — at these costs (10 bps RT) and this noise substrate, nothing
real cleared a bar that a ~5–10 bps/bar conditional edge clears easily.
All three directed wiring probes (drift-sign flip, cost wiring, rules.apply
lag) behave correctly.

Run by: adversarial Lane 2, 2026-06-10. Scratch scripts and full result
JSONs: `/tmp/lane2/lane2_calibrate.py`, `/tmp/lane2/lane2_probes.py`,
`/tmp/lane2/lane2_sweep_edge{5,10,25,50}bps.json` (+ run logs). Nothing in
`lab/`, `tests/`, or `artifacts/` was modified; `run_sweep` was called
directly (it does not write artifacts).

---

## 1. Planted-edge construction (documented per assignment)

Substrate: the real panel, `add_features(load_panel("full"))` — 2598 4h bars,
2025-04-03 00:00 → 2026-06-09 20:00.

- **Aligned variant:** `DIR-TC-H8-fade_pos_extreme_only` (the real sweep's
  near-miss). Action map: short −1 in `pos-extreme`, flat elsewhere;
  `rules.apply` lags one bar, so the variant is positioned on the bar AFTER
  each pos-extreme label.
- **Injection mask:** TC labels computed once from thresholds derived on the
  FULL window of the unperturbed features (`funding_hi_abs = 8.051e-05`).
  TC depends only on `funding_rate_8h`, which the price perturbation never
  touches, so the mask is invariant under injection. Mask:
  `positioned[t] = (label[t-1] == 'pos-extreme')` — 472/2598 bars (18.2%),
  150 of the 1344 pooled-OOS bars.
- **Drift:** per positioned bar `t`, `d_t ~ Normal(edge, edge)` (seeded
  `default_rng(99)`; noise sd = mean keeps E[d]=edge with realistic
  dispersion on top of the real market noise); `d_t = 0` elsewhere.
- **Price path:** multiplicative and self-consistent.
  `M_open[t] = Π_{s<t}(1−d_s)`, `M_close[t] = M_open[t]·(1−d_t)`;
  `open' = open·M_open`, `close' = close·M_close` (the close of bar t sits at
  open[t+1] time, so the whole bar-t drift lands inside bar t); high/low
  scaled by `M_close` then enveloped to contain open'/close'. Hence
  `r'[t] = (1+r[t])(1−d_t)−1 ≈ r[t]−d_t`: a short earns +d_t expected per
  positioned bar. Funding, OI, F&G, volume untouched; the daily RSI/SMA
  features are recomputed from the perturbed closes (fully consistent world).
- The perturbed panel then goes through the unmodified
  `lab.sweep.run_sweep` with the production fold/threshold/null/guard/gate
  machinery.

**Deliberate realism in the construction (and its consequence):** the
pipeline re-derives thresholds per fold-train (R1), so the variant's actual
positions only partially overlap the injection mask. Per-fold
`funding_hi_abs` came out 8.39e-5 … 9.78e-5 (all stricter than the mask's
8.05e-5), so H8's positions are a strict SUBSET of masked bars: it held
92 of the 150 drift-carrying pooled-OOS bars (F1 34/60, F2 38/66, F3 0/0,
F4 20/24; full-index Jaccard 0.665/0.720/0.805/0.911 by fold). F3 OOS has
zero pos-extreme bars under both threshold sets — funding was calm
2026-02→04, so the pooled OOS edge is carried by F1/F2/F4 only. Detection
numbers below already include this realistic threshold-mismatch haircut.

**Null-draw counts:** 25 bps rung at the pre-registered n_null = 1000;
the 5/10/50 rungs at n_null = 300 (runtime budget, as permitted by the
assignment); `n_gate_null = 200` everywhere. Wall times 72–245 s per rung
(8 cores).

## 2. Power curve

The 0 bps row is the committed real sweep (`artifacts/sweep_results.json`),
which is by construction the planted run's baseline. All numbers are for
`DIR-TC-H8-fade_pos_extreme_only-1.0` at the gate rung (10 bps RT) on pooled
OOS; the −0.5 twin behaves identically on every clause at every rung.

| edge (bps/bar) | n_null | H8 train rank | rank_key | OOS Sharpe | OOS net | null_p95 | top5 net | net @20bps | gate | total passes /36 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 (real sweep) | 1000 | #4 (of 36) | 0.96 | 2.38 | +15.50% | 2.26 | **−2.13%** | +12.1%* | **fail: top5 only** | 0 |
| 5 | 300 | #3 | 2.14 | 2.94 | +19.98% | 2.17 | +0.59% | +16.4% | **PASS** | 2 (H8 pair) |
| 10 | 300 | **#1** | 3.29 | 3.48 | +24.62% | 2.25 | +3.38% | +20.9% | **PASS** | 2 (H8 pair) |
| 25 | 1000 | **#1** | 6.34 | 4.83 | +39.62% | 2.79 | +12.19% | +35.5% | **PASS** | 6 (H8/H7/H10 pairs) |
| 50 | 300 | **#1** | 9.85 | 6.30 | +68.61% | 3.11 | +28.52% | +63.6% | **PASS** | 6 (H8/H7/H10 pairs) |

\* baseline @20bps value from the committed artifact's ladder.

**Power statement for the report:** on the real full-stack panel at 10 bps RT
costs, the pre-registered gate detects an additional regime-conditional edge
on this action-map shape at **≥ 10 bps/bar robustly** (train rank #1 and all
five clauses pass with margin) and at **5 bps/bar marginally** (gate passes;
top-5 margin only +0.59%, single drift seed — treat as the edge of
detectability, not as reliable power). 10 bps/bar over the 92 held OOS bars
is ≈ +9.6% incremental OOS net — a modest, realistic edge size. Nothing real
cleared it.

Sanity reconciliations: at 10 bps the observed OOS net lift
(15.50%→24.62%) matches the hand-computed 92 bars × 10 bps ≈ +9.6% within
the injected-noise dispersion; per-fold train Sharpes are flat across folds
at every rung (e.g. 3.14–3.47 at 10 bps), as expected for a window-wide
planted effect.

## 3. What the rungs say about each gate clause

- **top5 (the clause that killed the real near-miss):** moves
  −2.13% → +0.59% → +3.38% → +12.19% → +28.52% across rungs. It is the
  binding clause at small edge sizes, i.e. the gate's effective detection
  threshold IS the top-5-removal clause for this concentrated-exposure
  shape (30 OOS trades, ~92 positioned OOS bars). Equivalently: the real
  H8's failure margin is **less than ~5 bps/bar of true per-bar edge**.
  That cuts both ways and is reported as such: the gate is not absurdly
  strict (a 5 bps/bar true edge passes), and the near-miss is genuinely
  close — but it failed the pre-registered binary clause, and this lane
  found no defect in that clause's mechanics.
- **null clause is conservative against real edges:** null_p95 RISES with
  the planted edge (2.25 → 2.79 → 3.11). Episode-shuffled labels still
  overlap drift-carrying bars by chance, so the null inherits part of any
  real edge. A true edge must beat a null that partially contains it —
  this biases toward false NEGATIVES, never false positives. Consistent
  with direction (a) of the adversarial brief: noted, measured, and it did
  NOT prevent detection at 5 bps/bar.
- **R3 calibration is stable in planted worlds:** expected null-clause
  pass-rate stays 0.0500 at every rung; the full-gate null pass-rate of the
  top variant stays 1.5–2.0% (200 draws) with and without a planted edge.
  The observed real-sweep values (5.0% / 1.5%) are therefore not artifacts
  of a miscalibrated null machine.
- **Correlated co-passes:** at 25/50 bps, H7 and H10 (which share the
  short-pos-extreme leg) pass alongside H8 — the gate has no
  family-wise-error control across correlated variants, exactly as ADR-001
  R3 already discloses. At 5–10 bps only the aligned H8 pair passes.
- **beats_hodl caveat:** the injection mechanically degrades HODL (TC
  pooled-OOS Sharpe −2.10 → −2.58/−3.29/−4.40 across rungs) since planted
  bars drift the price down. Not material: beats_hodl already passed at
  baseline; the binding clause was top5 throughout.
- **Cost ladder:** monotone decreasing in cost at every rung (e.g. 10 bps
  rung: +26.5%/+24.6%/+20.9% at 5/10/20 bps), matching probe (ii).

## 4. Directed wiring probes (lab.sweep internals, tiny/synthetic frames)

Synthetic panel for (i)/(iii): real 4h calendar grid (PR-6 folds need it),
near-flat price (5 bps/bar noise), funding stamps engineered so ~23% of bars
are TC-extreme (2-bar episodes — the minimum on a 4h grid with 8h funding
stamps), drift planted deterministically at 25 bps. Full `run_sweep` with
n_null=20, n_gate_null=0.

**(i) Drift-sign flip — PASS (TC-scoped).**
- Drift DOWN after pos-extreme: top TC variant = `DIR-TC-H8-…-0.5`
  (rank_key +18.98, global #3/#4); the only menu variant LONG pos-extreme
  (`RISK-TC-ladder-1_0.25_1_1`, weight 0.25) sinks to rank_key −19.83.
- Drift UP (sign flipped): H8 collapses to global #28, rank_key −24.77;
  `RISK-TC-ladder-1_0.25_1_1` becomes the top TC variant. (The PR-8 menu
  contains no direction-family "follow pos-extreme" map; the 0.25-weight
  risk ladder is the only counterparty, and it surfaced as predicted.)
- Finding, not a defect: on the near-flat synthetic, the GLOBAL top in both
  directions is `DIR-TB-H3-follow_all` (rank_key 22.8/13.1) — a planted
  conditional drift with nonzero unconditional mean creates a price trend
  that the TB trend feature legitimately captures across ALL bars. The same
  is true of real conditional edges; on the real panel (Section 2) the
  trend variants do not confound because real volatility dwarfs the
  injected unconditional component.

**(ii) Cost wiring — PASS (exact).** 8-bar flat-price frame through
`rules.apply` + `run_backtest` (the sweep's step-4 path) with the real H8
action map forcing 7 fills: net@0bps = 0 exactly; net@10bps =
(1−5e-4)^7 − 1 = −3.494754e-03, matching the engine output to 1e-12.
Direction and magnitude of cost handling are correct (corroborated at scale
by the monotone ladders in Section 3).

**(iii) rules.apply lag — PASS (sharp tent at lag 1).** Drift planted at
shifts {0,1,2,3} bars after the pos-extreme label bar. With 2-bar episodes
the overlap with H8's lagged position is {50%, 100%, 50%, 0%}, and H8's
rank_key tracks it exactly:

| plant shift | 0 | 1 (= rules lag) | 2 | 3 |
|---|---|---|---|---|
| H8 rank_key | 10.24 | **18.98** | 8.24 | −15.06 |
| H8 OOS net | +20.9% | +67.3% | +20.6% | −12.8% |

Peak precisely at shift 1; at shift 3 (zero overlap) the variant earns
nothing and the result equals the pure cost drag (~134 OOS round trips
× 10 bps RT ≈ −13%, observed −12.8%). A look-ahead bug would have peaked at
shift 0; there is none.

## 5. Limitations of this calibration

1. **Baseline contamination:** the substrate is the real panel, so the
   planted rungs sit ON TOP of H8's real near-miss pattern (baseline OOS
   Sharpe 2.38). The power statement is explicitly "additional edge needed
   on this substrate for this shape" — it cannot be read as power on a
   pattern-free world. The 0-rung anchor makes this honest: the committed
   sweep IS the 0 bps row.
2. **Single drift seed (99) per rung; one aligned shape (H8/TC).** The
   5 bps marginal pass (top5 +0.59%) could flip under another seed; the
   robust claim is the 10 bps rung. Power for other action-map shapes
   (e.g. high-turnover risk ladders, whose cost drag is larger) was not
   measured and is plausibly worse.
3. **Mask uses full-window thresholds** while the pipeline uses per-fold
   thresholds — this UNDERSTATES capture (subset overlap, Section 1), so it
   biases the measured detection threshold conservatively (upward), not in
   the pipeline's favor.
4. n_null = 300 on the 5/10/50 rungs (1000 on 25, pre-registered value);
   null_p95 at 300 draws is slightly noisier but the pass margins at ≥10 bps
   are not close.

## 6. Conclusion for the shipping decision (not ours to make)

The full pre-registered machinery — folds, R1 thresholds, episode-shuffle
null, DD guard, cost ladder, all five gate clauses — passes a genuine
regime-conditional edge of 5–10 bps/bar planted on the real panel, with the
aligned variant ranking #1 on train from 10 bps/bar. The wiring probes
confirm direction, costs, and the 1-bar lag are correct. Direction (a) of
the brief (pipeline destroys real edges → null is an artifact) is
**refuted for this family/shape**: the R-NULL outcome stands as evidence
about the data, not the machinery. Direction (b) (talking the near-miss
past the gate): the calibration quantifies the near-miss's shortfall at
under ~5 bps/bar of true edge equivalent, and finds the clause that failed
it (top5) mechanically sound and the binding detection margin of the gate —
the close call is real, and so is the fail.
