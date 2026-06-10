# Reference table — btc-funding-regime-monitor

Maintenance artifact for humans. **The Skill NEVER consults this file at
runtime.** The runtime classifier is fully specified in `SKILL.md`: one frozen
absolute threshold, two clauses, four labels. This file documents (1) where
the frozen numbers came from (percentile → absolute mapping on the F4-train
slice), (2) how a human would re-derive them after a post-event refresh, and
(3) the funding-basis calibration samples behind the D1 disclaimer.

Sources of record: `docs/FREEZE.md` §2.2, `docs/gate0/GATE0-FREEZE.md`,
`docs/gate0/FREEZE-ADDENDUM-decisions.md` (D1), ADR-001 (R1),
`data/backfill/funding_calibration.csv`.

---

## 1. F4-train percentile → absolute mapping (frozen 2026-06-10)

Derivation window: **F4-train slice, 2025-04-03 00:00 ≤ t < 2026-04-01 UTC,
2178 bars** (4h grid). Quantiles computed over that slice and nothing else
(train-only, ADR-001 R1). Funding source: Binance BTCUSDT 8h settled funding
(`data/backfill/funding_btcusdt_binance.csv`), decimal per 8h period. Values
verbatim full precision from `docs/FREEZE.md` §2.2.

| key | percentile definition (on F4-train) | frozen absolute value | consumed by the shipped TC classifier? |
|---|---|---|---|
| `funding_hi` | q80 of signed `funding_rate_8h` | `8.186200000000001e-05` | no |
| `funding_lo` | q20 of signed `funding_rate_8h` | `1.458000000000004e-06` | no — see caveat below |
| `funding_hi_abs` | q80 of \|`funding_rate_8h`\| | `8.385600000000002e-05` | **YES — the only cut TC consumes** |
| `oi_surge` | q80 of \|`oi_chg_24h`\| | `0.05107445682896805` | no |
| `fg_lo` | q20 of `fg` (F&G index) | `24.0` | no |
| `fg_hi` | q80 of `fg` (F&G index) | `55.0` | no |

The non-consumed rows are recorded so the refresh procedure (§2) reproduces
the full tuple the lab derives; only `funding_hi_abs` is load-bearing for the
shipped monitor.

**Caveat on `funding_lo` (binding, Lane 1):** `funding_lo` is
bottom-quintile-RELATIVE and **positive** (+1.458e-06) — funding was ≥ 0 for
more than 80% of F4-train bars, so the 20th percentile of the *signed* rate
sits just above zero. It is **not** a negative-funding extreme, and any
"short-crowded" gloss on it is wrong. (The TC classifier does not consume it;
this caveat exists so a future refresh does not mis-read the tuple.)

## 2. Refresh procedure (post-event, human-operated)

The shipped thresholds are frozen. Any change to the consumed threshold, the
regime enum, the taxonomy, or the monitor's emitted schema triggers **full
re-validation** (`docs/FREEZE.md` §7) — a refresh is a new derivation plus a
new gate run, never an in-place edit.

1. **Pick a NEW train window** ending strictly before any data you intend to
   evaluate or act on. Thresholds are train-window-scoped (ADR-001 R1): every
   quantile is computed on the new train slice only, with no out-of-sample row
   influencing any threshold, including through feature construction.
2. **Rebuild the inputs from the same sources** (R-SRC: one source per feature
   end-to-end): Binance REST `fapi/v1/fundingRate` for `funding_rate_8h`; the
   lab's OI and F&G sources for the non-consumed rows if the full tuple is
   wanted.
3. **Recompute the six quantiles** exactly as defined in §1 (q20/q80 on the
   new train slice) and record both the percentile definition and the new
   absolute value, replacing this table in a NEW freeze document — never
   editing the frozen one.
4. **Re-run the full pre-registered gate** (walk-forward, honesty hooks, R3
   disclosure) before anything derived from the new numbers ships. The
   hypothesis family caught by the gate (fade positive funding extremes)
   additionally requires a new pre-registration on data after 2026-06-09;
   the un-registered knobs that flip the near-miss to PASS (q=(0.25,0.75),
   top-N=3) cannot be adopted retroactively.

## 3. Funding-basis calibration (D1)

The live field the monitor classifies on (`get_global_metrics_latest →
leverage.funding_rate.average.current`) is a global cross-venue average; the
lab history behind the frozen threshold is Binance-BTC 8h funding. D1
mandates a paired-sample calibration: a cron polls both CMC funding fields
alongside the Binance BTCUSDT anchors ~3×/day and appends to
`data/backfill/funding_calibration.csv`. Snapshot of that file as of
2026-06-10:

| ts_utc | cmc_deriv_fundingRate_current | cmc_global_avg_funding_pct | binance_btc_predicted_8h_rate | binance_btc_last_settled_rate |
|---|---|---|---|---|
| 2026-06-10 18:39:45 | 0.00035047 | +0.0015866% | -0.00000063 | 0.00002542 |
| 2026-06-10 18:40:14 | 0.00027104 | +0.0015866% | -0.00000079 | 0.00002542 |
| 2026-06-10 18:41:06 | 0.00027104 | +0.0015866% | -0.00000079 | 0.00002542 |

**Sample count: 3 polls**, all within 2026-06-10 18:39–18:41 UTC — effectively
a single market snapshot sampled three times.

What can and cannot be concluded yet:

- **Cannot conclude:** any stable scale relationship between the CMC global
  average and the Binance-BTC rate; a sign-agreement rate; or the unit of the
  derivatives-tool field `fundingRate.current` (OPEN-1 in
  `docs/gate0/GATE0-FREEZE.md` remains open for that field — which is why the
  monitor only echoes it, labeled unit-unresolved, and never compares it).
- **Observed at this single snapshot (not evidence-grade):** the global-average
  field (+0.0015866% = +1.5866e-05 decimal) agrees in sign with the Binance
  last *settled* rate (+2.542e-05) but not with the Binance *predicted* next
  rate (−6.3e-07 / −7.9e-07, essentially zero); the derivatives-tool field
  moved 0.00035047 → 0.00027104 between polls one minute apart (and read
  0.00069614 at the 18:23 Gate-0 dump) while the global-average string stayed
  constant — consistent with different refresh cadences and different baskets.
- **D1 trigger, restated:** if the accumulated paired samples show sign
  disagreement on more than 10% of polls, funding clauses degrade to
  extremity-only (no sign clause). With N=3 polls from one snapshot, that
  assessment is **deferred**; the cron keeps appending 3×/day and this table
  should be regenerated from the CSV before submission.

This calibration is exactly why the monitor's runtime comparison is restricted
to sign + extremity band (scale-free forms) and why every emission carries the
basis disclaimer — see `SKILL.md` §3.2.

---

*Repeated for emphasis: this file is documentation for a human performing a
post-event refresh. The Skill's runtime behavior is defined solely by
`SKILL.md` and never reads this file.*
