#!/usr/bin/env bash
# Layer-2 proof for the draw-parallel calibration flag (design Phase 1,
# docs/plans/2026-06-12-cal-fast-sketch.md, amendment B9): re-run one
# COMPLETED lane W-B calibration cell with W_NULL_FAST=1 AND W_CAL_JOBS
# into a SCRATCH out-root and byte-diff its sweep_results_w.json against
# the cell of record. The combined-flags run attributes cleanly: the
# committed P-BTC_5bps reference already carries the proven W_NULL_FAST
# byte-identity (commits 4575ab6/d39e119/dd1f068), so any difference here
# is the new flag's by definition.
#
#   scripts/prove_cal_fast.sh [ASSET] [RUNG] [JOBS]   # default BTC 5 6
#
# JOBS drives BOTH pools: --jobs (the registered 29(g) variant pool) and
# W_CAL_JOBS (the calibration pool under proof). The cell of record
# (artifacts/w/calibration/P-<ASSET>_<RUNG>bps/) is an INPUT here — never
# written. The scratch root must live outside the repo's artifacts/ tree
# (guarded below, extending lab/calibration_w.py's
# _assert_isolated_out_dir discipline to every artifact dir). The rerun
# is for proof only; lane W-B's registered claim ("UNMODIFIED
# run_w_sweep") stays attached to the committed cells, and production
# runs keep W_CAL_JOBS unset until a future lane's pre-registration cites
# this design + the proof artifacts (B10).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

ASSET="${1:-BTC}"
RUNG="${2:-5}"
JOBS="${3:-6}"
SCRATCH="${CAL_FAST_SCRATCH:-$(mktemp -d /tmp/cal_fast_proof.XXXXXX)}"

case "$(readlink -f "$SCRATCH")" in
  "$REPO"/artifacts*)
    echo "[prove] REFUSED: scratch root $SCRATCH resolves inside" \
         "$REPO/artifacts — proof reruns never write artifact dirs" >&2
    exit 2;;
esac

REF="artifacts/w/calibration/P-${ASSET}_${RUNG}bps/sweep_results_w.json"
if [ ! -f "$REF" ]; then
  echo "[prove] missing cell of record: $REF" >&2
  exit 1
fi

UV=uv
command -v uv >/dev/null 2>&1 || UV=/home/arista/.local/bin/uv

echo "[prove] P-${ASSET} ${RUNG}bps -> scratch $SCRATCH (jobs $JOBS," \
     "W_CAL_JOBS $JOBS)"
echo "[prove] start $(date -u +%FT%TZ)"
W_NULL_FAST=1 W_CAL_JOBS="$JOBS" "$UV" run --no-sync python -u \
  -m lab.calibration_w \
  --asset "$ASSET" --rung "$RUNG" --jobs "$JOBS" --out-root "$SCRATCH"
echo "[prove] end $(date -u +%FT%TZ)"

OUT="$SCRATCH/P-${ASSET}_${RUNG}bps/sweep_results_w.json"
if cmp "$OUT" "$REF"; then
  echo "[prove] BYTE-IDENTICAL: cmp silent for $OUT vs $REF"
else
  echo "[prove] BYTE DIFFERENCE — a twin bug by definition (design" \
       "Phase 1 proof bar)" >&2
  exit 1
fi
