"""Binance USD-M 4h-kline backfills for ETHUSDT and SOLUSDT (W-sweep Bars).

Registered per the widening pre-registration
(docs/plans/2026-06-10-widening-preregistration.md §1 panels, §2 "Bars":
P-ETH/P-SOL use Binance USDⓈ-M futures klines, `fapi/v1/klines` 4h, one
source end-to-end), on the spans verified by
docs/research/2026-06-10-widening-recon.md §1:

  ETHUSDT earliest 2019-11-27 04:00 UTC · SOLUSDT earliest 2020-09-14 04:00
  UTC. Tail capped at open_time 2026-06-09 20:00 UTC — the registered panel
  end, matching the committed BTC bars file.

Unlike `fapi/v1/fundingRate`, this endpoint HONORS startTime=0 (recon §1),
so pagination starts there. Duplicate open_time stamps are dropped
keep-first (D4.1 precedent, lab/dataset.py), and the 4h grid is verified
contiguous with any gaps reported.

Writes data/lab/bars_4h_{eth,sol}.csv in the exact committed bars_4h.csv
format (open_time,open,high,low,close,volume; open_time with .000 ms;
numeric strings trimmed of trailing zeros).

Usage: uv run python scripts/backfill_klines_eth_sol.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
LAB_DIR = REPO_ROOT / "data" / "lab"

BINANCE_URL = "https://fapi.binance.com/fapi/v1/klines"
INTERVAL = "4h"
START_MS = 0          # honored by fapi/v1/klines (recon §1)
LIMIT = 1500          # endpoint max for klines
SLEEP_S = 0.5

FOUR_H_MS = 4 * 3600 * 1000
# Registered panel end (§1): last bar open_time 2026-06-09 20:00 UTC.
END_OPEN_MS = int(
    datetime(2026, 6, 9, 20, tzinfo=timezone.utc).timestamp() * 1000
)

# Recon §1 earliest open stamps — asserted after the fetch.
SYMBOLS: dict[str, dict[str, object]] = {
    "ETHUSDT": {
        "csv": LAB_DIR / "bars_4h_eth.csv",
        "earliest": datetime(2019, 11, 27, 4, tzinfo=timezone.utc),
    },
    "SOLUSDT": {
        "csv": LAB_DIR / "bars_4h_sol.csv",
        "earliest": datetime(2020, 9, 14, 4, tzinfo=timezone.utc),
    },
}


def trim_number(s: str) -> str:
    """Trim a Binance numeric string to the committed bars_4h.csv style.

    "7189.43000000" -> "7189.43", "60755.00000000" -> "60755", "150" -> "150".
    Pure string surgery — never round-trips through float.
    """
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def format_open_time(ts_ms: int) -> str:
    """Format an open_time stamp exactly like bars_4h.csv (with .000 ms)."""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S.000")


def dedupe_klines(rows: list[list]) -> tuple[list[list], int]:
    """Drop duplicate open_time stamps, keep FIRST occurrence (D4.1).

    Returns (kept rows sorted by open_time, number dropped).
    """
    seen: dict[int, list] = {}
    dropped = 0
    for row in rows:
        open_ms = int(row[0])
        if open_ms in seen:
            dropped += 1
            continue
        seen[open_ms] = row
    kept = [seen[k] for k in sorted(seen)]
    return kept, dropped


def fetch_all_klines(symbol: str) -> list[list]:
    """Paginate forward from startTime=0; return raw kline rows to END_OPEN_MS."""
    rows: list[list] = []
    start = START_MS
    calls = 0
    while True:
        resp = requests.get(
            BINANCE_URL,
            params={
                "symbol": symbol,
                "interval": INTERVAL,
                "startTime": start,
                "limit": LIMIT,
            },
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        calls += 1
        if not batch:
            break
        rows.extend(batch)
        last_open = int(batch[-1][0])
        if len(batch) < LIMIT or last_open >= END_OPEN_MS:
            break
        start = last_open + 1
        time.sleep(SLEEP_S)
    rows = [r for r in rows if int(r[0]) <= END_OPEN_MS]
    print(f"{symbol}: fetched {len(rows)} klines (<= panel end) in {calls} calls")
    return rows


def verify_grid(symbol: str, rows: list[list], expected_earliest: datetime) -> None:
    """Assert 4h-grid alignment, recon span, panel end; report any gaps."""
    stamps = [int(r[0]) for r in rows]
    off_grid = [t for t in stamps if t % FOUR_H_MS != 0]
    assert not off_grid, f"{symbol}: {len(off_grid)} open_time stamps off the 4h grid"

    earliest = datetime.fromtimestamp(stamps[0] / 1000, tz=timezone.utc)
    assert earliest == expected_earliest, (
        f"{symbol}: earliest open {earliest:%Y-%m-%d %H:%M} != recon "
        f"expectation {expected_earliest:%Y-%m-%d %H:%M}"
    )
    assert stamps[-1] == END_OPEN_MS, (
        f"{symbol}: last open_time {datetime.fromtimestamp(stamps[-1] / 1000, tz=timezone.utc)} "
        f"!= registered panel end 2026-06-09 20:00 UTC"
    )

    gaps = [
        (prev, nxt)
        for prev, nxt in zip(stamps, stamps[1:])
        if nxt - prev != FOUR_H_MS
    ]
    for prev, nxt in gaps:
        p = datetime.fromtimestamp(prev / 1000, tz=timezone.utc)
        n = datetime.fromtimestamp(nxt / 1000, tz=timezone.utc)
        print(f"{symbol}: GAP {p:%Y-%m-%d %H:%M} -> {n:%Y-%m-%d %H:%M} UTC")
    print(f"{symbol}: 4h-grid gaps: {len(gaps)} (must be 0)")
    assert not gaps, f"{symbol}: 4h grid is not contiguous"


def write_csv(symbol: str, rows: list[list], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["open_time,open,high,low,close,volume"]
    for r in rows:
        # kline row: [open_time, open, high, low, close, volume, ...]
        vals = ",".join(trim_number(str(v)) for v in r[1:6])
        lines.append(f"{format_open_time(int(r[0]))},{vals}")
    csv_path.write_text("\n".join(lines) + "\n")
    first = datetime.fromtimestamp(int(rows[0][0]) / 1000, tz=timezone.utc)
    last = datetime.fromtimestamp(int(rows[-1][0]) / 1000, tz=timezone.utc)
    print(f"{symbol}: wrote {len(rows)} rows to {csv_path}")
    print(f"{symbol}: span {first:%Y-%m-%d %H:%M} -> {last:%Y-%m-%d %H:%M} UTC")


def main() -> int:
    for symbol, cfg in SYMBOLS.items():
        raw = fetch_all_klines(symbol)
        rows, dropped = dedupe_klines(raw)
        print(f"{symbol}: dropped {dropped} duplicate open_time stamps (D4.1)")
        verify_grid(symbol, rows, cfg["earliest"])  # type: ignore[arg-type]
        write_csv(symbol, rows, cfg["csv"])  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    sys.exit(main())
