---
name: btc-funding-regime-monitor
description: >-
  Live BTC funding-regime monitor. Classifies the current market into one of
  four frozen regimes (pos-mild, pos-extreme, neg-mild, neg-extreme) from a
  single Gate-0-verified CoinMarketCap MCP field, using walk-forward-derived,
  frozen absolute thresholds, and reports per-regime expected-behavior notes —
  every note carries "validated": false. This is a regime MONITOR, not a
  trading strategy: 0 of 36 variants passed our pre-registered shipping gate,
  and the monitor never emits entry/exit/sizing advice. Trigger phrases:
  "what funding regime is BTC in", "btc funding regime", "check btc
  positioning regime", "btc crowding check", "run the btc regime monitor",
  "is btc funding extreme".
license: MIT
compatibility: ">=1.0.0"
user-invocable: true
allowed-tools:
  - mcp__cmc-mcp__get_global_metrics_latest
  - mcp__cmc-mcp__get_crypto_quotes_latest
  - mcp__cmc-mcp__get_global_crypto_derivatives_metrics
---

# BTC Funding Regime Monitor

Classifies BTC's current funding regime from live CoinMarketCap MCP data using
the frozen TC taxonomy (funding sign × extremity) and emits a regime report
plus a machine-readable monitor spec block.

**What this Skill is NOT.** It is not a trading strategy and emits no
entry/exit/sizing recommendation, ever. The strategy candidates built on this
taxonomy were swept through a pre-registered walk-forward shipping gate and
**0 of 36 variants passed** (expected null-clause pass-rate 0.0500). The
classifier and its thresholds are exactly the frozen, walk-forward-derived
artifacts that were validated as machinery; the per-regime notes are train-period
descriptive statistics, each labeled `"validated": false`. Provenance: §7.

---

## 1. Prerequisites

- Access to the CoinMarketCap MCP server (`https://mcp.coinmarketcap.com/mcp`,
  streamable HTTP). Authentication: API key in the `X-CMC-MCP-API-KEY` header,
  configured in the consuming agent's MCP client settings. Never print or echo
  the key.
- The three tools in `allowed-tools` must resolve in the server's `tools/list`.
  Only `get_global_metrics_latest` is load-bearing for classification; the
  other two supply display-only context (degradation table in §6).
- **Payload parsing rule** (Gate-0, `docs/gate0/GATE0-FREEZE.md`): every tool's
  payload arrives as a JSON **string** inside `result.content[0].text`. Parse
  that string before reading any field.

## 2. Tool-call workflow

Execute in order. Record the UTC invocation time first — it becomes `as_of_utc`.

1. **Call `mcp__cmc-mcp__get_global_metrics_latest`** with arguments `{}`.
   Parse `result.content[0].text` as JSON. Extract:
   - `leverage.funding_rate.average.current` — **the only classification
     input** (string with explicit `%` sign, e.g. `"+0.0015866%"`). Field path
     verified in `docs/gate0/get_global_metrics_latest.json`.
   - `sentiment.fear_greed.current.index` — context display only (raw int
     0–100), never branched on. Same dump file.
   - `last_updated` — echo it; this payload carries a **daily** stamp
     (`"10 June 2026 12:00 AM UTC+0"` at Gate 0), so do not claim intraday
     freshness for it. Same dump file.
2. **Call `mcp__cmc-mcp__get_crypto_quotes_latest`** with arguments
   `{"id": "1"}` (BTC). Parse `result.content[0].text` (a JSON array). Extract
   from element `[0]` — context display only, never branched on:
   - `[0].price` (raw float, USD), `[0].percent_change_24h` (raw float,
     **percent points**), `[0].last_updated_time`. Field paths verified in
     `docs/gate0/get_crypto_quotes_latest.json`. This is the only tool that
     returns raw numeric floats.
3. **Call `mcp__cmc-mcp__get_global_crypto_derivatives_metrics`** with
   arguments `{}`. Parse `result.content[0].text`. Extract — context display
   only, never branched on:
   - `fundingRate.current` (string, bare decimal, **unit-undeclared and
     basket-ambiguous** — echo verbatim, label it "secondary funding field,
     unit unresolved (OPEN-1)", and never use it in a comparison; D1 in
     `docs/gate0/FREEZE-ADDENDUM-decisions.md`).
   - `btc_liquidations.total_usd_4h.{total,long,short}` (formatted USD
     strings; the 4h window matches the lab bar size — display-only live
     context per Gate-0 §9). Field paths verified in
     `docs/gate0/get_global_crypto_derivatives_metrics.json`.
4. **Convert units** per the walkthrough in §3.1.
5. **Classify** per the decision table in §3.
6. **Emit** the human-readable regime report and the fenced JSON monitor spec
   block per §5, applying the degradation rules of §6 if any tool failed.

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
  the emitted schema triggers full re-validation.)

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
- The emission MUST then mark itself degraded: `signal_snapshot` carries the
  null/raw failed value, the human report headline is prefixed `DEGRADED`, and
  a disclaimer states that the label is the deterministic missing-data default,
  not a market reading (§6).

## 4. Per-regime expected-behavior notes (F4-train statistics — `"validated": false`)

Descriptive statistics of the F4-train slice only (2025-04-03 00:00 ≤ t <
2026-04-01, 2178 bars), aligned to the PR-3 convention: label known at close
t → the described return is bar t+1, open-to-open. These are the ONLY numbers
the monitor's expected-behavior notes may cite, each carrying
`"validated": false`. They are train-period descriptions, not validated
edges — the shipping gate found NO variant on this taxonomy (or any other)
shippable. No OOS-derived number appears in any note.

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
  see the falsification chapter, `docs/report/REPORT.md`. Do not read this
  note as an actionable fade. `"validated": false`.
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
dishonesty the gate exists to prevent (`docs/FREEZE.md` §3, amendment 2).

## 5. Output format

Emit BOTH of the following.

**(1) Human-readable regime report** — headline `BTC funding regime: <regime>`
(prefixed `DEGRADED — ` when §6 applies), then: the raw fetched funding string
and its decimal conversion; the threshold comparison shown explicitly (e.g.
`|1.5866e-05| < 8.3856e-05 → mild`); the context fields (BTC price, 24h
change, F&G index, 4h BTC liquidations, secondary funding field labeled
unit-unresolved); the expected-behavior note for the current regime with its
caveats; and the validation status line: *"Validation: null result — 0/36
variants passed the pre-registered shipping gate; nothing here is a validated
edge. See docs/report/REPORT.md."*

**(2) Fenced JSON monitor spec block** — exact schema (top-level keys:
`regime`, `as_of_utc`, `signal_snapshot`, `expected_behavior`, `validation`,
`disclaimers`). Worked example with the Gate-0 dump values:

```json
{
  "regime": "pos-mild",
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
    "validated_metrics_ref": "docs/report/REPORT.md#falsification"
  },
  "validation": {
    "status": "null-result",
    "gate": "0/36 variants passed",
    "ref": "docs/report/REPORT.md"
  },
  "disclaimers": [
    "Walk-forward provenance: pre-registered purged/embargoed walk-forward, 2025-04-03..2026-06-09, 4 folds. Taxonomy-level honest_N = 225 pooled-OOS regime episodes — a taxonomy-level count, not a strategy sample. The single near-miss candidate (DIR-TC-H8, FAILED) had an active sample of only 30 OOS trades / 92 nonzero-position OOS bars / 3 of 4 folds.",
    "Funding basis: live value is the CMC global cross-venue average (leverage.funding_rate.average.current, % string, decimal = value/100); the frozen threshold derives from Binance BTCUSDT 8h funding history. Sign and extremity-band comparisons only — never raw-magnitude arithmetic across the two bases.",
    "No strategy cleared our pre-registered shipping gate (0/36 variants; expected null-clause pass-rate 0.0500). Expected-behavior notes are train-period descriptions with validated: false.",
    "Not financial advice."
  ]
}
```

Echo every fetched value verbatim in `signal_snapshot` — raw strings as
served, including signs, `%` symbols, and magnitude suffixes — alongside any
parsed decimals. `expected_behavior` always quotes the row for the **current**
regime from the §4 table, with the matching note text and `"validated": false`.

## 6. Graceful per-tool degradation

| tool | role | on failure / missing field |
|---|---|---|
| `mcp__cmc-mcp__get_global_metrics_latest` | classification input (funding); context (F&G, last_updated) | Sign and extremity clauses both evaluate FALSE (§3.3) ⇒ deterministic label `neg-mild`. Emission is marked degraded: `signal_snapshot.status` = `"degraded: primary funding field unavailable"`, funding fields `null`, human headline prefixed `DEGRADED`, and an extra disclaimer string: "Label is the deterministic missing-data default (neg-mild), not a market reading." F&G context omitted. |
| `mcp__cmc-mcp__get_crypto_quotes_latest` | context only (BTC price, 24h change) | Omit/`null` the price fields; note the omission in the human report. Classification unaffected. |
| `mcp__cmc-mcp__get_global_crypto_derivatives_metrics` | context only (secondary funding echo, 4h BTC liquidations) | Omit/`null` those fields; note the omission. Classification unaffected. |

A field that is present but unparseable (format drift from the Gate-0 dump) is
treated identically to missing: clause FALSE, degraded marking, and the raw
value echoed verbatim in `signal_snapshot` for diagnosis.

## 7. Validation provenance

- **Result of record: a rigorous null.** 36 variants were swept through a
  pre-registered, purged/embargoed walk-forward shipping gate; **0 passed**;
  the expected null-clause pass-rate was **0.0500**. Full report and
  falsification chapter: `docs/report/REPORT.md`. Freeze decision:
  `docs/FREEZE.md`.
- **Gate power.** The gate was calibrated by planting known regime-conditional
  edges into the real panel: the unmodified pipeline passes a true edge of
  ≥ 10 bps/bar robustly and 5 bps/bar marginally. The null result is evidence
  about the data, not the machinery.
- **The failed candidate.** `DIR-TC-H8-fade_pos_extreme_only-{0.5,1.0}` —
  **FAILED**, `"validated": false` — is published in full in the report's
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
  near independence).
- **Inputs freeze.** Every field this Skill reads is verified in the Gate-0
  dumps cited inline in §2 (`docs/gate0/*.json`, `docs/gate0/GATE0-FREEZE.md`).
- **Reference table.** `reference_table.md` (same folder) documents the
  percentile→absolute threshold mapping, the post-event refresh procedure, and
  the funding-basis calibration samples. The Skill **never** consults it at
  runtime.
