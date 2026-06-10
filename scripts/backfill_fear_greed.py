"""Fear & Greed backfill (plan Task 0.4).

Primary source: CMC Pro REST ``GET /v3/fear-and-greed/historical`` (the
identical source the shipped Skill reads live). Paginated with ``start``
(1-based) and ``limit<=500``; auth header ``X-CMC_PRO_API_KEY`` from the
``CMC_MCP_API_KEY`` env var (never printed).

Decision rule (pre-registered, PR-2 / Task 0.4): record the EARLIEST date the
CMC series reaches. If earliest > 2025-04-03 (full-stack window start), fetch
alternative.me's full history, compute same-day |CMC - alternative.me| stats
over the overlap, and:
  - median |delta| > 5 points  -> recommend DROP F&G from the Feature list
    (source mismatch too large to claim equivalence); CSV ships CMC-only.
  - otherwise                  -> splice: alternative.me rows for the pre-CMC
    span, CMC rows from CMC's earliest date on, with a ``source`` column.

Outputs:
  - data/backfill/fear_greed.csv          (date_utc,value,source)
  - data/backfill/fg_source_decision.txt  (span + decision + overlap stats)

Run:  uv run --env-file .env python scripts/backfill_fear_greed.py
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

CMC_URL = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical"
ALT_URL = "https://api.alternative.me/fng/?limit=0&format=json"
PAGE_LIMIT = 500
FULL_STACK_START = date(2025, 4, 3)  # PR-1 full-stack window start
MEDIAN_DELTA_DROP_THRESHOLD = 5.0  # points; pre-registered in plan Task 0.4

REPO = Path(__file__).resolve().parents[1]
OUT_CSV = REPO / "data" / "backfill" / "fear_greed.csv"
OUT_DECISION = REPO / "data" / "backfill" / "fg_source_decision.txt"


def _to_date_utc(ts: str | int) -> date:
    """CMC/alternative.me timestamps: unix seconds (string) or ISO-8601."""
    s = str(ts)
    if s.isdigit():
        return datetime.fromtimestamp(int(s), tz=timezone.utc).date()
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).date()


def fetch_cmc(session: requests.Session, api_key: str) -> dict[date, int]:
    """Paginate the CMC F&G historical endpoint; newest-first pages."""
    out: dict[date, int] = {}
    start = 1
    while True:
        r = session.get(
            CMC_URL,
            params={"start": start, "limit": PAGE_LIMIT},
            headers={"X-CMC_PRO_API_KEY": api_key},
            timeout=60,
        )
        r.raise_for_status()
        batch = r.json().get("data") or []
        for row in batch:
            d = _to_date_utc(row["timestamp"])
            out.setdefault(d, int(row["value"]))
        if len(batch) < PAGE_LIMIT:
            break
        start += PAGE_LIMIT
        time.sleep(0.3)
    return out


def fetch_alternative_me(session: requests.Session) -> dict[date, int]:
    r = session.get(ALT_URL, timeout=60)
    r.raise_for_status()
    out: dict[date, int] = {}
    for row in r.json()["data"]:
        out.setdefault(_to_date_utc(row["timestamp"]), int(row["value"]))
    return out


def overlap_stats(cmc: dict[date, int], alt: dict[date, int]) -> dict[str, float]:
    common = sorted(set(cmc) & set(alt))
    deltas = [abs(cmc[d] - alt[d]) for d in common]
    if not deltas:
        return {"n_overlap_days": 0}
    deltas_sorted = sorted(deltas)
    p90 = deltas_sorted[min(len(deltas_sorted) - 1, int(round(0.90 * (len(deltas_sorted) - 1))))]
    return {
        "n_overlap_days": len(deltas),
        "overlap_start": common[0].isoformat(),
        "overlap_end": common[-1].isoformat(),
        "mean_abs_delta": round(statistics.fmean(deltas), 3),
        "median_abs_delta": float(statistics.median(deltas)),
        "p90_abs_delta": float(p90),
        "max_abs_delta": float(max(deltas)),
        "pct_within_5": round(100.0 * sum(d <= 5 for d in deltas) / len(deltas), 2),
    }


def main() -> int:
    api_key = os.environ.get("CMC_MCP_API_KEY")
    if not api_key:
        print("ERROR: CMC_MCP_API_KEY not set (source .env)", file=sys.stderr)
        return 1

    session = requests.Session()
    cmc = fetch_cmc(session, api_key)
    if not cmc:
        print("ERROR: CMC returned no Fear & Greed rows", file=sys.stderr)
        return 1
    cmc_earliest, cmc_latest = min(cmc), max(cmc)
    print(f"CMC F&G span: {cmc_earliest} -> {cmc_latest} ({len(cmc)} days)")

    decision_lines = [
        "Fear & Greed source decision (plan Task 0.4, pre-registered rule)",
        f"generated_utc: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"cmc_span: {cmc_earliest} -> {cmc_latest} ({len(cmc)} days)",
        f"full_stack_window_start: {FULL_STACK_START}",
    ]

    rows: list[tuple[date, int, str]]
    if cmc_earliest <= FULL_STACK_START:
        decision = (
            "CMC-ONLY: CMC series reaches "
            f"{cmc_earliest} <= {FULL_STACK_START}; no fallback needed. "
            "Single source (R-SRC) across train+OOS; identical to what the "
            "shipped Skill reads live."
        )
        rows = [(d, v, "cmc") for d, v in sorted(cmc.items())]
        decision_lines += [
            "fallback_triggered: no",
            "overlap_stats: n/a (fallback branch not triggered)",
        ]
    else:
        print(f"CMC earliest {cmc_earliest} > {FULL_STACK_START}: fetching alternative.me")
        alt = fetch_alternative_me(session)
        stats = overlap_stats(cmc, alt)
        decision_lines += ["fallback_triggered: yes"] + [
            f"{k}: {v}" for k, v in stats.items()
        ]
        median_delta = stats.get("median_abs_delta", float("inf"))
        if stats.get("n_overlap_days", 0) == 0 or median_delta > MEDIAN_DELTA_DROP_THRESHOLD:
            decision = (
                f"DROP F&G: median same-day |CMC - alternative.me| = {median_delta} "
                f"> {MEDIAN_DELTA_DROP_THRESHOLD} points over the overlap — source "
                "mismatch too large to claim equivalence. F&G must be dropped from "
                "the Feature list (Gate-0 freeze doc to record this). CSV ships "
                "CMC-only rows as evidence."
            )
            rows = [(d, v, "cmc") for d, v in sorted(cmc.items())]
        else:
            decision = (
                f"SPLICE: median same-day |CMC - alternative.me| = {median_delta} "
                f"<= {MEDIAN_DELTA_DROP_THRESHOLD} points — sources equivalent. "
                f"alternative.me rows for dates < {cmc_earliest}, CMC rows from "
                f"{cmc_earliest} on; per-row source column records provenance."
            )
            rows = [
                (d, v, "alternative.me") for d, v in sorted(alt.items()) if d < cmc_earliest
            ] + [(d, v, "cmc") for d, v in sorted(cmc.items())]

    decision_lines += [f"decision: {decision}"]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w") as f:
        f.write("date_utc,value,source\n")
        for d, v, src in rows:
            f.write(f"{d.isoformat()},{v},{src}\n")
    OUT_DECISION.write_text("\n".join(decision_lines) + "\n")

    print(f"wrote {OUT_CSV} ({len(rows)} rows)")
    print(f"wrote {OUT_DECISION}")
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
