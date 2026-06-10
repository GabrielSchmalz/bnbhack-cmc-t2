# Widening recon — data spans, CMC REST surface, compute budget (Phase R)

Date: 2026-06-10 · Lane: recon (5 parallel probes, read-only, no OOS contact)
Purpose: empirical inputs to the widening pre-registration
(`docs/plans/2026-06-10-widening-preregistration.md`). Curated record; raw
probe outputs were not committed.

---

## 1. Free-history spans (verified by live probe, 2026-06-10)

| series | source (one source end-to-end) | earliest | latest | cadence |
|---|---|---|---|---|
| BTCUSDT funding | Binance REST `fapi/v1/fundingRate` | 2019-09-10 08:00 | live | 8h |
| ETHUSDT funding | same | 2019-11-27 08:00 | live | 8h |
| SOLUSDT funding | same | 2020-09-13 16:00 | live | 8h (ms jitter +3..11ms on stamps — snap to 8h grid) |
| BTCUSDT 4h bars | committed `data/lab/bars_4h.csv` (mirror of Binance klines) | 2020-01-01 | 2026-06-09 | 4h |
| ETHUSDT 4h futures klines | Binance REST `fapi/v1/klines` | 2019-11-27 04:00 | live | 4h |
| SOLUSDT 4h futures klines | same | 2020-09-14 04:00 | live | 4h |
| BTC daily OI | CoinGlass-relayed history (read-only mirror), Binance-BTCUSDT subset | 2020-02-27 | **2026-05-18 (frozen)** | strictly daily for 2 259 of 2 285 gaps; a handful of 8h/16h stamps in 2026 only |
| BTC DVOL | committed `data/lab/dvol.csv` (Deribit) | 2021-03-24 | live | 1h (15m from 2026) |
| ETH DVOL | Deribit REST (not yet committed) | 2021-03-24 | live | probe-verified |
| CMC Fear & Greed | committed `data/backfill/fear_greed.csv` (CMC Pro REST) | 2023-06-29 | live | daily |

Other findings:

- Binance `futures/data/*` endpoints (OI hist, top/global long-short ratio)
  are hard-capped to a **rolling ~30-day window** — confirmed empirically
  (186 × 4h rows, earliest advances daily). No deep OI/LS backfill from
  Binance REST.
- `fapi/v1/fundingRate` **ignores `startTime=0`** and silently returns the
  newest page — backfill scripts must pass a realistic early `startTime`.
- Mirror-side ETH/SOL klines exist only at 1h/5m/15m and are frozen
  2026-05-16; Binance REST is the proper single source for ETH/SOL 4h.
- Hyperliquid funding: BTC hourly 2023-05→live; ETH stale (2026-05-09).
  Not used (R-SRC: Binance REST funding is the decided source of record).
- cg CVD (1h, 2019-12→2026-05-29) and LS/liquidation history remain
  unusable or non-shippable (stale / no CMC field / short span).

## 2. CMC Pro REST surface reachable with the event key

Key profile (`/v1/key/info`): 15 000 credits/month, 50 req/min; ~14 950
credits remaining at probe time. No plan-name string returned.

| endpoint | accessible | note |
|---|---|---|
| `/v3/fear-and-greed/historical` | **yes** | daily, 2023-06-29 →; `count` param ignored — use start/limit pagination |
| `/v1/global-metrics/quotes/historical` | **no** (403 / error 1006) | no dominance / total-mcap history on this plan |
| `/v2/cryptocurrency/ohlcv/historical` | **no** (403 / 1006) | |
| `/v2/cryptocurrency/quotes/historical` | **no** (403 / 1006) | |
| `/v1/cryptocurrency/listings/historical` | **no** (403 / 1006) | |
| `/v5/cryptocurrency/derivatives/market-pairs/list/latest` | **yes** | per-pair OI / funding / index price / basis — **latest-only**, 60s cache; docs list no historical derivatives REST endpoint at all |

**Implication (binds the pre-registration):** the only CMC-historical series
available as a *backtest* Feature is Fear & Greed. CMC-MCP deepening
therefore happens (a) lab-side via F&G end-to-end, and (b) live-side via
wider verified-tool usage in the Skill — not via CMC-sourced deep price/
derivatives history.

## 3. Compute budget (micro-benchmarks, ±30%)

- `run_backtest`: 5.6 ms @ 2 598 bars · 13.9 ms @ 14 112 bars.
- One null draw (permute + apply + backtest + Sharpe): 8.8 ms @ 2 598 ·
  24.2 ms @ 14 112 (generation amortizes across a taxonomy's variants;
  the **backtest part is per variant** — dominant term scales V×F×D).
- Frozen sweep (36×4×1000 @ 2 598 bars) = 283.7 s wall ⇒ ~3.1× effective
  speedup on the 8-worker pool.
- Projection @ ~14.5 ms/draw, V≈160 variants, F≈21 folds, D=1000:
  ≈ 13.5 core-h ⇒ ≈ 4.5 h wall at observed parallel efficiency. Headroom:
  restricting each null backtest to the fold's OOS window (bar returns are
  bar-local) cuts the dominant term ~F-fold — to be adopted **only** with a
  bit-for-bit equivalence proof against the frozen artifact.
- Full test suite: 226 passed (one known worktree-name environment artifact
  when run outside the canonical checkout).

## 4. Hypothesis survey

The structured survey of untried hypotheses, binding constraints, and
prior-contact disclosures is folded directly into the pre-registration
(`docs/plans/2026-06-10-widening-preregistration.md` §2, §9, §10) rather
than duplicated here.
