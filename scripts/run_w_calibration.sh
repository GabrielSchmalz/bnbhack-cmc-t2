#!/usr/bin/env bash
# Lane W-B: planted-edge power calibration chain (registration §9).
#
# Nine cells SEQUENTIALLY — (P-BTC, P-ETH, P-SOL) x (5, 10, 25 bps/bar) —
# each one UNMODIFIED run_w_sweep on the planted panel via
# lab/calibration_w.py, --jobs 6, registered draws (1000 / 200 cal).
# Output per cell: artifacts/w/calibration/P-<ASSET>_<rung>bps/
# sweep_results_w.json. The committed artifacts/w/sweep_results_w.json is
# never written (guarded in lab/calibration_w.py).
#
# Resumable: a cell whose results file already exists is skipped, so a
# systemd Restart=on-failure re-run resumes at the first unfinished cell.
# All progress appends to /tmp/w_cal_run.log.
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1
LOG=/tmp/w_cal_run.log
exec >>"$LOG" 2>&1

UV=uv
command -v uv >/dev/null 2>&1 || UV=/home/arista/.local/bin/uv

echo "[w-cal] chain start $(date -u +%FT%TZ) pid=$$ repo=$REPO"
fail=0
for asset in BTC ETH SOL; do
  for rung in 5 10 25; do
    dir="artifacts/w/calibration/P-${asset}_${rung}bps"
    if [ -f "$dir/sweep_results_w.json" ]; then
      echo "[w-cal] skip P-${asset} ${rung}bps (results present)"
      continue
    fi
    echo "[w-cal] start P-${asset} ${rung}bps $(date -u +%FT%TZ)"
    if "$UV" run --no-sync python -u -m lab.calibration_w \
        --asset "$asset" --rung "$rung" --jobs 6; then
      echo "[w-cal] done P-${asset} ${rung}bps $(date -u +%FT%TZ)"
    else
      rc=$?
      echo "[w-cal] FAIL P-${asset} ${rung}bps rc=$rc $(date -u +%FT%TZ)"
      fail=1
    fi
  done
done
echo "[w-cal] chain end $(date -u +%FT%TZ) fail=$fail"
exit "$fail"
