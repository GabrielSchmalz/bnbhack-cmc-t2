# BNB HACK 2026 — Track 2: BTC Funding-Regime Monitor + Falsification-First Backtest Lab

A Track 2 entry that ships two things: a **falsification-first backtest lab** and a
**frozen-threshold BTC funding-regime monitor** authored as an LLM Skill over the
CoinMarketCap MCP.

The headline result is an **honest null**. We pre-registered a shipping gate —
OOS beats HODL, beats flat after 10 bps round-trip costs, and survives a
falsification battery (regime-shuffle null, top-5-trade removal, cost ladder
{5, 10, 20} bps) — then swept 36 variants across two families and three regime
taxonomies on a purged/embargoed walk-forward. **0 of 36 passed.** We attacked
the null from both directions before accepting it: an independent
re-implementation reproduced every compared artifact scalar with max |diff| = 0.0,
and a planted-edge calibration showed the *unmodified* pipeline passes a real
regime-conditional edge of **≥ 10 bps/bar robustly** (5 bps/bar marginally). The
null is evidence about the data, not the machinery.

What ships, therefore, is exactly what was earned: the Skill is a **regime
monitor** — a frozen 4-state funding-regime classifier (`pos-mild` ·
`pos-extreme` · `neg-mild` · `neg-extreme`), computed live from one verified CMC
MCP field, emitting train-period expected-behavior notes that all carry
`"validated": false`. It recommends no entry, no exit, no sizing, because the
shipping gate validated none. The one near-miss
(`DIR-TC-H8-fade_pos_extreme_only`, pooled-OOS Sharpe 2.38) is published in
full — as a **FAILED candidate** in the report's falsification chapter: its 5
best trades carry over 114% of the entire OOS gain and the remaining 25 trades
net −1.03% (size 0.5) / −2.13% (size 1.0), which is precisely the
concentration failure the pre-registered
top-5-removal clause exists to catch. A shipping gate you obey when it says
*no* is worth more than an OOS curve picked from 36.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│ Unit 1 — Lab (offline; reproducible without any database)              │
│   lab/        dataset → features → classifier → fill simulator →       │
│               walk-forward → honesty hooks → shipping gate → sweep     │
│   tests/      TDD suite (pytest), every component test-first           │
│   data/       committed CSVs (Binance klines/funding, bybit OI/LS,     │
│               DVOL, F&G) — the sweep needs no network, no ClickHouse   │
│   artifacts/  sweep_results.json · sweep_summary.md (inputs of record) │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │  frozen taxonomy + thresholds (docs/FREEZE.md)
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Unit 2 — The Skill (live; read-only over CMC MCP)                      │
│   skills/btc-funding-regime-monitor/                                   │
│     SKILL.md            regime monitor: one Gate-0-verified funding    │
│                         field → frozen classifier → {regime,           │
│                         as_of_utc, signal_snapshot, disclaimed         │
│                         expected-behavior note}                        │
│     reference_table.md  human refresh procedure — never read at        │
│                         runtime                                        │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │  invoked by
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Unit 3 — Demo + Report                                                 │
│   demo/run_demo.py        live MCP fetch → regime + monitor output     │
│   demo/validate_skill.py  executes the SKILL.md workflow literally     │
│                           against the live MCP                         │
│   docs/report/REPORT.md   validation report + falsification chapter    │
│                           (the FAILED candidate lives here)            │
└────────────────────────────────────────────────────────────────────────┘
```

## Quickstart (live demo)

Requires [uv](https://docs.astral.sh/uv/) and a CoinMarketCap API key.

```bash
uv sync
cp .env.example .env            # then set CMC_MCP_API_KEY=<your key>
uv run --no-sync python demo/run_demo.py
```

`run_demo.py` fetches the live funding Feature from the CMC MCP, runs the
frozen classifier, and prints the current regime plus the monitor's JSON block
(regime, `signal_snapshot`, expected-behavior note — `"validated": false`).

To re-run the Skill's literal validation (every `allowed-tools` entry resolves,
every referenced field exists in the live payload, output validates against the
schema):

```bash
uv run --no-sync python demo/validate_skill.py
```

## Reproduce the backtest (no network, no database)

The full pre-registered sweep — 36 variants, purged/embargoed walk-forward,
1000-draw shuffle null per (taxonomy, fold) — runs from the committed CSVs:

```bash
uv run --no-sync python -m lab.sweep    # ~5 minutes
```

It regenerates `artifacts/sweep_results.json` and `artifacts/sweep_summary.md`.
The test suite is `uv run --no-sync pytest`.

## Results

Window: 2025-04-03 → 2026-06-09, 4h bars (2598), select-on-train / gate-on-OOS
(ADR-001), all variants through the same fixed execution model (close-evaluated
rules → next-bar-open fill, 8h funding accrual, DD guard, 10 bps RT base costs).

| Result | Value |
|---|---|
| Variants swept / shipping-gate passes / expected null-clause pass-rate (R3) | **36 / 0 / 0.0500** |
| Full-gate pass rate of the top train-ranked variant over 200 null draws | 1.5% |
| Shipping-gate power (planted-edge calibration, unmodified pipeline) | passes a true regime-conditional edge **≥ 10 bps/bar robustly**; 5 bps/bar marginally |
| HODL pooled-OOS benchmark @ 10 bps | Sharpe **−2.10**, net **−45.9%** (the OOS spans a bear market) |
| Honest-N (pooled-OOS regime episodes, shipped taxonomy TC) | **225** — taxonomy-level; the failed candidate's active sample is only 30 trades / 92 in-position bars / 3 of 4 folds |
| Near-miss | `DIR-TC-H8-fade_pos_extreme_only` — OOS Sharpe 2.38, but FAILS the pre-registered top-5-removal clause: top 5 trades = 114.8–116.2% of OOS gain, remaining 25 trades net −1.03% (size 0.5) / −2.13% (size 1.0) |

Frozen Skill internals: taxonomy **TC** (funding sign × extremity), single
binding threshold `funding_hi_abs = 8.3856e-05` (q80 of |funding_rate_8h|,
F4-train slice only — the same slice every expected-behavior statistic comes
from). The live field is a global average funding rate while the frozen cut
derives from Binance-BTC 8h history; the monitor therefore compares **sign and
extremity band only** and states that basis difference in every emission.

Full numbers, figures, and the adversarial lanes that tried to break the null:
`docs/report/REPORT.md` and `docs/FREEZE.md`.

## Methodology

- `CONTEXT.md` — the domain vocabulary (Variant, Survivor, shipping gate,
  honesty hooks, Regime vs Band — read this first to parse everything else)
- `docs/adr/001-select-on-train-gate-on-oos.md` — selection is on train, OOS is
  a binary pass/fail, never a ranking key
- `docs/FREEZE.md` — the threshold-freeze decision: null verdict, frozen
  taxonomy + thresholds, monitor shape with binding amendments 1–6
- `docs/report/REPORT.md` — validation report; the falsification chapter
  carries the shuffle-null distribution, top-5 removal, cost ladder, R3
  disclosure, and the FAILED candidate in full
- `docs/plans/2026-06-10-bnbhack-t2-build-plan.md` — the pre-registered build
  plan the lanes executed
- `docs/gate0/` — Gate 0: the day-1 field dump that froze the classifier's
  inputs to live-verified CMC MCP fields, plus the addendum decisions D1–D5
- `docs/DATA_PROVENANCE.md` — committed-dataset provenance: original
  sources/venues, spans, regeneration commands, redistribution note

## Security

- The CMC API key lives **only** in `.env`, which is gitignored
  (`.env.example` is the committed template). It is sent as the
  `X-CMC-MCP-API-KEY` header and never logged or printed.
- The key is rotated after the event.
- The Lab makes no network calls; only `demo/` and the Skill touch the live MCP,
  read-only.

## License

MIT — see [LICENSE](LICENSE).
