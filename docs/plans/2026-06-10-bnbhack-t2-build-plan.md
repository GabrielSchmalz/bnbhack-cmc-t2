# BNB HACK T2 — Regime-Derivatives CMC Skill: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execution is orchestrated via the Workflow tool per the operator's instruction; the orchestration map is §W at the end.

**Goal:** Ship the Track 2 submission — a backtest lab (Unit 1), a CMC Skill with frozen, walk-forward-validated parameters (Unit 2), and a demo/report (Unit 3) — as a public repo submitted on DoraHacks before 2026-06-21 12:00 UTC.

**Architecture:** A pure-Python vectorized backtest lab reads committed CSV exports (sourced once from read-only ClickHouse + REST backfills), TDD'd from the start; a variant sweep over two rule families is selected on train and gated on a purged/embargoed walk-forward (ADR-001 R1–R3); the Winner's frozen thresholds are transcribed into a `SKILL.md` driven exclusively by Gate-0-verified CMC MCP fields. A clean null result ships as the submission if nothing clears the gate (R-NULL).

**Tech Stack:** Python 3.12 + uv · pandas/numpy/matplotlib · pytest · requests · ClickHouse HTTP (read-only) · CMC MCP (streamable-HTTP JSON-RPC) · gh CLI.

**Vocabulary:** CONTEXT.md is binding. Say *builder agent* (not executor), *fill simulator*, *Variant/Survivor/Winner*, *full-stack window / deep-history window / deep-history proxy*, *Feature* (never "signal" except the `signal_snapshot` JSON key).

---

## Preflight facts (verified live 2026-06-10, this session)

These were verified by the builder agent before planning; tasks below cite them.

| Fact | Value |
|---|---|
| CMC MCP key | in `/home/arista/src/bnbhack-cmc-t2/.env` (`CMC_MCP_API_KEY`, gitignored, chmod 600); initialize handshake OK on `https://mcp.coinmarketcap.com/mcp` |
| Same key on Pro REST | **works** — `GET pro-api.coinmarketcap.com/v3/fear-and-greed/historical` (header `X-CMC_PRO_API_KEY`) returned data |
| ClickHouse | `http://localhost:8123`, unauthenticated read OK. **Lab must always send `readonly=1`** |
| `binance_klines` BTCUSDT 4h | 2020-01-01 → 2026-06-09 (live); 1h live; 1m/5m/15m frozen ~2026-05-29; 1d frozen 2026-05-28 |
| `oi_snapshots` BTCUSDT | **venue=bybit 2025-04-03 → now (live)**; venue=binance only 2026-04-02 → now. ⚠️ Spec said "Binance-native"; the series spanning the full-stack window is **bybit**. R-SRC ⇒ use bybit |
| `long_short_snapshots` BTCUSDT | same: **bybit 2025-04-03 → now (live)**; binance only from 2026-04-02 |
| `cg_funding_history` BTCUSDT/Binance | 2019-09-10 → **2026-05-18 (frozen)** |
| `cg_fear_greed` | 2018-02-01 → **2026-05-18 (frozen)** ⚠️ also CoinGlass-frozen — inside OOS |
| `cg_cvd_history` BTCUSDT/Binance | → 2026-05-29 (stale mid-OOS) |
| `deribit_dvol` | 2021-03-24 → now (live) |
| `liquidation_events` BTCUSDT/bybit | 2026-05-06 → now (live; ~5 wks) |
| `regime_matrix_labels` rm17-derivs-4h-20260530 | 1357 bars 2025-10-04 → 2026-05-18; region01/02/03 = 450/455/452 |
| gh CLI | authed as GabrielSchmalz; can create the public repo |
| Tooling | python3.12, uv 0.11.1, jq, curl, ffmpeg present |

## Pre-registered constants (decided NOW; changing any after sweep start = re-validation)

**PR-1 Bars & window.** BTCUSDT 4h bars from `binance_klines` (`interval='4h'`). **Full-stack window: 2025-04-03 00:00 → 2026-06-09 20:00 UTC** (bybit OI/LS start → last complete 4h bar; refresh end-date at export time). Deep-history window: 2021-03-24 → 2026-05-18 (DVOL start → CoinGlass freeze).

**PR-2 Feature sources (R-SRC: one source per feature across train+OOS).**
| Feature | Source | Why |
|---|---|---|
| price/returns/TA | `binance_klines` 4h (resample → 1d for daily TA) | live, single source |
| funding rate | **Binance REST `fapi/v1/fundingRate` full backfill 2019→now** → `data/backfill/funding_btcusdt_binance.csv` | one relay end-to-end; cross-checked vs `cg_funding_history` on overlap (tolerance 1e-6) |
| OI (level, Δ24h) | `oi_snapshots` venue=**bybit** | only venue spanning full-stack window |
| F&G | **CMC Pro REST `/v3/fear-and-greed/historical`** (our key works). If span < 2025-04 → fallback alternative.me full history; if both fail → drop F&G | identical source to what the shipped Skill reads live |
| LS-skew | `long_short_snapshots` venue=bybit | **lab discovery only**; ships only if Gate 0 verifies a CMC LS field (expected: NO) |
| DVOL | `deribit_dvol` | **lab discovery only** — not a CMC field, never distilled |
| CVD | **DROPPED** (stale 2026-05-29, mid-OOS; operator pre-approved drop) | R-SRC |
| liquidations | `liquidation_events` (5 wks) | report-context + live Skill confirmation only; never a classifier input |

**PR-3 Execution model (G8).** Position `w[t] ∈ [-1,1]` held during bar t (open[t]→open[t+1]); decided from data ≤ close[t-1] (signal at close, next-bar-open fill). Period return `r[t] = open[t+1]/open[t] − 1` (final bar: close[T]/open[T] − 1). Costs: round-trip `c` bps ⇒ per-side `c/2` bps on traded notional: `equity *= 1 − |Δw|·(c/2)/1e4` at each fill. Funding: at each 8h stamp (00/08/16 UTC) inside bar t, `equity *= 1 − w[t]·rate` (**R-FUND: short earns when rate>0** — sign pinned by test). Sharpe annualization: √2190 (4h bars/yr).

**PR-4 DD guard (fixed plumbing, never swept).** Trailing equity drawdown > **20%** from running peak ⇒ force `w=0`; re-enter at the first regime-label change after breach. Identical across all variants and the vol-target benchmark? — **No**: guard applies to variants only; benchmarks are pure reference curves (HODL must be allowed to draw down, else it's not HODL). Document this in the report.

**PR-5 Benchmarks (fixed).** HODL: `w≡1` perp long incl. funding + one entry cost. Flat: `w≡0`. Vol-target: `w[t] = clip(0.30 / σ_ann[t], 0, 1)` long-only, σ from EWMA(λ=0.94) of 4h log-returns, same costs+funding, 1-bar lag.

**PR-6 Walk-forward (R2).** Expanding folds, embargo `E = max(42 bars, median regime-episode length)` between train end and OOS start:
- F1: train 2025-04-03→2025-10-01, OOS 2025-10-01+E → 2025-12-01
- F2: train →2025-12-01, OOS 2025-12-01+E → 2026-02-01
- F3: train →2026-02-01, OOS 2026-02-01+E → 2026-04-01
- F4: train →2026-04-01, OOS 2026-04-01+E → window end
Thresholds re-derived **per fold on that fold's train only** (R1). Pooled OOS = concatenated fold-OOS segments. **Shipped frozen thresholds = the F4-train-derived numbers** (the exact numbers gated on F4 OOS) — validated thing ≡ shipped thing (G7). Headline honest-N = pooled-OOS regime-episode count (R2).

**PR-7 Ranking & gate (ADR-001).** Rank key: mean per-fold **train** Sharpe @10 bps RT; tiebreak lower mean train max-DD. Shipping gate (pooled OOS, binary): (a) net return > 0 after 10 bps (beats flat); (b) Sharpe > HODL's pooled-OOS Sharpe; (c) honesty hooks all pass. Hooks: episode-block shuffle null (1000 draws, seed 17; variant OOS Sharpe > 95th pct of null), top-5 OOS trade removal (net return stays > 0), cost ladder (gate holds at 10 bps; still beats flat at 20 bps; 5 bps reported). R3 disclosure: total variants, gate passes, expected pass-rate under the shuffle null.

**PR-8 Variant space (both families, ≤256 total, exact count disclosed).** Taxonomy candidates (final enum + public names chosen at threshold freeze): T-A stress-only 3-state; T-B stress×trend 4-state; T-C funding-sign×extremity 4-state. Direction family: curated action-map menu per taxonomy (each regime → {long, short, flat}) × size {0.5, 1.0}. Risk-switching family: long-only exposure ladders monotone non-increasing in stress from {0, 0.25, 0.5, 1.0} × carry-switch {off, flat-when-funding>q_hi, short-0.25-when-funding>q_hi}. Enumeration is code (`lab/variants.py`), not vibes.

**PR-9 Reproducibility.** The backtest runs **entirely from committed CSVs** in `data/lab/` (exported once from ClickHouse + backfills). Judges never need our ClickHouse. Export script is committed; ClickHouse access is optional re-export plumbing.

**PR-10 Honest null (R-NULL).** If zero variants pass: ship the machinery + the negative result. Report leads with the falsification story; Skill ships as a "regime monitor" emitting regime + per-regime *expected-behavior notes* with `"validated": false` disclaimers, or is dropped in favor of report+demo of the gate — decision at freeze with the critic agent's sign-off.

---

## File structure

```
bnbhack-cmc-t2/
├── .env (gitignored)            # CMC_MCP_API_KEY, CLICKHOUSE_URL — already present
├── .env.example                 # variable names only
├── pyproject.toml               # uv project: pandas, numpy, matplotlib, requests, pytest
├── README.md
├── CONTEXT.md                   # (exists) domain model
├── docs/
│   ├── adr/001-...md            # (exists) binding methodology
│   ├── plans/                   # this plan
│   ├── gate0/                   # tool dumps + GATE0-FREEZE.md
│   └── report/REPORT.md         # backtest report (+ figures)
├── data/
│   ├── backfill/                # funding_btcusdt_binance.csv, fear_greed.csv (committed)
│   └── lab/                     # bars_4h.csv, oi_bybit.csv, ls_bybit.csv, dvol.csv, bands_rm17.csv (committed)
├── lab/
│   ├── __init__.py
│   ├── ch.py                    # read-only ClickHouse HTTP client (readonly=1 enforced)
│   ├── export.py                # CH+backfills → data/lab/*.csv
│   ├── dataset.py               # CSVs → aligned 4h DataFrame (causal joins, staleness rules)
│   ├── features.py              # feature columns + train-only threshold derivation (R1)
│   ├── classifier.py            # taxonomy configs → regime label series; episodes()
│   ├── engine.py                # fill simulator: w + bars (+funding) → equity, trades (PR-3)
│   ├── metrics.py               # sharpe, sortino, cagr, max_dd, hit_rate, turnover
│   ├── dd_guard.py              # PR-4 overlay
│   ├── benchmarks.py            # PR-5
│   ├── walkforward.py           # PR-6 folds, embargo, episode counting
│   ├── rules.py                 # action-maps: (regime series, params) → w series
│   ├── variants.py              # PR-8 enumeration
│   ├── hooks.py                 # shuffle null, top-N removal, cost ladder
│   ├── gate.py                  # PR-7 predicate + R3 stats
│   ├── sweep.py                 # the full pipeline → artifacts/sweep_results.json
│   └── report_figs.py           # equity curves, regime ribbons → docs/report/figs/
├── scripts/
│   ├── gate0_dump.py            # 12-tool MCP dump → docs/gate0/
│   ├── backfill_funding.py      # Binance REST → data/backfill/
│   ├── backfill_fear_greed.py   # CMC Pro REST (fallback alternative.me)
│   └── mcp_client.py            # minimal streamable-HTTP JSON-RPC client (shared w/ demo)
├── skills/<NAME-AT-FREEZE>/     # SKILL.md + reference_table.md + examples/ (R-NAME)
├── demo/
│   └── run_demo.py              # live MCP → regime → strategy spec block + curve
└── tests/                       # test_engine.py, test_funding.py, test_metrics.py,
                                 # test_dd_guard.py, test_walkforward.py, test_hooks.py,
                                 # test_gate.py, test_classifier.py, test_dataset.py
```

---

# Phase 0 — Foundation (Day 1)

### Task 0.1: Scaffold + first commit

**Files:** Create `pyproject.toml`, `.env.example`, `README.md` (stub); commit with existing `CONTEXT.md`, `docs/`, `.gitignore`.

- [ ] **Step 1: pyproject**

```toml
[project]
name = "bnbhack-cmc-t2"
version = "0.1.0"
description = "BNB HACK 2026 Track 2: regime-switched derivatives-positioning CMC Skill — backtest lab, frozen-threshold classifier, SKILL.md"
requires-python = ">=3.12"
dependencies = ["pandas>=2.2", "numpy>=1.26", "matplotlib>=3.8", "requests>=2.32"]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: `.env.example`**

```bash
# Copy to .env and fill in. NEVER commit .env.
CMC_MCP_API_KEY=            # pro.coinmarketcap.com dashboard; header X-CMC-MCP-API-KEY
CLICKHOUSE_URL=http://localhost:8123   # optional: only for re-exporting data/lab/
```

- [ ] **Step 3: README stub** — one paragraph: what this is, three units, "see docs/plans for build plan". Full README is Task 4.3.
- [ ] **Step 4: `uv sync` → verify `uv run pytest` collects 0 tests, exits 5 (no tests yet = OK).**
- [ ] **Step 5: Remove `.omc/` from tracking risk (already gitignored), then:**

```bash
git add .gitignore pyproject.toml uv.lock .env.example README.md CONTEXT.md docs/
git commit -m "chore: scaffold lab repo — domain model, ADR-001, build plan"
```

Guard: `git status --short` must show NO `.env`.

### Task 0.2: Gate 0 — live CMC MCP field dump + input freeze

**Files:** Create `scripts/mcp_client.py`, `scripts/gate0_dump.py`, `docs/gate0/GATE0-FREEZE.md` + `docs/gate0/*.json`.

- [ ] **Step 1: minimal MCP client** (verified handshake pattern: initialize → notifications/initialized → tools/list → tools/call; responses are `text/event-stream` `data:` lines; tolerate empty 202s):

```python
# scripts/mcp_client.py
import json, os, itertools, requests

URL = "https://mcp.coinmarketcap.com/mcp"

class McpClient:
    def __init__(self, url: str = URL, key: str | None = None):
        self.url = url
        self.key = key or os.environ["CMC_MCP_API_KEY"]
        self.sess = requests.Session()
        self.sess.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-CMC-MCP-API-KEY": self.key,
        })
        self._id = itertools.count(1)
        self._session_id = None

    def _post(self, payload: dict) -> dict | None:
        headers = {}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        r = self.sess.post(self.url, json=payload, headers=headers, timeout=60)
        if sid := r.headers.get("Mcp-Session-Id"):
            self._session_id = sid
        if r.status_code == 202 or not r.text.strip():
            return None
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            for line in r.text.splitlines():
                if line.startswith("data:"):
                    msg = json.loads(line[5:].strip())
                    if msg.get("id") is not None:
                        return msg
            return None
        return r.json()

    def initialize(self):
        out = self._post({"jsonrpc": "2.0", "id": next(self._id), "method": "initialize",
                          "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                     "clientInfo": {"name": "bnbhack-t2", "version": "0.1"}}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return out

    def tools_list(self) -> list[dict]:
        return self._post({"jsonrpc": "2.0", "id": next(self._id),
                           "method": "tools/list"})["result"]["tools"]

    def call(self, name: str, arguments: dict) -> dict:
        return self._post({"jsonrpc": "2.0", "id": next(self._id), "method": "tools/call",
                           "params": {"name": name, "arguments": arguments}})
```

- [ ] **Step 2: dump script** — initialize, `tools/list` → save `docs/gate0/tools_list.json`; then call each of the 12 tools with BTC-centric args (e.g. quotes id=1, TA symbol=BTC, derivatives global, global metrics, on-chain BTC, news BTC, narratives, macro events, search "bitcoin", info id=1, concept "funding rate", mcap TA) → save raw result per tool `docs/gate0/<tool>.json`. Print a field-inventory table (flattened JSON paths + example values).
- [ ] **Step 3: run it** — `uv run --env-file .env python scripts/gate0_dump.py`. Expected: 12 JSON files + table.
- [ ] **Step 4: author `docs/gate0/GATE0-FREEZE.md`** answering, with payload excerpts as evidence: (1) exact funding-rate field(s) + units (8h rate? annualized? per-exchange or aggregate?); (2) OI field(s) — level only, or 24h change included?; (3) liquidations fields; (4) F&G current value + does Pro REST `/v3/fear-and-greed/historical` span ≥ 2025-04-03 (call it; record span); (5) any long/short ratio field (expected NO → LS stays lab-only); (6) TA tool: which indicators/timeframes for BTC (RSI period? SMA windows? daily or intraday?); (7) **the frozen Feature list** the distilled classifier may use, each mapped CMC-field → lab-column; (8) per-feature unit reconciliation (e.g. funding % vs decimal — exact conversion constants).
- [ ] **Step 5: commit** `feat(gate0): live CMC MCP field dump + classifier input freeze`.

**Acceptance:** every Feature used by `lab/features.py` later MUST cite a `docs/gate0/*.json` path. The freeze doc explicitly lists rejected fields too (LS, DVOL, CVD) with reasons.

### Task 0.3: Funding backfill (one source end-to-end)

**Files:** Create `scripts/backfill_funding.py`, `data/backfill/funding_btcusdt_binance.csv`; Test `tests/test_backfill_funding.py` (run on the committed CSV, no network).

- [ ] **Step 1: script** — paginate `GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1000` from startTime=2019-09-01 → now (no key needed; 8 calls; sleep 0.5s). Columns: `funding_time_utc,funding_rate`. Sort asc, dedupe on time, write CSV.
- [ ] **Step 2: run; expected ~7,400 rows, 2019-09-10 → today, all stamps ≡ 0 mod 8h UTC.**
- [ ] **Step 3: overlap cross-check (R-SRC evidence)** — in the script, after writing: query ClickHouse (`readonly=1`) `SELECT ts, close_rate FROM default.cg_funding_history WHERE symbol='BTCUSDT' AND exchange='Binance' AND ts BETWEEN '2025-01-01' AND '2026-05-18'`; join on timestamp; assert `max(|rest − cg|) < 1e-6` on ≥ 95% of joined rows; print the comparison stats into `data/backfill/funding_crosscheck.txt` (committed — it's report evidence).
- [ ] **Step 4: test** (no network): CSV loads; stamps 8h-aligned; no duplicates; span covers 2025-04-03 → ≥ 2026-06-09; rates within (−0.0075, +0.0075) sanity bounds.
- [ ] **Step 5: commit** `feat(data): Binance funding full backfill + CoinGlass overlap cross-check`.

### Task 0.4: Fear & Greed backfill

**Files:** Create `scripts/backfill_fear_greed.py`, `data/backfill/fear_greed.csv`; Test `tests/test_backfill_fg.py`.

- [ ] **Step 1: script** — `GET https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical?limit=500` paginated (`start` param) with `X-CMC_PRO_API_KEY` from env. Columns `date_utc,value`. Record earliest date. **If earliest > 2025-04-03:** fall back to `https://api.alternative.me/fng/?limit=0&format=json` for the full span and write `source` column per row; the freeze doc then documents F&G as alternative.me-sourced with a CMC-vs-alternative.me same-day comparison over the overlap (if median |Δ| > 5 points, DROP F&G from the Feature list — source mismatch too large to claim equivalence).
- [ ] **Step 2: run; inspect span + source decision printed.**
- [ ] **Step 3: test on committed CSV:** daily continuity ≥ 99% over full-stack window; values ∈ [0,100].
- [ ] **Step 4: commit** `feat(data): fear & greed history backfill (source decision documented)`.

### Task 0.5: ClickHouse → committed lab CSVs

**Files:** Create `lab/ch.py`, `lab/export.py`, `data/lab/*.csv`; Test `tests/test_export_csvs.py` (committed CSVs only).

- [ ] **Step 1: `lab/ch.py`** — tiny client: `query(sql) -> list[tuple]` via `requests.post(f"{url}/?readonly=1&default_format=TSV", data=sql)`. **`readonly=1` is hardcoded in the URL, not optional** — the read-only constraint is structural.
- [ ] **Step 2: `lab/export.py`** writes:
  - `bars_4h.csv`: `SELECT open_time, open, high, low, close, volume FROM default.binance_klines WHERE symbol='BTCUSDT' AND interval='4h' AND open_time >= '2020-01-01' ORDER BY open_time` (one file serves both windows)
  - `oi_bybit.csv`: `SELECT ts, open_interest FROM default.oi_snapshots WHERE symbol='BTCUSDT' AND venue='bybit' ORDER BY ts`
  - `ls_bybit.csv`: `SELECT ts, long_short_ratio FROM default.long_short_snapshots WHERE symbol='BTCUSDT' AND venue='bybit' ORDER BY ts`
  - `dvol.csv`: `SELECT ts, close FROM default.deribit_dvol ORDER BY ts`
  - `bands_rm17.csv`: `SELECT bar_ts, region_id FROM default.regime_matrix_labels WHERE run_version='rm17-derivs-4h-20260530' ORDER BY bar_ts` (**filter on run_version, never tf alone**)
  - `liq_events.csv`: `SELECT ts, side, usd_notional, cascade FROM default.liquidation_events WHERE symbol='BTCUSDT' ORDER BY ts`
- [ ] **Step 3: run; sanity-print row counts + spans; expected ≈ 14k bars / 12k OI / 12k LS / 50k DVOL / 1.4k bands.**
- [ ] **Step 4: test on committed CSVs:** spans match Preflight table; 4h bar grid has no gaps > 1 bar in full-stack window; OI/LS cadence ≤ 2h median gap.
- [ ] **Step 5: commit** `feat(data): committed lab CSV exports — backtest is fully reproducible without ClickHouse`.

---

# Phase 1 — Backtest harness, TDD (Days 2–4; the long pole)

Strict red-green per component: write failing test → run (must FAIL) → minimal impl → run (must PASS) → commit. Tests use small hand-constructed frames with hand-computed expectations — never lab CSVs.

### Task 1.1: `lab/dataset.py` — aligned 4h panel

Causal joins of all sources onto the 4h bar grid. Rules: as-of backward join (`merge_asof`), staleness cap 24h (older → NaN), daily series (F&G) joined to bars of the **following** UTC day (no same-day peek: F&G published for day D is known at D 00:20 — join to bars ≥ D 04:00 to be safe). Output columns: `open,high,low,close,volume,funding_rate (at 8h stamps, else 0),oi,ls_ratio,dvol,fg,band`.

- [ ] Failing tests: (a) as-of join takes the LAST value ≤ bar open, never after; (b) staleness > 24h → NaN; (c) F&G for day D first appears on D 04:00 bar; (d) funding lands only on 00/08/16 bars and is 0 elsewhere.
- [ ] Implement → pass → commit `feat(lab): causal 4h dataset assembly`.

### Task 1.2: `lab/engine.py` — fill simulator + equity

The PR-3 mechanics. Interface:

```python
@dataclass
class BTResult:
    equity: pd.Series      # indexed by bar open_time, starts 1.0
    bar_returns: pd.Series # per-bar strategy simple returns (net of costs+funding)
    trades: pd.DataFrame   # entry_ts, exit_ts, w, pnl_pct (sign-constant nonzero-w runs)
    turnover: float        # sum |Δw|

def run_backtest(bars: pd.DataFrame, w: pd.Series, funding: pd.Series,
                 cost_bps_rt: float) -> BTResult
```

- [ ] **Failing tests (hand-computed):**

```python
def test_long_one_bar_no_costs():
    # opens [100, 110, 121] → w=[1,1] → equity [1.10, 1.21]
def test_next_bar_open_convention():
    # w produced by a rule from close[t-1] must multiply r[t]=open[t+1]/open[t]-1 — alignment test
def test_costs_per_side():
    # w goes 0→1→0 at 10 bps RT: two fills × 5 bps on traded notional
def test_short_funding_sign():           # R-FUND pin
    # w=-1, funding_rate=+0.0001 at an 8h stamp → equity INCREASES by ~1e-4
def test_long_funding_sign():
    # w=+1, rate=+0.0001 → equity DECREASES
def test_trades_extraction():
    # w=[0,1,1,-1,0] → exactly 2 trades with correct entry/exit ts and pnl
```

- [ ] Implement vectorized → pass → commit `feat(lab): fill simulator + funding accrual (sign pinned by test)`.

### Task 1.3: `lab/metrics.py`

`sharpe(bar_returns)` (√2190, mean/std, std=0→0.0), `sortino`, `cagr(equity)`, `max_dd(equity)`, `hit_rate(trades)`, `turnover`. 

- [ ] Failing tests with hand-computed values (e.g. constant +10 bps/bar → Sharpe = ∞-guard case; alternating ±1% → Sharpe 0; known drawdown path → max_dd exact). Implement → commit `feat(lab): metrics`.

### Task 1.4: `lab/dd_guard.py`

`apply_dd_guard(w, bars, funding, cost_bps_rt, regimes, threshold=0.20) -> pd.Series` — iterative (state machine): track equity under guard; on drawdown > 20% from peak set w=0 from next bar; re-arm at first regime change after breach (PR-4).

- [ ] Failing tests: (a) crafted crash path triggers guard at the right bar; (b) stays flat until regime change; (c) no breach → w unchanged. Implement → commit.

### Task 1.5: `lab/benchmarks.py`

`hodl(bars, funding, cost)`, `flat(bars)`, `vol_target(bars, funding, cost, target=0.30, lam=0.94)` — all through `run_backtest` (PR-5).

- [ ] Failing tests: HODL equity equals buy&hold-with-funding hand-calc on a 3-bar frame; vol-target w lagged 1 bar and ∈ [0,1]. Implement → commit.

### Task 1.6: `lab/classifier.py` + episodes

`label(df, config) -> pd.Series[str]` (taxonomy configs from PR-8; thresholds passed in — derivation lives in features.py), `episodes(labels) -> pd.DataFrame[label, start, end, n_bars]`.

- [ ] Failing tests: tiny frame with engineered features → expected labels; episode segmentation on `[A,A,B,B,B,A]` → 3 episodes. Implement → commit.

### Task 1.7: `lab/walkforward.py`

`folds(index, episodes) -> list[Fold]` with PR-6 boundaries; embargo `E = max(42, median_episode_len)` bars; `Fold = (train_idx, oos_idx)`. `pooled_oos(folds)` concatenation helper.

- [ ] Failing tests: (a) fold boundaries exactly as PR-6 on a synthetic 2025-04→2026-06 index; (b) `min(oos_idx) − max(train_idx) ≥ E` bars for every fold; (c) no index overlap anywhere. Implement → commit `feat(lab): purged/embargoed walk-forward (ADR-001 R2)`.

### Task 1.8: `lab/hooks.py`

```python
def shuffle_null(variant, dataset, folds, n=1000, seed=17) -> dict
    # episode-block permutation of regime labels (preserve episode lengths),
    # rerun rules → pooled-OOS Sharpe distribution; returns {p95, null_sharpes}
def top_n_removal(trades_oos, bar_returns_oos, n=5) -> float   # net return after removing n best trades
def cost_ladder(variant, dataset, folds) -> dict               # gate metrics at {5,10,20} bps
```

- [ ] Failing tests: (a) shuffle preserves label multiset AND episode-length multiset; (b) seed reproducibility; (c) top-5 removal on crafted trades = hand-computed; (d) ladder monotone: returns non-increasing in cost. Implement → commit `feat(lab): honesty hooks`.

### Task 1.9: `lab/gate.py`

`shipping_gate(variant_result, hodl_result, hooks) -> GateVerdict` per PR-7, plus `null_pass_rate(variants, ...)` for R3 (expected gate-pass-rate under shuffled labels).

- [ ] Failing tests: crafted pass case, and one failing-each-clause case per clause (beats-flat, beats-HODL, null, top5, ladder). Implement → commit `feat(lab): shipping gate (ADR-001)`.

---

# Phase 2 — Discovery, sweep, freeze (Days 4–6)

### Task 2.1: `lab/features.py`

Feature columns (Gate-0-frozen list only; cite freeze doc per feature) + **train-only threshold derivation** (R1):

```python
def add_features(df) -> df:   # funding_rate_8h (ffilled to bar grid for level checks),
                              # oi_chg_24h, fg, rsi14_1d, close_vs_sma50_1d, trend_sign
def derive_thresholds(df_train, spec: dict) -> dict[str, float]
    # e.g. {"funding_hi": q80(train funding), "funding_lo": q20, "oi_surge": q80(|oi_chg|), ...}
    # returns ABSOLUTE numbers; these are what freezes (G7)
```

- [ ] Failing tests: thresholds computed on a train slice ignore OOS rows (feed a frame where OOS values would shift the quantile — assert they don't); RSI/SMA hand-checked on a small series; oi_chg_24h uses value 6 bars back (24h/4h). Implement → commit.

### Task 2.2: Band reconciliation (discovery aid, lab-only)

Script `lab/band_recon.py` (not part of the shipped pipeline): cross-tab lab stress features vs rm17 Bands on their overlap (2025-10→2026-05-18); mutual information / occupancy table → `docs/report/band_recon.md`. Purpose: evidence the distilled stress axis tracks the Band structure (G1 "distill" story) — NOT a fit target.

- [ ] Run, write the table, commit. No test (descriptive artifact).

### Task 2.3: `lab/rules.py` + `lab/variants.py`

Action-maps and the PR-8 enumeration. `rules.apply(regimes, action_map, sizes) -> w` (then dd_guard overlay). `variants.enumerate_all() -> list[Variant]` — deterministic, ordered, with stable IDs like `DIR-TB-fade_stress-1.0`.

- [ ] Failing tests: action map → expected w on a synthetic regime series (incl. 1-bar lag: regime known at close t ⇒ w from bar t+1); enumeration count is stable and ≤ 256; IDs unique. Implement → commit. **Print and record the exact variant count in the test (R3 needs the denominator).**

### Task 2.4: `lab/sweep.py` — the pipeline

Per fold: derive thresholds on fold-train (R1) → label regimes → run every variant (train + OOS segments, 10 bps) → per-variant: mean train Sharpe (rank key), pooled OOS metrics, hooks, gate verdict. Output `artifacts/sweep_results.json`: per-variant record {id, family, taxonomy, per-fold train Sharpe, pooled OOS metrics, hook outcomes, gate verdict} + globals {variant count, episode counts per fold OOS, honest-N, null pass-rate}.

- [ ] Failing test: end-to-end on a 200-bar synthetic dataset with a planted regime effect — a variant aligned with the planted effect must out-rank misaligned ones and the JSON schema must validate. Implement (runtime budget: full sweep ≤ ~30 min single-process; parallelize folds with multiprocessing if needed) → commit.
- [ ] **Run the real sweep.** Commit `artifacts/sweep_results.json` + log.

### Task 2.5: Adversarial verification of survivors (separate lane)

Independent critic agents (Workflow §W phase F) attack the sweep output: re-derive the Winner's OOS numbers from committed CSVs independently; check threshold derivation cites only train rows; check episode honest-N math; attempt to refute each survivor (look-ahead, source-swap artifacts around 2026-05-18, DD-guard interaction, fold-boundary sensitivity). Written verdict → `docs/report/adversarial_review.md`.

### Task 2.6: Threshold freeze

- [ ] Apply ADR-001: Winner = highest train-ranked survivor (or **null result** → PR-10 branch).
- [ ] Write `docs/FREEZE.md`: frozen taxonomy + public regime names, frozen absolute thresholds (F4-train numbers), Winner ruleset + sizing, variant-count denominator, gate stats, null pass-rate. 
- [ ] Name the skill folder NOW (R-NAME) — e.g. family-true name like `btc-regime-risk-switch` or `btc-positioning-fade`; create `skills/<name>/`.
- [ ] Commit `feat: threshold freeze — <Winner id or null result>`.

### Task 2.7: Deep-history proxy replay (robustness only)

Winner's rules restricted to deep-history Features (funding, price TA — whatever of the Winner's inputs exist 2021→2026-05-18), thresholds re-derived once on full-stack F4-train (unchanged), replayed on the deep-history window. Output: separate curve + metrics, clearly labeled `deep-history proxy (a DIFFERENT strategy by construction)`. If the Winner's Features don't restrict meaningfully (e.g. OI-dependent), report that the proxy is not computable and why — honesty over reach.

- [ ] Script + figure + paragraph in report. Commit.

---

# Phase 3 — The Skill (Day 7)

### Task 3.1: `skills/<name>/SKILL.md`

Frontmatter exactly per the verified template (inventory §9): `name`, `description` + trigger phrases, `license: MIT`, `compatibility: ">=1.0.0"`, `user-invocable: true`, `allowed-tools:` = ONLY the Gate-0-verified tools the rules need (expected: `get_global_crypto_derivatives_metrics`, `get_global_metrics_latest`, `get_crypto_quotes_latest`, `get_crypto_technical_analysis`; plus optional context tools). Body sections, in order:

1. Prerequisites (CMC MCP setup, key header) 
2. Step-by-step tool-call workflow (numbered; exact tool + args per step)
3. **Regime classification rules** — the frozen absolute thresholds, decision table form; every comparison names the exact CMC payload field (cite Gate-0 dump path)
4. **Per-regime strategy spec** — entry/exit/sizing per regime from the Winner; DD-guard statement; explicit "size 0–1× equity, no leverage"
5. Output format: human-readable regime report + the fenced **strategy spec block** (exact JSON schema below)
6. Per-tool graceful degradation (tool down → which clause degrades, what gets emitted)
7. Validation provenance: link to report; `validated_metrics_ref`; the multiple-testing disclosure one-liner; disclaimers ("not financial advice", null-result framing if PR-10)

Strategy spec block schema (G9):

```json
{
  "regime": "<frozen enum>",
  "as_of_utc": "...",
  "signal_snapshot": {"<feature>": "<value as fetched>"},
  "active_ruleset": {"entry": "...", "exit": "...", "sizing": "..."},
  "dd_guard": {"type": "trailing_equity", "threshold_pct": 20, "reentry": "next regime change"},
  "validated_metrics_ref": "docs/report/REPORT.md#headline",
  "disclaimers": ["backtested on 2025-04..2026-06 walk-forward; OOS regime-episodes N=<honest-N>", "not financial advice"]
}
```

- [ ] Author from FREEZE.md only (no reaching back into sweep internals). Commit.

### Task 3.2: `skills/<name>/reference_table.md`

Lab percentile→absolute mapping per threshold + refresh procedure (re-derive on a NEW train window post-event; explicitly: **the Skill never reads this at runtime**).

### Task 3.3: Live validation

- [ ] Script `demo/validate_skill.py`: executes the SKILL.md workflow literally via `scripts/mcp_client.py` — every `allowed-tools` entry resolves in `tools/list`; every field the rules reference exists in the live payload; classification completes on live data; spec block validates against the schema (jsonschema-lite check in code). Output → `docs/gate0/skill_validation_run.json`. Commit. **If any field drifted from the Gate-0 dump → STOP, re-open freeze with the critic.**

---

# Phase 4 — Demo, report, README, video (Day 8)

### Task 4.1: `docs/report/REPORT.md`

Structure (the panel-facing rigor story):
1. Headline: Winner (or null), pooled-OOS metrics, **honest-N = OOS regime-episode count**, train/OOS curves figure
2. Method: select-on-train/gate-on-OOS (ADR link), walk-forward diagram, R1 threshold hygiene, source-consistency table (PR-2, incl. the bybit-venue decision + funding cross-check stats + CoinGlass-freeze handling)
3. Falsification chapter: shuffle-null distribution figure, top-5 removal, cost ladder table, **R3 disclosure** (variants swept / passes / expected null pass-rate), Phase-2 prior nulls cited openly (rm17 L1 forward-return null; 1h DVOL lead died in causal OOS)
4. Benchmarks table (HODL/flat/vol-target, same costs+funding)
5. Deep-history proxy section (separate, labeled, never merged)
6. Limitations: 14-month window, episode count, single venue, snapshot-only Skill, what would falsify this going forward
- [ ] `lab/report_figs.py` renders all figures from `artifacts/sweep_results.json` + CSVs. Commit.

### Task 4.2: `demo/run_demo.py`

One command: loads frozen classifier → live MCP calls → prints regime + full strategy spec block → renders `docs/report/figs/equity_oos.png` + today's regime marker. This is the demo-video script. Commit.

### Task 4.3: README.md (full)

What it is (one screen) → architecture diagram (three units) → quickstart (`uv sync; cp .env.example .env; uv run python demo/run_demo.py`) → reproduce-the-backtest (`uv run python -m lab.sweep` from committed CSVs) → results summary table → methodology/ADR links → key security note (key in .env only) → license MIT.

### Task 4.4: Demo video

- [ ] Record: `asciinema rec` (or `script` + ffmpeg) of `run_demo.py` live run + a matplotlib walkthrough of report figures; assemble ≤ 3-min MP4 with ffmpeg (title card → live MCP call → regime+spec → equity/falsification figures → repo tour). Output `docs/demo/demo.mp4` (and/or YouTube link by operator). Fallback per submission rules: "demo link/video **or clear setup instructions**" — README quickstart already satisfies the floor; the video is for the Demo criterion score. Flag to operator if a human-voiced video is preferred.

---

# Phase 5 — Independent review + ship (Day 9; Day 10 buffer)

### Task 5.1: Independent review (separate lane — never self-approve)

Critic + code-reviewer agents over the full repo: ADR compliance audit (R1/R2/R3 spot-checks against code), CONTEXT.md vocabulary lint of all prose, SKILL.md vs live-validation transcript, report claims vs artifacts (every number in REPORT.md must be re-derivable from committed files), secrets scan (`git log -p | grep -iE 'api[-_]?key|7fb3'` must be clean + gitleaks if available). Findings → fix → re-verify.

### Task 5.2: Publish

- [ ] `gh repo create GabrielSchmalz/bnbhack-cmc-t2 --public --source . --push` (after final secrets scan of FULL history).
- [ ] Verify public render: README, figures, SKILL.md display correctly.

### Task 5.3: DoraHacks submission package

- [ ] Write `docs/SUBMISSION.md`: project name, one-paragraph pitch, repo URL, demo video link, strategy explanation (panel-facing, maps to the 4 criteria), track = Track 2 (+ "Best Use of Agent Hub" special-prize checkbox rationale).
- [ ] **Operator action (DoraHacks form is bot-hostile):** submit via the DoraHacks UI before 2026-06-21 12:00 UTC using SUBMISSION.md text. Builder agent notifies operator with the exact paste-ready content. Buffer: aim operator handoff by **Jun 19**.

---

# §W — Workflow orchestration map

Executed via the Workflow tool (operator's explicit opt-in). Phases → fan-out:

- **WF-A (Phase 0):** sequential scaffold commit, then **parallel**: gate0_dump ∥ funding backfill ∥ F&G backfill ∥ CH export. Barrier: GATE0-FREEZE.md authored after dump lands (needs all four for the source table).
- **WF-B (Phase 1):** harness TDD — pipeline with limited parallelism: (1.1 dataset) → then parallel {1.2 engine+1.3 metrics} ∥ {1.6 classifier} → {1.4 dd_guard, 1.5 benchmarks} → {1.7 walkforward} → {1.8 hooks} → {1.9 gate}. **Worktree isolation** for parallel mutating agents; integrate via rebase-merge per task; full `uv run pytest` green at every merge.
- **WF-C (Phase 2):** features+rules+variants (parallel, worktrees) → sweep run (single agent, long) → **adversarial verify fan-out** (3 refuters per survivor, perspective-diverse: leakage / source-swap / boundary-sensitivity) → freeze (single agent + critic sign-off).
- **WF-D (Phases 3–4):** SKILL.md ∥ report ∥ README authoring (parallel) → live validation + demo (sequential, needs network) → video.
- **WF-E (Phase 5):** review fan-out (code-reviewer, critic, security) → fixes → publish → submission package → operator notification.
- Checkpoint discipline: builder agent reviews results between workflow invocations (one Workflow call per phase, not one giant script) — keeps the human-readable decision trail in the session.

## Timeline vs lock (2026-06-21 12:00 UTC)

| Day | Date | Milestone |
|---|---|---|
| 1 | Jun 10–11 | Phase 0 complete (Gate 0 frozen, data committed) |
| 2–4 | Jun 11–13 | Harness TDD green |
| 4–6 | Jun 13–15 | Sweep run + adversarial verify + freeze |
| 7 | Jun 16 | Skill authored + live-validated |
| 8 | Jun 17 | Report, README, demo, video |
| 9 | Jun 18 | Independent review + fixes + publish |
| 10 | Jun 19 | Operator submits on DoraHacks (2-day buffer) |

## Self-review (plan vs spec) — done 2026-06-10

- Spec coverage: G1(distill: 2.1–2.6) G2(4h: PR-1) G3(both families: PR-8) G4(gate: PR-7/1.9) G5(two windows: PR-1/2.7) G6(Gate 0: 0.2) G7(frozen absolutes: PR-6/2.6) G8(execution: PR-3/1.2) G9(spec block: 3.1) G10(homes/keys: preflight) · R-LEAK(R1: 2.1 test) R-N(R2: PR-6/1.7) R-SRC(PR-2/0.3/0.4) R-GATE(R3: 1.9/4.1) R-NULL(PR-10) R-FUND(1.2 test) R-NAME(2.6) · DoD §8 all mapped (repo 5.2, report 4.1, skill validation 3.3, video 4.4, submission 5.3, review 5.1).
- Known data-dependent open points (decision rules pre-registered, not placeholders): F&G source fallback (0.4), LS ships-or-not (Gate 0), final taxonomy names (2.6), null-result branch (PR-10).
