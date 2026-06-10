# Pre-registration — the widened search (W-sweep)

Date of registration: **2026-06-10** (commit timestamp of record on branch
`widening`) · Author: builder agent (Fable 5), operator-mandated widening
· Binding companions: ADR-001 (unchanged), **ADR-002** (W-panels as gating
domains), CONTEXT.md, `docs/FREEZE.md` (frozen floor), REPORT.md §6.2
(forward falsification protocol — honored, not amended),
`docs/research/2026-06-10-widening-recon.md` (data-availability evidence).

**Amendment policy.** This registration may be amended only by dated
commits made **before the first OOS evaluation of any registered Variant**
(the "OOS-contact event" = first execution of the W-sweep gate path against
any OOS index). The critic-lane review happens inside that window and its
amendments are expected and logged in §13. After OOS contact this document
is frozen; any later change triggers full re-validation (G7) and is a
deviation, not an amendment.

---

## 0. What this is

The frozen floor (`0334868`) shipped an honest null: 0/36 Variants passed
the pre-registered shipping gate on a 14-month, single-asset,
bear-dominated window. This registration widens the search — more
families, more taxonomies, three assets, and ~5–6-year gating panels —
under the **same gate plus three strictly-added clauses**. The honesty
contract is unchanged:

- everything below is written down before any OOS result is seen;
- clauses are added, never removed;
- the wider denominator and its expected null pass-rate are disclosed (R3);
- honest-N stays the pooled-OOS **regime-episode** count, and any candidate
  statement quotes its ACTIVE sample (FREEZE §3 amendment 4);
- a wider null is a legitimate ship.

## 1. Panels (gating domains, per ADR-002)

| panel | asset / series | span (4h grid) | folds | bars (approx) |
|---|---|---|---|---|
| **P-BTC** | BTCUSDT perp | 2020-04-01 00:00 → 2026-06-09 20:00 | F01…F21 | ~13,560 |
| **P-ETH** | ETHUSDT perp | 2020-04-01 00:00 → 2026-06-09 20:00 | F01…F21 | ~13,560 |
| **P-SOL** | SOLUSDT perp | 2020-10-01 00:00 → 2026-06-09 20:00 | F01…F19 | ~12,470 |

Warmup data earlier than each panel start (bars, funding, daily OI) is used
only for Feature construction (SMA200/RSI warmup, OI Δ baseline), never as
train or OOS rows.

**Fold geometry (PR-6 mechanics unchanged).** Expanding folds on quarterly
calendar-UTC boundaries: P-BTC/P-ETH boundaries 2021-04-01, 2021-07-01, …,
2026-04-01 (21 folds; first train = 1 year); P-SOL boundaries 2021-10-01 …
2026-04-01 (19 folds). Train = every grid bar strictly before the boundary;
OOS = [boundary + E bars … next boundary); final fold's OOS runs to panel
end. Embargo E = max(42 bars, ceil(median regime-episode length)) per
(panel, taxonomy) — R2 unchanged.

## 2. Data sources of record (R-SRC: one source per Feature, full span)

| Feature (lab column) | lab source (single, end-to-end) | live CMC analog (Gate-0-verified) |
|---|---|---|
| `funding_rate_8h` (per asset) | Binance REST `fapi/v1/fundingRate` backfill (BTC committed; ETH/SOL new backfills; SOL stamps snapped to the 8h grid) | derivatives/global-metrics funding fields — **sign + extremity band only** (D1/D3 scale-free rule; basis difference disclosed in every emission, and it is wider for ETH/SOL since the live field is a global average) |
| `oi_chg_24h_daily` (BTC only) | CoinGlass-relayed daily OI history, Binance-BTCUSDT subset, 2020-02-27 → 2026-05-18 (read-only mirror export; verified strictly-daily cadence over its whole life — recon §1). Frozen tail 2026-05-18→panel end: rows are NaN → explicit `oi-na` label (§4) | `totalOpenInterest.percentage_change_24h` (F2, D3 basis disclosure) |
| `fg` | CMC Pro REST F&G historical (committed; same vendor live) | `sentiment.fear_greed.current.index` (F3) — CMC end-to-end |
| `rsi14_1d` | computed from panel bars (Wilder-14, frozen features.py code) | `rsi.rsi14` (F4) |
| `close_vs_sma200_1d` | computed from panel bars (daily closes, SMA-200, causal D−1→D join — same mechanics as the frozen SMA30 Feature) | `moving_averages.simple_moving_average_200_day` + quotes price (F5; the 200-day window was Gate-0-verified as served) |
| `pc_24h` | close/close(6 bars back) − 1 from panel bars | `percent_change_24h` (F6) |

Bars: P-BTC uses the committed `data/lab/bars_4h.csv` (same source as the
frozen build); P-ETH/P-SOL use Binance USDⓈ-M futures klines
(`fapi/v1/klines`, 4h) — new committed backfills. The BTC-mirror/REST
asymmetry is disclosed; each panel's bar series is one source end-to-end.

**Every Feature above is point-in-time live-computable from
Gate-0-verified CMC fields** (ADR-002 requirement; G1: validated ≡
shipped). Excluded from the gated set for exactly that reason: DVOL, LS,
CVD, liquidation history, funding momentum/Δ (the live `percentage_change`
funding fields were Gate-0-rejected for cause), episode-age conditioning,
and trailing realized vol (no live history tool). These remain lab-side
research axes only and are NOT registered.

**Coverage floor (registered rule).** A taxonomy's threshold for Feature X
derives on a fold only if that fold's train slice holds ≥ 90 days of
non-NaN X; otherwise every bar of that fold carries the taxonomy's `na`
label for that axis (action 0; see §4). This is mechanical and applies
uniformly (it governs early-F&G folds, the SOL SMA200 warmup, etc.).

## 3. Execution model — UNCHANGED

PR-3 verbatim per panel: decided at close t → next-bar-open fill;
r[t] = open[t+1]/open[t] − 1; per-side c/2 bps on |Δw|; funding accrues at
00/08/16 UTC stamps with the R-FUND sign (short earns positive funding);
w ∈ [−1, 1]; Sharpe annualized √2190; cost ladder {5, 10, 20} bps RT, gate
rung 10. DD guard PR-4 verbatim (trailing 20%, flat until next label
change, variants only, never swept). Benchmarks PR-5 verbatim per panel
(HODL incl. funding, flat, vol-target EWMA λ=0.94 / 30% ann / long-only).
Note disclosed in advance: on these panels HODL is strongly positive over
2021→2026, so beats-HODL is a REAL clause again — the gate is harder than
the floor's, as the widening contract demands.

**Two registered rule-surface extensions** (variant parameters, not
execution-model changes; TDD-pinned):

- **Time-stop k:** a continuous nonzero-position run is forced to w = 0
  after k bars in position; re-entry only when the regime label next
  changes to a label with nonzero action. Registered values: k ∈ {none, 6}.
- **Vol-band overlay:** final w is multiplied by 0.5 on bars where
  |pc_24h| > q80(|pc_24h|, fold-train) (R1 train-only cut). Registered
  values: {off, on}.

## 4. Taxonomies (all thresholds per-fold train-only, R1)

NaN policy: funding NaN keeps the frozen D4.3 semantics (NaN → neg / mild
branch, continuity with TC). For every **non-funding** axis, a NaN Feature
bar maps to an explicit `na` label whose action is 0 in EVERY map of that
taxonomy (stricter and more honest than silent clause-FALSE: missing data
⇒ flat).

| id | axes | labels (canonical order) | train-derived cuts |
|---|---|---|---|
| **T-D** | graded funding | pos-mid, pos-hi, pos-x, neg-mid, neg-hi, neg-x | c_hi = q60(\|f\|), c_x = q90(\|f\|); pos ⇔ f ≥ 0 |
| **T-E** (P-BTC only) | funding sign × daily-OI build/unwind | pos-build, pos-unwind, neg-build, neg-unwind, oi-na | build ⇔ oi_chg_24h_daily ≥ 0; NaN → oi-na |
| **T-F** | funding sign × F&G corners | pos-fear, pos-greed, neg-fear, neg-greed, fg-mid, fg-na | fear ⇔ fg ≤ q20(fg), greed ⇔ fg ≥ q80(fg) |
| **T-G** | funding sign × SMA200 side | pos-above, neg-above, pos-below, neg-below, sma-na | above ⇔ close_vs_sma200_1d > 0 |
| **T-H** | funding sign × RSI14 bands | pos-os, pos-mid, pos-ob, neg-os, neg-mid, neg-ob, rsi-na | fixed absolute bands: os ⇔ rsi ≤ 30, ob ⇔ rsi ≥ 70 (canonical constants, not data-derived) |

Design-influence disclosure: T-D's graded two-cut form responds to the
published lane-3 knife-edge critique of single-quantile cuts (machinery
knowledge, §10); q60/q90 are registered here, blind to any OOS outcome.

## 5. Registered Variant enumeration (exact grids — test-pinned counts)

Direction sizes are {1.0, 0.5} multipliers, as in PR-8. Canonical label
order per §4. `na` labels always act 0 and are omitted from the vectors
below for brevity.

**T-D direction** (order pos-mid, pos-hi, pos-x, neg-mid, neg-hi, neg-x):
- D1 `fade_extremes_graded_sym` (0, −0.5, −1, 0, +0.5, +1)
- D2 `fade_x_only_sym` (0, 0, −1, 0, 0, +1)
- D3 `follow_extremes_graded_sym` (0, +0.5, +1, 0, −0.5, −1)
- D4 `follow_x_only_sym` (0, 0, +1, 0, 0, −1)

4 maps × 2 sizes × time-stop {none, 6} = **16**.

**T-D risk ladders** (long-only):
R1 (1, 0.5, 0, 1, 0.5, 0) · R2 (1, 0.5, 0.25, 1, 0.5, 0.25) ·
R3 (1, 1, 0, 1, 1, 0) · R4 (1, 0.5, 0, 1, 1, 0.5)
× vol-band {off, on} = **8**. → T-D per panel: **24**.

**T-E direction** (order pos-build, pos-unwind, neg-build, neg-unwind):
- E1 `fade_build_sym` (−1, 0, +1, 0)
- E2 `follow_unwind_sym` (0, −1, 0, +1)
- E3 `fade_pos_long_neg` (−1, −1, +1, +1)
- E4 `follow_build_sym` (+1, 0, −1, 0)

4 maps × 2 sizes × time-stop {none, 6} = **16**; ladders
L1 (1, 0.5, 1, 0.5) · L2 (1, 0, 1, 1) = **2**. → T-E (P-BTC only): **18**.

**T-F direction** (order pos-fear, pos-greed, neg-fear, neg-greed):
- F1 `capitulation_euphoria` (0, −1, +1, 0)
- F2 `contrarian_fg` (+1, −1, +1, −1)
- F3 `follow_fg` (−1, +1, −1, +1)

3 maps × 2 sizes = **6**; ladders (incl. fg-mid exposure 1):
L1 de-risk-greed (1, 0.5, 1, 0.5 | mid 1) · L2 de-risk-fear
(0.5, 1, 0.5, 1 | mid 1) = **2**. → T-F per panel: **8**.

**T-G direction** (order pos-above, neg-above, pos-below, neg-below):
- G1 `follow_trend` (+1, +1, −1, −1)
- G2 `trend_crowding_filtered` (0, +1, −1, 0)

2 maps × 2 sizes = **4**; ladders L1 (1, 1, 0, 0) · L2 (1, 1, 0.5, 0) ·
L3 (0.5, 1, 0, 0) = **3**. → T-G per panel: **7**.

**T-H direction** (order pos-os, pos-mid, pos-ob, neg-os, neg-mid, neg-ob):
- H1 `fade_ob_pos_buy_os_neg` (0, 0, −1, +1, 0, 0)
- H2 `contrarian_rsi` (+1, 0, −1, +1, 0, −1)

2 maps × 2 sizes = **4**; ladders L1 (1, 1, 0.5, 1, 1, 0.5) ·
L2 (1, 1, 0, 1, 1, 0) = **2**. → T-H per panel: **6**.

**Gated denominator:**

| panel | T-D | T-E | T-F | T-G | T-H | total |
|---|---|---|---|---|---|---|
| P-BTC | 24 | 18 | 8 | 7 | 6 | **63** |
| P-ETH | 24 | — | 8 | 7 | 6 | **45** |
| P-SOL | 24 | — | 8 | 7 | 6 | **45** |
| **N (gated)** | | | | | | **153** |

Variant ids: `<PANEL>-DIR-<TAX>-<map>-<size>[-ts6]` /
`<PANEL>-RISK-<TAX>-ladder-<vec>[-vb]`. Counts are pinned by a test
(`enumerate_all_w()` total == 153 + 8 annex). Frozen 36-variant enumeration
is untouched.

## 6. The locked annex (evaluated, published, CANNOT ship)

REPORT §6.2 pre-committed that the BTC hypothesis family **fade positive
funding extremes** becomes shippable only on data created after
2026-06-09 20:00 UTC. We honor that commitment verbatim. The family's
widened pure expressions are still evaluated on P-BTC — as falsification
context, exactly like the frozen deep replay — but are excluded from
ship-eligibility regardless of outcome:

**Annex variants (P-BTC, T-D label space):**
- A1 `fade_pos_x_only` (0, 0, −1, 0, 0, 0)
- A2 `fade_pos_graded` (0, −0.5, −1, 0, 0, 0)

× 2 sizes × time-stop {none, 6} = **8** (reported separately in R3; never
in the gated denominator's survivor pool).

**Family-lock predicate (mechanical).** A P-BTC Variant is locked iff its
action map (i) is short in ≥ 1 positive-funding extremity band, (ii) takes
no nonzero action in any negative-funding label, and (iii) is long
nowhere. (A1/A2 satisfy it; the symmetric D1/D2 do not — they are
disclosed kin.)

**Leg-decomposition lock (registered ship-eligibility rule).** Any
Survivor on any panel has its pooled-OOS net PnL decomposed by bars where
(funding label is a positive extremity band AND w < 0). If that leg
carries > 80% of pooled-OOS net PnL for a P-BTC Survivor, the Survivor is
treated as family-locked (published, not shipped this cycle). This closes
the "locked strategy in a trench coat" hole in advance.

**Forward registration (the §6.2 protocol, made concrete).** The 8 annex
variants are hereby also registered on post-freeze data: OOS =
2026-06-11 00:00 UTC onward, quarterly folds per §6.2.4, same 8-clause
gate, §6.2.3 active-sample bar verbatim. Evaluation occurs when ≥ 4
post-freeze quarterly folds exist (earliest 2027-07-01); any earlier
readout is labeled underpowered and non-shippable. This cycle's submission
reports the registration itself, not a result.

## 7. The shipping gate — 5 frozen clauses + 3 added (pooled OOS per panel, 10 bps rung)

| # | clause | status |
|---|---|---|
| 1 | beats_flat: net@10 bps > 0 | frozen |
| 2 | beats_hodl: Sharpe > HODL Sharpe | frozen |
| 3 | null_p95: Sharpe > episode-shuffle null q95 | frozen |
| 4 | top5_pass: net after removing the 5 best OOS trades > 0 | frozen |
| 5 | ladder_pass: net@20 bps > 0 | frozen |
| 6 | **null_p99**: Sharpe > episode-shuffle null q99 | **added** |
| 7 | **min_active_sample** (from REPORT §6.2.3): OOS trades ≥ 60 ∧ nonzero-position OOS bars ≥ 200 ∧ nonzero trades in ≥ 60% of feature-covered folds (a fold is covered iff its OOS holds ≥ 1 non-`na` bar for the Variant's taxonomy) ∧ no single fold contributes > 50% of pooled-OOS net return (compounded fold nets; evaluated when pooled net > 0) | **added** |
| 8 | **topk_pass**: net after removing the K best OOS trades > 0, K = max(5, ceil(0.02 × OOS trade count)) | **added** |

All eight must hold. Nulls: episode-shuffle, common draws per (panel,
taxonomy, fold), **D = 1000**, rng convention identical to the frozen
sweep (numpy `default_rng(seed_base + fold ordinal)`, seed_base = 17);
quantiles via the same numpy quantile call as the frozen p95. Clause
mechanics for 1–5 are byte-identical to `lab/gate.py` / `lab/hooks.py`.

**Selection (ADR-001 unchanged).** Rank key = mean per-fold train Sharpe
@10 bps (tiebreak: lower mean train max-DD), within panel. Winner =
highest train-ranked, ship-eligible Survivor on the highest-priority panel
with any such Survivor; panel priority **P-BTC → P-ETH → P-SOL**
(pre-stated; the Skill ships on the Winner's asset). For any Winner, the
same Variant's results on the other panels are published as transfer
evidence (disclosure, not a clause).

**Honest-N.** Headline per (panel, taxonomy): pooled-OOS regime-episode
count. Any candidate statement quotes its ACTIVE sample (trades /
nonzero-position bars / folds-with-trades) — FREEZE §3 amendment 4 carried
forward.

## 8. R3 disclosure plan (the denominator, in advance)

- Gated N = **153** (63 + 45 + 45); locked annex = **8**, reported
  separately; total evaluated = **161**.
- Expected null-clause pass-rate: clause 3 alone ≈ 5% by construction;
  clauses 3 ∧ 6 jointly ≈ 1% ⇒ ~1.5 expected null-clause passers across
  153. Full-gate expected false-pass rate is re-calibrated per panel
  exactly as the frozen build did (200 null draws pushed through the full
  8-clause gate for the top train-ranked variant) and disclosed next to
  observed passes. An observed pass-count near null expectation is
  reported as exactly that.
- Family-level readout: passes are grouped by (family, taxonomy, panel); a
  lone pass with no support from its family/transfer panels is reported
  with that context.
- **Cumulative-contact disclosure:** 36 frozen Variants (≈ 26 effective
  hypotheses) were already evaluated on the overlapping 2025-04→2026-06
  window, plus the lane-3 perturbation grid and the H8 deep replay; the
  report states this next to the new denominator.

## 9. Power and calibration (planned, adversarial lane)

Lane-2-style planted-edge calibration is re-run on P-BTC with the
unmodified W-sweep pipeline (drift aligned with a registered map;
labels/funding untouched) to restate gate power on the new panel — the
frozen power statement (≥ 10 bps/bar robust, 5 bps/bar marginal) does not
automatically transfer to 21 folds and 8 clauses. An independent lane also
re-implements any Survivor's scalars from raw CSVs (lane-1 standard:
max |diff| ≤ 1e-9, thresholds re-derived from boundary-truncated raw
files).

**Performance note (registered implementation rule):** the null-backtest
path may restrict each draw's backtest to the fold's OOS window (bar
returns are bar-local) ONLY after a bit-for-bit equivalence run reproduces
the frozen `artifacts/sweep_results.json` scalars through the optimized
path; otherwise the unoptimized path runs.

## 10. Prior-contact register (what we already knew when we wrote this)

Design-relevant contacts, disclosed in full (details and exact numbers in
the cited artifacts):

1. **H8 deep replay** (REPORT §5, `artifacts/deep_replay.json`): the
   frozen-cut fade rule on 2021→2026 — net +40.4% @10 bps, top-5 removal
   flips to −22.6%, 2022 alone +109.8%, pos-extreme = 46.8% of bars, DD
   guard fired 1,506 bars. This is why the BTC fade family is locked
   (§6) and why clause 7's no-fold>50% rule exists. Pre-2025 BTC data is
   evaluation-contaminated for THIS family only; no other registered
   family has ever been evaluated on it.
2. **Lane-3 perturbation grid** (lane3_near_miss.md §2): q=(0.25,0.75) and
   top-N=3 flip the old near-miss to PASS on the old window — both remain
   banned retroactive knobs; T-D's graded cuts (q60/q90) are a different,
   here-registered structure, and no registered Variant reuses the old
   q=(0.25,0.75) derivation.
3. **Lane-2 power curve** (lane2_gate_calibration.md): gate-machinery
   knowledge used to size D, K, and the active-sample bar — legitimate and
   cited.
4. **Threshold-drift / stability studies** (lane1 §2/§4, FREEZE §2):
   funding-only taxonomies relabel least under threshold re-derivation —
   informs why T-D stays funding-led; cited, not blind.
5. **Band recon** (band_recon.md): Bands are not used anywhere in the
   W-sweep; NMI evidence stands.
6. **Funding cross-check window** (Jan–Mar 2025 rows inspected;
   funding_crosscheck.txt): source decision (Binance REST end-to-end)
   already made and carried forward.
7. **Committed pre-window CSV spans** (DATA_PROVENANCE.md): gross facts
   (2021-24 funding ran hotter; F&G floor 5) were published; thresholds
   remain per-fold train-derived so no constant is transcribed from them.
8. **Prior internal nulls** (REPORT §3.7): Band main effects null at 4h; a
   1h DVOL lead died in causal OOS — DVOL stays out of the gated set, and
   no registered family resurrects Band main effects.
9. **2026-06-10 live snapshots** (Gate-0 dump, funding_calibration.csv):
   point values after the frozen window end were observed pre-registration
   (extreme fear, near-zero predicted funding). The forward registration's
   OOS therefore starts 2026-06-11 00:00 UTC, after every observed stamp.
10. **CSV tails to 2026-06-10** committed but never consumed by any sweep;
    W-panel ends 2026-06-09 20:00, inside all sources' verified spans.

## 11. What ships under each outcome (pre-stated)

- **Ship-eligible Survivor exists** → the Winner ships as a validated
  strategy Skill: SKILL.md re-authored from the frozen parameters of the
  Winner (thresholds = its panel's final-fold train numbers, the exact
  numbers gated on the final fold's OOS), live-validated against the CMC
  MCP, REPORT/FREEZE/README/SUBMISSION/demo/video updated, with the full
  R3 story and transfer evidence. Threshold freeze + amendments procedure
  as in the floor.
- **Only locked Survivors** → the entry ships the upgraded monitor + the
  locked candidate(s) published in the falsification chapter + the active
  forward registration (§6) — "the gate found something it refuses to
  ship until its own published protocol is satisfiable" is the story,
  verbatim.
- **Null** → the wider-null entry: 153 registered Variants, three assets,
  ~5–6-year multi-regime OOS, 8-clause gate, expected-vs-observed passes
  disclosed. Strictly stronger than the floor's null.
- **In every outcome** the Skill deepens CMC MCP usage: ≥ 7 verified tools
  with honest roles (classifier inputs only Gate-0-verified Features;
  derivatives/narratives/macro-events as labeled display context), F&G
  CMC-end-to-end, and the live/lab basis disclosures per D1/D3.

## 12. Build phases (execution sketch; details in task list)

1. **Lab extension (TDD, floor tests stay green):** ETH/SOL funding +
   klines backfills; CG daily-OI export; panel loader (multi-panel);
   T-D…T-H classifiers; time-stop + vol-band rule surface; W-fold
   geometry; W-variant enumeration (count-pinned); null-path equivalence
   run.
2. **W-sweep** exactly as registered; artifacts committed.
3. **Adversarial lanes** (separate, never self-approving): reproduction,
   planted-edge calibration, survivor refutation, R3 audit.
4. **Re-author** per §11 outcome; independent review; submission package
   by 2026-06-19.

## 13. Amendment log

- *(empty at registration; critic-lane amendments land here as dated
  entries before OOS contact)*
