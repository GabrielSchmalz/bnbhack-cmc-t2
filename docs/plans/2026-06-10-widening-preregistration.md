# Pre-registration — the widened search (W-sweep)

Registered: **2026-06-10** (commit `b76c324`) · Amended: **2026-06-10**
(critic-lane review, three independent lanes, all
approve-with-amendments; every amendment logged in §13 — all before any
OOS contact) · Author: builder agent (Fable 5), operator-mandated widening
· Binding companions: ADR-001 (unchanged), **ADR-002** (W-panels as gating
domains), CONTEXT.md, `docs/FREEZE.md` (frozen floor), REPORT.md §6.2
(forward falsification protocol — honored, not amended),
`docs/research/2026-06-10-widening-recon.md` (data-availability evidence).

**Amendment policy.** This registration may be amended only by dated
commits made **before the first OOS evaluation of any registered Variant**
(the "OOS-contact event" = first execution of the W-sweep gate path against
any OOS index). After OOS contact this document is frozen; any later
change triggers full re-validation (G7) and is a deviation, not an
amendment.

---

## 0. What this is

The frozen floor (`0334868`) shipped an honest null: 0/36 Variants passed
the pre-registered shipping gate on a 14-month, single-asset,
bear-dominated window. This registration widens the search — more
hypothesis families, more taxonomies, three assets, and ~5–6-year gating
panels — under the **same gate plus three strictly-added clauses**. The
honesty contract is unchanged:

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

**Span-start rule (mechanical):** panel start = first quarterly UTC
boundary ≥ max(earliest stamps of the panel's registered sources); P-ETH
is aligned to P-BTC's start for cross-panel fold comparability (registered
choice; its sources are live from 2019-11). Warmup data earlier than each
panel start (bars, funding, daily OI) is used only for Feature
construction (SMA200/RSI warmup, OI Δ baseline), never as train or OOS
rows. Note: no panel has 200 daily closes before its start, so
early-panel bars are `sma-na` on every panel (coverage floor, §2).

**Fold geometry (PR-6 mechanics unchanged).** Expanding folds on quarterly
calendar-UTC boundaries: P-BTC/P-ETH boundaries 2021-04-01, 2021-07-01, …,
2026-04-01 (21 folds; first train = 1 year); P-SOL boundaries 2021-10-01 …
2026-04-01 (19 folds). Train = every grid bar strictly before the boundary;
OOS = [boundary + E bars … next boundary); final fold's OOS runs to panel
end.

**Embargo (pinned).** E per (panel, taxonomy) = max(42 bars, ceil(median
regime-episode length)), where the median is computed **once,
pre-OOS-contact, on the panel's FIRST fold's train slice labeled with that
fold's train-derived cuts** (train-only by construction), **over non-`na`
labeled episodes only** (`na` episodes are missing-feature placeholders,
not regime episodes — consistent with honest-N's regime-episode unit and
the null's `na`-freeze; if a slice has no non-`na` episodes, the floor
binds — §13 amendment 27). Every E is printed in the sweep artifact; the
42-bar floor is expected to bind, and any (panel, taxonomy) where it does
not is disclosed in R3.

## 2. Data sources of record (R-SRC: one source per Feature, full span)

| Feature (lab column) | lab source (single, end-to-end) | live CMC analog (Gate-0-verified) |
|---|---|---|
| `funding_rate_8h` (per asset) | Binance REST `fapi/v1/fundingRate` backfill (BTC committed; ETH/SOL new backfills; SOL stamps snapped to the 8h grid) | derivatives/global-metrics funding fields — **sign + extremity band only** (D1/D3 scale-free rule; basis difference disclosed in every emission, and it is wider for ETH/SOL since the live field is a global average) |
| `oi_chg_24h_daily` (BTC only) | CoinGlass-relayed daily OI history, Binance-BTCUSDT subset, 2020-02-27 → 2026-05-18 (read-only mirror export). Cadence per recon §1: **strictly daily for 2,259 of 2,285 gaps, with a handful of 8h/16h stamps in 2026 only.** Loader registered below. Frozen tail 2026-05-18 → panel end: NaN → `oi-na` label (§4) | `totalOpenInterest.percentage_change_24h` (F2, D3 basis disclosure) |
| `fg` | CMC Pro REST F&G historical (committed; same vendor live) | `sentiment.fear_greed.current.index` (F3) — CMC end-to-end |
| `rsi14_1d` | computed from panel bars (Wilder-14, frozen features.py code) | `rsi.rsi14` (F4) |
| `close_vs_sma200_1d` | computed from panel bars (daily closes, SMA-200, causal D−1→D join — same mechanics as the frozen SMA30 Feature) | `moving_averages.simple_moving_average_200_day` + quotes price (F5; the 200-day window was Gate-0-verified as served) |
| `pc_24h` | close/close(6 bars back) − 1 from panel bars | `percent_change_24h` (F6) |

**Daily-OI loader (registered; mirrors D4.2/D4.4):** dedupe to the **last
stamp per UTC day D**; `oi_chg_24h_daily(D) = snap(D)/snap(D−1) − 1`;
the day-D value becomes usable at the **first 4h bar opening after the
day-D stamp** (a 00:00 stamp → the D 04:00 bar, mirroring the D4.4 F&G
rule); staleness > 48h → NaN → `oi-na`. Stamp semantics (00:00 snapshot
vs day-close) are determined pre-OOS by cross-checking the export against
overlapping bybit daily snapshots, and the determination is committed
with the loader tests. *(Determined 2026-06-11: the table stores daily OI
candles; stamp = candle start, `open_oi` = the D 00:00 snapshot — corr
peak at offset 0; `close_oi` peaks at +1 and is excluded as leaky. Export
uses `open_oi`; availability rule unchanged.
`docs/gate0/OI-CG-STAMP-SEMANTICS.md`, §13 amendment 26.)* `rsi14_1d` / `fg` / `close_vs_sma200_1d` reuse the
frozen causal join conventions on all three panels.

**D2 supersession note:** the freeze addendum's D2 rejected SMA200
("degenerate as a switching axis") **for the 14-month frozen window**;
that rationale dissolves on 5–6-year panels, the 200-day window is
Gate-0-verified as served, and this registration supersedes D2 **for
W-panels only** — the frozen build and its artifacts are untouched.

Bars: P-BTC uses the committed `data/lab/bars_4h.csv` (same source as the
frozen build); P-ETH/P-SOL use Binance USDⓈ-M futures klines
(`fapi/v1/klines`, 4h) — new committed backfills. The BTC-mirror/REST
asymmetry is disclosed; each panel's bar series is one source end-to-end.

**Live-computability and the Gate-0 scope.** Every Feature above is
point-in-time live-computable from Gate-0-verified CMC fields (ADR-002;
G1: validated ≡ shipped). The day-1 Gate-0 dump was BTC-centric, so a
**Gate-0 addendum dump is required pre-OOS-contact**: call
`get_crypto_technical_analysis` and `get_crypto_quotes_latest` for ETH
(id 1027) and SOL (id 5426), commit the raw JSON under `docs/gate0/`, and
cite it here. If the addendum dump cannot run before OOS contact, the
Gate-0-verified claim is scoped to P-BTC and a registered ship-eligibility
precondition applies: a P-ETH/P-SOL Winner ships only after its per-asset
fields pass an identical Gate-0-style verification.

Excluded from the gated set for failing live-computability: DVOL, LS,
CVD, liquidation history, funding momentum/Δ (the live
`percentage_change` funding fields were Gate-0-rejected for cause),
episode-age conditioning, and trailing realized vol. These remain
lab-side research axes only and are NOT registered.

**Coverage floor (registered rule, per fold × taxonomy × axis).** If a
fold's train slice holds **< 90 distinct UTC calendar days each
containing ≥ 1 non-NaN observation of Feature X**, then EVERY bar of that
fold (train and OOS) carries the axis's `na` label — whether or not the
axis has a train-derived cut. Otherwise only NaN bars map to `na`.
Funding axes are exempt (no `na` label; D4.3 semantics; their verified
spans cover every fold train).

## 3. Execution model — UNCHANGED

PR-3 verbatim per panel: decided at close t → next-bar-open fill;
r[t] = open[t+1]/open[t] − 1; per-side c/2 bps on |Δw|; funding accrues at
00/08/16 UTC stamps with the R-FUND sign (short earns positive funding);
w ∈ [−1, 1]; Sharpe annualized √2190; cost ladder {5, 10, 20} bps RT, gate
rung 10. DD guard PR-4 verbatim (trailing 20%, flat until next label
change, variants only, never benchmarks, never swept). Benchmarks PR-5
verbatim per panel (HODL incl. funding, flat, vol-target EWMA λ=0.94 /
30% ann / long-only). Disclosed in advance: on these panels HODL is
strongly positive over 2021→2026, so beats-HODL is a REAL clause again —
the gate is harder than the floor's.

**Two registered rule-surface extensions** (variant parameters, not
execution-model changes; TDD-pinned):

- **Time-stop k (pinned semantics):** a *run* starts at the first bar with
  w ≠ 0 preceded by w = 0 (or panel start); a sign flip without an
  intervening flat bar **continues** the same run; the position is forced
  to w = 0 at the close of the k-th bar of the run; a DD-guard flat
  supersedes and terminates the run; re-entry occurs at the first label
  TRANSITION into any label whose mapped action is nonzero, regardless of
  intervening zero-action labels. Registered values: k ∈ {none, 6}.
- **Vol-band overlay:** final w is multiplied by 0.5 on bars where
  |pc_24h| > q80(|pc_24h|, fold-train) (R1 train-only cut). Registered
  values: {off, on}.

## 4. Taxonomies (all train-derived thresholds per-fold, R1)

NaN policy: funding NaN keeps the frozen D4.3 semantics (NaN → neg / mild
branch, continuity with TC). For every **non-funding** axis, a NaN Feature
bar maps to an explicit `na` label whose action is 0 in EVERY map of that
taxonomy (missing data ⇒ flat). The coverage floor (§2) can force whole
folds to `na` on an axis.

| id | axes | labels (canonical order) | cuts |
|---|---|---|---|
| **T-D** | graded funding | pos-mid, pos-hi, pos-x, neg-mid, neg-hi, neg-x | c_hi = q60(\|f\|), c_x = q90(\|f\|) train-derived; pos ⇔ f ≥ 0 |
| **T-E** (P-BTC only) | funding sign × daily-OI build/unwind | pos-build, pos-unwind, neg-build, neg-unwind, oi-na | build ⇔ oi_chg_24h_daily ≥ 0; NaN → oi-na |
| **T-F** | funding sign × F&G corners | pos-fear, pos-greed, neg-fear, neg-greed, fg-mid, fg-na | fear ⇔ fg ≤ q20(fg), greed ⇔ fg ≥ q80(fg), train-derived |
| **T-G** | funding sign × SMA200 side | pos-above, neg-above, pos-below, neg-below, sma-na | above ⇔ close_vs_sma200_1d > 0; NaN → sma-na |
| **T-H** | funding sign × RSI14 bands | pos-os, pos-mid, pos-ob, neg-os, neg-mid, neg-ob, rsi-na | fixed absolute bands: os ⇔ rsi ≤ 30, ob ⇔ rsi ≥ 70 (canonical constants, not data-derived); NaN → rsi-na |

Design-influence disclosure: T-D's graded two-cut form responds to the
published lane-3 knife-edge critique of single-quantile cuts (machinery
knowledge, §10); q60/q90 are registered here, blind to any OOS outcome.

## 5. Registered Variant enumeration (exact grids — test-pinned counts)

Direction sizes are {1.0, 0.5} multipliers, as in PR-8. Canonical label
order per §4. **`na` labels — and, for T-F direction maps, `fg-mid` —
always act 0** and are omitted from the vectors below. Maps marked
**[axis-collapse control]** deliberately ignore one axis; §11 pre-states
how a Winner from one is framed. Direction grids are **mirrored wherever a
directional prior exists** (every map below has its sign-mirror registered,
except G2, an interaction filter whose mirror is economically vacuous —
disclosed in §8 as the one asymmetric cell).

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
(Ladders are long-only by family design — the registered hypothesis is
long-side risk management; no short-only ladder family exists, disclosed
in §8.)

**T-E direction** (order pos-build, pos-unwind, neg-build, neg-unwind):
- E1 `fade_build_sym` (−1, 0, +1, 0)
- E2 `follow_unwind_sym` (0, −1, 0, +1)
- E3 `fade_pos_long_neg` (−1, −1, +1, +1) **[axis-collapse control: ignores OI axis]**
- E4 `follow_build_sym` (+1, 0, −1, 0) *(mirror of E1)*
- E5 `fade_unwind_sym` (0, +1, 0, −1) *(mirror of E2)*

5 maps × 2 sizes × time-stop {none, 6} = **20**; ladders
L1 (1, 0.5, 1, 0.5) · L2 (1, 0, 1, 1) = **2**. → T-E (P-BTC only): **22**.

**T-F direction** (order pos-fear, pos-greed, neg-fear, neg-greed; fg-mid
and fg-na act 0):
- F1 `capitulation_euphoria` (0, −1, +1, 0)
- F2 `contrarian_fg` (+1, −1, +1, −1) **[axis-collapse control: ignores funding sign]**
- F3 `follow_fg` (−1, +1, −1, +1) **[axis-collapse control]** *(mirror of F2)*
- F4 `euphoria_follow` (0, +1, −1, 0) *(mirror of F1)*

4 maps × 2 sizes = **8**; ladders (fg-mid exposure 1, na 0):
L1 de-risk-greed (1, 0.5, 1, 0.5 | mid 1) · L2 de-risk-fear
(0.5, 1, 0.5, 1 | mid 1) = **2**. → T-F per panel: **10**.

**T-G direction** (order pos-above, neg-above, pos-below, neg-below):
- G1 `follow_trend` (+1, +1, −1, −1) **[axis-collapse control: ignores funding sign]**
- G2 `trend_crowding_filtered` (0, +1, −1, 0) *(asymmetric interaction cell, disclosed)*
- G3 `fade_trend` (−1, −1, +1, +1) **[axis-collapse control]** *(mirror of G1)*

3 maps × 2 sizes = **6**; ladders L1 (1, 1, 0, 0) · L2 (1, 1, 0.5, 0) ·
L3 (0.5, 1, 0, 0) = **3**. → T-G per panel: **9**.
Feasibility note (registered in advance): G1/G3 and L1 change position
only on SMA200 side flips (~15–25 over 5 years) and are **expected to be
structurally unable to meet clause 7's 60-trade floor**; they stay in the
denominator as registered hypotheses but §8 discloses the effective
(structurally-gateable) denominator alongside N.

**T-H direction** (order pos-os, pos-mid, pos-ob, neg-os, neg-mid, neg-ob):
- H1 `fade_ob_pos_buy_os_neg` (0, 0, −1, +1, 0, 0)
- H2 `contrarian_rsi` (+1, 0, −1, +1, 0, −1) **[axis-collapse control: ignores funding sign]**
- H3 `momentum_rsi` (−1, 0, +1, −1, 0, +1) **[axis-collapse control]** *(mirror of H2)*

3 maps × 2 sizes = **6**; ladders L1 (1, 1, 0.5, 1, 1, 0.5) ·
L2 (1, 1, 0, 1, 1, 0) = **2**. → T-H per panel: **8**.

**Gated denominator:**

| panel | T-D | T-E | T-F | T-G | T-H | total |
|---|---|---|---|---|---|---|
| P-BTC | 24 | 22 | 10 | 9 | 8 | **73** |
| P-ETH | 24 | — | 10 | 9 | 8 | **51** |
| P-SOL | 24 | — | 10 | 9 | 8 | **51** |
| **N (gated)** | | | | | | **175** |

Variant ids: `<PANEL>-DIR-<TAX>-<map>-<size>[-ts6]` /
`<PANEL>-RISK-<TAX>-ladder-<vec>[-vb]`. Counts are pinned by a test
(`enumerate_all_w()` total == 175 gated + 8 annex). The frozen 36-variant
enumeration is untouched.

**Pre-OOS structural-feasibility readout (registered):** before OOS
contact, per-variant TRAIN-side trade frequencies are computed (train rows
only — no OOS contact) and every variant whose projected pooled-OOS trade
count falls below clause 7's floor is flagged
**structurally-ungateable-as-registered**; the flags are committed with
the sweep artifact and §8's effective denominator uses them.

## 6. The hypothesis-family quarantine (lock), in full

**Principle (one sentence):** REPORT §6.2 is a *contamination quarantine*,
not a general new-data-only doctrine — the universal rule is registration
before OOS contact (ADR-001), which every other registered family
satisfies on these panels because none has ever been evaluated there; the
fade-positive-funding-extremes family cannot, because it was (H8 deep
replay, the near-miss), and that is why it alone waits for post-freeze
data. The quarantine travels with the **hypothesis**, not the ticker:
funding-extreme episodes on ETH/SOL are the same 2021/2022 market events
the H8 replay mined, so the lock applies on **all panels**.

**Locked annex (evaluated, published, CANNOT ship):**
- A1 `fade_pos_x_only` (0, 0, −1, 0, 0, 0) — T-D label space
- A2 `fade_pos_graded` (0, −0.5, −1, 0, 0, 0)

× 2 sizes × time-stop {none, 6} = **8** P-BTC annex Variants (reported
separately in R3; never in the gated survivor pool). They run as
falsification context, exactly like the frozen deep replay.

**Reference extremity labeling (taxonomy-independent, all panels).** For
every Survivor, regardless of its taxonomy, compute on its panel the
per-fold train-only reference cuts c_hi = q60(|funding_rate_8h|),
c_x = q90(|funding_rate_8h|) (identical to T-D §4). A pooled-OOS bar is a
**reference positive-extremity bar** iff funding_rate_8h ≥ 0 ∧
|funding_rate_8h| ≥ c_hi (that fold's cut). All lock tests below use this
labeling; test-pinned.

**Lock layer 1 — pure-map predicate.** A Variant is locked iff its action
map (i) is short in ≥ 1 positive-funding extremity band of its own label
space or, for taxonomies without extremity bands, is short on every
positive-funding label, (ii) takes no nonzero action in any
negative-funding label, and (iii) is long nowhere. (A1/A2 satisfy it; the
registered symmetric maps do not.)

**Lock layer 2 — counterfactual extremity-neutralized twin (the binding
test, both directions of the burned signal).** For every Survivor on
every panel, construct the twin w′: on every reference positive-extremity
OOS bar, w′ = w̄_mild(fold) — the Survivor's mean signed w over the
reference positive-MILD (f ≥ 0, |f| < c_hi) bars of that fold's OOS
(fallback 0 if that fold has none); w′ = w elsewhere. Re-run the pooled
OOS pipeline on w′ (same fills, costs, funding; same registered common
null draws). **The Survivor is family-locked unless the twin still passes
beats_flat@10 bps AND null_p95.** This catches the short-fade coat
(twin zeroes the short leg) and the long-only de-risk coat (twin re-risks
the extremity bars to the Variant's own mild-bar exposure) with one
registered instrument.

**Lock layer 3 — share backstop (majority rule).** Decompose pooled-OOS
net PnL as bar-level net return contributions (each bar's return including
that bar's |Δw| cost and any funding accrual), summed arithmetically.
Locked-leg bars = reference positive-extremity bars with w < 0. Evaluated
only when the arithmetic total > 0: the Survivor is family-locked iff
leg_sum / total_sum > **0.5**. (Majority rule — a Schelling point chosen
for defensibility, not tuned to any observed share.)

A family-locked Survivor is published in the falsification chapter with
full numbers and the specific layer that locked it; it cannot be the
Winner this cycle, on any panel.

**Forward registration (the §6.2 protocol, made concrete).** A1/A2 ×
2 sizes × time-stop {none, 6} are registered on **all three assets**
(24 forward Variants) on post-freeze data: OOS = 2026-06-11 00:00 UTC
onward, quarterly folds per §6.2.4 with §1's embargo rule inherited, this
document's 8-clause gate, §6.2.3 active-sample bar verbatim. Evaluation
occurs when ≥ 4 post-freeze quarterly folds exist (earliest 2027-07-01);
any earlier readout is labeled underpowered and non-shippable. This
cycle's submission reports the registration itself, not a result.

## 7. The shipping gate — 5 frozen clauses + 3 added (pooled OOS per panel, 10 bps rung)

| # | clause | status |
|---|---|---|
| 1 | beats_flat: net@10 bps > 0 | frozen |
| 2 | beats_hodl: Sharpe > HODL Sharpe | frozen |
| 3 | null_p95: Sharpe > episode-shuffle null q95 | frozen |
| 4 | top5_pass: net after removing the 5 best OOS trades > 0 | frozen |
| 5 | ladder_pass: net@20 bps > 0 | frozen |
| 6 | **null_p99**: Sharpe > episode-shuffle null q99 | **added** |
| 7 | **min_active_sample** (from REPORT §6.2.3): OOS trades ≥ 60 ∧ nonzero-position OOS bars ≥ 200 ∧ nonzero trades in ≥ 60% of feature-covered folds (a fold is covered iff its OOS holds ≥ 1 non-`na` bar for the Variant's taxonomy) ∧ fold-concentration rule below | **added** |
| 8 | **topk_pass**: net after removing the K best OOS trades > 0, K = max(5, ceil(0.02 × OOS trade count)) | **added** |

All eight must hold. **Fold-concentration formula (pinned):** with
per-fold OOS compounded nets r_i and pooled net R = Π(1+r_i) − 1,
evaluated only when R > 0: contribution_i = ln(1+r_i)/ln(1+R); the clause
fails iff max_i contribution_i > 0.5. (Negative folds give negative
contributions; a contribution may exceed 1 — that fails. The small-R
discontinuity is accepted as conservative.) A unit test pins a worked
example before OOS contact. **"Trades" in clauses 7 and 8 are the trade
objects produced by the frozen `lab/hooks.py` segmentation.**

**Null mechanics (pinned).** Episode-shuffle, common draws per (panel,
taxonomy, fold), **D = 1000**. **`na`-labeled episodes are frozen in
place:** the permutation acts only on non-`na` episodes, which fill the
non-`na` bar positions in permuted order with lengths preserved; `na` bar
positions are invariant across draws. (Registered now because the frozen
panel had no structurally-missing eras, so "byte-identical to frozen
hooks" cannot pin this case; freezing `na` blocks keeps every draw's
activity profile inside the Variant's feature-covered eras — the
conservative choice.) RNG map: a fresh
`numpy.random.default_rng([17, panel_index, taxonomy_index, fold_ordinal])`
per (panel, taxonomy, fold), with panel_index P-BTC=0 / P-ETH=1 /
P-SOL=2, taxonomy_index T-D=0 / T-E=1 / T-F=2 / T-G=3 / T-H=4, and
fold_ordinal the panel-local 1-based index; the index tables are printed
in the sweep artifact. Frozen-artifact byte-compatibility applies only to
the frozen 36-variant path. Null and variant backtests run over the full
panel index with returns restricted to OOS (frozen semantics); the
performance shortcut in §9 is permitted only under its equivalence proof.
Quantiles via the same numpy quantile call as the frozen p95; clause
mechanics for 1–5 are byte-identical to `lab/gate.py` / `lab/hooks.py`.

**Selection (ADR-001 unchanged).** Rank key = mean per-fold train Sharpe
@10 bps (tiebreak: lower mean train max-DD; residual exact ties break
lexicographically on variant id), within panel. Winner = highest
train-ranked, ship-eligible Survivor (gate-passing, not family-locked,
live-verifiability precondition met) on the highest-priority panel with
any such Survivor; panel priority **P-BTC → P-ETH → P-SOL** (pre-stated;
the Skill ships on the Winner's asset). For any Winner, the same
Variant's results on the other panels are published as transfer evidence
(disclosure, not a clause; see §8 for the correlation discount).

**Honest-N.** Headline per (panel, taxonomy): pooled-OOS regime-episode
count. Any candidate statement quotes its ACTIVE sample (trades /
nonzero-position bars / folds-with-trades) — FREEZE §3 amendment 4 carried
forward.

## 8. R3 disclosure plan (the denominator, in advance)

- Gated N = **175** (73 + 51 + 51); locked annex = **8**, reported
  separately; forward registration = **24** (reported as registered, not
  evaluated); total evaluated this cycle = **183**.
- **Effective hypotheses: ≈ 32** distinct map/ladder structures (T-D 8,
  T-E 7, T-F 6, T-G 6, T-H 5). Dressings (size, time-stop, vol-band) and
  the three correlated panels do NOT multiply hypotheses. Cross-panel
  agreement is expected under both signal and null because the assets are
  correlated; transfer evidence is reported as **correlation-discounted
  consistency, never independent confirmation**, with measured pairwise
  pooled-OOS return correlations disclosed next to it.
- Expected null-clause pass-rate: clause 6 alone (it implies clause 3)
  ≈ 1% by construction ⇒ ~1.75 expected null-clause passers across 175.
- Full-gate false-pass calibration: **per (panel, taxonomy) cell** (13
  cells), ≥ 200 common null draws pushed through the full 8-clause gate
  for that cell's top train-ranked Variant; per-cell rates AND their
  Monte-Carlo standard errors disclosed. The only analytically binding
  expectation is the ~1% clause-6 rate; full-gate numbers are indicative
  calibration, never the headline.
- **Effective denominator:** the §5 structural-feasibility flags are
  reported next to N; the wider-null narrative counts only
  structurally-gateable Variants as evidence strength.
- **Era-split disclosure:** for any Survivor — pooled-OOS net PnL, trade
  count, and clause-by-clause pass status split at **2025-04-01**
  (pre-frozen-window era vs frozen-window-overlap era), plus the count of
  its OOS trades coinciding with the five published near-miss crash days
  (2025-11-04, 2025-11-20, 2025-12-29, 2026-05-27→28, 2026-06-01→02). A
  Survivor whose pass disappears in the pre-2025-04 era is reported with
  exactly that framing.
- Clause-6 marginality: for any Variant whose clause-6 margin lies inside
  the bootstrap CI of its cell's pooled q99 (D = 1000), that CI is
  disclosed next to the verdict.
- Grid-asymmetry disclosure: G2 is the one direction-asymmetric cell
  (interaction filter without an economic mirror); ladder families are
  long-only by design. Both stated here so no post-hoc framing is needed.
- **Cumulative-contact disclosure:** 36 frozen Variants (≈ 26 effective
  hypotheses) were already evaluated on the overlapping 2025-04→2026-06
  window, plus the lane-3 perturbation grid and the H8 deep replay; the
  report states this next to the new denominator.

## 9. Power, calibration, and the performance shortcut

- **Planted-edge power calibration runs once per panel** (lane-2 style,
  unmodified pipeline, drift aligned with a registered map,
  labels/funding untouched), ≥ 3 rungs (5/10/25 bps/bar) on each panel.
  The frozen power statement does not transfer automatically to 21 folds,
  8 clauses, or other assets' vol profiles. Budget ≈ 4× the corresponding
  panel's sweep share; rung count may be reduced (min 2) ONLY by a dated
  §13 amendment made before lane-2 starts.
- An independent lane re-implements any Survivor's scalars from raw CSVs
  (lane-1 standard: max |diff| ≤ 1e-9; thresholds re-derived from
  boundary-truncated raw files).
- **Performance shortcut (conditional):** restricting each null draw's
  backtest to the fold's OOS window is permitted ONLY after BOTH (a) a
  bit-for-bit equivalence run reproducing the frozen
  `artifacts/sweep_results.json` scalars, AND (b) a pinned W-panel pilot
  cell — P-BTC, T-D, folds {F03, F08, F21}, full D = 1000 — matching the
  unrestricted reference path bit-for-bit, with the DD guard verified to
  fire in ≥ 1 draw of the pilot (guard/time-stop state is path-dependent;
  "bar returns are bar-local" does not cover it). If either fails, the
  unoptimized path runs (≈ 12 h wall is budgeted and acceptable).

## 10. Prior-contact register (what we already knew when we wrote this)

Design-relevant contacts, disclosed in full (details and exact numbers in
the cited artifacts):

1. **H8 deep replay** (REPORT §5, `artifacts/deep_replay.json`): the
   frozen-cut fade rule on 2021→2026 — net +40.4% @10 bps, top-5 removal
   flips to −22.6%, 2022 alone +109.8%, pos-extreme = 46.8% of bars, DD
   guard fired 1,506 bars. This is why the fade family is quarantined
   (§6) on every panel and why clause 7's fold-concentration rule exists.
   Pre-2025 data is evaluation-contaminated for THIS hypothesis family
   only; no other registered family has ever been evaluated on it.
2. **Lane-3 perturbation grid** (lane3_near_miss.md §2): q=(0.25,0.75) and
   top-N=3 flip the old near-miss to PASS on the old window — both remain
   banned retroactive knobs; T-D's graded cuts (q60/q90) are a different,
   here-registered structure, and no registered Variant reuses the old
   q=(0.25,0.75) derivation. The §6 lock layers are the structural answer
   to this contact.
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
   OOS starts 2026-06-11 00:00 UTC. *(Update, §13 amendment 28: the live
   calibration cron keeps appending paired funding point-snapshots 3×/day,
   including stamps after that OOS start — these are monitor-calibration
   samples, not bar series, and not evaluation contact; forward evaluation
   discloses the cron's full sample log. The W-sweep is unaffected — its
   OOS ends 2026-06-09 20:00.)*
10. **CSV tails to 2026-06-10** committed but never consumed by any sweep;
    W-panels end 2026-06-09 20:00, inside all sources' verified spans.
11. **Frozen-window-overlap era knowledge** (REPORT §3.2 trade table,
    FREEZE §1 bear-OOS framing): the last ~5 folds of every W-panel OOS
    were studied exhaustively by the frozen build — the §8 era-split
    disclosure is the registered mechanical consequence.

## 11. What ships under each outcome (pre-stated)

- **Ship-eligible Survivor exists** → the Winner ships as a validated
  strategy Skill: SKILL.md re-authored from the frozen parameters of the
  Winner (thresholds = its panel's final-fold train numbers, the exact
  numbers gated on the final fold's OOS), live-validated against the CMC
  MCP (incl. the §2 per-asset Gate-0 addendum for a non-BTC Winner),
  REPORT/FREEZE/README/SUBMISSION/demo/video updated, with the full R3
  story and correlation-discounted transfer evidence. Threshold freeze +
  amendments procedure as in the floor. **A Winner from an axis-collapse
  control is framed honestly as evidence that the collapsed axis added
  nothing for that family** (e.g. a G1/G3 Winner is a trend strategy and
  the Skill's regime narrative says so) — the honest readout, not an
  embarrassment.
- **Only family-locked Survivors** → the entry ships the upgraded monitor
  + the locked candidate(s) published in the falsification chapter (with
  the §6 layer that locked each) + the active forward registration — "the
  gate found something it refuses to ship until its own published
  protocol is satisfiable" is the story, verbatim.
- **Null** → the wider-null entry: 175 registered Variants (~32 effective
  hypotheses), three assets, ~5–6-year multi-regime OOS, 8-clause gate,
  expected-vs-observed passes disclosed with the effective denominator.
  Strictly stronger than the floor's null.
- **In every outcome** the Skill deepens CMC MCP usage: ≥ 7 verified tools
  with honest roles (classifier inputs only Gate-0-verified Features;
  derivatives/narratives/macro-events as labeled display context), F&G
  CMC-end-to-end, and the live/lab basis disclosures per D1/D3.

## 12. Build phases (execution sketch; details in task list)

1. **Lab extension (TDD, floor tests stay green):** ETH/SOL funding +
   klines backfills; CG daily-OI export + registered loader (§2) with the
   stamp-semantics cross-check; Gate-0 addendum dump for ETH/SOL (§2);
   panel loader (multi-panel); T-D…T-H classifiers with `na` semantics;
   time-stop + vol-band rule surface (§3 pinned semantics); W-fold
   geometry + embargo computation (§1); W-variant enumeration
   (count-pinned 175+8); lock layers 1–3 implementation (test-pinned);
   clause 6/7/8 implementation with the §7 worked example; null
   `na`-freeze mechanics; structural-feasibility readout (train-side);
   equivalence runs for the §9 shortcut (optional).
2. **W-sweep** exactly as registered; artifacts committed.
3. **Adversarial lanes** (separate, never self-approving): reproduction,
   per-panel planted-edge calibration, survivor refutation (incl. lock
   layers audit), R3 audit.
4. **Re-author** per §11 outcome; independent review; submission package
   by 2026-06-19.

## 13. Amendment log

**2026-06-10 — critic-lane review folded in (pre-OOS-contact; lanes:
methodology M*, feasibility W*, judge J*; all three verdicts
approve-with-amendments).** Amendments:

1. (M1, J-W1, J-W3, W3, M5) §6 rebuilt: taxonomy-independent reference
   extremity labeling; lock extended to ALL panels (J-W2; aligns with
   ADR-002 Decision 4 and asset-unqualified REPORT §6.2); counterfactual
   extremity-neutralized twin added as the binding layer (catches both
   the short-fade and long-only de-risk circumventions); share backstop
   lowered 80% → 50% with attribution formula pinned.
2. (M2) Null `na`-episode treatment registered: `na` episodes frozen in
   place; permutation over non-`na` episodes only.
3. (M3) §9 shortcut now additionally requires the pinned W-panel pilot
   cell with a verified guard-fire; frozen-artifact equivalence alone
   ruled insufficient (path-dependent guard/time-stop state).
4. (M4, W8, J-W9b) Clause 7 fold-concentration formula pinned
   (log-contribution, max > 0.5 fails); trade objects pinned to frozen
   hooks segmentation; worked-example unit test required pre-OOS.
5. (M6, J-W7) Structural-feasibility readout registered (train-side,
   pre-OOS); effective denominator in R3; G1/G3/L1 infeasibility
   expectation stated in §5.
6. (M7) Full-gate calibration widened to per-(panel, taxonomy) cells with
   MC standard errors; binding expectation scoped to the clause-6 rate.
7. (M8, W4) §2 CG-OI cadence sentence corrected to recon wording; daily-OI
   loader registered (dedupe, formula, availability, staleness, pre-OOS
   stamp-semantics cross-check).
8. (M9, J-W4) Direction mirrors registered: E5, F4, G3, H3 (+22 Variants;
   N 153 → 175; counts table, R3 expectations, effective-hypothesis count
   restated); remaining asymmetric cell (G2) and long-only ladder design
   disclosed in §8; ADR-002 wording corrected (hand-chosen direction
   hypotheses with mechanically-enumerated dressings, mirrored).
9. (M10, W7) RNG seed map pinned per (panel, taxonomy, fold); residual
   rank-tie rule pinned (lexicographic id).
10. (M11, J-W6) Effective-hypothesis convention registered (≈ 32;
    collapse over size/time-stop/vol-band/panel); cross-panel transfer
    pre-framed as correlation-discounted consistency; "clauses 3∧6"
    phrasing corrected to clause-6-alone.
11. (M12, W11) Embargo computation slice pinned (first-fold train, that
    fold's cuts, computed once pre-OOS, printed in artifact).
12. (M13) Span-start rule written; ETH alignment stated as registered
    choice.
13. (M14) Clause-6 marginality CI disclosure registered (D stays 1000).
14. (M15, W9, J-W9a) ADR-002 lock pointer fixed (§8 → §6); coverage-floor
    unit defined (90 distinct UTC days); hygiene lines added.
15. (W1) T-F direction maps: fg-mid (and `na`) act 0 — explicit.
16. (W2) Gate-0 addendum dump for ETH/SOL registered as a pre-OOS
    requirement with a ship-eligibility precondition fallback.
17. (W5) Coverage floor restated per (fold, taxonomy, axis), covering
    fixed-cut axes; SMA200 "warmup" framing corrected (sma-na on every
    panel's early bars).
18. (W6) Time-stop semantics pinned (run definition, sign-flip
    continuation, k-th-bar exit, DD-guard precedence, re-entry rule).
19. (W10) D2 supersession note added (§2), scoped to W-panels.
20. (W12, J-W10) Planted-edge calibration extended to once per panel,
    ≥ 3 rungs, with the descope-only-by-amendment rule.
21. (J-W5) Era-split disclosure + crash-day-coincidence count registered
    in §8; prior-contact item 11 added.
22. (J-W8) The quarantine principle stated head-on in §6 (and mirrored in
    ADR-002).
23. (J-W9c) Forward registration inherits §1's embargo rule and is
    extended to all three assets (24 forward Variants).
24. (J-W9d) "Hypothesis family" added to CONTEXT.md as a defined term
    distinct from the frozen "Family".

**2026-06-11 — Phase-1 build findings folded in (still pre-OOS-contact;
no OOS row of any W-panel has been evaluated).** Amendments:

25. (build lane, SOL funding) Binance ran SOLUSDT funding on a ~2h
    interval during the FTX crash week: 75 genuine off-schedule
    settlements 2022-11-09 20:00 → 2022-11-18 06:00 UTC (incl. −2% cap
    prints). These are EXCLUDED from `funding_rate_8h`: the registered
    execution model (§3) accrues funding only at 00/08/16 UTC stamps, and
    the 00/08/16 series is verified hole-free through the episode.
    Millisecond-jitter snap tolerance is 60s (max observed 47ms). BTC and
    ETH histories verified to contain zero off-schedule settlements.
    Consequence disclosed: ~9 days of SOL intra-window funding accrual is
    omitted; direction of bias is conservative for short-carry variants
    in that week (they would have EARNED the omitted negative prints).
    Disclosed in `docs/DATA_PROVENANCE.md`.
26. (registered determination outcome, CG OI) `cg_oi_history` stores
    daily OI candles, not single values; the §2 cross-check determined
    stamp = candle start and `open_oi` = the D 00:00 snapshot (corr
    +0.370 at offset 0 vs the bybit daily era; `close_oi` peaks at offset
    +1 and is excluded as a ~24h leak). Export uses `open_oi`; the §2
    availability and staleness rules apply unchanged.
27. (embargo formula repair, T-F) The §1 embargo median is computed over
    **non-`na` episodes** of the first fold's train slice; the 42-bar
    floor binds when none exist. Without this, T-F's first-fold train —
    100% `fg-na` (F&G history starts 2023-06-29) — forms ONE 2,190-bar
    episode, E = 2,190, and every T-F OOS slice is structurally empty:
    a formula artifact that would silently void all 30 T-F variants,
    discovered by the panels lane's train-side tests. `na` episodes are
    missing-feature placeholders, not regime episodes (they are frozen in
    the null and excluded from honest-N), so the repaired formula is the
    registered intent stated precisely. Amended before any OOS
    evaluation; `panels_w.compute_embargo` updated to match.
28. (§10 item 9 update) The live calibration cron continues appending
    paired funding point-snapshots 3×/day to
    `data/backfill/funding_calibration.csv`, including stamps after the
    forward registration's OOS start (first: 2026-06-11 00:07 UTC).
    Point snapshots for the monitor's D1 basis table are not bar-series
    evaluation contact; recorded here so the forward evaluation
    (≥ 2027-07) can disclose the full log.
