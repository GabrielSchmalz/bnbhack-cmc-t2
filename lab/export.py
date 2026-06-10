"""Export ClickHouse series → committed lab CSVs (data/lab/).

Run once (or to refresh): `uv run python -m lab.export`.
The backtest lab never touches ClickHouse — it reads these committed CSVs
(PR-9). All queries go through lab.ch.query, which hardcodes readonly=1.
"""

import csv
from pathlib import Path

from lab.ch import query

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "lab"

# Exact SQL per the build plan (Task 0.5). bands filter on run_version, never tf alone.
EXPORTS: dict[str, tuple[list[str], str]] = {
    "bars_4h.csv": (
        ["open_time", "open", "high", "low", "close", "volume"],
        "SELECT open_time, open, high, low, close, volume FROM default.binance_klines "
        "WHERE symbol='BTCUSDT' AND interval='4h' AND open_time >= '2020-01-01' "
        "ORDER BY open_time",
    ),
    "oi_bybit.csv": (
        ["ts", "open_interest"],
        "SELECT ts, open_interest FROM default.oi_snapshots "
        "WHERE symbol='BTCUSDT' AND venue='bybit' ORDER BY ts",
    ),
    "ls_bybit.csv": (
        ["ts", "long_short_ratio"],
        "SELECT ts, long_short_ratio FROM default.long_short_snapshots "
        "WHERE symbol='BTCUSDT' AND venue='bybit' ORDER BY ts",
    ),
    "dvol.csv": (
        ["ts", "close"],
        "SELECT ts, close FROM default.deribit_dvol ORDER BY ts",
    ),
    "bands_rm17.csv": (
        ["bar_ts", "region_id"],
        "SELECT bar_ts, region_id FROM default.regime_matrix_labels "
        "WHERE run_version='rm17-derivs-4h-20260530' ORDER BY bar_ts",
    ),
    "liq_events.csv": (
        ["ts", "side", "usd_notional", "cascade"],
        "SELECT ts, side, usd_notional, cascade FROM default.liquidation_events "
        "WHERE symbol='BTCUSDT' ORDER BY ts",
    ),
}


def export_all(out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, (header, sql) in EXPORTS.items():
        rows = query(sql)
        path = out_dir / name
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        first = rows[0][0] if rows else "—"
        last = rows[-1][0] if rows else "—"
        print(f"{name}: {len(rows)} rows, {first} → {last}")


if __name__ == "__main__":
    export_all()
