"""CG daily-OI export for BTC + registered stamp-semantics determination.

Widening pre-registration §2 ("Daily-OI loader", R-SRC row
`oi_chg_24h_daily`) / recon §1 (BTC daily OI row). Read-only SELECTs via
lab.ch (readonly=1 is structural); the lab itself runs from the committed
CSV this script writes.

The source table `default.cg_oi_history` stores daily OI **candles**
(open_oi/high_oi/low_oi/close_oi per stamp). The registration requires a
single daily value (ts, oi) plus a pre-OOS determination of stamp
semantics (00:00 snapshot vs day-close), cross-checked against the
overlapping bybit daily snapshots (`data/lab/oi_bybit.csv`, daily-snapshot
era 2025-04 -> 2026-04). The determination procedure (registered):
correlate day-over-day changes at day offsets {-1, 0, +1}; the offset
maximizing correlation pins whether row D is the D 00:00 snapshot or the
day-D close.

Outputs:
  data/lab/oi_cg_daily_btc.csv          (ts, oi) raw rows, no dedupe
  docs/gate0/OI-CG-STAMP-SEMANTICS.md   determination + numbers

Usage: uv run python scripts/export_oi_cg.py   (CLICKHOUSE_URL from .env;
credentials are never printed — lab.ch strips userinfo from error text).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lab.ch import query  # noqa: E402

CSV_PATH = REPO_ROOT / "data" / "lab" / "oi_cg_daily_btc.csv"
DOC_PATH = REPO_ROOT / "docs" / "gate0" / "OI-CG-STAMP-SEMANTICS.md"
BYBIT_CSV = REPO_ROOT / "data" / "lab" / "oi_bybit.csv"

EXCHANGE = "Binance"
SYMBOL = "BTCUSDT"

# Registered facts for the frozen series (recon §1): the export must
# reproduce them exactly or fail loudly.
EXPECTED_ROWS = 2286
EXPECTED_FIRST = pd.Timestamp("2020-02-27 00:00:00")
EXPECTED_LAST = pd.Timestamp("2026-05-18 00:00:00")
EXPECTED_GAPS = {
    pd.Timedelta(days=1): 2259,
    pd.Timedelta(hours=16): 13,
    pd.Timedelta(hours=8): 13,
}

# bybit daily-snapshot era used for the cross-check (task/recon: the
# 5-minute era starts 2026-04; before that the file is daily 00:00 rows).
ERA_START = pd.Timestamp("2025-04-01")
ERA_END = pd.Timestamp("2026-04-01")

OFFSETS = (-1, 0, 1)
MIN_PEAK_CORR = 0.2   # the winning offset must clear this ...
MAX_OFF_CORR = 0.2    # ... and every other offset must stay below it


def confirm_filter_values() -> None:
    """Cheap SELECT DISTINCT: the (exchange, symbol) filter must exist."""
    pairs = query(
        "SELECT DISTINCT exchange, symbol FROM default.cg_oi_history "
        "ORDER BY exchange, symbol"
    )
    print(f"distinct (exchange, symbol) pairs: {pairs}")
    assert (EXCHANGE, SYMBOL) in pairs, (
        f"({EXCHANGE!r}, {SYMBOL!r}) not in cg_oi_history: {pairs}"
    )


def fetch_candles() -> pd.DataFrame:
    """All Binance-BTCUSDT rows: ts + candle open/close (strings kept raw)."""
    rows = query(
        "SELECT ts, open_oi, close_oi FROM default.cg_oi_history "
        f"WHERE exchange='{EXCHANGE}' AND symbol='{SYMBOL}' ORDER BY ts"
    )
    df = pd.DataFrame(rows, columns=["ts_raw", "open_oi_raw", "close_oi_raw"])
    df["ts"] = pd.to_datetime(df["ts_raw"])
    df["open_oi"] = df["open_oi_raw"].astype(float)
    df["close_oi"] = df["close_oi_raw"].astype(float)
    return df


def validate(df: pd.DataFrame) -> dict[str, object]:
    """Pin the registered span/cadence facts; return stats for the doc."""
    assert len(df) == EXPECTED_ROWS, f"{len(df)} rows != {EXPECTED_ROWS}"
    assert df["ts"].is_monotonic_increasing and df["ts"].is_unique
    assert df["ts"].iloc[0] == EXPECTED_FIRST, df["ts"].iloc[0]
    assert df["ts"].iloc[-1] == EXPECTED_LAST, df["ts"].iloc[-1]
    assert (df["ts"].dt.microsecond == 0).all() and (
        df["ts"].dt.second == 0).all() and (df["ts"].dt.minute == 0).all()
    gaps = df["ts"].diff().dropna().value_counts().to_dict()
    assert gaps == EXPECTED_GAPS, f"gap histogram {gaps} != {EXPECTED_GAPS}"
    assert (df["open_oi"] > 0).all() and (df["close_oi"] > 0).all()

    # candle continuity: open(D) vs close(previous row) — evidence the rows
    # are candles whose open is sampled at the stamp boundary
    cont = (df["open_oi"].to_numpy()[1:]
            / df["close_oi"].to_numpy()[:-1] - 1)
    cont_abs = pd.Series(cont).abs()
    n_dup_days = int(df["ts"].dt.normalize().duplicated().sum())
    stats = {
        "n_rows": len(df),
        "n_days": len(df) - n_dup_days,
        "n_dup_days": n_dup_days,
        "cont_median": float(cont_abs.median()),
        "cont_p90": float(cont_abs.quantile(0.9)),
        "cont_max": float(cont_abs.max()),
    }
    print(f"validated: {stats}")
    return stats


def load_bybit_era_chg() -> pd.Series:
    """Day-over-day changes of the bybit daily-snapshot era (00:00 stamps).

    by_chg(D) = snap(D 00:00)/snap(D-1 00:00) - 1 — it covers OI movement
    during UTC day D-1.
    """
    by = pd.read_csv(BYBIT_CSV)
    by["ts"] = pd.to_datetime(by["ts"])
    era = by[(by["ts"] >= ERA_START) & (by["ts"] < ERA_END)]
    s = era.set_index("ts")["open_interest"].astype(float).sort_index()
    # daily-snapshot era guard: pure 00:00 stamps, pure 1-day gaps
    assert (s.index.hour == 0).all() and (s.index.minute == 0).all()
    assert (s.index.to_series().diff().dropna() == pd.Timedelta(days=1)).all()
    return s.pct_change().dropna()


def offset_correlations(df: pd.DataFrame,
                        by_chg: pd.Series) -> dict[str, dict[int, tuple]]:
    """corr(cg_chg(D), by_chg(D+k)) for k in {-1, 0, +1}, both candle cols.

    cg rows are deduped to the last stamp per UTC day first (the loader's
    registered dedupe), then day-over-day pct changes are indexed by the
    stamp's UTC day D. Offset k aligns the CG change stamped D with the
    bybit change stamped D+k.
    """
    day = df["ts"].dt.normalize()
    dedup = df.loc[~day.duplicated(keep="last")].set_index(
        day[~day.duplicated(keep="last")])
    out: dict[str, dict[int, tuple]] = {}
    for col in ("open_oi", "close_oi"):
        chg = dedup[col].pct_change().dropna()
        out[col] = {}
        for k in OFFSETS:
            shifted = chg.copy()
            shifted.index = shifted.index + pd.Timedelta(days=k)
            j = pd.concat(
                [shifted.rename("cg"), by_chg.rename("by")], axis=1).dropna()
            out[col][k] = (float(j["cg"].corr(j["by"])), len(j))
            print(f"{col} offset {k:+d}: corr={out[col][k][0]:+.4f} "
                  f"n={out[col][k][1]}")
    return out


def determine(corrs: dict[str, dict[int, tuple]]) -> None:
    """Assert the registered determination is unambiguous.

    open_oi must peak at offset 0 (row D = D 00:00 snapshot) and close_oi
    at offset +1 (row D = day-D close): stamps are candle-START times.
    """
    for col, want in (("open_oi", 0), ("close_oi", 1)):
        by_off = {k: c for k, (c, _) in corrs[col].items()}
        peak = max(by_off, key=lambda k: by_off[k])
        assert peak == want, f"{col}: peak offset {peak} != {want}: {by_off}"
        assert by_off[peak] >= MIN_PEAK_CORR, f"{col}: weak peak {by_off}"
        assert all(abs(c) < MAX_OFF_CORR
                   for k, c in by_off.items() if k != peak), (
            f"{col}: ambiguous off-peak correlation {by_off}")
    print("determination: stamps are candle-START times; "
          "open_oi(D) = D 00:00 snapshot; close_oi(D) = day-D close")


def write_csv(df: pd.DataFrame) -> None:
    """(ts, oi) with oi = open_oi — the column whose stamp IS the snapshot
    time, making the registered availability rule causal verbatim. Raw
    relay strings are written unmodified (full float fidelity)."""
    lines = ["ts,oi"]
    for ts, raw in zip(df["ts"], df["open_oi_raw"]):
        lines.append(f"{ts:%Y-%m-%d %H:%M:%S},{raw}")
    CSV_PATH.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(df)} rows to {CSV_PATH}")


def write_doc(stats: dict[str, object],
              corrs: dict[str, dict[int, tuple]]) -> None:
    def row(col: str) -> str:
        return " | ".join(
            f"{corrs[col][k][0]:+.4f} (n={corrs[col][k][1]})"
            for k in OFFSETS)

    lines = [
        "# Gate-0 addendum — CG daily-OI stamp semantics (registered "
        "determination)",
        "",
        f"Generated by `scripts/export_oi_cg.py` on "
        f"{datetime.now(timezone.utc):%Y-%m-%d} (pre-OOS-contact). "
        "Registration: widening pre-registration §2 (Daily-OI loader); "
        "recon §1 (BTC daily OI row). Consumer: `lab/oi_cg.py` "
        "(`data/lab/oi_cg_daily_btc.csv`).",
        "",
        "## Question",
        "",
        "The CG relay (`cg_oi_history`, exchange=Binance, symbol=BTCUSDT) "
        "stamps one row per UTC day. Is row D the **D 00:00 snapshot** or "
        "the **day-D close**? The answer pins the loader's availability "
        "rule (registered: day-D value usable at the first 4h bar opening "
        "AFTER the day-D stamp; a 00:00 stamp -> the D 04:00 bar).",
        "",
        "## Schema finding",
        "",
        "The table stores daily OI **candles** "
        "(`open_oi/high_oi/low_oi/close_oi` per stamp), not single "
        "snapshots, so the question becomes: is the stamp the candle "
        "START or END? Continuity check `open_oi(row i) vs close_oi(row "
        f"i-1)`: median |rel diff| = {stats['cont_median']:.5f}, "
        f"p90 = {stats['cont_p90']:.5f}, max = {stats['cont_max']:.5f} "
        "— consecutive candles share their boundary value (the slop is "
        "boundary-sampling jitter), consistent with candles.",
        "",
        "## Registered cross-check (decides it)",
        "",
        "Day-over-day changes of the CG series (deduped to the last stamp "
        "per UTC day, per the registered loader) vs the bybit "
        "daily-snapshot era of `data/lab/oi_bybit.csv` "
        f"({ERA_START:%Y-%m-%d} -> {ERA_END:%Y-%m-%d}, 00:00 snapshots, "
        "different venue but correlated daily OI changes). "
        "`by_chg(D) = snap(D)/snap(D-1) - 1` covers day D-1. Offset k "
        "aligns CG change stamped D with bybit change stamped D+k:",
        "",
        "| CG column | k = -1 | k = 0 | k = +1 |",
        "|---|---|---|---|",
        f"| `open_oi` | {row('open_oi')} |",
        f"| `close_oi` | {row('close_oi')} |",
        "",
        "`open_oi` changes co-move with bybit at **offset 0 only**; "
        "`close_oi` changes at **offset +1 only**. That cross-pattern is "
        "the candle signature:",
        "",
        "- **Determination: the stamp is the candle-START time.** "
        "`open_oi(D)` is the **D 00:00 snapshot**; `close_oi(D)` is the "
        "day-D close (only fully known ~D+1 00:00).",
        "",
        "## Consequences (committed with the loader tests)",
        "",
        "- The export writes `oi = open_oi`: row D of "
        "`data/lab/oi_cg_daily_btc.csv` is the day-D **00:00 snapshot** "
        "(16:00 snapshot on the 13 double-stamp days, see below). The "
        "registered availability rule is therefore causal **verbatim**: "
        "the day-D value becomes usable at the first 4h bar opening "
        "strictly after the day-D stamp (00:00 stamp -> D 04:00 bar; the "
        "13 16:00 stamps -> the D 20:00 bar). A bar opening exactly at "
        "the stamp must NOT see that value (pinned in "
        "`tests/test_oi_cg.py`).",
        "- Using `close_oi` under the stamp-based rule would leak ~24h of "
        "future OI; it is excluded by this determination.",
        "- Staleness > 48h from the stamp -> NaN -> `oi-na` (exactly 48h "
        "is still fresh, frozen `_asof` convention). Frozen tail: last "
        "stamp 2026-05-18 00:00 -> panel bars from **2026-05-20 04:00** "
        "onward are NaN -> `oi-na` (registered §2).",
        "",
        "## Export facts (validated on every run)",
        "",
        f"- rows: {stats['n_rows']} (span {EXPECTED_FIRST:%Y-%m-%d} -> "
        f"{EXPECTED_LAST:%Y-%m-%d}, frozen mirror), "
        f"{stats['n_days']} distinct UTC days after the loader's "
        "last-stamp-per-day dedupe",
        f"- cadence: 2,259 one-day gaps; {stats['n_dup_days']} days in "
        "2026-04 carry an extra 16:00 stamp (13 x 16h + 13 x 8h gaps); "
        "no other cadence",
        "- read-only SELECT export (readonly=1 structural, lab/ch.py); "
        "filter values confirmed via SELECT DISTINCT",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n")
    print(f"wrote determination doc to {DOC_PATH}")


def main() -> int:
    confirm_filter_values()
    df = fetch_candles()
    stats = validate(df)
    corrs = offset_correlations(df, load_bybit_era_chg())
    determine(corrs)
    write_csv(df)
    write_doc(stats, corrs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
