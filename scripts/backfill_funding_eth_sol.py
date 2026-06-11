"""Binance USD-M funding-rate backfills for ETHUSDT and SOLUSDT (W-sweep).

Registered source of record per the widening pre-registration
(docs/plans/2026-06-10-widening-preregistration.md §2, R-SRC: Binance REST
`fapi/v1/fundingRate` end-to-end; SOL stamps snapped to the 8h grid), on the
spans verified by docs/research/2026-06-10-widening-recon.md §1:

  ETHUSDT earliest 2019-11-27 08:00 UTC · SOLUSDT earliest 2020-09-13 16:00
  UTC (with +3..11 ms stamp jitter on the 00/08/16 boundaries).

Recon hazard honored: the endpoint IGNORES startTime=0 and silently returns
the NEWEST page, so pagination walks forward from an explicit realistic
early stamp (2019-01-01 00:00 UTC = 1546300800000 ms).

EMPIRICAL FINDING (this backfill, 2026-06-10; recon §1 missed it): during
the FTX crash week Binance ran SOLUSDT funding on a ~2h interval —
75 genuine OFF-SCHEDULE settlements between 2022-11-09 20:00 and
2022-11-18 06:00 UTC at 02/04/06/10/12/14/18/20/22 stamps (incl. −2%
cap prints). These are real settlements, not stamp jitter, so they are NOT
snapped (round-to-nearest would overwrite the genuine 00/08/16 settled
rates). Policy here: snap only millisecond-level jitter (tolerance 60 s),
EXCLUDE off-schedule settlements from the 8h series, print every excluded
stamp, and assert the resulting 00/08/16 series has no 8h holes. The
registered Feature is `funding_rate_8h` and the execution model accrues
funding only at 00/08/16 UTC (registration §3); the excluded intra-window
accruals are a disclosed limitation, recorded in docs/DATA_PROVENANCE.md.

Writes data/backfill/funding_{ethusdt,solusdt}_binance.csv with columns
funding_time_utc,funding_rate (sorted asc, deduped on the snapped stamp) —
byte-format-identical to the committed BTC backfill
(scripts/backfill_funding.py).

Usage: uv run python scripts/backfill_funding_eth_sol.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKFILL_DIR = REPO_ROOT / "data" / "backfill"

BINANCE_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
# Recon §1: startTime=0 is ignored (newest page returned); 2019-01-01 UTC is
# honored and predates both listings.
START_MS = 1546300800000
LIMIT = 1000
SLEEP_S = 0.5

EIGHT_H_MS = 8 * 3600 * 1000
# "Millisecond-jittered" stamps (recon §1: +3..11 ms observed; ETH shows up
# to ~50 ms) snap to the boundary; anything further off is a genuine
# off-schedule settlement (the real ones sit >= 2h away) and is excluded.
JITTER_TOLERANCE_MS = 60 * 1000

# Recon §1 earliest stamps — asserted after the fetch.
SYMBOLS: dict[str, dict[str, object]] = {
    "ETHUSDT": {
        "csv": BACKFILL_DIR / "funding_ethusdt_binance.csv",
        "earliest": datetime(2019, 11, 27, 8, tzinfo=timezone.utc),
    },
    "SOLUSDT": {
        "csv": BACKFILL_DIR / "funding_solusdt_binance.csv",
        "earliest": datetime(2020, 9, 13, 16, tzinfo=timezone.utc),
    },
}


def snap_to_8h_grid_ms(ts_ms: int) -> int:
    """Snap a millisecond epoch stamp to the nearest 8h UTC boundary.

    SOL fundingTime stamps carry +3..11 ms jitter around the 00/08/16 UTC
    boundaries (recon §1); ETH/BTC stamps are exact. Same rounding as
    scripts/backfill_funding.py.
    """
    return round(ts_ms / EIGHT_H_MS) * EIGHT_H_MS


def fetch_all_funding(symbol: str) -> dict[int, float]:
    """Paginate the Binance endpoint forward; return {8h-grid epoch ms: rate}.

    Stamps within JITTER_TOLERANCE_MS of an 8h boundary snap onto it;
    genuine off-schedule settlements are excluded from the 8h series and
    printed one per line (see module docstring for the SOL FTX-week case).
    """
    out: dict[int, float] = {}
    off_schedule: list[tuple[int, float]] = []
    start = START_MS
    calls = 0
    max_jitter = 0
    while True:
        resp = requests.get(
            BINANCE_URL,
            params={"symbol": symbol, "startTime": start, "limit": LIMIT},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        calls += 1
        if not batch:
            break
        for row in batch:
            raw_ms = int(row["fundingTime"])
            grid_ms = snap_to_8h_grid_ms(raw_ms)
            jitter = abs(raw_ms - grid_ms)
            if jitter > JITTER_TOLERANCE_MS:
                off_schedule.append((raw_ms, float(row["fundingRate"])))
                continue
            max_jitter = max(max_jitter, jitter)
            out[grid_ms] = float(row["fundingRate"])  # dedupe on time: last wins
        last_raw = max(int(row["fundingTime"]) for row in batch)
        if len(batch) < LIMIT:
            break
        start = last_raw + 1
        time.sleep(SLEEP_S)
    print(
        f"{symbol}: fetched {len(out)} on-grid funding stamps in {calls} calls "
        f"(max snapped jitter {max_jitter} ms)"
    )
    print(f"{symbol}: off-schedule settlements excluded from 8h series: "
          f"{len(off_schedule)}")
    for raw_ms, rate in off_schedule:
        dt = datetime.fromtimestamp(raw_ms / 1000, tz=timezone.utc)
        print(f"{symbol}:   excluded {dt:%Y-%m-%d %H:%M:%S}.{raw_ms % 1000:03d} "
              f"UTC rate={rate:.8f}")
    # Exclusion must not punch holes in the 00/08/16 series: during the SOL
    # FTX-week 2h-interval episode the boundary settlements still occurred.
    stamps = sorted(out)
    holes = [
        (a, b) for a, b in zip(stamps, stamps[1:]) if b - a != EIGHT_H_MS
    ]
    for a, b in holes:
        da = datetime.fromtimestamp(a / 1000, tz=timezone.utc)
        db = datetime.fromtimestamp(b / 1000, tz=timezone.utc)
        print(f"{symbol}: HOLE {da:%Y-%m-%d %H:%M} -> {db:%Y-%m-%d %H:%M} UTC")
    print(f"{symbol}: 8h-grid holes: {len(holes)} (must be 0)")
    assert not holes, f"{symbol}: 8h series has holes"
    return out


def write_csv(symbol: str, rates: dict[int, float], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["funding_time_utc,funding_rate"]
    for ts_ms in sorted(rates):
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        lines.append(f"{dt.strftime('%Y-%m-%d %H:%M:%S')},{rates[ts_ms]:.8f}")
    csv_path.write_text("\n".join(lines) + "\n")
    first = datetime.fromtimestamp(min(rates) / 1000, tz=timezone.utc)
    last = datetime.fromtimestamp(max(rates) / 1000, tz=timezone.utc)
    print(f"{symbol}: wrote {len(rates)} rows to {csv_path}")
    print(f"{symbol}: span {first:%Y-%m-%d %H:%M} -> {last:%Y-%m-%d %H:%M} UTC")
    print(f"{symbol}: rate range [{min(rates.values()):.8f}, "
          f"{max(rates.values()):.8f}]")
    off_grid = [t for t in rates if t % EIGHT_H_MS != 0]
    print(f"{symbol}: off-8h-grid stamps after snapping: {len(off_grid)} (must be 0)")
    assert not off_grid, f"{symbol}: stamps must all be 0 mod 8h UTC"


def main() -> int:
    for symbol, cfg in SYMBOLS.items():
        rates = fetch_all_funding(symbol)
        earliest = datetime.fromtimestamp(min(rates) / 1000, tz=timezone.utc)
        expected = cfg["earliest"]
        assert earliest == expected, (
            f"{symbol}: earliest stamp {earliest:%Y-%m-%d %H:%M} != recon "
            f"expectation {expected:%Y-%m-%d %H:%M} — pagination or span drifted"
        )
        write_csv(symbol, rates, cfg["csv"])  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    sys.exit(main())
