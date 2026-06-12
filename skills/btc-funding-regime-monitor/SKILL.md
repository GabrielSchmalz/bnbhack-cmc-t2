---
name: btc-funding-regime-monitor
description: >-
  Live BTC funding-regime monitor. Classifies the current market into one of
  four frozen regimes (pos-mild, pos-extreme, neg-mild, neg-extreme) from a
  single Gate-0-verified CoinMarketCap MCP field, using walk-forward-derived,
  frozen absolute thresholds, reports per-regime expected-behavior notes —
  every note carries "validated": false — and renders a clearly-separated
  market-context display from six further verified CMC MCP tools (labeled
  context, never branched on). This is a regime MONITOR, not a trading
  strategy: two validation layers stand behind it — the floor sweep (0 of 36
  variants passed) and the widened W-sweep (183 Variants, 3 assets, 8-clause
  gate: no Winner; the one effective passer was quarantined by pre-registered
  hypothesis-family locks) — and the monitor never emits entry/exit/sizing
  advice. Trigger phrases: "what funding regime is BTC in", "btc funding
  regime", "check btc positioning regime", "btc crowding check", "run the btc
  regime monitor", "is btc funding extreme".
license: MIT
compatibility: ">=1.0.0"
user-invocable: true
allowed-tools:
  - mcp__cmc-mcp__get_global_metrics_latest
  - mcp__cmc-mcp__get_crypto_quotes_latest
  - mcp__cmc-mcp__get_global_crypto_derivatives_metrics
  - mcp__cmc-mcp__get_crypto_technical_analysis
  - mcp__cmc-mcp__trending_crypto_narratives
  - mcp__cmc-mcp__get_upcoming_macro_events
  - mcp__cmc-mcp__get_crypto_latest_news
---

# BTC Funding Regime Monitor

Classifies BTC's current funding regime from live CoinMarketCap MCP data using
the frozen TC taxonomy (funding sign × extremity) and emits a regime report
plus a machine-readable monitor spec block, followed by a clearly-separated
market-context display (labeled context, never branched on).

**What this Skill is NOT.** It is not a trading strategy and emits no
entry/exit/sizing recommendation, ever. Two validation layers stand behind
that refusal. Floor layer: 36 variants on this taxonomy family were swept
through a pre-registered walk-forward shipping gate and **0 of 36 passed**
(expected null-clause pass-rate 0.0500). Widened layer (W-freeze 2026-06-11,
`docs/FREEZE-W.md`): **183 registered Variants** were evaluated across three
assets (~5–6-year multi-regime OOS) under a strictly harder 8-clause gate —
**4 gate passes = 1 effective hypothesis, quarantined by the pre-registered
hypothesis-family locks; `ship_eligible_count = 0`; no Winner**. The
classifier and its thresholds remain exactly the frozen floor artifacts that
were validated as machinery; the per-regime notes are train-period descriptive
statistics, each labeled `"validated": false`. Provenance: §7.

---

## 1. Prerequisites

- Access to the CoinMarketCap MCP server (`https://mcp.coinmarketcap.com/mcp`,
  streamable HTTP). Authentication: API key in the `X-CMC-MCP-API-KEY` header,
  configured in the consuming agent's MCP client settings. Never print or echo
  the key.
- The seven tools in `allowed-tools` must resolve in the server's
  `tools/list`. Only `get_global_metrics_latest` is **load-bearing for
  classification**; the other six supply labeled display context only
  (per-tool roles and degradation table in §6). The last three
  (`trending_crypto_narratives`, `get_upcoming_macro_events`,
  `get_crypto_latest_news`) are optional context — their failure is noted and
  otherwise ignored.
- **Payload parsing rule** (Gate-0, `docs/gate0/GATE0-FREEZE.md`): every tool's
  payload arrives as a JSON **string** inside `result.content[0].text`. Parse
  that string before reading any field.

## 2. Tool-call workflow

Execute in order. Record the UTC invocation time first — it becomes `as_of_utc`.
Steps 1–3 feed the classification + monitor block; steps 4–7 feed ONLY the §5
market-context display and are never branched on. Every step degrades
gracefully per §6 — a failed tool produces a noted omission, never an abort.

1. **Call `mcp__cmc-mcp__get_global_metrics_latest`** with arguments `{}`.
   Parse `result.content[0].text` as JSON. Extract:
   - `leverage.funding_rate.average.current` — **the only classification
     input** (string with explicit `%` sign, e.g. `"+0.0015866%"`). Field path
     verified in `docs/gate0/get_global_metrics_latest.json`.
   - `sentiment.fear_greed.current.index` — context display only (raw int
     0–100), never branched on. F&G is CMC end-to-end: the lab history behind
     the report is the same vendor's index. Same dump file.
   - `dominance.btc.current` (signed % string) and
     `rotation.altcoin_season.current.index` (raw int) — context display
     only, never branched on; both were Gate-0-REJECTED as classifier inputs
     (no lab-side per-bar history under R-SRC; the dominance payload also
     carries a known server-side field-level oddity in its `eth`/`others`
     yearly blocks — display the BTC value verbatim, claim nothing more).
     Same dump file.
   - `last_updated` — echo it; this payload carries a **daily** stamp
     (`"10 June 2026 12:00 AM UTC+0"` at Gate 0), so do not claim intraday
     freshness for it. Same dump file.
2. **Call `mcp__cmc-mcp__get_crypto_quotes_latest`** with arguments
   `{"id": "1"}` (BTC). Parse `result.content[0].text` (a JSON array). Extract
   from element `[0]` — context display only, never branched on:
   - `[0].price` (raw float, USD), `[0].percent_change_24h` and
     `[0].percent_change_7d` (raw floats, **percent points**),
     `[0].last_updated_time`. Field paths verified in
     `docs/gate0/get_crypto_quotes_latest.json`. This is the only tool that
     returns raw numeric floats.
3. **Call `mcp__cmc-mcp__get_global_crypto_derivatives_metrics`** with
   arguments `{}`. Parse `result.content[0].text`. Extract — context display
   only, never branched on:
   - `totalOpenInterest.current` (magnitude-suffixed USD string, e.g.
     `"381.77 B"`) and `totalOpenInterest.percentage_change_24h` (signed %
     string) — global derivatives OI display. Field paths verified in
     `docs/gate0/get_global_crypto_derivatives_metrics.json`.
   - `fundingRate.current` (string, bare decimal, **unit-undeclared and
     basket-ambiguous** — echo verbatim, label it "secondary funding field,
     unit unresolved (OPEN-1)", and never use it in a comparison; D1 in
     `docs/gate0/FREEZE-ADDENDUM-decisions.md`).
   - `btc_liquidations.total_usd_4h.{total,long,short}` (formatted USD
     strings; the 4h window matches the lab bar size — display-only live
     context per Gate-0 §9). Same dump file.
4. **Call `mcp__cmc-mcp__get_crypto_technical_analysis`** with arguments
   `{"id": "1"}` (BTC; daily timeframe only — the tool has no timeframe
   parameter). Extract — context display only, never branched on:
   - `rsi.rsi14` (string, e.g. `"23.89"`) and
     `moving_averages.simple_moving_average_200_day` (comma-grouped USD
     string, e.g. `"78,240.34"`). Both field paths Gate-0-verified in
     `docs/gate0/get_crypto_technical_analysis.json` (the 200-day window was
     verified as served). For display you may strip commas and show
     price-vs-SMA200 side (above/below) using the step-2 price — a derived
     display line, never a clause.
5. **Call `mcp__cmc-mcp__trending_crypto_narratives`** with arguments `{}`
   (optional context). Payload: `categoryList.headers` (column names) +
   `categoryList.rows` (arrays aligned to headers). Display the top ≤ 3 rows'
   `trendingRank` + `categoryName` columns as "trending narratives". Verified
   shape: `docs/gate0/trending_crypto_narratives.json`. Unstructured/
   non-quantitative — Gate-0 §9 permits it as optional context only.
6. **Call `mcp__cmc-mcp__get_upcoming_macro_events`** with arguments `{}`
   (optional context). Payload: `upcomingEventNews.headers` +
   `upcomingEventNews.rows`. Display ≤ 3 rows' `title` + `eventDate` columns
   as "upcoming macro/regulatory events". Verified shape:
   `docs/gate0/get_upcoming_macro_events.json`. Optional context only.
7. **Call `mcp__cmc-mcp__get_crypto_latest_news`** with arguments
   `{"id": "1", "limit": 5}` (optional context). Payload: top-level `headers`
   + `rows`. Display ≤ 3 rows' `title` + `publishedAt` columns as "latest BTC
   headlines". Verified shape: `docs/gate0/get_crypto_latest_news.json`.
   Optional context only.
8. **Convert units** per the walkthrough in §3.1.
9. **Classify** per the decision table in §3 — from the step-1 funding field
   and nothing else.
10. **Emit** the human-readable regime report, the fenced JSON monitor spec
    block (schema unchanged from the floor freeze — §5), and the separated
    market-context display section, applying the degradation rules of §6 for
    any tool that failed.

## 3. Regime classification rules (frozen TC decision table)

The classifier consumes **one** Feature: the live global average funding rate,
converted to a decimal 8h-style rate `f`.

Two clauses:

- **Sign clause:** `f >= 0` → `pos`; `f < 0` → `neg`.
- **Extremity clause:** `|f| >= funding_hi_abs` → `extreme`; else `mild`,
  where the frozen threshold is

  ```
  funding_hi_abs = 8.385600000000002e-05
  ```

  (q80 of |funding_rate_8h| on the F4-train slice, 2025-04-03 00:00 ≤ t <
  2026-04-01, 2178 bars of Binance BTCUSDT 8h settled funding; frozen
  2026-06-10, `docs/FREEZE.md` §2.2. Any change to this number, the enum, or
  the emitted schema triggers full re-validation. The W-freeze
  (`docs/FREEZE-W.md` §3) re-confirmed all of them UNTOUCHED: the W-sweep
  validated nothing shippable, so no G7 re-validation was triggered.)

| sign clause (`f >= 0`) | extremity clause (`\|f\| >= 8.385600000000002e-05`) | regime |
|---|---|---|
| TRUE | FALSE | `pos-mild` |
| TRUE | TRUE | `pos-extreme` |
| FALSE | FALSE | `neg-mild` |
| FALSE | TRUE | `neg-extreme` |

The enum ships verbatim — `pos-mild` · `pos-extreme` · `neg-mild` ·
`neg-extreme` (gloss: long-crowding mild/extreme, short-crowding mild/extreme —
funding sign proxies which side pays).

### 3.1 Unit-conversion walkthrough

The live field `leverage.funding_rate.average.current` is a string carrying an
explicit `%` sign. Conversion to decimal:

1. Raw fetched value (Gate-0 dump example): `"+0.0015866%"`
2. Strip the trailing `%` and any leading `+`: `"0.0015866"`
3. Parse as float: `0.0015866` (percent points)
4. Divide by 100: `f = 1.5866e-05` (decimal)

Worked classification: `1.5866e-05 >= 0` → `pos`; `|1.5866e-05| =
1.5866e-05 < 8.385600000000002e-05` → `mild` ⇒ **`pos-mild`**.

Negative example: `"-0.0091%"` → `-9.1e-05` → sign clause FALSE → `neg`;
`9.1e-05 >= 8.385600000000002e-05` → `extreme` ⇒ **`neg-extreme`**.

### 3.2 Funding-basis disclaimer (D1 — mandatory in every emission)

The live field is the **CMC global cross-venue average** funding rate; the
frozen threshold derives from **Binance BTCUSDT 8h settled funding history**
(`data/backfill/funding_btcusdt_binance.csv`). These are different baskets.
The monitor therefore compares **sign and extremity band only** — scale-free
forms — and never performs raw-magnitude arithmetic across the two bases. This
basis difference must be stated in every emission (it is one of the
`disclaimers` strings in §5). The paired-sample calibration between the two
bases lives in `reference_table.md` (never consulted at runtime).

### 3.3 Missing/NaN field — deterministic degradation

Any clause referencing a missing, null, or unparseable Feature evaluates
**FALSE** (frozen rule D4.3). Consequences:

- funding missing ⇒ sign clause FALSE → `neg` branch; extremity clause FALSE →
  `mild` ⇒ deterministic label **`neg-mild`**.
- The emission MUST then mark itself degraded: the top-level `degraded` key is
  `true`, `signal_snapshot` carries the null/raw failed value, the human report
  headline is prefixed `DEGRADED`, and a disclaimer states that the label is
  the deterministic missing-data default, not a market reading (§6).

## 4. Per-regime expected-behavior notes (F4-train statistics — `"validated": false`)

Descriptive statistics of the F4-train slice only (2025-04-03 00:00 ≤ t <
2026-04-01, 2178 bars), aligned to the PR-3 convention: label known at close
t → the described return is bar t+1, open-to-open. These are the ONLY numbers
the monitor's expected-behavior notes may cite, each carrying
`"validated": false`. They are train-period descriptions, not validated
edges — the shipping gate found NO variant on this taxonomy (or any other)
shippable, and the widened W-sweep then found no Winner on any of three assets
(§7). No OOS-derived number appears in any note.

| regime | bars (share) | episodes | med ep len | next-bar mean r | median r | %neg | ann. vol | train funding range |
|---|---|---|---|---|---|---|---|---|
| pos-mild | 1356 (62.3%) | 184 | 4 | −0.005% | +0.019% | 48.8% | 0.41 | +3.2e-07 .. +8.379e-05 |
| pos-extreme | 410 (18.8%) | 88 | 2 | −0.066% | −0.041% | 53.4% | 0.38 | +8.39e-05 .. +1.0e-04 |
| neg-mild | 386 (17.7%) | 100 | 2 | +0.067% | +0.032% | 48.7% | 0.47 | −8.326e-05 .. −6e-08 |
| neg-extreme | 26 (1.2%) | 9 | 2 | −0.159% | −0.256% | 69.2% | 0.63 | −1.518e-04 .. −8.417e-05 |

Per-regime note text (emit the one matching the current regime):

- **pos-mild** — Modal state: 62.3% of F4-train bars, 184 episodes, median
  episode 4 bars. Train next-bar drift is indistinguishable from noise (mean
  −0.005%, median +0.019%, 48.8% negative). `"validated": false`.
- **pos-extreme** — 18.8% of F4-train bars, 88 episodes, median episode
  2 bars. Train next-bar mean −0.066% (median −0.041%, 53.4% negative). This
  negative drift is precisely the pattern whose tradable form (fade positive
  funding extremes, `DIR-TC-H8`) **FAILED** the pre-registered shipping gate —
  see the falsification chapter, `docs/report/REPORT.md` — and whose widened
  symmetric sibling was **family-locked** by the W-sweep's pre-registered
  quarantine (§7). Do not read this note as an actionable fade.
  `"validated": false`.
- **neg-mild** — 17.7% of F4-train bars, 100 episodes, median episode 2 bars.
  Train next-bar mean +0.067% (median +0.032%). A train-period description,
  not a validated edge. `"validated": false`.
- **neg-extreme** — 26 bars / 9 episodes in F4-train: **insufficient sample to
  characterize**. The tabulated statistics are reported for completeness only
  and support no inference. `"validated": false`.

Extended quiet periods in which an extreme state never fires are normal
monitor behavior (one full OOS fold contained zero pos-extreme bars) — a long
run of `pos-mild`/`neg-mild` is not a malfunction.

The monitor emits **no** `active_ruleset`, no entry, no exit, no sizing —
the gate refused to validate any, and emitting one anyway would be the exact
dishonesty the gate exists to prevent (`docs/FREEZE.md` §3, amendment 2;
re-confirmed by `docs/FREEZE-W.md` §3, amendment 6).

## 5. Output format

Emit ALL THREE of the following, in this order.

**(1) Human-readable regime report** — headline `BTC funding regime: <regime>`
(prefixed `DEGRADED — ` when §6 applies), then: the raw fetched funding string
and its decimal conversion; the threshold comparison shown explicitly (e.g.
`|1.5866e-05| < 8.3856e-05 → mild`); the expected-behavior note for the
current regime with its caveats; and the validation status line: *"Validation:
two layers, nothing shippable — floor 0/36 variants passed the pre-registered
shipping gate; W-sweep 183 Variants evaluated on 3 assets under an 8-clause
gate, 4 passes = 1 effective hypothesis, family-locked, 0 ship-eligible, no
Winner. Nothing here is a validated edge. See docs/report/REPORT.md §3 and
§7."*

**(2) Fenced JSON monitor spec block** — exact schema (top-level keys:
`regime`, `degraded`, `as_of_utc`, `signal_snapshot`, `expected_behavior`,
`validation`, `disclaimers`). **The schema is byte-compatible with the floor
freeze** (`docs/FREEZE.md` §2–§3; `docs/FREEZE-W.md` §3 amendment 6): no new
top-level key, no new `signal_snapshot` key — the new context tools appear
ONLY in section (3), never in this block. `degraded` is a REQUIRED boolean:
`true` when any clause-relevant fetch failed and the §3.3 deterministic
missing-data default was used, `false` otherwise. Worked example with the
Gate-0 dump values:

```json
{
  "regime": "pos-mild",
  "degraded": false,
  "as_of_utc": "2026-06-10T18:23:00Z",
  "signal_snapshot": {
    "leverage.funding_rate.average.current": "+0.0015866%",
    "funding_rate_decimal": 1.5866e-05,
    "funding_threshold_abs": 8.385600000000002e-05,
    "global_metrics_last_updated": "10 June 2026 12:00 AM UTC+0",
    "sentiment.fear_greed.current.index": 15,
    "btc_price_usd": 61820.477784763956,
    "btc_percent_change_24h": 0.03458382,
    "derivatives.fundingRate.current_unit_unresolved": "0.00069614",
    "btc_liquidations.total_usd_4h": {
      "total": "17.91 M",
      "long": "1.64 M",
      "short": "16.27 M"
    },
    "status": "ok"
  },
  "expected_behavior": {
    "source": "F4-train descriptive statistics (2025-04-03..2026-04-01, 2178 bars; next-bar open-to-open convention)",
    "bars": 1356,
    "share_pct": 62.3,
    "episodes": 184,
    "median_episode_len_bars": 4,
    "next_bar_mean_return_pct": -0.005,
    "next_bar_median_return_pct": 0.019,
    "pct_negative": 48.8,
    "annualized_vol": 0.41,
    "train_funding_range": "+3.2e-07 .. +8.379e-05",
    "note": "Modal state; train next-bar drift indistinguishable from noise. Train-period description, not a validated edge.",
    "validated": false,
    "validated_metrics_ref": "docs/report/REPORT.md#3-falsification-chapter and §7 (W-sweep falsification chapter)"
  },
  "validation": {
    "status": "null-result",
    "gate": "floor: 0/36 variants passed; W-sweep: 4 of 183 evaluated = 1 effective hypothesis, family-locked; ship_eligible_count = 0; no Winner",
    "ref": "docs/report/REPORT.md"
  },
  "disclaimers": [
    "Walk-forward provenance: pre-registered purged/embargoed walk-forward, 2025-04-03..2026-06-09, 4 folds. Taxonomy-level honest_N = 225 pooled-OOS regime episodes — a taxonomy-level count, not a strategy sample. The single near-miss candidate (DIR-TC-H8, FAILED) had an active sample of only 30 OOS trades / 92 nonzero-position OOS bars / 3 of 4 folds.",
    "Funding basis: live value is the CMC global cross-venue average (leverage.funding_rate.average.current, % string, decimal = value/100); the frozen threshold derives from Binance BTCUSDT 8h funding history. Sign and extremity-band comparisons only — never raw-magnitude arithmetic across the two bases.",
    "No strategy cleared our pre-registered shipping gate (0/36 variants; expected null-clause pass-rate 0.0500). Expected-behavior notes are train-period descriptions with validated: false.",
    "Widened validation layer (W-freeze 2026-06-11, docs/FREEZE-W.md): 183 registered Variants evaluated across 3 assets (~5-6-year multi-regime OOS) under an 8-clause pre-registered gate; 4 passes = 1 effective hypothesis, quarantined by the pre-registered hypothesis-family locks (ship_eligible_count = 0, no Winner); 31 of 32 effective hypotheses cleared nothing on any panel. Locked candidates are published as falsification evidence only, validated: false. Forward registration active: 24 Variants, OOS 2026-06-11 onward, earliest evaluation 2027-07-01.",
    "Not financial advice."
  ]
}
```

Echo every fetched value verbatim in `signal_snapshot` — raw strings as
served, including signs, `%` symbols, and magnitude suffixes — alongside any
parsed decimals. `expected_behavior` always quotes the row for the **current**
regime from the §4 table, with the matching note text and `"validated": false`.

**(3) Market-context display section** — a clearly-separated section headed
`MARKET CONTEXT (display only — never branched on)`, AFTER the spec block,
containing the labeled context values from §2 steps 2–7 (plus the step-1
context fields): BTC price, 24h/7d change, RSI14, SMA200 (+ price-vs-SMA200
side), global derivatives OI + 24h change, secondary funding echo (labeled
unit-unresolved), 4h BTC liquidations, F&G index, BTC dominance, altcoin
season index, top trending narratives, upcoming macro events, latest BTC
headlines. Every line carries its role label; any failed tool's lines read
"unavailable (tool degraded)" or are omitted with a note. NOTHING in this
section feeds the classifier, the spec block, or any clause.

## 6. Graceful per-tool degradation

| tool | role | on failure / missing field |
|---|---|---|
| `mcp__cmc-mcp__get_global_metrics_latest` | **classification input** (funding); context (F&G, dominance, altseason, last_updated) | Sign and extremity clauses both evaluate FALSE (§3.3) ⇒ deterministic label `neg-mild`. Emission is marked degraded: top-level `degraded` = `true`, `signal_snapshot.status` = `"degraded: primary funding field unavailable"`, funding fields `null`, human headline prefixed `DEGRADED`, and an extra disclaimer string: "Label is the deterministic missing-data default (neg-mild), not a market reading." F&G/dominance/altseason context omitted. |
| `mcp__cmc-mcp__get_crypto_quotes_latest` | context only (BTC price, 24h/7d change) | Omit/`null` the price fields; note the omission. Classification unaffected. |
| `mcp__cmc-mcp__get_global_crypto_derivatives_metrics` | context only (global OI, secondary funding echo, 4h BTC liquidations) | Omit/`null` those fields; note the omission. Classification unaffected. |
| `mcp__cmc-mcp__get_crypto_technical_analysis` | context only (RSI14, SMA200) | Omit those context lines; note the omission. Classification unaffected. |
| `mcp__cmc-mcp__trending_crypto_narratives` | optional context (trending narrative categories) | Omit the narratives block with a one-line note. Classification and spec block unaffected. |
| `mcp__cmc-mcp__get_upcoming_macro_events` | optional context (upcoming macro/regulatory events) | Omit the events block with a one-line note. Classification and spec block unaffected. |
| `mcp__cmc-mcp__get_crypto_latest_news` | optional context (latest BTC headlines) | Omit the headlines block with a one-line note. Classification and spec block unaffected. |

A field that is present but unparseable (format drift from the Gate-0 dump) is
treated identically to missing: clause FALSE (when clause-relevant), degraded
marking, and the raw value echoed verbatim in `signal_snapshot` for diagnosis.
Context-only fields never set `degraded`.

## 7. Validation provenance (two layers)

- **Floor layer — a rigorous null.** 36 variants were swept through a
  pre-registered, purged/embargoed walk-forward shipping gate; **0 passed**;
  the expected null-clause pass-rate was **0.0500**. Full report and
  falsification chapter: `docs/report/REPORT.md` §3. Freeze decision:
  `docs/FREEZE.md`.
- **Widened layer — the W-sweep (W-freeze 2026-06-11, `docs/FREEZE-W.md`).**
  183 registered Variants evaluated (175 gated ≈ 32 effective hypotheses
  across P-BTC/P-ETH/P-SOL + 8 locked-annex Variants reported separately; 24
  forward Variants recorded, never evaluated) under an 8-clause gate on
  ~5–6-year multi-regime OOS. Outcome: **4 gate passes = 1 effective
  hypothesis** (`P-BTC-DIR-TD-D1-fade_extremes_graded_sym-{0.5, 1.0, 0.5-ts6,
  1.0-ts6}` — four dressings of one structure), **all four family-locked**;
  `ship_eligible_count = 0`; **NO Winner**. **31 of 32 effective hypotheses
  produced zero full-gate passes on any panel** (effective denominator 110
  after 65 train-side structural-feasibility flags). The headline honest-N:
  P-BTC/T-D = 1,502 pooled-OOS regime episodes vs the floor's 225, embargo
  E = 42 bars in all 13 (panel, taxonomy) cells.
- **The lock, and why the verdict is substantive.** The binding layer-2
  extremity-neutralized twin went net-negative for every passer (twin net
  −3.8%/−8.3% plain, −4.7%/−9.8% ts6; twin Sharpe −0.159/−0.230, below even
  the null q95); the layer-3 short-leg share on reference positive-extremity
  bars was 88.3–92.4% vs the 0.50 line. The same map fails 7 of 8 clauses on
  both other assets with negative nets, and its PnL lives in the
  replay-contaminated pre-2025-04 era. Marginality, disclosed wherever the
  passers are described (FREEZE-W §3 amendment 4): the strongest dressing
  (1.0-ts6) survives clause 8 by **topk_net = +0.000608205257158767** — six
  basis points of net after removing its K = 9 best trades — with max fold
  contribution **0.4898** vs the 0.50 fail line, driven by F05, the 2022-Q2
  Luna quarter. The story, verbatim from the registration: **"the gate found
  something it refuses to ship until its own published protocol is
  satisfiable."** The locked candidates are published in the W falsification
  chapter (`docs/report/REPORT.md` §7) with the lock layer that caught each,
  never as tradable specs, each carrying `"validated": false`.
- **Forward registration (active, stated here per FREEZE-W §3 amendment 2).**
  24 Variants (A1/A2 × 2 sizes × time-stop {none, 6} × 3 assets), OOS =
  2026-06-11 00:00 UTC onward, quarterly folds, this cycle's 8-clause gate;
  evaluation when ≥ 4 post-freeze quarterly folds exist (earliest
  2027-07-01); any earlier readout is underpowered and non-shippable. This
  cycle reports the registration itself, not a result.
- **Gate power.** Floor gate: calibrated by planting known regime-conditional
  edges into the real panel — the unmodified pipeline passes a true edge of
  ≥ 10 bps/bar robustly and 5 bps/bar marginally; the floor null is evidence
  about the data, not the machinery. W gate (readout 2026-06-12 under the
  `docs/report/adversarial/w_lane2_launch_note.md` §5 protocol; full readout
  `docs/report/adversarial/w_lane2_power_readout.md`): the per-panel
  planted-edge calibration (`bnbhack-wcal`, 9 cells: 3 panels × rungs 5/10/25
  bps/bar, the unmodified pipeline, 9/9 cells clean) measured **P-BTC
  detection at ≥ 5 bps/bar robustly** — all four aligned dressings pass all
  8 clauses at every rung, train rank #1 — and **P-ETH / P-SOL detection
  only at 25 bps/bar, marginally** (never top-ranked; ETH 10 bps misses by
  one clause; SOL ≤ 10 bps undetected). The W nulls behind this Skill's
  expected-behavior notes are therefore power-qualified: informative down to
  ≈ 5 bps/bar on BTC, only ≳ 25 bps/bar on ETH/SOL. All 20 aligned planted
  passers stayed family-locked; one planted ETH cell emitted a ship-eligible
  out-of-family trend confound with no lock layer firing — disclosed as a
  lock-scope defect finding: the family quarantine does not block
  secular-drift capture, and the era-split / 0-rung counterfactual
  disclosures are blocking checks for any future Winner claim.
- **The failed floor candidate.** `DIR-TC-H8-fade_pos_extreme_only-{0.5,1.0}`
  — **FAILED**, `"validated": false` — is published in full in the report's
  falsification chapter as a gate-caught exhibit (its 5 best trades carried
  >100% of the OOS gain; it failed the pre-registered top-5-trade-removal
  clause). It is referenced here for provenance only and is never emitted as
  actionable. Its active sample is 30 OOS trades / 92 nonzero-position OOS
  bars / 3 of 4 folds; the taxonomy-level honest_N of 225 episodes must never
  be quoted as that candidate's sample.
- **Taxonomy provenance.** TC (funding-sign × extremity) was selected on
  pre-stated criteria — classification stability (5.2% relabel under F1→F4
  threshold re-derivation), episode structure, live-computability from one
  Gate-0-verified field — not on OOS performance of any variant. The taxonomy
  is Band-inspired and independently gated on its own walk-forward; we claim
  no Band distillation for the shipped taxonomy (NMI vs rm17 Bands = 0.0228 —
  near independence). The W-freeze left the TC classifier, threshold, enum,
  and emission schema UNTOUCHED (`docs/FREEZE-W.md` §3) — no G7 re-validation
  was triggered, and any post-freeze change to them still triggers one.
- **Inputs freeze.** Every field this Skill reads is verified in the Gate-0
  dumps cited inline in §2 (`docs/gate0/*.json`, `docs/gate0/GATE0-FREEZE.md`).
  The four context-only tools added at the W re-authoring carry the honest
  roles Gate-0 §9 assigned them: TA/derivatives/global-metrics extras as
  labeled display context; narratives/macro-events/news as optional
  unstructured context, never in a classification clause. Live validation
  record for the 7-tool surface: `docs/gate0/skill_validation_run_w.json`.
- **Reference table.** `reference_table.md` (same folder) documents the
  percentile→absolute threshold mapping, the post-event refresh procedure
  (now including the W-cycle context), and the funding-basis calibration
  samples. The Skill **never** consults it at runtime.
