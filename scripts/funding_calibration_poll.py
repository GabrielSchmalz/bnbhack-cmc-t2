"""Append one paired funding sample: CMC live fields vs Binance BTC anchor.

Freeze-addendum D1: resolves the unit/basis ambiguity of CMC's two global
funding fields by collecting paired observations against Binance REST.
Run ~3x/day via cron until threshold freeze; output feeds
skills/<name>/reference_table.md. Idempotent append; never prints the key.
"""
import csv
import datetime as dt
import json
import pathlib
import sys

import requests

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from mcp_client import McpClient  # noqa: E402

OUT = pathlib.Path(__file__).parent.parent / "data" / "backfill" / "funding_calibration.csv"
COLS = [
    "ts_utc",
    "cmc_deriv_fundingRate_current",          # get_global_crypto_derivatives_metrics, unit-ambiguous string
    "cmc_global_avg_funding_pct",             # get_global_metrics_latest, %-signed string
    "binance_btc_predicted_8h_rate",          # fapi premiumIndex.lastFundingRate (decimal)
    "binance_btc_last_settled_rate",          # fapi fundingRate latest (decimal)
]


def dig(obj, *path):
    for p in path:
        obj = obj[p]
    return obj


def main() -> None:
    # Cron-friendly: on ANY fetch failure append nothing, print one line,
    # exit 1. Never prints the key.
    try:
        c = McpClient()
        c.initialize()

        deriv = json.loads(dig(c.call("get_global_crypto_derivatives_metrics", {}),
                               "result", "content", 0, "text"))
        glob = json.loads(dig(c.call("get_global_metrics_latest", {}),
                              "result", "content", 0, "text"))

        prem = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex",
                            params={"symbol": "BTCUSDT"}, timeout=30).json()
        settled = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                               params={"symbol": "BTCUSDT", "limit": 1}, timeout=30).json()[-1]
    except Exception as e:
        print(f"funding_calibration_poll: fetch failed, nothing appended - "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    row = {
        "ts_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "cmc_deriv_fundingRate_current": dig(deriv, "fundingRate", "current"),
        "cmc_global_avg_funding_pct": dig(glob, "leverage", "funding_rate", "average", "current"),
        "binance_btc_predicted_8h_rate": prem["lastFundingRate"],
        "binance_btc_last_settled_rate": settled["fundingRate"],
    }

    new = not OUT.exists()
    with OUT.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"appended sample at {row['ts_utc']}")


if __name__ == "__main__":
    main()
