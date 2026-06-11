# BNB HACK 2026 — Track 2: BTC Funding-Regime Monitor + Falsification-First Backtest Lab

A Track 2 entry that ships two things: a **falsification-first backtest lab** and a
**frozen-threshold BTC funding-regime monitor** authored as an LLM Skill over the
CoinMarketCap MCP.

The headline is a two-layer story about a shipping gate that said *no* twice.

**Layer 1 — the floor (frozen 2026-06-10).** We pre-registered a shipping
gate — OOS beats HODL, beats flat after 10 bps round-trip costs, and survives
a falsification battery (regime-shuffle null, top-5-trade removal, cost ladder
{5, 10, 20} bps) — then swept 36 variants across two families and three regime
taxonomies on a purged/embargoed walk-forward over 14 months of 4h BTC data.
**0 of 36 passed.** We attacked that null from both directions before
accepting it: an independent re-implementation reproduced every compared
artifact scalar with max |diff| = 0.0, and a planted-edge calibration showed
the *unmodified* pipeline passes a real regime-conditional edge of
**≥ 10 bps/bar robustly** on that panel. What shipped was a regime **monitor**
whose every output carries `"validated": false`.

**Layer 2 — the widening (frozen 2026-06-11).** The operator asked for a
winning edge. Instead of relaxing the gate, the search was widened ~5× under
the **same gate plus three stricter clauses** (8 clauses total): 183 Variants
evaluated (175 gated + 8 locked-annex; 24 more registered forward-only) across
**three assets** (BTC, ETH, SOL) on **~5–6 years of multi-regime OOS** — bull,
bear, and chop — **pre-registered before any OOS contact**
(`docs/plans/2026-06-10-widening-preregistration.md`), with a
hypothesis-family quarantine registered in advance on the one family the first
cycle had already burned through evaluation.

**The outcome.** The gate found exactly **one effective passer** — four
dressings of a single structure, and that structure is the previously-burned
fade-positive-extremes family wearing its registered symmetric mirror as a
coat. The pre-registered counterfactual lock **refused to ship it**:
88.3–92.4% of its pooled-OOS PnL sits on the quarantined leg, the
extremity-neutralized twin loses money in every dressing (net −3.8% … −9.8%),
and the same map loses money outright on ETH and SOL (7 of 8 clauses fail).
Everything else: a **wider null** — 31 of 32 effective hypotheses cleared
nothing on any panel, in any dressing. `ship_eligible_count = 0`. A shipping
gate you obey when it says *no* — twice — is the product.

What ships, therefore, is exactly what was earned: the Skill is a **regime
monitor** — the floor's frozen 4-state funding-regime classifier (`pos-mild` ·
`pos-extreme` · `neg-mild` · `neg-extreme`), untouched by the widening,
computed live from one verified CMC MCP field and upgraded per the
registration's every-outcome commitments (≥ 7 verified CMC tools with honest
roles, F&G CMC end-to-end, basis disclosures in every emission). It recommends
no entry, no exit, no sizing, because the shipping gate validated none. The
locked passers are published in full in the report's falsification chapter —
rule surface, gate numbers, and the lock layer that caught each — never as
tradable specs, each carrying `"validated": false`, alongside the floor's
near-miss. A forward registration (24 Variants, OOS = 2026-06-11 00:00 UTC
onward, evaluable at the earliest 2027-07-01) states exactly what evidence
would make the locked family shippable.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│ Unit 1 — Lab (offline; reproducible without any database)              │
│   lab/        dataset → features → classifier → fill simulator →       │
│               walk-forward → honesty hooks → shipping gate → sweep     │
│               + W modules (widening): panels_w → features_w /          │
│               classifiers_w → rules_w / variants_w → hooks_w (nulls)   │
│               → gate_w (8 clauses) → lock_w (family quarantine) →      │
│               sweep_w (driver) · calibration_w (planted-edge power)    │
│   tests/      TDD suite (pytest), every component test-first           │
│   data/       committed CSVs (Binance klines + funding for             │
│               BTC/ETH/SOL, bybit OI/LS, DVOL, F&G, daily OI) — the     │
│               sweeps need no network, no ClickHouse                    │
│   artifacts/  sweep_results.json (floor) · w/sweep_results_w.json +    │
│               w/structural_feasibility.json (inputs of record)         │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │  frozen taxonomy + thresholds (docs/FREEZE.md);
                   │  widening verdict + amendments (docs/FREEZE-W.md)
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Unit 2 — The Skill (live; read-only over CMC MCP)                      │
│   skills/btc-funding-regime-monitor/                                   │
│     SKILL.md            regime monitor: one Gate-0-verified funding    │
│                         field → frozen classifier → {regime,           │
│                         as_of_utc, signal_snapshot, disclaimed         │
│                         expected-behavior note}; ≥ 7 verified CMC      │
│                         tools — non-classifier reads are labeled       │
│                         display context only (FREEZE-W §3)             │
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
│                           (the FAILED floor candidate and the LOCKED   │
│                           W passers live here, "validated": false)     │
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

## Reproduce the backtests (no network, no database)

**Floor sweep (cycle 1).** The pre-registered 36-variant sweep —
purged/embargoed walk-forward, 1000-draw shuffle null per (taxonomy, fold) —
runs from the committed CSVs:

```bash
uv run --no-sync python -m lab.sweep    # ~5 minutes
```

It regenerates `artifacts/sweep_results.json` and `artifacts/sweep_summary.md`.

**W-sweep (cycle 2).** The registered widened sweep — 183 Variants, 3
W-panels, D = 1000 common null draws, the 8-clause gate, the §6 lock layers:

```bash
W_SWEEP_CONFIRM=registered uv run --no-sync python -m lab.sweep_w   # ~5 h
```

It regenerates `artifacts/w/sweep_results_w.json` (byte-deterministic). The
environment variable is a tripwire, not configuration: this command is the
registration's **OOS-contact event**, and the driver refuses to run without
the explicit confirmation. `python -m lab.sweep_w --feasibility` runs the
train-side structural-feasibility readout with no confirmation needed. Budget
~5 h at the production setting (`--jobs 6`: per-panel walls were 9,119 /
4,264 / 4,441 s for P-BTC / P-ETH / P-SOL).

**Planted-edge power calibration (one (panel, rung) cell):**

```bash
uv run --no-sync python -m lab.calibration_w --asset BTC --rung 10 --jobs 6
```

`scripts/run_w_calibration.sh` chains all 9 cells (3 panels × {5, 10, 25}
bps/bar; ~15–18 h; resumable). Outputs land under `artifacts/w/calibration/`
and never overwrite the committed sweep artifact (guard test-pinned).

The test suite is `uv run --no-sync pytest`.

## Results

### Cycle 1 — the floor: 0 of 36

Window: 2025-04-03 → 2026-06-09, 4h bars (2598), select-on-train / gate-on-OOS
(ADR-001), all variants through the same fixed execution model (close-evaluated
rules → next-bar-open fill, 8h funding accrual, DD guard, 10 bps RT base costs).

| Result | Value |
|---|---|
| Variants swept / shipping-gate passes / expected null-clause pass-rate (R3) | **36 / 0 / 0.0500** |
| Full-gate pass rate of the top train-ranked variant over 200 null draws | 1.5% |
| Shipping-gate power (planted-edge calibration, unmodified pipeline, floor panel) | passes a true regime-conditional edge **≥ 10 bps/bar robustly**; 5 bps/bar marginally |
| HODL pooled-OOS benchmark @ 10 bps | Sharpe **−2.10**, net **−45.9%** (the OOS spans a bear market) |
| Honest-N (pooled-OOS regime episodes, shipped taxonomy TC) | **225** — taxonomy-level; the failed candidate's active sample is only 30 trades / 92 in-position bars / 3 of 4 folds |
| Near-miss | `DIR-TC-H8-fade_pos_extreme_only` — OOS Sharpe 2.38, but FAILS the pre-registered top-5-removal clause: top 5 trades = 114.8–116.2% of OOS gain, remaining 25 trades net −1.03% (size 0.5) / −2.13% (size 1.0) |

### Cycle 2 — the widening: one passer, locked; wider null everywhere else

W-panels (ADR-002): P-BTC and P-ETH 2020-04-01 → 2026-06-09 (21 quarterly
folds), P-SOL 2020-10-01 → 2026-06-09 (19 folds), 4h bars, same execution
model, embargo E = 42 bars in all 13 (panel, taxonomy) cells. Same gate plus
three added clauses — null-p99, min-active-sample (≥ 60 trades, ≥ 200 position
bars, fold coverage, no fold > 50% of net PnL), and top-K-trade removal. All
numbers from `artifacts/w/sweep_results_w.json` (committed `74e6417`),
`docs/FREEZE-W.md`, and `docs/report/w_r3_supplement.md`.

| Result | Value |
|---|---|
| Variants evaluated / gate passes / ship-eligible | **183** (175 gated, 73/51/51 across P-BTC/P-ETH/P-SOL, + 8 locked-annex; 24 forward-registered, never evaluated) / **4 = 1 effective hypothesis** / **0** |
| R3, expected vs observed | clause-6 (null p99): expected **1.75 nominal / 0.32 effective** exceedances across the 175 gated; observed **8 nominal / 3 effective** — all P-BTC, all funding-fade-flavored (the registered contamination signature). Clause-3 (null p95): observed 23/175 = 13.1% |
| Per-cell full-gate null calibration (200 draws/cell, 13 cells) | nine cells 0/200, max 0.02; P(≥ 1 effective full-gate pass under the null) ≈ **22%** (point estimates) up to ≈ **81%** (blanket 2% on the 0/200 cells) — a single effective pass is NOT evidence of shippable signal |
| Honest-N (pooled-OOS regime episodes) | P-BTC/T-D **1,502** vs the floor's 225 (≈ 6.7×); effective denominator **110** of 175 after 65 train-side structural-feasibility flags (flags committed before the sweep artifact) |
| Wider null | **31 of 32 effective hypotheses produced zero full-gate passes on any panel, in any dressing** |
| The one passer — LOCKED | `P-BTC-DIR-TD-D1-fade_extremes_graded_sym` × 4 dressings (sizes 0.5/1.0 × time-stop {none, 6}): pooled-OOS Sharpe 0.677–0.811, net +31.2% … +83.1% @ 10 bps; active sample 381–405 trades / 1,541–4,492 in-position bars |
| Why it does not ship (lock numbers) | Layer 2: the extremity-neutralized twin is net-negative in every dressing (−3.8% / −8.3% / −4.7% / −9.8%; twin Sharpe −0.159 / −0.230, below even the null q95). Layer 3: the quarantined short leg carries **88.3–92.4%** of pooled-OOS PnL vs the 0.50 line. Transfer: the same map fails **7 of 8 clauses** on P-ETH (net −1.0% … −53.6%) and P-SOL (−41.7% … −45.2%). Era: net +25.8% … +67.0% in the replay-contaminated pre-2025-04 era vs +4.3% … +9.6% after, where the top-5 AND top-K clauses fail for all four dressings |
| Passer marginality (quoted wherever the passers are described) | strongest dressing (1.0-ts6) clears the top-K clause by **+0.000608** net after removing its 9 best trades; max fold contribution **0.4898** vs the 0.50 fail line, driven by the 2022-Q2 Luna quarter; 7 of each dressing's OOS trades sit on the five published near-miss crash-day groups |
| Gate power on the W-panels | **PENDING** — see note below |
| HODL pooled-OOS benchmark @ 10 bps (rung-invariant) | P-BTC Sharpe 0.10 / net −37.7% · P-ETH 0.22 / −41.5% · P-SOL 0.28 / −57.5% |

> **PENDING — W-panel gate-power readout (FREEZE-W amendment 5: a completion
> gate, not optional).** The planted-edge power calibration for the W-panels
> (`bnbhack-wcal`: 3 panels × {5, 10, 25} bps/bar) was launched 2026-06-11
> 07:14 UTC and was still running at the W freeze. This slot is filled from
> that readout — against the protocol in
> `docs/report/adversarial/w_lane2_launch_note.md` §5 — before submission;
> no number is written here until then. The floor's ≥ 10 bps/bar power figure
> was measured on the 14-month floor panel and does **not** transfer to the
> W-panels.

Frozen Skill internals (unchanged by the widening — FREEZE-W §3; no
re-validation triggered): taxonomy **TC** (funding sign × extremity), single
binding threshold `funding_hi_abs = 8.3856e-05` (q80 of |funding_rate_8h|,
F4-train slice only — the same slice every expected-behavior statistic comes
from). The live field is a global average funding rate while the frozen cut
derives from Binance-BTC 8h history; the monitor therefore compares **sign and
extremity band only** and states that basis difference in every emission.

Full numbers, figures, and the adversarial lanes that tried to break both
verdicts: `docs/report/REPORT.md`, `docs/FREEZE.md`, `docs/FREEZE-W.md`.

## Methodology

- `CONTEXT.md` — the domain vocabulary (Variant, Survivor, shipping gate,
  honesty hooks, Regime vs Band, W-panel — read this first to parse everything
  else)
- `docs/adr/001-select-on-train-gate-on-oos.md` — selection is on train, OOS is
  a binary pass/fail, never a ranking key
- `docs/adr/002-deep-panels-as-gating-domains.md` — W-panels (three assets,
  ~5–6-year spans) become selection/gating domains, and why gating on that
  history is honest
- `docs/plans/2026-06-10-widening-preregistration.md` — the frozen widening
  registration: exact Variant grids (test-pinned counts), the 8-clause gate,
  the §6 hypothesis-family lock, the R3 disclosure plan, and the forward
  registration — committed before any OOS contact
- `docs/FREEZE.md` — the floor freeze: null verdict, frozen taxonomy +
  thresholds, monitor shape with binding amendments 1–6
- `docs/FREEZE-W.md` — the widening freeze: the family-locked-Survivors
  verdict, the numbers block, binding amendments 1–7
- `docs/report/REPORT.md` — validation report; the falsification chapter
  carries the shuffle-null distributions, removal clauses, cost ladder, R3
  disclosures, the floor's FAILED candidate, and the widening's LOCKED passers
  in full
- `docs/report/adversarial/` — six committed lane reports: the floor's
  reproduction / gate-calibration / near-miss lanes, plus
  `w_lane1_reproduction.md` (independent re-implementation, 731 scalars at
  max |diff| = 0.0, all three lock layers rebuilt), `w_lane2_launch_note.md`
  (W-panel power-calibration design + readout protocol; readout pending), and
  `w_lane3_r3_audit.md` (R3 / era-split / null-mechanics audit)
- `docs/report/w_r3_supplement.md` — clause-6 bootstrap CIs (no passer is a
  knife-edge artifact of q99 estimation noise), §8 transfer correlations
  (market r 0.73–0.84 vs same-strategy r 0.14–0.49 — and the map still loses
  money cross-asset), era-restricted honest-N
- `docs/plans/2026-06-10-bnbhack-t2-build-plan.md` — the pre-registered build
  plan the floor lanes executed
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
