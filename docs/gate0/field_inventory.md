# Gate 0 — Field inventory (raw material for GATE0-FREEZE.md)

Generated from the raw dumps in `docs/gate0/*.json` (live CMC MCP, fetched 2026-06-10 UTC).
Each table lists flattened JSON field paths of the tool's *payload* (the JSON parsed from
`result.content[0].text` of the JSON-RPC response), one example value, and the JSON type.
Array-typed payloads show element `[0]`; tabular `headers`/`rows` payloads name columns as
`rows[0].<header>`. For **get_global_crypto_derivatives_metrics** and
**get_global_metrics_latest** the listing is exhaustive (every leaf field present in the dump).

Tool list (12 tools): `docs/gate0/tools_list.json`.

## get_crypto_quotes_latest

Args used: `{"id": "1"}` — dump: `docs/gate0/get_crypto_quotes_latest.json` — 38 entries

| field path | example value | type |
|---|---|---|
| `[0].id` | `1` | string |
| `[0].name` | `Bitcoin` | string |
| `[0].symbol` | `BTC` | string |
| `[0].slug` | `bitcoin` | string |
| `[0].price` | `61820.477784763956` | number(float) |
| `[0].rank` | `1` | number(int) |
| `[0].turnover` | `0.02393081` | number(float) |
| `[0].last_updated_time` | `2026-06-10T18:23:00.000Z` | string |
| `[0].percent_change_1h` | `-0.28408653` | number(float) |
| `[0].percent_change_24h` | `0.03458382` | number(float) |
| `[0].percent_change_7d` | `-5.93332177` | number(float) |
| `[0].percent_change_30d` | `-24.53579634` | number(float) |
| `[0].percent_change_60d` | `-15.58111576` | number(float) |
| `[0].percent_change_90d` | `-11.66876071` | number(float) |
| `[0].percent_change_1y` | `-43.2216581` | number(float) |
| `[0].percent_change_3y` | `139.615682451975` | number(float) |
| `[0].percent_change_all` | `100223427.84215315` | number(float) |
| `[0].percent_change_ytd` | `-30.329` | number(float) |
| `[0].market_cap` | `1238847755339.11` | number(float) |
| `[0].volume_24h` | `29646624340.63075` | number(float) |
| `[0].volume_change_24h` | `-21.873` | number(float) |
| `[0].last_updated_time_dup` | `2026-06-10T18:23:00.000Z` | string |
| `[0].fully_diluted_market_cap` | `1298230033480.04` | number(float) |
| `[0].market_cap_by_total_supply` | `1238847755339.11` | number(float) |
| `[0].date_added` | `2010-07-13T00:00:00.000Z` | string |
| `[0].max_supply` | `21000000.0` | number(float) |
| `[0].total_supply` | `20039440.0` | number(float) |
| `[0].self_reported_circulating_supply` | `0` | number(int) |
| `[0].circulating_supply` | `20039440.0` | number(float) |
| `[0].market_cap_percent_change_1h` | `-0.283106253112` | number(float) |
| `[0].market_cap_percent_change_24h` | `0.0363` | number(float) |
| `[0].market_cap_percent_change_7d` | `-5.93836227745` | number(float) |
| `[0].market_cap_percent_change_30d` | `-23.998985880648` | number(float) |
| `[0].market_cap_percent_change_90d` | `-11.734427204452` | number(float) |
| `[0].market_cap_percent_change_1y` | `-42.755149172341` | number(float) |
| `[0].market_cap_percent_change_3y` | `147.534117468154` | number(float) |
| `[0].market_cap_percent_change_all` | `6067534.292970478` | number(float) |
| `[0].market_cap_dominance` | `58.3139` | number(float) |

## get_crypto_technical_analysis

Args used: `{"id": "1"}` — dump: `docs/gate0/get_crypto_technical_analysis.json` — 23 entries

| field path | example value | type |
|---|---|---|
| `moving_averages.simple_moving_average_7_day` | `62,511.42` | string |
| `moving_averages.simple_moving_average_30_day` | `73,076.76` | string |
| `moving_averages.simple_moving_average_200_day` | `78,240.34` | string |
| `moving_averages.exponential_moving_average_7_day` | `63,603.18` | string |
| `moving_averages.exponential_moving_average_30_day` | `70,621.85` | string |
| `moving_averages.exponential_moving_average_200_day` | `80,102.83` | string |
| `macd.macdLine` | `-4,129.58` | string |
| `macd.signalLine` | `-3,200.19` | string |
| `macd.histogram` | `-929.39` | string |
| `rsi.rsi7` | `21.9` | string |
| `rsi.rsi14` | `23.89` | string |
| `rsi.rsi21` | `28.67` | string |
| `fibonacciLevels.swingHigh` | `82,326.23` | string |
| `fibonacciLevels.swingLow` | `59,108.92` | string |
| `fibonacciLevels.retracementLevels.50.0%` | `70,717.58` | string |
| `fibonacciLevels.retracementLevels.23.6%` | `76,846.95` | string |
| `fibonacciLevels.retracementLevels.38.2%` | `73,457.22` | string |
| `fibonacciLevels.retracementLevels.78.6%` | `64,077.42` | string |
| `fibonacciLevels.retracementLevels.61.8%` | `67,977.93` | string |
| `fibonacciLevels.extensionLevels.161.8%` | `96,674.53` | string |
| `fibonacciLevels.extensionLevels.127.2%` | `88,641.34` | string |
| `fibonacciLevels.extensionLevels.200.0%` | `105,543.55` | string |
| `pivotPoint` | `61962.19` | string |

## get_global_crypto_derivatives_metrics

Args used: `{}` — dump: `docs/gate0/get_global_crypto_derivatives_metrics.json` — 66 entries

| field path | example value | type |
|---|---|---|
| `totalOpenInterest.current` | `381.77 B` | string |
| `totalOpenInterest.percentage_change_24h` | `+0.51598%` | string |
| `totalOpenInterest.percentage_change_7d` | `-17.66%` | string |
| `totalOpenInterest.percentage_change_14d` | `-20.32%` | string |
| `totalOpenInterest.percentage_change_30d` | `-19.91%` | string |
| `totalVolume.total_usd_24h` | `240.94 T` | string |
| `totalVolume.pct_change_prev_24h_vs_prior_24h` | `+3.07%` | string |
| `totalVolume.pct_change_prev_7d_vs_prior_7d` | `+30.7%` | string |
| `totalVolume.pct_change_prev_14d_vs_prior_14d` | `+21.54%` | string |
| `totalVolume.pct_change_prev_30d_vs_prior_30d` | `+7.32%` | string |
| `futures.volume.total_usd_24h` | `84.85 B` | string |
| `futures.volume.pct_change_prev_24h_vs_prior_24h` | `-14.76%` | string |
| `futures.volume.pct_change_prev_7d_vs_prior_7d` | `+37.64%` | string |
| `futures.volume.pct_change_prev_14d_vs_prior_14d` | `+34.74%` | string |
| `futures.volume.pct_change_prev_30d_vs_prior_30d` | `+24.89%` | string |
| `futures.openInterest.current` | `3.27 B` | string |
| `futures.openInterest.percentage_change_24h` | `+11.28%` | string |
| `futures.openInterest.percentage_change_7d` | `+26.38%` | string |
| `futures.openInterest.percentage_change_14d` | `+12.83%` | string |
| `futures.openInterest.percentage_change_30d` | `-12.82%` | string |
| `perpetuals.volume.total_usd_24h` | `240.85 T` | string |
| `perpetuals.volume.pct_change_prev_24h_vs_prior_24h` | `+3.07%` | string |
| `perpetuals.volume.pct_change_prev_7d_vs_prior_7d` | `+30.7%` | string |
| `perpetuals.volume.pct_change_prev_14d_vs_prior_14d` | `+21.54%` | string |
| `perpetuals.volume.pct_change_prev_30d_vs_prior_30d` | `+7.31%` | string |
| `perpetuals.openInterest.current` | `378.51 B` | string |
| `perpetuals.openInterest.percentage_change_24h` | `+0.4322%` | string |
| `perpetuals.openInterest.percentage_change_7d` | `-17.9%` | string |
| `perpetuals.openInterest.percentage_change_14d` | `-20.53%` | string |
| `perpetuals.openInterest.percentage_change_30d` | `-19.97%` | string |
| `fundingRate.current` | `0.00069614` | string |
| `fundingRate.percentage_change_24h` | `+13.27%` | string |
| `fundingRate.percentage_change_7d` | `-88.46%` | string |
| `fundingRate.percentage_change_14d` | `-90.3%` | string |
| `fundingRate.percentage_change_30d` | `-4.17%` | string |
| `btc_liquidations.definitions.short` | `Total USD value of short positions that were forcibly closed` | string |
| `btc_liquidations.definitions.total` | `Total USD value of forced BTC position closures` | string |
| `btc_liquidations.definitions.long` | `Total USD value of long positions that were forcibly closed` | string |
| `btc_liquidations.definitions.pct_change_prev_x_vs_prior_x` | `Percent change in the metric between the most-recent <period> window and the <period> w...` | string |
| `btc_liquidations.total_usd_1h.total` | `0` | string |
| `btc_liquidations.total_usd_1h.long` | `0` | string |
| `btc_liquidations.total_usd_1h.short` | `0` | string |
| `btc_liquidations.total_usd_4h.total` | `17.91 M` | string |
| `btc_liquidations.total_usd_4h.long` | `1.64 M` | string |
| `btc_liquidations.total_usd_4h.short` | `16.27 M` | string |
| `btc_liquidations.total_usd_12h.total` | `60.09 M` | string |
| `btc_liquidations.total_usd_12h.long` | `17.21 M` | string |
| `btc_liquidations.total_usd_12h.short` | `42.88 M` | string |
| `btc_liquidations.total_usd_24h.total` | `84.05 M` | string |
| `btc_liquidations.total_usd_24h.long` | `30.33 M` | string |
| `btc_liquidations.total_usd_24h.short` | `53.71 M` | string |
| `btc_liquidations.pct_change_prev_4h_vs_prior_4h.total` | `-38.16%` | string |
| `btc_liquidations.pct_change_prev_4h_vs_prior_4h.long` | `-65.29%` | string |
| `btc_liquidations.pct_change_prev_4h_vs_prior_4h.short` | `-32.87%` | string |
| `btc_liquidations.pct_change_prev_12h_vs_prior_12h.total` | `+150.75%` | string |
| `btc_liquidations.pct_change_prev_12h_vs_prior_12h.long` | `+31.1%` | string |
| `btc_liquidations.pct_change_prev_12h_vs_prior_12h.short` | `+295.68%` | string |
| `btc_liquidations.pct_change_prev_24h_vs_prior_24h.total` | `-35.77%` | string |
| `btc_liquidations.pct_change_prev_24h_vs_prior_24h.long` | `-70.83%` | string |
| `btc_liquidations.pct_change_prev_24h_vs_prior_24h.short` | `+99.86%` | string |
| `btc_liquidations.pct_change_prev_7d_vs_prior_7d.total` | `+14.53%` | string |
| `btc_liquidations.pct_change_prev_7d_vs_prior_7d.long` | `-19.22%` | string |
| `btc_liquidations.pct_change_prev_7d_vs_prior_7d.short` | `+335.48%` | string |
| `btc_liquidations.pct_change_prev_30d_vs_prior_30d.total` | `+75.7%` | string |
| `btc_liquidations.pct_change_prev_30d_vs_prior_30d.long` | `+289.62%` | string |
| `btc_liquidations.pct_change_prev_30d_vs_prior_30d.short` | `-34.64%` | string |

## get_global_metrics_latest

Args used: `{}` — dump: `docs/gate0/get_global_metrics_latest.json` — 133 entries

| field path | example value | type |
|---|---|---|
| `last_updated` | `10 June 2026 12:00 AM UTC+0` | string |
| `market_size.definition` | `Market size captures the aggregate USD value of the entire crypto asset class, providin...` | string |
| `market_size.total_crypto_market_cap_usd.current` | `2.13 T` | string |
| `market_size.total_crypto_market_cap_usd.percent_change.24h` | `-0.40479%` | string |
| `market_size.total_crypto_market_cap_usd.percent_change.7d` | `-7.64%` | string |
| `market_size.total_crypto_market_cap_usd.percent_change.30d` | `-20.89%` | string |
| `market_size.total_crypto_market_cap_usd.yearly.max.value` | `4.28 T` | string |
| `market_size.total_crypto_market_cap_usd.yearly.max.timestamp` | `7 October 2025 12:00 AM UTC+0` | string |
| `market_size.total_crypto_market_cap_usd.yearly.min.value` | `2.1 T` | string |
| `market_size.total_crypto_market_cap_usd.yearly.min.timestamp` | `7 June 2026 12:00 AM UTC+0` | string |
| `liquidity.definition` | `Liquidity metrics track how much value changes hands—across spot markets and derivative...` | string |
| `liquidity.volume24h.total.current` | `75.29 B` | string |
| `liquidity.volume24h.total.percent_change.24h` | `-14.54%` | string |
| `liquidity.volume24h.total.percent_change.7d` | `-41.87%` | string |
| `liquidity.volume24h.total.percent_change.30d` | `-14.63%` | string |
| `liquidity.volume24h.spot.current` | `177.87 B` | string |
| `liquidity.volume24h.spot.percent_change.24h` | `+8.22%` | string |
| `liquidity.volume24h.spot.percent_change.7d` | `-14.17%` | string |
| `liquidity.volume24h.spot.percent_change.30d` | `+47.49%` | string |
| `liquidity.volume24h.derivatives.total.current` | `775.75 B` | string |
| `liquidity.volume24h.derivatives.total.percent_change.24h` | `+4.16%` | string |
| `liquidity.volume24h.derivatives.total.percent_change.7d` | `-12.23%` | string |
| `liquidity.volume24h.derivatives.total.percent_change.30d` | `+16.67%` | string |
| `liquidity.volume24h.derivatives.futures.current` | `320.49 M` | string |
| `liquidity.volume24h.derivatives.futures.percent_change.24h` | `+13.01%` | string |
| `liquidity.volume24h.derivatives.futures.percent_change.7d` | `-9.57%` | string |
| `liquidity.volume24h.derivatives.futures.percent_change.30d` | `+30.57%` | string |
| `liquidity.volume24h.derivatives.perpetuals.current` | `775.43 B` | string |
| `liquidity.volume24h.derivatives.perpetuals.percent_change.24h` | `+4.16%` | string |
| `liquidity.volume24h.derivatives.perpetuals.percent_change.7d` | `-12.23%` | string |
| `liquidity.volume24h.derivatives.perpetuals.percent_change.30d` | `+16.66%` | string |
| `liquidity.volume24h.spot_vs_perp_ratio` | `0.23` | string |
| `sentiment.fear_greed.definition` | `The CMC Fear & Greed Index distills overall crypto-market sentiment into a single 0-100...` | string |
| `sentiment.fear_greed.current.value` | `Extreme fear` | string |
| `sentiment.fear_greed.current.index` | `15` | number(int) |
| `sentiment.fear_greed.history.yesterday.value` | `Extreme fear` | string |
| `sentiment.fear_greed.history.yesterday.index` | `14` | number(int) |
| `sentiment.fear_greed.history.last_week.value` | `Fear` | string |
| `sentiment.fear_greed.history.last_week.index` | `23` | number(int) |
| `sentiment.fear_greed.history.last_month.value` | `Neutral` | string |
| `sentiment.fear_greed.history.last_month.index` | `52` | number(int) |
| `sentiment.fear_greed.yearly.max.value` | `Greed` | string |
| `sentiment.fear_greed.yearly.max.index` | `71` | number(int) |
| `sentiment.fear_greed.yearly.max.timestamp` | `18 July 2025 12:00 AM UTC+0` | string |
| `sentiment.fear_greed.yearly.min.value` | `Extreme fear` | string |
| `sentiment.fear_greed.yearly.min.index` | `5` | number(int) |
| `sentiment.fear_greed.yearly.min.timestamp` | `6 February 2026 12:00 AM UTC+0` | string |
| `rotation.altcoin_season.definition` | `The CMC Altcoin Season Index is a real-time sentiment gauge of crypto’s typical rotatio...` | string |
| `rotation.altcoin_season.current.value` | `` | string |
| `rotation.altcoin_season.current.index` | `48` | number(int) |
| `rotation.altcoin_season.percent_change.24h` | `+2.13%` | string |
| `rotation.altcoin_season.percent_change.7d` | `-9.43%` | string |
| `rotation.altcoin_season.percent_change.30d` | `-2.04%` | string |
| `rotation.altcoin_season.history.yesterday.value` | `` | string |
| `rotation.altcoin_season.history.yesterday.index` | `47` | number(int) |
| `rotation.altcoin_season.history.last_week.value` | `` | string |
| `rotation.altcoin_season.history.last_week.index` | `53` | number(int) |
| `rotation.altcoin_season.history.last_month.value` | `` | string |
| `rotation.altcoin_season.history.last_month.index` | `49` | number(int) |
| `rotation.altcoin_season.yearly.max.value` | `Altcoin Season` | string |
| `rotation.altcoin_season.yearly.max.index` | `78` | number(int) |
| `rotation.altcoin_season.yearly.max.timestamp` | `20 September 2025 12:00 AM UTC+0` | string |
| `rotation.altcoin_season.yearly.min.value` | `Bitcoin Season` | string |
| `rotation.altcoin_season.yearly.min.index` | `14` | number(int) |
| `rotation.altcoin_season.yearly.min.timestamp` | `19 December 2025 12:00 AM UTC+0` | string |
| `dominance.definition` | `Bitcoin dominance—BTC’s share of total crypto value—condenses sentiment, maturity, and ...` | string |
| `dominance.btc.current` | `+58.35%` | string |
| `dominance.btc.yearly.max.value` | `+65.12%` | string |
| `dominance.btc.yearly.max.timestamp` | `27 June 2025 12:00 AM UTC+0` | string |
| `dominance.btc.yearly.min.value` | `+56.74%` | string |
| `dominance.btc.yearly.min.timestamp` | `14 September 2025 12:00 AM UTC+0` | string |
| `dominance.btc.history.yesterday` | `+58.12%` | string |
| `dominance.btc.history.last_week` | `+58.09%` | string |
| `dominance.btc.history.last_month` | `+60.16%` | string |
| `dominance.eth.current` | `+9.24%` | string |
| `dominance.eth.yearly.max.value` | `+8.93%` | string |
| `dominance.eth.yearly.max.timestamp` | `27 June 2025 12:00 AM UTC+0` | string |
| `dominance.eth.yearly.min.value` | `+13.84%` | string |
| `dominance.eth.yearly.min.timestamp` | `14 September 2025 12:00 AM UTC+0` | string |
| `dominance.eth.history.yesterday` | `+9.38%` | string |
| `dominance.eth.history.last_week` | `+9.75%` | string |
| `dominance.eth.history.last_month` | `+10.46%` | string |
| `dominance.others.current` | `+32.41%` | string |
| `dominance.others.yearly.max.value` | `+25.95%` | string |
| `dominance.others.yearly.max.timestamp` | `27 June 2025 12:00 AM UTC+0` | string |
| `dominance.others.yearly.min.value` | `+29.42%` | string |
| `dominance.others.yearly.min.timestamp` | `14 September 2025 12:00 AM UTC+0` | string |
| `dominance.others.history.yesterday` | `+32.5%` | string |
| `dominance.others.history.last_week` | `+32.17%` | string |
| `dominance.others.history.last_month` | `+29.38%` | string |
| `leverage.definition` | `Leverage fields measure borrowed-risk exposure via derivatives open interest, funding r...` | string |
| `leverage.open_interest.total.current` | `384.71 B` | string |
| `leverage.open_interest.total.percent_change.24h` | `-0.77%` | string |
| `leverage.open_interest.total.percent_change.7d` | `-10.96%` | string |
| `leverage.open_interest.total.percent_change.30d` | `-13.44%` | string |
| `leverage.open_interest.total.yearly.max.value` | `1.2 T` | string |
| `leverage.open_interest.total.yearly.max.timestamp` | `2 October 2025 12:00 AM UTC+0` | string |
| `leverage.open_interest.total.yearly.min.value` | `356.5 B` | string |
| `leverage.open_interest.total.yearly.min.timestamp` | `22 February 2026 12:00 AM UTC+0` | string |
| `leverage.open_interest.perpetuals.current` | `381.76 B` | string |
| `leverage.open_interest.perpetuals.percent_change.24h` | `-0.83%` | string |
| `leverage.open_interest.perpetuals.percent_change.7d` | `-11.11%` | string |
| `leverage.open_interest.perpetuals.percent_change.30d` | `-13.37%` | string |
| `leverage.open_interest.perpetuals.yearly.max.value` | `1.2 T` | string |
| `leverage.open_interest.perpetuals.yearly.max.timestamp` | `2 October 2025 12:00 AM UTC+0` | string |
| `leverage.open_interest.perpetuals.yearly.min.value` | `2.26 B` | string |
| `leverage.open_interest.perpetuals.yearly.min.timestamp` | `28 June 2025 12:00 AM UTC+0` | string |
| `leverage.open_interest.futures.current` | `2.94 B` | string |
| `leverage.open_interest.futures.percent_change.24h` | `+6.61%` | string |
| `leverage.open_interest.futures.percent_change.7d` | `+13.35%` | string |
| `leverage.open_interest.futures.percent_change.30d` | `-21.2%` | string |
| `leverage.open_interest.futures.yearly.max.value` | `1.17 T` | string |
| `leverage.open_interest.futures.yearly.max.timestamp` | `9 October 2025 12:00 AM UTC+0` | string |
| `leverage.open_interest.futures.yearly.min.value` | `2.22 B` | string |
| `leverage.open_interest.futures.yearly.min.timestamp` | `29 May 2026 12:00 AM UTC+0` | string |
| `leverage.funding_rate.average.current` | `+0.0015866%` | string |
| `leverage.funding_rate.average.percent_change.24h` | `-164.38%` | string |
| `leverage.funding_rate.average.percent_change.7d` | `-79.21%` | string |
| `leverage.funding_rate.average.percent_change.30d` | `-443.12%` | string |
| `leverage.funding_rate.top_alts_minus_btc_spread_current` | `-0.002046` | string |
| `leverage.liquidations.btc.total_usd24h` | `84.05 M` | string |
| `leverage.liquidations.btc.total_usd7d` | `2.13 B` | string |
| `leverage.liquidations.btc.total_usd30d` | `5.71 B` | string |
| `leverage.liquidations.btc.percent_change24h` | `-35.77%` | string |
| `trad_fi_flows.definition` | `TradFi flows capture capital moving into or out of regulated exchange-traded products—s...` | string |
| `trad_fi_flows.etf_aum.btc.current` | `102.49 B` | string |
| `trad_fi_flows.etf_aum.btc.history.yesterday` | `102.05 B` | string |
| `trad_fi_flows.etf_aum.btc.history.last_week` | `105.03 B` | string |
| `trad_fi_flows.etf_aum.btc.history.last_month` | `107.4 B` | string |
| `trad_fi_flows.etf_aum.eth.current` | `13.74 B` | string |
| `trad_fi_flows.etf_aum.eth.history.yesterday` | `13.71 B` | string |
| `trad_fi_flows.etf_aum.eth.history.last_week` | `13.79 B` | string |
| `trad_fi_flows.etf_aum.eth.history.last_month` | `14.01 B` | string |

## get_crypto_marketcap_technical_analysis

Args used: `{}` — dump: `docs/gate0/get_crypto_marketcap_technical_analysis.json` — 19 entries

| field path | example value | type |
|---|---|---|
| `macd.macdLine` | `-120.52 B` | string |
| `macd.signalLine` | `-96.55 B` | string |
| `macd.histogram` | `-23.97 B` | string |
| `rsi.rsi7` | `29.52` | string |
| `rsi.rsi14` | `17.8` | string |
| `rsi.rsi21` | `21.1` | string |
| `fibonacciLevels.swingHigh` | `2.7 T` | string |
| `fibonacciLevels.swingLow` | `2.1 T` | string |
| `fibonacciLevels.retracementLevels.50.0%` | `2.4 T` | string |
| `fibonacciLevels.retracementLevels.23.6%` | `2.55 T` | string |
| `fibonacciLevels.retracementLevels.38.2%` | `2.47 T` | string |
| `fibonacciLevels.retracementLevels.78.6%` | `2.22 T` | string |
| `fibonacciLevels.retracementLevels.61.8%` | `2.32 T` | string |
| `fibonacciLevels.extensionLevels.161.8%` | `3.07 T` | string |
| `fibonacciLevels.extensionLevels.127.2%` | `2.86 T` | string |
| `fibonacciLevels.extensionLevels.200.0%` | `3.29 T` | string |
| `pivotPoint` | `2.12 T` | string |
| `currentMarketCap` | `2.12 T` | string |
| `currentVolume` | `75.29 B` | string |

## get_crypto_metrics

Args used: `{"id": "1"}` — dump: `docs/gate0/get_crypto_metrics.json` — 22 entries

| field path | example value | type |
|---|---|---|
| `definitions.traders` | `Addresses whose coins have moved in the last 30 days (< 1 month).` | string |
| `definitions.holders` | `Addresses whose coins have been untouched for more than 12 months (> 1 year).` | string |
| `definitions.avgTransactionFee30d` | `30-day trailing average fee per transaction onchain.` | string |
| `definitions.cruisers` | `Addresses whose coins last moved 1 – 12 months ago.` | string |
| `definitions.whales` | `Wallet addresses that each control more than 1% of the circulating crypto supply.` | string |
| `definitions.others` | `All wallet addresses that each control 1% or less of the circulating crypto supply.` | string |
| `addressesByHoldingValue.usd0To1k.count` | `42737795.0` | number(float) |
| `addressesByHoldingValue.usd0To1k.percentOfAddresses` | `76.55` | number(float) |
| `addressesByHoldingValue.usd1kTo100k.count` | `11972160.0` | number(float) |
| `addressesByHoldingValue.usd1kTo100k.percentOfAddresses` | `21.44` | number(float) |
| `addressesByHoldingValue.usd100kPlus.count` | `1121507.0` | number(float) |
| `addressesByHoldingValue.usd100kPlus.percentOfAddresses` | `2.01` | number(float) |
| `circulatingSupplyDistribution.whales.volume` | `248597.58` | number(float) |
| `circulatingSupplyDistribution.whales.percentOfSupply` | `1.25` | number(float) |
| `circulatingSupplyDistribution.others.volume` | `39351410.12` | number(float) |
| `circulatingSupplyDistribution.others.percentOfSupply` | `98.75` | number(float) |
| `addressesByHoldingTime.traders.count` | `2542722.0` | number(float) |
| `addressesByHoldingTime.traders.percentOfAddresses` | `4.61` | number(float) |
| `addressesByHoldingTime.cruisers.count` | `10681905.0` | number(float) |
| `addressesByHoldingTime.cruisers.percentOfAddresses` | `19.35` | number(float) |
| `addressesByHoldingTime.holders.count` | `41982983.0` | number(float) |
| `addressesByHoldingTime.holders.percentOfAddresses` | `76.05` | number(float) |

## get_crypto_info

Args used: `{"id": "1"}` — dump: `docs/gate0/get_crypto_info.json` — 22 entries

| field path | example value | type |
|---|---|---|
| `[0].id` | `1` | number(int) |
| `[0].name` | `Bitcoin` | string |
| `[0].symbol` | `BTC` | string |
| `[0].category` | `COIN` | string |
| `[0].description` | `## What Is Bitcoin (BTC)?  [Bitcoin](https://coinmarketcap.com/alexandria/article/an-in...` | string |
| `[0].slug` | `bitcoin` | string |
| `[0].logo` | `https://s2.coinmarketcap.com/static/img/coins/64x64/1.png` | string |
| `[0].tags[0]` | `mineable` | string |
| `[0].tags[1..36]` | `(+36 more elements, same shape)` | — |
| `[0].urls.website[0]` | `https://bitcoin.org/` | string |
| `[0].urls.twitter` | `[]` | array(empty) |
| `[0].urls.chat` | `[]` | array(empty) |
| `[0].urls.facebook` | `[]` | array(empty) |
| `[0].urls.explorer[0]` | `https://blockchain.info/` | string |
| `[0].urls.explorer[1..4]` | `(+4 more elements, same shape)` | — |
| `[0].urls.reddit[0]` | `https://reddit.com/r/bitcoin` | string |
| `[0].urls.announcement` | `[]` | array(empty) |
| `[0].urls.message_board[0]` | `https://bitcointalk.org` | string |
| `[0].urls.technical_doc[0]` | `https://bitcoin.org/bitcoin.pdf` | string |
| `[0].urls.source_code[0]` | `https://github.com/bitcoin/bitcoin` | string |
| `[0].date_added` | `2010-07-13T00:00:00.000Z` | string |
| `[0].infinite_supply` | `False` | boolean |

## get_crypto_latest_news

Args used: `{"id": "1", "limit": 5}` — dump: `docs/gate0/get_crypto_latest_news.json` — 7 entries

| field path | example value | type |
|---|---|---|
| `headers` | `["title", "description", "content", "url", "publishedAt", "quality"]` | array[string] |
| `rows[0].<title>` | `How high will Bitcoin get in 2026? \| Prediction Markets \| Coinbase` | string |
| `rows[0].<description>` | `Make your prediction on How high will Bitcoin get in 2026?. Trade on the future with Co...` | string |
| `rows[0].<content>` | `The Coinbase prediction market asks: Will Bitcoin's spot price, as measured by the CF B...` | string |
| `rows[0].<url>` | `https://www.coinbase.com/predictions/event/KXBTCMAXY-26DEC31` | string |
| `rows[0].<publishedAt>` | `31 December 2026 12:00 AM UTC+0` | string |
| `rows[0].<quality>` | `6.0` | string |

## trending_crypto_narratives

Args used: `{}` — dump: `docs/gate0/trending_crypto_narratives.json` — 19 entries

| field path | example value | type |
|---|---|---|
| `categoryList.headers` | `["trendingRank", "slug", "categoryCmcUrl", "categoryName", "marketCapUsd", "marketCapChang` | array[string] |
| `categoryList.rows[0].<trendingRank>` | `1` | number(int) |
| `categoryList.rows[0].<slug>` | `bitcoin-ecosystem` | string |
| `categoryList.rows[0].<categoryCmcUrl>` | `https://coinmarketcap.com/view/bitcoin-ecosystem` | string |
| `categoryList.rows[0].<categoryName>` | `Bitcoin Ecosystem` | string |
| `categoryList.rows[0].<marketCapUsd>` | `1.27 T` | string |
| `categoryList.rows[0].<marketCapChangePercentage24h>` | `+0.62758%` | string |
| `categoryList.rows[0].<marketCapChangePercentage7d>` | `-5.96%` | string |
| `categoryList.rows[0].<marketCapChangePercentage30d>` | `-23.83%` | string |
| `categoryList.rows[0].<marketCapChangePercentage90d>` | `-12.45%` | string |
| `categoryList.rows[0].<marketCapChangePercentage1y>` | `-42.26%` | string |
| `categoryList.rows[0].<volume24h>` | `32.82 B` | string |
| `categoryList.rows[0].<volumeChangePercentage24h>` | `-17.88%` | string |
| `categoryList.rows[0].<volumeWeightedPricePerfVsCryptoMarketCap24h>` | `+2.25%` | string |
| `categoryList.rows[0].<volumeWeightedPricePerfVsCryptoMarketCap7d>` | `+1.57%` | string |
| `categoryList.rows[0].<volumeWeightedPricePerfVsCryptoMarketCap30d>` | `-2.89%` | string |
| `categoryList.rows[0].<socialKeywords>` | `['BTC', 'Bitcoin', 'Accumulation', 'Blockchain', 'CPI', 'Price', 'Support', 'Resistance...` | array |
| `categoryList.rows[0].<socialKeywordUniqueAuthorCount>` | `39` | string |
| `categoryList.rows[0].<topCoinList>` | `{'headers': ['coinSymbol', 'coinName', 'coinCmcUrl', 'priceChangePercent7d'], 'rows': [...` | object |

## search_cryptos

Args used: `{"query": "bitcoin", "limit": 5}` — dump: `docs/gate0/search_cryptos.json` — 5 entries

| field path | example value | type |
|---|---|---|
| `[0].id` | `1` | number(int) |
| `[0].name` | `Bitcoin` | string |
| `[0].symbol` | `BTC` | string |
| `[0].slug` | `bitcoin` | string |
| `[0].rank` | `1` | number(int) |

## search_crypto_info

Args used: `{"prompt": "funding rate", "id": "1"}` — dump: `docs/gate0/search_crypto_info.json` — 4 entries

| field path | example value | type |
|---|---|---|
| `cryptoList.headers` | `["url", "title", "content"]` | array[string] |
| `cryptoList.rows[0].<url>` | `https://bitcointalk.org/index.php?topic=5556715.0` | string |
| `cryptoList.rows[0].<title>` | `Before Bitcoin hits 1 000 000 usd, it falls below 10 000 usd` | string |
| `cryptoList.rows[0].<content>` | `(OP) Jr. Member   Offline Activity: 68 Merit: 6 * * * First reason: Bitcoin price is no...` | string |

## get_upcoming_macro_events

Args used: `{}` — dump: `docs/gate0/get_upcoming_macro_events.json` — 6 entries

| field path | example value | type |
|---|---|---|
| `upcomingEventNews.headers` | `["title", "content", "url", "eventDate", "originalNewsContent"]` | array[string] |
| `upcomingEventNews.rows[0].<title>` | `SEC Decision Deadline for Grayscale ETF Options Proposal` | string |
| `upcomingEventNews.rows[0].<content>` | `The SEC must approve or disapprove the NYSE American proposal to list options on the Gr...` | string |
| `upcomingEventNews.rows[0].<url>` | `https://news.bitcoin.com/sec-opens-proceedings-on-nyse-proposal-to-list-grayscale-crypt...` | string |
| `upcomingEventNews.rows[0].<eventDate>` | `11 July 2026` | string |
| `upcomingEventNews.rows[0].<originalNewsContent>` | `The SEC has initiated proceedings to review NYSE American LLC’s proposal to list option...` | string |
