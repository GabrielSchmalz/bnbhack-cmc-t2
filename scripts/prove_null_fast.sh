#!/usr/bin/env bash
# Layer-2 proof for the fast null kernel (design §5,
# docs/plans/2026-06-12-null-fast-design.md): re-run one COMPLETED lane
# W-B calibration cell with W_NULL_FAST=1 into a SCRATCH out-root and
# byte-diff its sweep_results_w.json against the cell of record.
#
#   scripts/prove_null_fast.sh [ASSET] [RUNG] [JOBS]   # default BTC 5 6
#
# The cell of record (artifacts/w/calibration/P-<ASSET>_<RUNG>bps/) is an
# INPUT here — never written. The scratch root must live outside the
# repo's artifacts/ tree (guarded below, extending lab/calibration_w.py's
# _assert_isolated_out_dir discipline to every artifact dir). The rerun
# is for proof only; lane W-B's registered claim ("UNMODIFIED
# run_w_sweep") stays attached to the committed cells.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

ASSET="${1:-BTC}"
RUNG="${2:-5}"
JOBS="${3:-6}"
SCRATCH="${NULL_FAST_SCRATCH:-$(mktemp -d /tmp/null_fast_proof.XXXXXX)}"

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

echo "[prove] P-${ASSET} ${RUNG}bps -> scratch $SCRATCH (jobs $JOBS)"
echo "[prove] start $(date -u +%FT%TZ)"
W_NULL_FAST=1 "$UV" run --no-sync python -u -m lab.calibration_w \
  --asset "$ASSET" --rung "$RUNG" --jobs "$JOBS" --out-root "$SCRATCH"
echo "[prove] end $(date -u +%FT%TZ)"

OUT="$SCRATCH/P-${ASSET}_${RUNG}bps/sweep_results_w.json"
if cmp "$OUT" "$REF"; then
  echo "[prove] BYTE-IDENTICAL: cmp silent for $OUT vs $REF"
else
  echo "[prove] BYTE DIFFERENCE — a kernel bug by definition (design §5)" >&2
  exit 1
fi
