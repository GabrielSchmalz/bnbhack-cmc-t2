# Fast cell calibration — design of record for Phase 1 (follow-up to the null-fast kernel)

**Status:** Phase 1 IMPLEMENTED 2026-06-12 (guarded branch + parallel
twin in `lab/sweep_w.py::_cell_calibration`, flag `W_CAL_JOBS`, default
OFF; frozen modules untouched). Grilled before implementation — four
independent adversarial lenses, 29 findings, amendments B1–B13:
`docs/plans/2026-06-12-cal-fast-grill.md`. Proof battery green;
measured results in §5 below. **Phase 2 remains sketch-level and must
NOT be implemented from this document** — it is ungrilled, unpromoted,
and kept here only as the candidate follow-up sketch.
**Prerequisite:** the null-fast kernel (committed `4575ab6`, proofs in
`docs/plans/2026-06-12-null-fast-design.md` + `-grill.md`). This design
inherits its entire constraint frame and proof discipline.

## 1. Why this exists

With `W_NULL_FAST=1` the pooled null is no longer the cost. The proof
rerun of P-BTC_5bps took 1,343.6 s (vs 8,803 s frozen), split TD 333.5,
TE 530.9, TF 123.3, TG 200.1, TH 155.6. Inside each taxonomy block,
after the worker pool finishes the per-variant evaluations,
`sweep_w._cell_calibration` (§8 full-gate calibration, registered 200
draws on the cell's top gated variant) runs **serially in the parent
process while all workers sit idle**.

Measured today (probe: rebuild the real P-BTC_5bps TD cell context,
time `_cell_calibration` un-profiled at a 20-draw prefix, linear ×10 —
valid because per-draw cost is constant by construction):

- TD cell calibration ≈ **260 s of the 333.5 s block — ~78%**
  (1,302 ms/draw; 21 folds × 3 cost rungs = 63 `run_backtest` calls
  per draw).
- cProfile shares within calibration (relative shares from a profiled
  pass; wall numbers above are un-profiled): `engine._extract_trades`
  ≈ **56%** — dominated by ~1.2M per-element datetime boxings
  (`DatetimeIndex.__getitem__`) building trade timestamps, and the
  trades are **discarded at 2 of the 3 rungs** (only `c == 10` feeds
  `_pool_trades`); `_EpisodeShufflesW.__getitem__` ≈ 15% (same
  object-dtype materialization the null kernel bypasses);
  `_restrict` ≈ 7%.

TD's share will not be uniform — TE's calibration pick carries ts6
(slow Python time-stop in `_strategy_w`), TF/TG/TH have far smaller
honest_N — but the shape is clear: the serial calibration is the
dominant remaining term of a fast-null cell. Re-measure per taxonomy
at implementation time.

## 2. Two phases, independently justified

The user-level goal is iteration cadence before 2026-06-21: a 9-cell
chain currently ~3.4 h with the null kernel. Phase 1 is cheap and
near-riskless; Phase 2 has a real proof burden and only proceeds if
Phase 1's result still blocks the cadence.

### Phase 1 — draw-parallel calibration (scheduling only, no numeric change)
### [PROMOTED — design of record, grilled 2026-06-12, amendments B1–B13]

The 200 calibration draws are mutually independent: draw `i` consumes
`shuffles[fold][i]`, runs the same backtests, and contributes one
boolean `verdict.passed`. `passes` is an order-free integer sum;
`full_gate_pass_rate` and `mc_se` are pure functions of `(passes,
n_cal)`. Grill-verified down to the code level: the per-draw body
(`sweep_w.py:537-558`) re-initializes all per-draw containers, has no
`itertools.cycle`, no RNG consumption, no prints, and no shared-state
mutation; `_EpisodeShufflesW.__getitem__` is a pure uncached function
of `i` (all permutation orders drawn at construction,
`hooks_w.py:142`); the one observable side effect on shared state is
pandas 3.0.3 lazily populating `DatetimeIndex._cache` on the fold OOS
indexes — probed value-transparent, pinned by a Layer-1 seam case
(B11). So a fork pool over draw indices is *scheduling only* — a NEW
claim of the amendment-29(g) class (registration §29(g) covers the
VARIANT pool, cited as precedent, not sanction; this pool earns its own
on/off determinism pin via Layers 1–2 below) (B10).

- **Mechanism (B1, B3, B4, B5):** all new code lives in
  `lab/sweep_w.py` (a new lab module is outside the permitted edit
  set). One pure-insertion guarded branch in `_cell_calibration`, the
  `4575ab6` shape, placed strictly AFTER the frozen early return at
  :535 — degenerate cells (n_cal ≤ 0 / no active folds) return the
  frozen dict `{"draws": 0, "full_gate_pass_rate": None, "mc_se":
  None}` verbatim with no pool ever created. A NEW module-level worker
  `_mp_cal_draw` reads a NEW fork-shared global `_CAL_CTX_W` —
  SEPARATE from `_MP_CTX_W`, so the variant pool's reset invariant
  (:746) stays untangled — set immediately before Pool creation and
  reset to `{}` before `_cell_calibration` returns (otherwise
  `del shuffles, null_by_id` at :780 is defeated: ~320 MB of orders
  retained per taxonomy, ~1.6 GB parent growth per cell). The parallel
  twin `_cell_calibration_parallel` duplicates the per-draw body of
  :538-558 VERBATIM — hoisting or refactoring the serial loop is
  forbidden ("default unset ⇒ character-for-character" must survive an
  insertion-only diff) — and carries a coupling note mirroring
  `lab/null_fast.py:40-52`: any edit to the serial body re-opens the
  equivalence claim and the proof battery re-runs. Topology: one fresh
  pool per taxonomy, pool size `min(jobs, n_cal)`, ordered `pool.map`
  with explicit `chunksize=1` (the default chunksize 9 costs ~8%
  makespan and couples to per-draw cost variance; chunksize=1 IPC is
  one int each way, sub-ms vs a ~1.1 s draw); workers return per-draw
  ints only; the worker body stays print-free.
- **Plumbing (B2):** env flag `W_CAL_JOBS` — REQUIRED to be an env var
  read inside `_cell_calibration` after the early return, because the
  edit boundary forbids plumbing a parameter through
  `lab/calibration_w.py` (its `run_calibration_cell` is off-limits and
  intentionally does not forward `calibration_draws`, so Layer 2
  always proves the full 200-draw block). Parsing:
  `jobs = int(os.environ.get("W_CAL_JOBS", "0") or 0)`; non-integer
  values raise loudly (never a silent fallback — A3 spirit); integer
  values ≤ 1 (incl. unset) ⇒ the serial path. The parallel branch
  engages iff `jobs > 1 and n_cal > 1`. **Default unset ⇒ the existing
  serial loop, character-for-character** — mirroring `W_NULL_FAST`'s
  default-OFF posture. Reusing the `workers` arg is disqualified:
  every production invocation already passes `--jobs 6` (auto-enable =
  flag conceptually unset), and the registered docstring scopes
  `workers` to variant evaluation only. When the parallel path
  engages, the PARENT prints one A7-style provenance line per process
  (stdout only) citing this document; the artifact gains no field, no
  key, no whitespace (B6 — structurally enforced by the Layer-2 `cmp`,
  stated here as a constraint).
- **Proof (B7, B8, B9):** Layer 1 in NEW `tests/test_cal_fast.py`
  (mirror existing toy conventions, don't cross-import): (a) direct
  `_cell_calibration` serial-vs-parallel equality on toys incl.
  ts6/vb, all-na/empty-OOS folds, and the early-return toys —
  comparing the ORDERED per-draw verdict vector, not just the summed
  dict, on at least one fixture where `verdict.passed` varies across
  draws (a 0==0 equality is not evidence; committed TG/TH cells prove
  variation exists at production scale, so the real-cell case uses
  the REAL null vector, not the zeroed probe stand-in of §4); (b) toy
  `run_w_sweep` artifact byte-identity: flag off vs on vs
  on+workers=4 vs on+`W_NULL_FAST=1`; (c) a `run_calibration_cell`-
  seam case proving env propagation with zero plumbing; (d) an
  env-gated real-cell prefix test (`W_CAL_FAST_REALPANEL=1`, committed
  pick `P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0`); plus the
  cold-vs-warm `Index._cache` seam case (B11) and a flag-unset
  standing guard (subprocess, `W_CAL_JOBS` scrubbed: no calibration
  pool, no provenance line). Every case monkeypatches `W_CAL_JOBS`
  explicitly. Layer 2: NEW sibling script `scripts/prove_cal_fast.sh`
  — `scripts/prove_null_fast.sh` is NOT edited (it is the committed
  proof procedure the null-fast §9 note refers to) — same discipline
  (scratch-root guard verbatim, committed cell read-only), runs
  `W_NULL_FAST=1 W_CAL_JOBS=N` through `lab.calibration_w` and
  byte-`cmp`s scratch P-BTC_5bps against
  `artifacts/w/calibration/P-BTC_5bps/sweep_results_w.json` (primary
  target: its null-fast byte-identity is already proven, so a
  difference attributes cleanly to the new flag; P-BTC_10bps is an
  optional second target — value sensitivity is carried by the
  per-draw vector test). The equivalence argument is structural
  (independence + order-free reduction), so the battery is small.
- Expected effect at 6 workers: TD block 333.5 → ~117 s; cell
  plausibly ~1,344 → ~500–600 s (~9 min); 9-cell chain ~3.4 h →
  **~1.3–1.5 h**. Verify with measured per-taxonomy numbers.
- Watch items — all three resolved by the grill: (1) pool fork cost
  per taxonomy: do NOT amortize or reuse — measured 64-109 ms per
  pool create/teardown, ~0.5 s across 5 pools/cell vs ~0.2% of one
  taxonomy's calibration; per-cell pooling is ruled out by
  fork-snapshot semantics (shuffles are built and deleted per
  taxonomy, :713-719/:780 — an earlier-forked pool would have to
  pickle ~319 MB of orders per taxonomy), and reusing the still-open
  variant pool is ruled out because it forks before `null_by_id` and
  the top-gated pick exist. (2) Memory: COW measured safe at
  production scale (parent 411 MB, 6 workers dirty 27-49 MB each),
  CONDITIONAL on the `_CAL_CTX_W` reset in B4. (3) No nested pools:
  structural — the variant pool's with-block closes at :743-746
  before `_cell_calibration` runs at :774; defense in depth is free
  (daemonic workers make a nested `mp.Pool()` a loud crash).
- **Consumer census (B12):** `_cell_calibration` has exactly one
  production call site (:774, parent only); the dict shape is pinned
  by `tests/test_sweep_w.py:296` — the twin must return the same keys
  with plain Python types (a numpy-typed value breaks both the pinned
  test and byte identity).
- **File manifest (B13):** MUST TOUCH — `lab/sweep_w.py`,
  `tests/test_cal_fast.py` (new), `scripts/prove_cal_fast.sh` (new),
  `docs/plans/*`. MUST NOT TOUCH — the frozen six;
  `lab/calibration_w.py`; `lab/null_fast.py`;
  `scripts/prove_null_fast.sh`; `scripts/run_w_calibration.sh`;
  existing test files; `artifacts/w/sweep_results_w.json` and
  `artifacts/w/calibration/*` (inputs of record — proof reruns to
  scratch out-roots only); `demo/run_demo.py`; `docs/report/*`.

### Phase 2 — calibration kernel (only if Phase 1 is not enough)
### [NOT PROMOTED — sketch-level only; ungrilled; do NOT implement]

This section remains exactly the pre-grill sketch text. The 2026-06-12
grill covered Phase 1 only; Phase 2 must be grilled and promoted
separately (the null-fast grill Q6 verdict already classes a fast
trade/calibration numeric path as a separate design with its own proof
battery) before any implementation.

Entry criterion: after Phase 1 lands and is proven, the operator
judges the measured chain time still too slow for the remaining
widening-cycle iterations. Otherwise this phase never starts.

Reuse the null-fast machinery where the consumption profile allows:

- **Rungs 5 and 20 are returns-only** — their trades are built and
  discarded, exactly the null path's situation. The existing
  `null_fast` precompute (label codes, `act_by_code`, per-fold OOS
  positions, frozen-expression `r`/`fund` arrays) covers label→w and
  the growth formula; only the per-side cost scalar differs per rung.
  This alone removes roughly two-thirds of the `_extract_trades` cost
  and the shuffle materialization, with the *same class* of
  equivalence argument already proven once.
- **Rung 10 is the hard part**: `shipping_gate_w` consumes the pooled
  trades table (top-5/top-K removal) and `w_parts`. A fast
  `_extract_trades` equivalent needs a **new equivalence proof over a
  DataFrame** (entry/exit timestamps, per-trade returns) — a
  materially bigger battery than scalar Sharpe vectors. Do not bundle
  it with the rungs-5/20 work; it can even be a third, separate
  checkpoint inside Phase 2.
- Expected effect: calibration drops to seconds; combined with
  Phase 1 the chain approaches ~1 h, at which point the per-variant
  guarded evaluations (`_eval_variant_w`) dominate.

### Explicitly out of scope (candidates for a later sketch, measure first)

- `_eval_variant_w`'s discarded trades: per fold it runs 4
  `run_backtest`s and discards trades from 3 of them (unguarded run,
  rungs 5/20). Same returns-only idea applies, but it sits behind
  `apply_dd_guard` (another consumer to study) and is already
  parallelized over variants — lower leverage than the serial
  calibration.
- Pipelining calibration of taxonomy N with the variant pool of
  taxonomy N+1 — scheduling-only in principle, but a real scheduler
  change; Phase 1 captures most of the win without it.

## 3. Constraint frame (inherited verbatim from the null-fast design)

- Frozen six untouched: `lab/engine.py`, `lab/hooks.py`,
  `lab/hooks_w.py`, `lab/rules.py`, `lab/rules_w.py`, `lab/sweep.py`.
- All flags default OFF; unset ⇒ today's code path exactly.
- Bit-identity of the artifact, zero tolerance, proven not argued —
  Layer-1 unit equality + Layer-2 full-cell `cmp` into scratch.
- Committed artifacts (`artifacts/w/sweep_results_w.json`,
  `artifacts/w/calibration/*`) are inputs of record — never rewritten;
  proof reruns to scratch out-roots only.
- Registration posture (resolved by the grill, B10): the calibration
  pool is a NEW claim of the amendment-29(g) class (scheduling-only,
  byte-identical, pinned by its own on/off determinism test) — 29(g)
  itself registers the VARIANT pool only and is precedent, not
  sanction. Production runs keep `W_CAL_JOBS` unset until a future
  lane's pre-registration cites this design + the proof artifacts —
  the same closure path as `W_NULL_FAST`, one posture for both flags
  (they will be cited together by the same lane; the conservative path
  costs nothing since proof reruns are off-production anyway).
- Repo vocabulary per `CONTEXT.md` ("shipping gate" / "full-gate"
  qualified; no bare "signal"/"executor").

## 4. Probe methodology (for re-derivation)

Scratch script (not committed): rebuild the P-BTC 5 bps planted panel
via `build_planted_panel`, mirror `run_w_sweep`'s TD setup
(`_build_fold_ctx`, `episode_shuffles_w` at a 20-draw prefix, committed
calibration pick `P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0`), time
`_cell_calibration(n_cal=20)` un-profiled, then a second profiled pass
for shares only. `null_sharpes` substituted with zeros — timing is
draw-count-invariant, pass rates from the probe are not meaningful.

NOTE (grill, B7): the zeroed-null substitution is valid for TIMING
only. Equality/equivalence tests must NOT use it — with a zeroed null
vector every draw fails the gate's null clause and a serial-vs-parallel
comparison degenerates to 0==0. Layer-1 equality cases use the real
null vector (or a toy where `verdict.passed` varies across draws) and
compare the ordered per-draw verdict vector.

## 5. Phase-1 proof results (recorded 2026-06-12)

**Layer 1** (`tests/test_cal_fast.py`): 19 passed, 1 env-gated skip
(the `W_CAL_FAST_REALPANEL=1` real-cell prefix case). Equality cases
compare the ordered per-draw verdict vector on fixtures where
`verdict.passed` varies across draws (B7); the flag-unset standing
guard (subprocess, `W_CAL_JOBS` scrubbed) confirms no calibration pool
and no provenance line on the default path. Full repo suite:
558 passed, 2 skipped.

**Layer 2** (`scripts/prove_cal_fast.sh BTC 5 6`): re-ran the lane W-B
P-BTC_5bps cell with `W_NULL_FAST=1 W_CAL_JOBS=6` into scratch
(`~/.cache/cal_fast_proof/run1`); `cmp` silent vs the committed
artifact, independently re-run by the operator-side session — both
files sha256
`f08342f090b2857c578de1806cd434a849add27388e71957cc1d0dee093eb545`.
Gate passes 12/81, identical.
Stdout disclosed both provenance lines (null path: fast; calibration
path: parallel).

**Measured effect** (same VPS, `--jobs 6`, full cell): 475.0 s vs
1,343.6 s with the null kernel alone (**2.8×**) and 8,803 s frozen
(**18.5×** combined). Projected 9-cell chain: ~1.2 h vs ~3.4 h
(null-fast only) vs ~26 h (frozen). Note the rerun shared the host
with a concurrent full-suite run for part of its window; 475 s is
therefore an upper bound.

Production posture unchanged: `W_CAL_JOBS` stays unset until a future
lane's pre-registration cites this design + these proof artifacts
(B10), jointly with `W_NULL_FAST`.
