# Backtest report — BTC funding-regime Skill (BNB HACK 2026, Track 2)

Plan Task 4.1 (amended, R-NULL branch) · 2026-06-10 · binding inputs:
`docs/FREEZE.md`, ADR-001 (`docs/adr/001-select-on-train-gate-on-oos.md`),
CONTEXT.md. Every number below is re-derivable from committed files; the
artifact path is cited next to each table. Figures regenerate via
`uv run --no-sync python -m lab.report_figs` (which asserts its recomputed
numbers against `artifacts/sweep_results.json` to 1e-9 before drawing).

---

## 1. Headline: no strategy cleared our pre-registered shipping gate (0/36)

We swept **36 pre-registered variants** (two families × three taxonomy
candidates, enumerated in code, `lab/variants.py`) through a purged/embargoed
walk-forward on BTCUSDT 4h, selected on train, and gated on pooled OOS with a
five-clause shipping gate at 10 bps round-trip costs. **Zero variants
passed.** The expected pass-rate of the gate's null clause under the
episode-shuffle null is 5.0%; the observed full-gate pass rate of the top
train-ranked variant over 200 null draws is 1.5%. The outcome is consistent
with no detectable edge in this variant space on this window — and we ship
that result as-is.
*Source: `artifacts/sweep_results.json` → `.globals.r3`;
`artifacts/sweep_summary.md`.*

![pooled OOS equity overlay](figs/fig1_pooled_oos_equity.png)

**What survived is the machinery, and it is the submission:**

- **A calibrated shipping gate.** The unmodified pipeline passes a planted
  regime-conditional edge of **≥ 10 bps/bar robustly and 5 bps/bar
  marginally** on the real panel (§3.4). The null result is evidence about
  the data, not the machinery.
- **A reproducible lab.** An independent adversarial lane re-wired the fold
  pipeline from the plan text and reproduced every compared scalar
  **bit-for-bit (max |diff| = 0.0)** from the committed CSVs (§3.5).
- **An honest monitor.** The Skill (`skills/btc-funding-regime-monitor/`)
  ships as a **regime monitor**: the frozen TC taxonomy
  (`pos-mild · pos-extreme · neg-mild · neg-extreme`, funding-only), the
  frozen F4-train threshold `funding_hi_abs = 8.385600000000002e-05`, and
  per-regime expected-behavior notes that are F4-train descriptive statistics
  — every note carries `"validated": false`, and no entry/exit/sizing is
  emitted at runtime, because the shipping gate validated none.
  *Source: `docs/FREEZE.md` §2–§3.*

**Honest N.** The headline sample-size unit is the pooled-OOS **regime
episode** count (ADR-001 R2): **TC = 225** (52/48/60/65 by fold; TA = 250,
TB = 105), with embargo E = 42 bars at every fold boundary. That is a
taxonomy-level count. Per the freeze's active-sample rule, any statement
about the near-miss candidate quotes its **active** OOS sample instead:
**30 trades / 92 nonzero-position bars (6.8% of 1,344 pooled-OOS bars) /
3 of 4 folds** — roughly 7× smaller than the taxonomy-level honest-N.
*Source: `artifacts/sweep_results.json` → `.globals.taxonomies`;
`docs/FREEZE.md` §3 amendment 4, §6.*

Why we lead with a null in front of this panel: the alternative — quietly
widening one quantile or trimming one clause until a "Winner" appears — was
available, measured, and refused (§3.3). The pre-registered configuration
is the entry; the near-miss it caught is the demonstration that the gate
works.

---

## 2. Method

### 2.1 Select on train, gate on OOS (ADR-001)

Ranking key = mean per-fold **train** Sharpe @10 bps RT (tiebreak: lower mean
train max-DD). Pooled OOS is used ONLY as a binary pass/fail gate, never as a
ranking key. Refinements binding on the lab:

- **R1 — train-only thresholds.** Every absolute threshold is re-derived per
  fold on that fold's train rows only; nothing inherits the rm17 full-sample
  cuts (whose window overlaps the OOS).
- **R2 — walk-forward honest-N.** The gate runs on a purged/embargoed
  walk-forward; the headline N is the pooled-OOS regime-episode count, not
  trades or bars.
- **R3 — multiple-testing disclosed.** Total variants, gate passes, and the
  expected pass-rate under the shuffle null are published (§3.1), not waved
  away.

### 2.2 Walk-forward (PR-6)

Expanding folds, calendar-UTC boundaries, embargo E = max(42 bars, median
regime-episode length) = **42 bars (7 days)** for all three taxonomies.

```
full-stack window: 2025-04-03 00:00 -> 2026-06-09 20:00 UTC (2,598 4h bars)

F1  |== train 2025-04-03 .. 2025-10-01 ==|--E--|== OOS 10-08 .. 11-30 ==|
F2  |== train 2025-04-03 .. 2025-12-01 ========|--E--|== OOS 12-08 .. 01-31 ==|
F3  |== train 2025-04-03 .. 2026-02-01 ==============|--E--|== OOS 02-08 .. 03-31 ==|
F4  |== train 2025-04-03 .. 2026-04-01 ====================|--E--|== OOS 04-08 .. 06-09 ==|
         (train = every bar strictly before the boundary; E = 42-bar embargo)
```

Pooled OOS = concatenated fold-OOS segments: 324 + 330 + 312 + 378 =
**1,344 bars**. Per-fold thresholds derive on that fold's train only (R1);
the shipped frozen thresholds are the F4-train numbers — the exact numbers
gated on F4 OOS (validated thing ≡ shipped thing).
*Source: `artifacts/sweep_results.json` → `.globals.taxonomies.*.per_fold`;
fold geometry independently reproduced in
`docs/report/adversarial/lane1_reproduction.md` §1.*

### 2.3 Execution model (PR-3, fixed across all variants)

| constant | value |
|---|---|
| bars | BTCUSDT 4h (`data/lab/bars_4h.csv`) |
| fill | decided at close t → next-bar-open fill (1-bar lag lives in `lab/rules.py`, verified by a lag-tent probe, §3.4) |
| bar return | r[t] = open[t+1]/open[t] − 1 (final bar: close/open − 1) |
| costs | round-trip c bps ⇒ per-side c/2 bps on \|Δw\| traded notional; ladder {5, 10, 20}, gate rung 10 |
| funding | accrues at 00/08/16 UTC stamps: equity ×= 1 − w·rate; **short earns positive funding** (R-FUND, test-pinned, hand-verified on raw rows to 1e-16) |
| sizing | w ∈ [−1, 1], no leverage |
| DD guard | PR-4: trailing 20% equity stop, flat until next regime-label change; variants only, never benchmarks; never swept |
| Sharpe | annualized √2190 (4h bars/yr), population std |

### 2.4 Feature source consistency (PR-2 final — one source per Feature, train+OOS)

| Feature | source of record | decision & evidence |
|---|---|---|
| price / TA | `binance_klines` 4h → `data/lab/bars_4h.csv` | single live source; 7 byte-identical duplicate stamps dropped (D4.1) |
| funding | **Binance REST `fapi/v1/fundingRate` end-to-end** → `data/backfill/funding_btcusdt_binance.csv` | The CoinGlass relay **switched storage convention mid-stream on 2025-04-08** (settled-decimal-settlement-stamped → predicted-percent-interval-start-stamped). The naive pre-registered cross-check therefore failed (19.4% of rows < 1e-6); convention-aware, the two relays agree — pre-switch 291/291 rows exact, post-switch max \|diff\| = 7.768e-05 (0.78 bp on an 8h rate), 100% join coverage. This is precisely the mid-window relay hazard R-SRC exists to catch; the CG table is disqualified as a lab source. *Source: `data/backfill/funding_crosscheck.txt`.* |
| OI (level, Δ24h) | `oi_snapshots` venue=**bybit** → `data/lab/oi_bybit.csv` | only venue spanning the full-stack window (binance starts 2026-04-02). Cadence unified to daily 00:00 snapshots across the whole window (D4.2) so a mid-window cadence change cannot masquerade as a regime shift. |
| F&G | **CMC Pro REST `/v3/fear-and-greed/historical` only** → `data/backfill/fear_greed.csv` | CMC span 2023-06-29 → 2026-06-09 covers the window; fallback not triggered; identical source to what the shipped Skill reads live. *Source: `data/backfill/fg_source_decision.txt`.* |
| CVD | **DROPPED** | `cg_cvd_history` went stale 2026-05-29, mid-OOS (R-SRC; pre-approved drop) |
| LS-skew, DVOL | lab discovery only | never distilled — no Gate-0-verified CMC field (LS), not a CMC field (DVOL) |

**OI-hole sensitivity note (D4.3).** Two ~12.5-day OI/LS gaps
(2026-04-12→04-24, 2026-05-16→05-29) sit inside F4 OOS. Policy: NaN under
the staleness cap; any classifier clause referencing a NaN Feature evaluates
FALSE (deterministic, test-pinned). Consequently **TA/TB variants ran with
NaN→FALSE OI clauses on 142 of 378 F4-OOS bars** (~150; re-derivable as the
`oi_chg_24h` NaN count over the F4 OOS index of
`add_features(load_panel("full"))`). **TC consumes no OI** — the frozen
monitor taxonomy is unaffected by the holes, which is one of the pre-stated
reasons TC was frozen (`docs/FREEZE.md` §2).

---

## 3. Falsification chapter

This is the centerpiece. Both ways a null can be wrong — "the pipeline
destroyed a real edge" and "a real edge is being talked past the gate" —
were attacked by three independent adversarial lanes. Neither holds.

### 3.1 R3 disclosure (the denominator)

| quantity | value |
|---|---|
| variants swept | **36** |
| shipping-gate passes | **0** |
| expected pass-rate of the null clause under the shuffle null | **0.0500** (~5% by construction) |
| full-gate pass rate, top train-ranked variant, 200 null draws | **0.015** |
| observed null-clause passers | 2 of 36 (expected 1.8) — and they are one strategy at two sizes |

*Source: `artifacts/sweep_results.json` → `.globals.r3`;
`docs/report/adversarial/lane3_near_miss.md` §4.*

Disclosure: the beats-HODL clause was **near-vacuous on this window** — HODL's
pooled-OOS Sharpe is −2.10, so 98% of null draws clear that clause
(lane 3 §4). The clauses doing the real work were the shuffle null and
top-5 removal.

### 3.2 Anatomy of the near-miss: `DIR-TC-H8-fade_pos_extreme_only-{0.5,1.0}` — FAILED, `"validated": false`

The full spec, published here and only here (never as a tradable
recommendation):

- **Rule:** if the prior bar's TC label is `pos-extreme`
  (funding_rate_8h ≥ 0 and \|funding_rate_8h\| ≥ the fold-train q80 cut;
  F4-train: 8.385600000000002e-05), hold w = −size next bar
  (next-bar-open fill); flat otherwise. Sizes 0.5 / 1.0.
- **Execution:** PR-3 model, PR-4 DD guard (never fired in OOS), 10 bps RT
  gate rung, thresholds per-fold train-derived (R1).
- **Train rank:** #4/#5 of 36 (rank key 0.956) — not the top train pick.
- **Pooled OOS:** Sharpe 2.3763 / 2.3761, net +7.56% / +15.50%, 30 trades,
  92 of 1,344 OOS bars in position (6.8%), **F3 = zero trades** (funding
  never reached the positive cut Feb–Mar 2026).
- **Gate:** PASSES beats_flat, beats_hodl, the shuffle null (2.376 >
  null_p95 2.259; one-sided p ≈ 0.036), and the cost ladder
  (net @5/10/20 bps: +17.25%/+15.50%/+12.09% at size 1.0).
  **FAILS top-5 removal: top5_net = −1.03% / −2.13%.**

*Source: `artifacts/sweep_results.json` → variant records
`DIR-TC-H8-fade_pos_extreme_only-{0.5,1.0}`; `docs/FREEZE.md` §4.*

**The failure is substantive, not technical.** The 5 best trades — all
crash-day shorts — carry **114.8% / 116.2% of the entire OOS gain**; the
remaining 25 trades compound to **−1.03%**; hit rate 50%, median trade
+3 bp. The five removed trades (size 0.5; identical timestamps at size 1.0
at ~2× pnl):

| fold | entry | exit | w | pnl |
|---|---|---|---|---|
| F1 | 2025-11-20 12:00 | 2025-11-20 20:00 | −0.5 | +2.76% |
| F2 | 2025-12-29 04:00 | 2025-12-29 20:00 | −0.5 | +1.53% |
| F4 | 2026-06-01 20:00 | 2026-06-02 12:00 | −0.5 | +1.50% |
| F4 | 2026-05-27 04:00 | 2026-05-28 12:00 | −0.5 | +1.43% |
| F1 | 2025-11-04 04:00 | 2025-11-04 12:00 | −0.5 | +1.17% |

*Source: `docs/report/adversarial/lane3_near_miss.md` §1 (hand-recomputed,
matches the artifact to 10 decimals).*

![H8 concentration](figs/fig2_h8_concentration.png)

The one accounting asymmetry found (trade pnl excludes the exit fill cost,
making the hook marginally harsher) was checked: crediting exit costs back
leaves top5_net at **−0.91% / −1.88%** — still clearly negative. No
accounting artifact explains the failure (lane 3 §1).

**The null-clause margin is selection noise.** H8's unguarded pooled-OOS
Sharpe sits at the 96.4th percentile of its own 1000-draw null (p ≈ 0.036).
Across 36 variants the expected count of variants clearing their own null
p95 by chance is 1.8; observed 2 — the H8 pair, i.e. **one effective
hypothesis at two sizes**. A fails-only-top-5 near-miss arises in **~1 of 3
fully-null sweeps of this design** (≈1.5% per variant × ~26 effective
hypotheses). What we observed is the expected silhouette of a null sweep.
*Source: `docs/report/adversarial/lane3_near_miss.md` §4.*

![null distribution](figs/fig3_null_distribution.png)

*(Figure 3's 1,000 pooled null Sharpes are regenerated from the committed
CSVs with the sweep's exact seeds — numpy `default_rng(17 + fold#)`, common
draws — in ~31 s by `lab/report_figs.py`, which asserts the regenerated p95
equals the artifact value to 1e-9.)*

### 3.3 The knife-edge — including the two knobs we refuse to turn

Lane 3 perturbed the already-failed configuration in both directions
(post-hoc exploration of a pre-registered, already-failed gate; nothing here
re-opens the decision). Size 0.5 shown:

| scenario | OOS Sharpe | null_p95 | top5_net | gate @N=5 | @N=3 |
|---|---|---|---|---|---|
| base (pre-registered) | 2.376 | 2.089¹ | −1.03% | fail: top5 | PASS |
| embargo E=63 | 2.708 | 2.058 | −0.73% | fail: top5 | PASS |
| q=(0.15,0.85) | 2.656 | 2.332 | −0.24% | fail: top5 | PASS |
| **q=(0.25,0.75)** | 2.999 | 2.610 | **+1.75%** | **PASS (all 5)** | PASS |
| boundaries +14d | 2.445 | 2.413 | −0.50% | fail: top5 | PASS |
| **boundaries −14d** | **1.329** | 2.107 | −2.69% | **fail: null + top5** | fail |

¹ 300-draw p95 (vs 2.259 at the production 1,000 draws); the null clause
passes either way at base.
*Source: `docs/report/adversarial/lane3_near_miss.md` §2.*

Two **un-registered knobs flip the verdict to PASS**: widening the
threshold quantiles to q=(0.25,0.75) (more trades → the concentration
dilutes → all five clauses pass), or shrinking the removal count to
top-N=3 (passes in 5 of 6 scenarios). **We refuse both.** They were not
pre-registered; exercising either after seeing the OOS is exactly the
analyst degree of freedom ADR-001 exists to forbid — and on ~26 effective
hypotheses, allowing one post-hoc knob per variant would mint survivors
from noise at well above the gate's designed 1–1.5% false-pass rate. The
same grid shows the OOS performance itself is boundary-placement luck to a
substantial degree: shifting fold boundaries **−14 days halves the Sharpe
(2.38 → 1.33)** and fails the null clause outright on the same data with
the same rule. A result that one knob flips to PASS and another knob
collapses to a 2-clause fail is a knife edge, not an edge.

### 3.4 Gate calibration: the machinery can pass a real edge (lane 2)

A known regime-conditional drift was planted into the **real** panel
(price-path perturbation aligned with H8's action map; funding/labels
untouched) and pushed through the **unmodified** pre-registered pipeline —
real folds, R1 thresholds, episode-shuffle null, DD guard, full gate:

| planted edge (bps/bar) | H8 train rank | OOS Sharpe | top5_net | gate |
|---|---|---|---|---|
| 0 (= the committed real sweep) | #4 | 2.38 | −2.13% | fail: top5 only |
| 5 | #3 | 2.94 | +0.59% | **PASS** (marginal) |
| 10 | **#1** | 3.48 | +3.38% | **PASS** (robust) |
| 25 | #1 | 4.83 | +12.19% | PASS |
| 50 | #1 | 6.30 | +28.52% | PASS |

*Source: `docs/report/adversarial/lane2_gate_calibration.md` §2 (figure 4
hardcodes this table and cites the same file).*

![gate power curve](figs/fig4_gate_power.png)

**Power statement:** at 10 bps RT on this panel, the shipping gate detects a
true conditional edge of **≥ 10 bps/bar robustly** (train rank #1, all five
clauses with margin) and **5 bps/bar marginally** (single seed; treat as the
edge of detectability). Equivalently, the real H8's shortfall is **less than
~5 bps/bar of true per-bar edge** — the close call is real, and so is the
fail. The top-5 clause is the gate's binding detection margin for this
concentrated shape. Three directed wiring probes all behaved correctly:
drift-sign flip (aligned variant collapses to rank #28 when the sign
flips), exact cost arithmetic ((1−5e-4)^7 − 1 matched to 1e-12), and a
lag tent that peaks **exactly at the rules lag of 1 bar** (a look-ahead bug
would peak at 0). R3 calibration is stable in planted worlds (5.0% /
1.5–2.0%).

**Conservative null design (disclosure).** The episode-shuffle null permutes
episodes over the whole index, so null draws hold the **global** share of
short-labeled bars inside the OOS, while the real variant's OOS share is
much lower (F1 10.5%, F2 11.5%, F3 0%, F4 5.3%). In a falling OOS the null
therefore carries *more* short exposure than the variant and its Sharpe
distribution shifts up — and with a planted edge, shuffled labels still
overlap drift-carrying bars, so null_p95 *rises* with the edge (2.25 → 3.11
across rungs). Both effects bias toward **false negatives only**, never
false positives. This is pre-registered behavior, disclosed; it did not
cause the H8 failure (H8 passed its null clause).
*Source: `docs/report/adversarial/lane1_reproduction.md` §6;
`lane2_gate_calibration.md` §3.*

### 3.5 Independent reproduction (lane 1)

An adversarial lane rebuilt the fold loop, threshold derivation calls,
pooled metrics, shuffle null, and top-5 formula **independently of
`lab.sweep`/`lab.hooks`/`lab.walkforward`/`lab.gate`/`lab.metrics`** and
reproduced every compared scalar in `artifacts/sweep_results.json` —
per-fold train Sharpes, rank keys, pooled OOS metrics, null_p95, top5_net,
full cost ladders, and all taxonomy globals — with **max |difference| = 0.0**
(demanded tolerance 1e-9). R1 hygiene was proven the strong way: all 6
thresholds × 4 folds recomputed **from raw CSVs truncated strictly before
each fold boundary, zero lab imports** — exact match, so no OOS row
influences any threshold, including through feature construction. Trade
PnL, cost sides, and the R-FUND sign were hand-verified on raw rows to
1e-16. The bear OOS is the market, not the engine: the four raw-bar OOS
segments compound to ≈ −46%, matching HODL's −45.9% net.
*Source: `docs/report/adversarial/lane1_reproduction.md` §1–§6.*

### 3.6 Band provenance: "Band-inspired, independently gated"

The TC taxonomy's normalized mutual information against the rm17-derivs
Bands on their overlap is **0.0228** — near independence (TA: 0.0453; TB's
0.211 is carried by the trend clause co-locating in calendar time with the
Band mix, and Bands are direction-less, so it is not distillation evidence
either). We therefore claim **no Band distillation** for the shipped
taxonomy: the honest framing is *Band-inspired, independently gated on its
own walk-forward*. Bands never appear in the shipped Skill.
*Source: `docs/report/band_recon.md`.*

### 3.7 Prior internal nulls (cited, not hidden)

An unpublished internal study on the same regime-matrix dataset, run under a
stricter research evidence bar, found the Band (L1) forward-return main
effects **null at 4h**, and a 1h DVOL lead that **died in causal OOS**. This
sweep's null is consistent with those results, and we cite them rather than
shopping the same data for a friendlier bar.

### 3.8 The frozen monitor (what the Skill actually ships)

With no Survivor, the Skill ships as a regime **monitor** on the frozen TC
taxonomy — selected on pre-stated criteria that never touch variant OOS
performance: label stability under threshold re-derivation (5.2% relabel
F1→F4 vs TA 48.0% / TB 28.4%), episode uniformity across folds, and
live-computability (one Gate-0-verified field, in the sanctioned scale-free
sign + extremity-band form). The monitor emits regime + a live
`signal_snapshot` + F4-train expected-behavior notes, each
`"validated": false`; it emits **no** entry/exit/sizing, and its
`validated_metrics_ref` points at this chapter. The pos-extreme note
cross-references this chapter explicitly: the negative train-period drift
after pos-extreme labels is precisely the pattern whose tradable form
FAILED the gate above.
*Source: `docs/FREEZE.md` §2–§3.*

![regime ribbon](figs/fig5_regime_ribbon.png)

---

## 4. Benchmarks (pooled OOS @10 bps RT, PR-5 — same fill simulator, costs, funding)

| benchmark | pooled-OOS Sharpe | pooled-OOS net | note |
|---|---|---|---|
| HODL (w ≡ 1 perp incl. funding) | **−2.0963** | **−45.90%** | identical at 5/10/20 bps — its single entry fill is at the window start, outside every OOS segment; this makes the beats-HODL clause near-vacuous on this window (98% null pass rate, disclosed §3.1) |
| flat (w ≡ 0) | 0.00 | 0.00% | by construction |
| vol-target (EWMA λ=0.94, 30% ann, long-only, 1-bar lag) | −2.3513 | −38.03% | max-DD 39.68%; pays the same costs + funding |

*Source: HODL — `artifacts/sweep_results.json` →
`.globals.taxonomies.TC.hodl_oos` (also bit-for-bit in
`docs/report/adversarial/lane1_reproduction.md` §1); flat — by construction;
vol-target — not stored in the sweep artifact, recomputed from committed
CSVs by `uv run --no-sync python -m lab.report_figs` (printed in its
benchmark block alongside the HODL assertion against the artifact).*

The pooled OOS window was a bear: every long-only reference lost ~38–46%.
This context cuts both ways and is reported as such — short-anything made
money in this OOS (the shuffle-null p95 of 2.26 says random short placement
reaches Sharpe 2.26 at the 95th percentile), which is exactly why
"profits that survive top-5 removal" was the pre-registered test of timing
skill versus bear beta. It failed (§3.2).

---

## 5. Failed-candidate deep-history replay (falsification context — NOT a track record)

**Binding framing:** this section replays the FAILED candidate
`DIR-TC-H8-fade_pos_extreme_only-1.0` on the deep-history window
(2021-03-24 → 2026-05-18, 11,292 bars; funding + price only). It is
**falsification context, never a track record**. And per CONTEXT.md this is
explicitly **not a "deep-history proxy"** — that term attaches to a
Winner's rules, and **there is no Winner** (0/36). TC consumes funding only,
so the rule restricts to the deep-history field set without modification;
the frozen F4-train cut `funding_hi_abs = 8.385600000000002e-05` is applied
**verbatim, not re-derived**. Run: `uv run --no-sync python -m lab.deep_replay`.
*Source for every number in this section: `artifacts/deep_replay.json`.*

![deep replay](figs/fig6_deep_replay.png)

| quantity | guarded @10 bps | unguarded |
|---|---|---|
| Sharpe | 0.36 | 0.51 |
| net return | +40.4% | +90.4% |
| max drawdown | 44.9% | 53.2% |
| trades | 437 | — |
| bars in position | 3,774 / 11,292 (33.4%) | — |

What the replay actually shows — three reasons it falsifies rather than
flatters:

1. **The frozen "extremity" semantics do not transfer.** `pos-extreme`
   covers **46.8%** of deep-history bars vs **18.8%** of F4-train: 2021–2024
   funding ran far hotter than the 2025–2026 era the cut was derived on, so
   the train-relative q80 threshold classifies nearly half of history as
   "extreme". The replayed rule is in position 33.4% of bars here vs 6.8%
   of pooled OOS bars on the full-stack window — a structurally different
   exposure profile. Same rule text, different strategy in effect; this is
   why the curve can never be read as the candidate's history.
2. **The same concentration pathology, at 5-year scale.** Removing the top-5
   of 437 trades flips the net return from **+40.4% to −22.6%**
   (`top5_net` in the artifact), and a single year carries more than the
   entire gain: 2021 −29.6%, **2022 +109.8%**, 2023 −19.9%, 2024 +10.6%,
   2025 +6.6%, 2026 +0.5%. The deep window corroborates the top-5 clause's
   verdict; it does not soften it.
3. **The PR-4 DD guard fires here** (1,506 bars forced flat) — it never
   fired in the full-stack OOS. Another marker that the two windows are
   different regimes for this rule.

HODL context on the same window, same fill simulator: Sharpe 0.24, net
−9.1%, max-DD 79.1%.

---

## 6. Limitations, and what would change our mind

### 6.1 Limitations

- **One window, one venue, one asset.** 14 months of full-stack data
  (2,598 4h bars), bybit-venue OI/LS history, BTCUSDT only. The pooled OOS
  is bear-dominated; the gate's clauses were calibrated against that
  background (beats-HODL near-vacuous, disclosed).
- **Honest-N is taxonomy-level.** 225 pooled-OOS TC episodes, but any single
  sparse variant's active sample is far smaller (the near-miss: 30 trades /
  92 bars / 3 of 4 folds). `neg-extreme` has 26 bars / 9 episodes on
  F4-train — the monitor's note for it says "insufficient sample to
  characterize", and that is all it says.
- **The TC extremity cut sits in a microstructure-thin band** just below
  Binance's 1e-4 baseline funding clump; the pos-extreme boundary is
  sensitive to quantile choice (lane 3 §2), and F3's OOS had zero
  pos-extreme bars — extended quiet periods where an extreme state never
  fires are normal monitor behavior.
- **Train-relative semantics.** The deep replay (§5) shows the frozen q80
  cut labels 46.8% of 2021–2026 "extreme". The monitor's regime labels are
  statements relative to the F4-train funding distribution, not universal
  constants; the reference table documents the human refresh procedure
  (never consulted at runtime).
- **Live-field basis difference (D1/D3).** The Skill's live funding field is
  a CMC global average in percent units; the lab history is Binance-BTC 8h.
  The monitor compares sign + extremity band only (scale-free forms) and
  states the basis difference in every emission.
- **Episode-shuffle null is conservative** against concentrated real edges
  (§3.4) — our gate is biased toward exactly the error we shipped (a false
  negative is survivable; a false positive is not).

### 6.2 Forward falsification protocol — what would make a future variant shippable

The hypothesis family "fade positive funding extremes" remains open as a
hypothesis. It becomes shippable only via a **new pre-registration on data
that did not exist at freeze time**:

1. **New OOS only.** Evaluation data strictly after **2026-06-09 20:00 UTC**
   (the frozen window end). Nothing from the swept window may re-enter as
   OOS evidence.
2. **Registration before contact.** Taxonomy, thresholds-derivation rule,
   action map, sizes, fold boundaries, embargo, all five gate clauses, and
   the seed are written down before the new OOS is touched.
   **q=(0.25,0.75) and top-N=3 cannot be adopted retroactively** (§3.3); if
   a wider-quantile variant is the hypothesis, it enters the new sweep as a
   pre-registered variant and pays the multiple-testing disclosure like
   everything else.
3. **Minimum active sample.** Gate evaluation requires, for the candidate
   itself (not the taxonomy): ≥ 4 new walk-forward folds with nonzero trades
   in ≥ 3, **≥ 60 trades and ≥ 200 nonzero-position OOS bars** (≥ 2× the
   near-miss's active sample), and no single fold contributing > 50% of net
   PnL.
4. **The same gate, re-run mechanically.** Extend the committed CSVs, append
   PR-6-style quarterly boundaries, and run
   `uv run --no-sync python -m lab.sweep` — the gate predicate
   (beats flat ∧ beats HODL ∧ shuffle null @p95 ∧ top-5 removal ∧
   {5,10,20} bps ladder, pooled OOS, 10 bps rung) is frozen, including the
   top-5 clause that failed the near-miss. Passing every clause **including
   top-5 removal** on the new OOS, with the R3 triple disclosed for the new
   sweep's denominator, is the bar.
5. **Falsifiers we accept in advance.** A future pass that appears only
   under a widened quantile, a smaller removal count, shifted boundaries, or
   any other knob not in the new registration is a null result. A pass whose
   gain concentration exceeds the top-5 clause again is a null result. We
   wrote this down before knowing the answer; that is the point.

---

*Reproduction quick-reference: sweep —
`uv run --no-sync python -m lab.sweep` (regenerates
`artifacts/sweep_results.json` + `artifacts/sweep_summary.md`; 1,000 null
draws, seed base 17, wall time 283.7 s on the freeze machine); figures +
consistency assertions — `uv run --no-sync python -m lab.report_figs`;
deep replay — `uv run --no-sync python -m lab.deep_replay`. The backtest
reads only committed CSVs under `data/`; no network, no ClickHouse needed.*
