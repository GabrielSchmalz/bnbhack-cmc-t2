# Gate-0 Freeze Addendum — builder-agent decisions (2026-06-10)

Resolves the OPEN decisions left by `GATE0-FREEZE.md` and pins dataset policies
forced by the export findings. These are pre-sweep decisions; the independent
review lane audits them (plan Task 5.1). Changing any of them after sweep start
triggers re-validation (G7).

## D1 — OPEN-1: live funding field + units

The Skill reads **`get_global_metrics_latest` → `leverage.funding_rate.average.current`**
(explicit `%` sign, decimal = value/100) as the primary live funding Feature, NOT
`get_global_crypto_derivatives_metrics.fundingRate.current` (unit-ambiguous: face
value is ~27× the Binance BTC anchor as a decimal and ~0.27× as a percent; no unit
declared; rejected until CMC documents it).

Mitigations, because the live field is a global average while lab history is
Binance-BTC (OPEN-3 overlap):
- Funding clauses in the distilled classifier use **sign and extremity bands only**
  (scale-free forms), never raw-magnitude arithmetic across sources.
- Pre-SKILL calibration task (runs during Phase 2/3): poll both CMC funding fields
  ~3×/day alongside Binance REST `fapi/v1/fundingRate` live; the paired samples go in
  `skills/<name>/reference_table.md` as the documented basis between the lab series
  and the live field. If the paired samples show sign disagreement > 10% of polls,
  funding clauses degrade to extremity-only (no sign clause) before threshold freeze.

## D2 — OPEN-2: trend SMA window

`close_vs_sma30_1d` (W=30). Rationale: the TA tool serves only {7, 30, 200}-day
SMAs; 7d is noise at regime timescale; 200d produces ~2 crossings in the 14-month
full-stack window (degenerate as a switching axis). W=30 is the only viable trend
Feature. SMA200 is rejected, not held as a variant axis (feature list stays small).
Plan PR-8/`features.py` references to `close_vs_sma50_1d` are amended to
`close_vs_sma30_1d`.

## D3 — OPEN-3: global-aggregate live fields vs BTC-specific lab series (F1/F2)

Accepted with disclosure, per D1 mitigations: funding and OI features use
scale-free forms (sign, extremity vs frozen thresholds, 24h percentage change).
`totalOpenInterest.percentage_change_24h` is a global aggregate in which BTC is
the dominant component; the lab's bybit-BTC OI Δ24h is the closest source-consistent
history. The report's limitations section and SKILL.md disclaimers state this
basis difference explicitly — it qualifies the G1 distill claim and is part of the
honesty story, not hidden.

## D4 — Dataset policies (export findings → Task 1.1 requirements)

1. **Duplicate bars:** `binance_klines` 4h has 7 byte-identical duplicate stamps
   (2026-05-28 00:00 → 2026-05-29 00:00). `dataset.py` MUST `drop_duplicates('open_time')`;
   test pinned.
2. **OI/LS cadence unification:** bybit OI/LS is daily-00:00-only until 2026-04-02,
   then ~5-min. To avoid a mid-window cadence change masquerading as signal
   (the R-SRC hazard in time-resolution form), `dataset.py` resamples the 5-min era
   to **daily 00:00 snapshots** — one cadence (daily) across the whole window.
   `oi_chg_24h` = day-over-day change of the daily snapshot, as-of-joined to 4h bars
   (staleness cap 36h to tolerate snapshot jitter; beyond → NaN).
3. **OI/LS holes:** two ~12.5-day gaps (2026-04-12→04-24, 2026-05-16→05-29) sit
   inside F4 OOS. Policy: NaN under the staleness cap; **classifier NaN semantics:
   any clause referencing a NaN Feature evaluates FALSE** (deterministic, distillable —
   the live Skill always has fresh OI; only lab history has holes). The report runs a
   sensitivity check on F4 OOS excluding the hole bars vs including them under this
   fallback, and discloses the affected bar count.
4. **F&G timing:** value stamped day D 00:00 UTC becomes usable at the **D 04:00 bar**
   (first bar opening after publication). CMC F&G history is daily-complete
   2023-06-29 → present, single source (CMC) on both lab and live sides.
5. **Funding source:** Binance REST end-to-end (`data/backfill/funding_btcusdt_binance.csv`).
   The CoinGlass relay switched storage convention mid-stream on 2025-04-08
   (settled-decimal-settlement-stamped → predicted-percent-interval-start-stamped);
   see `data/backfill/funding_crosscheck.txt`. This is exactly the mid-window relay
   hazard R-SRC exists to catch and is cited in the report's source-consistency table.

## Decisions of record (freeze)

### D5 — Freeze outcome (2026-06-10, critic lane; full text in `docs/FREEZE.md`)

**R-NULL ships: 0/36 variants passed the shipping gate; no Winner.** All three
adversarial lanes upheld the null (bit-for-bit reproduction; planted-edge
calibration shows the unmodified gate passes a 5–10 bps/bar real edge; the
DIR-TC-H8 near-miss fails the pre-registered top-5 clause substantively and is
base-rate-expected under the global null). No reopen items.

- Frozen taxonomy: **TC (funding-sign × extremity)**, enum
  {pos-mild, pos-extreme, neg-mild, neg-extreme}; binding F4-train threshold
  `funding_hi_abs = 8.385600000000002e-05` (full tuple + reference-table
  caveats in FREEZE.md §2.2). Selection basis: classification stability
  (5.2% relabel under F1→F4 threshold drift vs TA 48%/TB 28%), episode
  structure, live-computability (single D1-sanctioned scale-free Feature) —
  not OOS performance of any variant.
- Skill shape (PR-10): **regime monitor** — {regime, signal_snapshot,
  per-regime expected-behavior notes from F4-train stats, all
  `"validated": false`}; no `active_ruleset` emitted at runtime; the near-miss
  is published in the falsification chapter as a FAILED candidate only
  (amendments 1–6 in FREEZE.md §3 are binding).
- R-NAME: `skills/btc-funding-regime-monitor/`.
- R3 triple: 36 swept / 0 passes / expected null-clause pass-rate 0.0500
  (full-gate null pass rate 1.5% over 200 draws).
