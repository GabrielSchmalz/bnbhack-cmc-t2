# GATE 0 — ADDENDUM: per-asset dumps for ETH and SOL

**Status: CAPTURED 2026-06-10, pre-OOS-contact** (registration
`docs/plans/2026-06-10-widening-preregistration.md` §2, "Live-computability and
the Gate-0 scope"). The day-1 Gate-0 dump (`GATE0-FREEZE.md`) was BTC-centric;
§2 registers this addendum as a pre-OOS requirement: call
`get_crypto_technical_analysis` and `get_crypto_quotes_latest` for ETH
(CMC id 1027) and SOL (CMC id 5426), commit the raw JSON under `docs/gate0/`,
and verify the exact field paths the registration relies on. A P-ETH/P-SOL
Winner ships only if its per-asset fields pass this Gate-0-style verification.

**Provenance.** Live dump 2026-06-10 ~23:10 UTC against
`https://mcp.coinmarketcap.com/mcp` (server `cmc-mcp-service v1.0.0`), same
JSON-RPC sequence as the day-1 dump (`scripts/mcp_client.py`:
initialize → notifications/initialized → tools/call). All four calls returned
`isError: false` on the first attempt. Raw JSON-RPC responses saved verbatim
(pretty-printed, byte-for-byte payloads — these short-form dumps contain no
third-party prose, so the README's redistribution-hygiene truncation does not
apply):

| File | Tool | Arguments |
|---|---|---|
| `get_crypto_technical_analysis_eth.json` | `get_crypto_technical_analysis` | `{"id": "1027"}` |
| `get_crypto_technical_analysis_sol.json` | `get_crypto_technical_analysis` | `{"id": "5426"}` |
| `get_crypto_quotes_latest_eth.json` | `get_crypto_quotes_latest` | `{"id": "1027"}` |
| `get_crypto_quotes_latest_sol.json` | `get_crypto_quotes_latest` | `{"id": "5426"}` |

As in every Gate-0 dump, the payload arrives as **JSON-as-string** inside
`result.content[0].text` and must be parsed before reading any field.

---

## 1. Required-field verification (registration §2 / F4–F6)

The registration's live analogs for the W-panel Features are `rsi.rsi14` (F4,
`rsi14_1d`), `moving_averages.simple_moving_average_200_day` + quotes price
(F5, `close_vs_sma200_1d`), and quotes `[0].percent_change_24h` (F6, `pc_24h`).

### ETH (id 1027)

| Required path | Present | Sample value (this dump) | Type / format vs BTC dump |
|---|---|---|---|
| `rsi.rsi14` | YES | `"25.74"` | string, plain decimal on 0–100 scale — identical to BTC (`"23.89"`) |
| `moving_averages.simple_moving_average_200_day` | YES | `"2,438.62"` | string with comma thousands separator — identical format family to BTC (`"78,240.34"`); §8 frozen parse rule (strip commas → float) applies unchanged |
| `[0].price` | YES | `1612.2458123121455` | raw numeric float — identical to BTC; quotes remains the only raw-float tool |
| `[0].percent_change_24h` | YES | `-1.59620255` | raw numeric float, percent units — identical to BTC (`0.03458382`) |

### SOL (id 5426)

| Required path | Present | Sample value (this dump) | Type / format vs BTC dump |
|---|---|---|---|
| `rsi.rsi14` | YES | `"26.73"` | string, plain decimal on 0–100 scale — identical to BTC |
| `moving_averages.simple_moving_average_200_day` | YES | `"101.39"` | string; **no comma** because the value is < 1,000 — the comma is a thousands separator, not a fixed format, and the frozen strip-commas → float parse covers both cases |
| `[0].price` | YES | `62.65625175948232` | raw numeric float — identical to BTC |
| `[0].percent_change_24h` | YES | `-3.49052946` | raw numeric float, percent units — identical to BTC |

**All four required paths are present and well-formed for both assets. No unit
or format difference vs the BTC dump affects any required field.**

## 2. Non-gating shape differences vs the BTC dump (disclosed for completeness)

- `get_crypto_technical_analysis`: identical key set for BTC/ETH/SOL — the
  same 23 leaf paths (`moving_averages.*`, `macd.*`, `rsi.*`,
  `fibonacciLevels.*`, `pivotPoint`), all human-formatted strings.
- `get_crypto_quotes_latest`: BTC serves 38 leaf paths; ETH and SOL serve 37 —
  **`[0].max_supply` is absent** for both (ETH has no max supply; SOL's is not
  served). No registered Feature or parsing constant touches `max_supply`.
- `[0].self_reported_circulating_supply` is a non-zero float for SOL
  (`525236893.3`) vs `0` for BTC/ETH — a type wobble on a field nothing
  registered consumes.

## 3. Verdict

**The §2 ship-eligibility precondition PASSES for P-ETH and PASSES for
P-SOL.** Every field path the registration relies on — `rsi.rsi14`,
`moving_averages.simple_moving_average_200_day`, quotes `[0].price`, and
quotes `[0].percent_change_24h` — is live-served for both assets with the same
types and parse rules already frozen for BTC (`GATE0-FREEZE.md` §8). The
Gate-0-verified live-computability claim of registration §2 therefore extends
from P-BTC to P-ETH and P-SOL for F4, F5, and F6. This addendum gates ship
eligibility of P-ETH/P-SOL Winners only; it does not alter the sweep.
