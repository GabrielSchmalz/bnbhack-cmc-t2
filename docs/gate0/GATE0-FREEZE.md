# GATE 0 — FREEZE: distilled-classifier input set

**Status: FROZEN 2026-06-10** (plan Task 0.2 Step 4). From this point the distilled
classifier may consume **only** the Features in §7; every Feature column added in
`lab/features.py` must cite the `docs/gate0/*.json` path given there. Changes to this
list after sweep start require full re-validation (plan preamble, pre-registered
constants rule).

**Provenance.** Live dump 2026-06-10 ~18:23 UTC against `https://mcp.coinmarketcap.com/mcp`
(server `cmc-mcp-service v1.0.0`). Exactly **12 tools** in `tools/list`
(`docs/gate0/tools_list.json`); all 12 called with BTC-centric args, all returned
`isError: false`. Raw JSON-RPC saved verbatim per tool in `docs/gate0/<tool>.json`.
Every tool's payload arrives as **JSON-as-string** inside `result.content[0].text` —
the Skill must parse that string before reading any field. Flattened-path inventory
with per-tool args: `docs/gate0/field_inventory.md` (exhaustive for the two global
tools: 66 + 133 leaf fields).

Payload type rule discovered at the dump: **`get_crypto_quotes_latest` is the only
tool that returns raw numeric floats.** Everything else serves human-formatted
strings — thousands commas (`"62,511.42"`), magnitude suffixes (`"381.77 B"`),
sign-and-percent decorations (`"+0.51598%"`). §8 freezes the parsing constants.

---

## 1. Funding rate — fields and units (question 1)

Two candidate fields exist. **Neither is BTC-specific, neither declares its unit or
window (8h vs annualized), neither offers per-exchange or per-symbol breakdown.**
No BTC-only funding field exists anywhere in the 12 dumps.

**(a)** `get_global_crypto_derivatives_metrics` → `fundingRate.current`
(`docs/gate0/get_global_crypto_derivatives_metrics.json`):

```json
"fundingRate":{"current":"0.00069614","percentage_change_24h":"+13.27%",
               "percentage_change_7d":"-88.46%","percentage_change_14d":"-90.3%",
               "percentage_change_30d":"-4.17%"}
```

String, bare decimal, **no % sign**, global aggregate. The `percentage_change_*`
siblings are changes **of** the rate, not rates.

**(b)** `get_global_metrics_latest` → `leverage.funding_rate.average.current`
(`docs/gate0/get_global_metrics_latest.json`):

```json
"funding_rate":{"average":{"current":"+0.0015866%","percent_change":{"24h":"-164.38%",
                "7d":"-79.21%","30d":"-443.12%"}},
                "top_alts_minus_btc_spread_current":"-0.002046"}
```

Explicit **% sign**. The spread field is bare (no % sign) — unit conventions are
inconsistent even within one tool.

**Unit reconciliation anomaly (material).** Read at face value (a = decimal,
b = percent), the two "current global funding" values differ by **~44×**
(0.00069614 vs 0.0015866 % = 0.000015866). Magnitude analysis against the lab
anchor — Binance BTCUSDT settled funding at the dump hour was **+0.00002542**
decimal (stamp 2026-06-10 16:00, `data/backfill/funding_btcusdt_binance.csv`):

| reading | decimal 8h value | vs BTC anchor 2.54e-5 |
|---|---|---|
| (a) as decimal | 6.96e-4 | 27× larger |
| (a) as percent (% sign omitted) | 6.96e-6 | 0.27× |
| (b) as percent (as printed) | 1.59e-5 | 0.62× |

The percent reading of (a) puts both tools and the BTC anchor in the same order of
magnitude; the decimal reading puts (a) 27–44× away from everything else in an
extreme-fear market (F&G = 15) where (a)'s own `percentage_change_7d` = −88.46%
says funding has collapsed. Evidence therefore **leans toward (a) being a percent
value with the % sign omitted**, but this is not provable from one snapshot — and
the two tools' 24h changes even disagree in sign (+13.27% vs −164.38%), so they
aggregate **different baskets**, not just different units. Field selection + unit
convention is **OPEN-1** (§10) — it must close before any funding threshold is
transcribed into `SKILL.md`.

## 2. Open interest — level and change (question 2)

**Both level and change are served**, in two tools, all human-formatted strings:

- `get_global_crypto_derivatives_metrics` (`docs/gate0/get_global_crypto_derivatives_metrics.json`):
  `totalOpenInterest.current` = `"381.77 B"` (USD, B/T suffix) plus
  `totalOpenInterest.percentage_change_{24h,7d,14d,30d}` (e.g. `"+0.51598%"`).
  Same shape under `futures.openInterest.*` and `perpetuals.openInterest.*`.
- `get_global_metrics_latest` (`docs/gate0/get_global_metrics_latest.json`):
  `leverage.open_interest.{total,perpetuals,futures}.current` +
  `.percent_change.{24h,7d,30d}` + `.yearly.{max,min}.{value,timestamp}`.

The 24h-change Feature the distilled classifier needs exists **directly** as
`totalOpenInterest.percentage_change_24h` — no live differencing required.
Scope caveat: these are **global aggregates** (all coins, all venues); the lab series
is Bybit BTCUSDT and denominated in BTC contracts (~55,621 at export,
`data/lab/oi_bybit.csv`), so only scale-free forms (percent change, train-quantile
extremity) are comparable across lab and live — see OPEN-3.

## 3. Liquidations fields (question 3)

A **BTC-specific** block exists — the only BTC-specific derivatives data on the
server (`docs/gate0/get_global_crypto_derivatives_metrics.json`):

- `btc_liquidations.total_usd_{1h,4h,12h,24h}.{total,long,short}` — formatted USD
  (24h at dump: total `"84.05 M"`, long `"30.33 M"`, short `"53.71 M"`)
- `btc_liquidations.pct_change_prev_{4h,12h,24h,7d,30d}_vs_prior_*.{total,long,short}`
- `btc_liquidations.definitions.*` (server-provided definitions sub-object)

Also `get_global_metrics_latest` → `leverage.liquidations.btc.{total_usd24h,total_usd7d,total_usd30d,percent_change24h}`.

The **4h window aligns with our bar size** — useful for the Skill's live
confirmation display. Per PR-2, liquidations are **never a classifier input**
(§9); the lab's `liquidation_events` history is ~5 weeks (2026-05-06 →), far short
of the train span, so no threshold could be derived from it anyway.

## 4. Fear & Greed (question 4)

Live snapshot (`docs/gate0/get_global_metrics_latest.json`):

```json
"fear_greed":{"current":{"value":"Extreme fear","index":15},
              "history":{"yesterday":{"value":"Extreme fear","index":14}, ...},
              "yearly":{"max":{"index":71,...},"min":{"index":5,...}}}
```

`current.index` is a **raw int 0–100** (one of the few non-string numerics);
`current.value` is the label. The payload snapshot is daily
(`last_updated: "10 June 2026 12:00 AM UTC+0"`).

**Historical span question: YES with margin.** CMC Pro REST
`/v3/fear-and-greed/historical` was called (Task 0.4): span **2023-06-29 →
2026-06-09, 1,077 daily rows, zero missing days** — earliest date precedes the
full-stack window start 2025-04-03 by ~21 months. The pre-registered fallback
branch (alternative.me) was **not triggered**; F&G is **CMC-only end-to-end**
(R-SRC satisfied: the lab trains on the same source the shipped Skill reads live).
Evidence: `data/backfill/fg_source_decision.txt`, CSV `data/backfill/fear_greed.csv`
(`date_utc,value,source`; all `source=cmc`; values 5..92; full-stack-window
continuity 433/433). Note: the REST series publishes with a 1-day lag (latest row
2026-06-09 on run date 2026-06-10) — Task 1.1's following-UTC-day join rule already
covers this.

## 5. Long/short ratio (question 5)

**NONE — confirmed absent.** All 12 dumps were grepped for
`long_short`/`longShort`/`long-short`/ratio variants. Only hits: the liquidation
long/short USD splits (§3, position *closures*, not positioning) and
`liquidity.volume24h.spot_vs_perp_ratio` = `"0.23"` (a **volume** ratio, not
positioning). The expected-NO is confirmed → **LS-skew stays lab-only** exactly as
PR-2 pre-registered; it can never ship in the distilled classifier.

## 6. TA tool — indicators and timeframes (question 6)

`get_crypto_technical_analysis` with `{"id": "1"}` (BTC)
(`docs/gate0/get_crypto_technical_analysis.json`): **DAILY timeframe only — there is
no timeframe parameter** (only an optional `includeFields` array). All values are
formatted strings with thousands commas. Served indicators:

| group | fields |
|---|---|
| SMA | `moving_averages.simple_moving_average_{7,30,200}_day` |
| EMA | `moving_averages.exponential_moving_average_{7,30,200}_day` |
| MACD | `macd.{macdLine,signalLine,histogram}` |
| RSI | `rsi.{rsi7,rsi14,rsi21}` (dump: `rsi14` = `"23.89"`) |
| Fibonacci | `fibonacciLevels.{swingHigh,swingLow}`, retracement 23.6/38.2/50/61.8/78.6%, extension 127.2/161.8/200% |
| Pivot | `pivotPoint` |

Consequences: (i) `rsi14_1d` is directly verified; (ii) **no 50-day SMA exists** —
the `close_vs_sma50_1d` sketch in plan Task 2.1 cannot ship as written; the trend
Feature must use a verified window from {7, 30, 200} → **OPEN-2** (§10);
(iii) intraday TA is impossible live, so any TA Feature must be computed on daily
bars in the lab to match.

`get_crypto_marketcap_technical_analysis`
(`docs/gate0/get_crypto_marketcap_technical_analysis.json`) is the same indicator
set minus moving averages (MACD, RSI{7,14,21}, fib, pivot, `currentMarketCap`,
`currentVolume`) computed on **TOTAL crypto market cap, not BTC** — rejected as a
BTC classifier input (§9).

## 7. THE FROZEN FEATURE LIST (question 7)

The distilled classifier may use these Features and **nothing else**. Lab-side
sources are PR-2; live-side fields are the Gate-0-verified paths below. Derived
columns (e.g. `trend_sign`, funding z/quantile extremity, `fg` bucket) are legal
iff computed **only** from these frozen inputs with train-only thresholds (R1).

| # | Feature (lab column) | CMC tool → payload field path | Gate-0 dump (citation) | Lab source (PR-2) | Unit conversion (live → lab) |
|---|---|---|---|---|---|
| F1 | `funding_rate_8h` | `get_global_crypto_derivatives_metrics` → `fundingRate.current` (alt: `get_global_metrics_latest` → `leverage.funding_rate.average.current`) | `docs/gate0/get_global_crypto_derivatives_metrics.json`, `docs/gate0/get_global_metrics_latest.json` | Binance REST `fapi/v1/fundingRate` full backfill → `data/backfill/funding_btcusdt_binance.csv` (`funding_rate`, decimal 8h) | **OPEN-1** — field choice + ÷100-or-×1 unresolved (§1, §10) |
| F2 | `oi_chg_24h` | `get_global_crypto_derivatives_metrics` → `totalOpenInterest.percentage_change_24h` | `docs/gate0/get_global_crypto_derivatives_metrics.json` | `data/lab/oi_bybit.csv` → pct change vs value 6 bars back (24h/4h) | strip `+`/`%`, ÷100 → decimal fraction; composition caveat OPEN-3 |
| F3 | `fg` | `get_global_metrics_latest` → `sentiment.fear_greed.current.index` | `docs/gate0/get_global_metrics_latest.json` | CMC Pro REST `/v3/fear-and-greed/historical` → `data/backfill/fear_greed.csv` (`value`) | none — int 0–100 both sides, same index, same vendor |
| F4 | `rsi14_1d` | `get_crypto_technical_analysis` (id=1) → `rsi.rsi14` | `docs/gate0/get_crypto_technical_analysis.json` | computed from `data/lab/bars_4h.csv` resampled → 1d (Wilder RSI-14) | strip commas, parse float; 0–100 both sides |
| F5 | `close_vs_sma{W}_1d`, W ∈ {30, 200} (**OPEN-2**) | `get_crypto_technical_analysis` → `moving_averages.simple_moving_average_{30,200}_day`, with price from `get_crypto_quotes_latest` → `[0].price` | `docs/gate0/get_crypto_technical_analysis.json`, `docs/gate0/get_crypto_quotes_latest.json` | computed from `data/lab/bars_4h.csv` daily closes | strip commas, parse float; ratio `price/SMA − 1` computed identically both sides |
| F6 | `price` / returns (`percent_change_24h` etc.) | `get_crypto_quotes_latest` (id=1) → `[0].price`, `[0].percent_change_{1h,24h,7d,30d}` | `docs/gate0/get_crypto_quotes_latest.json` | `data/lab/bars_4h.csv` (`open,high,low,close`) | price: raw float, none; percent_change: raw float in percent points, ÷100 → decimal |

`trend_sign` (Task 2.1) is a derived column over F5/F6 — no additional field.
The Skill's `allowed-tools` implied by this table:
`get_global_crypto_derivatives_metrics`, `get_global_metrics_latest`,
`get_crypto_quotes_latest`, `get_crypto_technical_analysis` — matching the Task 3.1
expectation exactly.

## 8. Per-Feature unit reconciliation — frozen parsing constants (question 8)

| payload form | example | rule |
|---|---|---|
| bare decimal string | `"0.00069614"` | `float(s)` |
| signed percent string | `"+0.51598%"`, `"-17.66%"` | strip `+`/`%` → `float` → **÷100** for decimal fractions (keep percent points only where the lab column is in percent points) |
| comma-grouped number | `"62,511.42"` | remove `,` → `float` |
| magnitude suffix | `"84.05 M"`, `"381.77 B"`, `"2.13 T"` | `float(head) × {K:1e3, M:1e6, B:1e9, T:1e12}[suffix]`; bare `"0"` → 0.0 |
| raw numeric (quotes tool only) | `61820.477…`, `0.03458382` | use as-is; `percent_change_*` are **percent points** (0.0346 = +0.0346%), ÷100 for decimals |
| F&G index | `15` (int) | use as-is, 0–100 |

Feature-specific constants:

- **F1 funding**: lab unit = decimal-per-8h-period (Binance REST native; e.g.
  `0.0001` = 1 bp). Live conversion is the OPEN-1 decision: ×1 if `fundingRate.current`
  is decimal; **÷100 if percent** (evidence leans percent, §1). The alt field
  `leverage.funding_rate.average.current` is unambiguous: strip `%`, ÷100.
- **F2 OI change**: live `"+0.51598%"` → +0.0051598. Lab computes the same decimal
  fraction from raw Bybit levels. Lab OI **level** is BTC-denominated (contracts);
  live level is global USD — levels are never compared cross-side, only scale-free
  transforms (OPEN-3).
- **F3 F&G**: identity. Same vendor index live and historical.
- **F4/F5 TA**: comma-strip float; RSI same 0–100 scale; SMA in USD matches bar
  closes in USD.
- **F6**: identity for price; ÷100 for `percent_change_*` when a decimal fraction
  is needed.

## 9. REJECTED FIELDS / sources (with reasons)

| candidate | verdict | reason |
|---|---|---|
| **LS-skew** (`long_short_snapshots`, bybit) | REJECTED for shipping — **lab discovery only** | No CMC long/short positioning field exists anywhere (§5, grep across all 12 dumps). PR-2 pre-registered exactly this outcome. |
| **DVOL** (`deribit_dvol`) | REJECTED for shipping — **lab discovery only** | Not a CMC field; no implied-vol field in any dump. Per PR-2: never distilled. |
| **CVD** (`cg_cvd_history`) | DROPPED entirely | Source stale 2026-05-29, mid-OOS (R-SRC); operator pre-approved the drop in PR-2. Independently: no CMC CVD field exists. |
| **Liquidations as classifier input** (`btc_liquidations.*`, `leverage.liquidations.btc.*`) | REJECTED as input; **allowed as Skill report-context / live confirmation only** | PR-2 pre-registration; lab history is ~5 weeks (2026-05-06 →) — cannot span train, no threshold derivable. The verified 4h fields (§3) may be **displayed**, never branched on. |
| `liquidity.volume24h.spot_vs_perp_ratio` | REJECTED | Volume ratio, not positioning — not an LS substitute; no lab-side history (R-SRC). |
| `get_crypto_marketcap_technical_analysis.*` | REJECTED as classifier input | Computed on total crypto market cap, not BTC (§6). Context-display only. |
| `get_crypto_metrics` (on-chain whales/holders/address buckets) | REJECTED | On-chain supply distribution, not derivatives positioning; no historical lab series (R-SRC). |
| `dominance.*`, `rotation.altcoin_season.*`, `trad_fi_flows.etf_aum.*` | REJECTED as classifier inputs | No lab-side per-bar history under R-SRC; outside the positioning-stress/direction axes. Also `dominance.eth`/`dominance.others` `yearly.max < yearly.min` (server-side data oddity) — payload not trustworthy at field level. |
| `totalVolume.*` / `futures.volume.*` / `perpetuals.volume.*` (derivatives tool) | REJECTED | Internally inconsistent with `get_global_metrics_latest`: `totalVolume.total_usd_24h` = `"240.94 T"` vs `liquidity.volume24h.derivatives.total` = `"775.75 B"` (~300×) — failed cross-tool verification. |
| News / narratives / macro-events / search tools (`get_crypto_latest_news`, `trending_crypto_narratives`, `get_upcoming_macro_events`, `search_cryptos`, `search_crypto_info`, `get_crypto_info`) | REJECTED as classifier inputs | Unstructured/non-quantitative; no historical lab series (R-SRC). May appear in SKILL.md only as optional context, never in a classification clause. |
| `fundingRate.percentage_change_*` (rate-of-rate changes) | REJECTED | Changes **of** the funding rate with funding's unresolved basket/unit (§1); percent-change of a sign-flipping quantity is ill-conditioned (cf. `-164.38%`, `-443.12%`). |

## 10. OPEN DECISIONS — deviations from PR-2 / plan forced by the evidence

For the builder agent at the relevant task. None of these may be resolved silently;
each touches a pre-registered constant or the G1 distill claim.

**OPEN-1 (blocks SKILL.md funding clauses; decide before Task 3.1, ideally before
sweep start). Live funding field + unit convention.** No BTC-specific funding field
exists; the two global candidates disagree ~44× at face value, with inconsistent %
conventions and sign-divergent 24h changes (§1). Options:
(a) `fundingRate.current` (derivatives tool) read as **percent** (÷100) — magnitude
evidence supports this; (b) same field read as decimal (×1) — face-value reading,
27× off all anchors; (c) `leverage.funding_rate.average.current` — unit-explicit but
a different basket (and a 30d change of −443% suggests a noisy, sign-flipping
average). **Recommendation: (a), confirmed by a multi-day re-poll** of both fields
against Binance REST BTCUSDT funding before the Skill freezes — a one-snapshot unit
inference is not evidence enough to transcribe a threshold. If the re-poll cannot
disambiguate, funding clauses must degrade to **sign-and-extremity-only** forms
(quantile-of-train on the lab side, sign + relative-magnitude live).

**OPEN-2 (blocks `lab/features.py`; decide before sweep start). Trend SMA window.**
Plan Task 2.1 sketches `close_vs_sma50_1d`; **no 50-day SMA is served** (§6 —
verified windows: 7/30/200 for both SMA and EMA). Pick W ∈ {30, 200} (7 is too fast
for a trend axis at 4h bars) and pin it in `features.py` before any sweep. This is a
forced amendment to a pre-registered sketch, so it must be recorded in FREEZE.md at
threshold freeze as well.

**OPEN-3 (affects feature forms in Task 2.1 + report disclosure in Task 4.1).
BTC-specific lab series vs global-aggregate live fields for funding (F1) and OI
(F2).** The lab trains on Binance BTCUSDT funding and Bybit BTCUSDT OI; the only
live fields are all-coin/all-venue aggregates (§1, §2). The distilled classifier
therefore executes live on a **proxy basket** for these two Features. Options:
(a) accept + disclose: restrict F1/F2 clauses to scale-free forms (sign, percent
change, train-quantile extremity) that transfer across baskets, and state the proxy
gap in SKILL.md §validation-provenance and the report's source-consistency table;
(b) drop F1/F2 from the distilled classifier (guts the derivatives-positioning
story — effectively a different submission). **Recommendation: (a).** Not silently
resolvable: it qualifies the G1 "distill" claim (lab Feature → live field is a
basket change, not just a unit change).

**No deviation needed for F&G** — the PR-2 fallback branch was not triggered
(§4, `data/backfill/fg_source_decision.txt`). **No deviation for funding backfill**
— Binance REST worked end-to-end; and the cross-check vindicated PR-2's
single-relay decision: the CoinGlass table switches storage convention mid-stream
at **2025-04-08 00:00 UTC** (settled-decimal-settlement-stamped → predicted-percent-
interval-start-stamped), which fails the naive pre-registered 1e-6 check (19.38%)
while the convention-aware comparison passes (pre-switch 100% exact; post-switch
max diff 0.78 bp) — see `data/backfill/funding_crosscheck.txt`. That is precisely
the mid-window source hazard R-SRC exists to catch.

## 11. Payload-trust anomalies (for the record + report source-consistency table)

1. **Funding unit/basket ambiguity** across the two global tools (§1, OPEN-1).
2. **Derivatives-tool volume fields inconsistent** with global-metrics by ~300×
   (§9) — derivatives tool trusted for OI/funding/liquidations shape only, never
   volume.
3. `get_global_metrics_latest`: `dominance.eth.yearly.max` (8.93%) <
   `yearly.min` (13.84%); same inversion for `dominance.others`; all dominance
   values carry a spurious `+` prefix. `liquidity.volume24h.total.current`
   (75.29 B) < its own `spot` component (177.87 B). Server-side oddities — fields
   near these are display-grade, not classifier-grade.
4. `get_global_metrics_latest.last_updated` is a **daily** stamp
   (`12:00 AM UTC+0`) although leverage sub-fields plausibly refresh intraday —
   live cadence of F3 (and field (b) of §1) is daily-snapshot-grade; the Skill
   must not claim intraday F&G freshness.
5. Lab-side (for Task 1.1 and the report, from the export/backfill agents):
   7 duplicated-but-byte-identical 4h bar timestamps 2026-05-28→29
   (`dataset.py` must `drop_duplicates('open_time')`); OI/LS series is two-phase
   (daily 00:00 snapshots 2025-04-03→2026-04-02, then ~5-min) with two ~12.5-day
   holes inside the F4 OOS segment (2026-04-06→07, 2026-04-12→24, 2026-05-16→29
   spans) that become NaN under the 24h staleness cap; F&G REST publishes T−1.

---

*Authored from the raw dumps in `docs/gate0/`, `data/backfill/funding_crosscheck.txt`,
`data/backfill/fg_source_decision.txt`, and the committed lab CSVs. CONTEXT.md
vocabulary binding. The key was sourced from `.env` into env only and appears
nowhere in this document or the dumps.*
