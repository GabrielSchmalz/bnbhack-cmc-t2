# Fast cell calibration (Phase 1) — autonomous grill of the sketch

**Subject:** `docs/plans/2026-06-12-cal-fast-sketch.md`, **Phase 1 only**
(draw-parallel calibration). Phase 2 (calibration kernel) was NOT
grilled and remains sketch-level; nothing here promotes it.
**Mode:** autonomous grill — four independent adversarial lenses
(bit-identity of the reduction; fork/pool mechanics; scope and
registration posture; completeness), every branch closed in writing with
evidence, no human in the loop.
**Date:** 2026-06-12. Environment snapshot for every verdict below:
pandas 3.0.3, numpy 2.4.6, `bottleneck` NOT installed, `numexpr` NOT
installed, pandas `nanops._USE_BOTTLENECK=False` (checked in the repo
venv) — sharpe/mean/std run plain numpy pairwise reductions,
single-threaded deterministic; `uv.lock` pins all of it.

Probe scripts: `~/.cache/calfast_probe/` (scratch; probes P1–P5, probe2–
probe4, probe_pool — toy and real planted P-BTC 5 bps TD cell contexts).
Load-bearing checks are re-expressed as standing tests in the Layer-1
battery this grill mandates (B7/B8). No probe wrote under
`$REPO/artifacts`.

Verdict tally: 29 findings (Q1–Q29) — 12 hold, 16 hold-with-amendment,
1 broken (Q23, the "extend prove_null_fast.sh" option) which is
**resolved by amendment B9** (sibling script). Promotion proceeds.

---

## Lens A — bit-identity of the reduction

### Q1. Cross-draw state inside `_cell_calibration`'s per-draw body

**Grilling.** `lab/sweep_w.py:537-558`: `segs`/`trades_list`/`w_parts`
are constructed INSIDE `for i in range(n_cal)`; the only cross-draw
accumulator is the int `passes`. All other inputs (bars, funding,
hodl_r10, null_sharpes, pooled_oos_idx, fold_oos_idx, covered_folds,
`fc["hot"]`, `fc["labels"]`) are fixed before the loop. No
`itertools.cycle` (unlike `_null_sharpes_w:275` — calibration uses
`fc["hot"]` directly per fold, order-free). Probe (toy TD cell, 24
draws, plain/ts6/vb variants): reversed draw order produced hex-exact
per-draw verdict stats (P3 True x3); running `_cell_calibration` twice
on the same shared objects returned identical dicts (P1 True x3).

**Verdict: holds.** Draw `i` is a pure function of `i` and the fixed
inputs; no required change.

### Q2. `_EpisodeShufflesW`: lazy `__getitem__` mutation / RNG consumption

**Grilling.** `lab/hooks_w.py:142`: all permutation orders are drawn
from the registered rng AT CONSTRUCTION
(`orders = [rng.permutation(...) for _ in range(n)]`) — no RNG state is
consumed in `__getitem__`, so draw `i` is a pure function of `i`
regardless of access order. `hooks_w.py:97-110`: `__getitem__` does
`self._base.copy()` and builds a fresh `pd.Series`; `__slots__` (71-74)
has no cache slot, nothing is memoized or mutated. Probe P5: `s[5]`
accessed before vs after `s[20]`/`s[0]` — element-identical Series.

**Verdict: holds.** Workers can index any draw subset in any order.

### Q3. `shipping_gate_w` purity per draw (incl. frozen gate/hooks it delegates to)

**Grilling.** `lab/gate_w.py:119` `np.asarray(null_sharpes, dtype=float)`
rebinds, never mutates; clauses build only fresh objects;
`lab/gate.py:32-57` pure; `lab/hooks.py:71-79` top_n_removal pure
(boolean-mask copy + nlargest, non-mutating). The ONLY shared-input
change the probes caught: pandas 3.0.3 lazily populates
`DatetimeIndex._cache` with `{_as_range_index, _can_use_libjoin}` on the
fold OOS indexes during the first `Index.intersection` (probe3: cache
keys grow, freq unchanged, `asi8` values bit-equal; probe2:
`fold_oos_idx` pickle_same=False, values_same=True — every other input
pickle-stable). Cold-vs-warm fresh-process probe (probe4): draw 7
computed first-thing vs after draws 0–6 — full hex-encoded stats blob
identical, so the cache is value-transparent.

**Verdict: holds, with amendment (B11 + B7).** The design records the
pandas `Index._cache` observation explicitly (it is the one observable
side effect of the draw body on shared state) and the Layer-1 battery
gains one cold-vs-warm-cache seam case (compute draw k in a fresh
process vs after a prefix, compare exact).

### Q4. Order-free reduction: `passes` sum, `full_gate_pass_rate`, `mc_se`

**Grilling.** `lab/sweep_w.py:558-562`: `passes += int(verdict.passed)`
is exact integer arithmetic (commutative, no float accumulation);
`rate = passes/n_cal` and `mc_se = sqrt(rate*(1-rate)/n_cal)` are pure
functions of two ints computed in the parent either way. Probe P4b:
reconstructing the dict from per-draw booleans (sum of ints) equals the
serial `_cell_calibration` return exactly for all three variant classes.
Returning per-draw ints through `Pool.map` is pickle-exact (no float
payload need cross the pipe at all).

**Verdict: holds.**

### Q5. Fork-pool float identity vs parent (BLAS threading, env, library state)

**Grilling.** Measured in the uv venv: numpy 2.4.6, pandas 3.0.3,
numexpr ABSENT, bottleneck ABSENT — sharpe/mean/std run plain numpy
pairwise reductions, single-threaded deterministic. The draw body
contains no BLAS-routed op (`engine.py:96-115` is elementwise
mul/cumprod/sum; `np.quantile` is sort-based; no dot/gemm anywhere).
fork inherits memory+env exactly. Direct probe P4: 4-worker fork pool vs
parent serial, hex-exact per-draw stats for plain/ts6/vb (True x3). Repo
precedent carries over: `tests/test_sweep_w.py:126`
`test_parallel_byte_identical_to_serial` pins workers=1 == workers=4
artifact bytes for the variant pool, and the committed P-BTC_5bps cell
(produced `--jobs 6`) matched the null-fast Layer-2 rerun byte-for-byte;
artifact of record verified intact now (sha256 f08342f0…e545).

**Verdict: holds.**

### Q6. Carry-over of the `_MP_CTX_W` pattern; no nested pools; empty-cell edge

**Grilling.** `lab/sweep_w.py:743-746`: the variant pool's
`with mp.Pool(...)` block closes and `_MP_CTX_W = {}` is reset BEFORE
`_cell_calibration` is called at line 774 — a calibration pool is
non-nested by construction (sketch watch item confirmed structurally).
But the sketch's "same fork-shared-context pattern as `_MP_CTX_W`" needs
concretization: `_MP_CTX_W` is empty at calibration time, so the
calibration pool must set its own module-global context around its Pool.
The draw body also prints nothing (`sweep_w.py:537-558`), so worker
stdout cannot perturb the byte-deterministic artifact (written only in
the parent, line 857).

**Verdict: holds, with amendment (B1/B3/B4/B5).** (a) calibration pool
uses its own fork-shared context global (`_CAL_CTX_W`) set immediately
before Pool creation and cleared after (W_NULL_FAST-style guarded branch
in `sweep_w.py` only); (b) the early return at `sweep_w.py:533-535`
(n_cal<=0 / no active folds) is preserved before any pool is created;
(c) pool size `min(jobs, n_cal)`; (d) workers return per-draw ints only.

---

## Lens B — fork/pool mechanics

### Q7. Fork cost per pool vs the ~45 s payload ("amortize or reuse" watch item)

**Grilling.** Scratch probe (`probe_pool.py`, real planted P-BTC 5 bps
TD context, parent RSS 411 MB): `mp.get_context("fork").Pool(6)`
create=64-84 ms, create+first-roundtrip=67-85 ms, create+teardown=
92-109 ms, stable across 5 repetitions (mimicking 5 pools/cell). Serial
calibration measured 1,094-1,172 ms/draw (3- and 12-draw runs; the
sketch's own probe said 1,302 ms/draw under load) → per-taxonomy
parallel payload at 6 workers ~37-45 s. Five pool create/teardowns per
cell total ~0.5 s, i.e. ~0.2% of the TD calibration alone.

**Verdict: holds.** The watch item resolves as: **do not amortize** — a
fresh pool per taxonomy is measured noise (B3).

### Q8. Memory: shuffles dict + panel inherited COW

**Grilling.** Measured on the real TD context at production draws=1000:
orders arrays sum 318.7 MB + base object-pointer arrays 2.3 MB across 21
folds; parent RSS 411 MB (private_dirty 380 MB) once shuffles exist.
After forking 6 workers and running 12 calibration draws (chunksize=1),
per-worker Private_Dirty was only 27-49 MB (smaps_rollup read inside
each worker) — the 318 MB orders list is NOT bulk-dirtied because each
worker refcount-touches only the order arrays of its own draws. Parent
RSS after pool close: 414 MB. Worst case ~411 MB + 6×~50 MB on a 32 GB
box — same regime the variant pool already runs in (`sweep_w.py:609-611`
COW comment).

**Verdict: holds, with amendment (B4).** `_CAL_CTX_W` MUST be reset to
`{}` before `_cell_calibration` returns, mirroring `_MP_CTX_W`'s reset
at `sweep_w.py:746`. If it retains a reference, the frozen-style memory
hygiene `del shuffles, null_by_id` at `sweep_w.py:780` is defeated:
~320 MB of orders per taxonomy stays live, the parent grows ~1.6 GB
across a 5-taxonomy cell and every later fork inherits dirtier state.

### Q9. Pool once per cell vs one pool per taxonomy (5/cell)

**Grilling.** Per-taxonomy is structurally forced, not just preferred:
shuffles are constructed inside the taxonomy loop (`sweep_w.py:713-719`)
and deleted at :780, so a pool forked once per cell snapshots the heap
BEFORE any later taxonomy's shuffles exist — fork COW only shares what
existed at `Pool()` time. A per-cell pool would therefore need ~319 MB
of orders pickled per taxonomy's tasks — the exact cost the `_MP_CTX_W`
pattern exists to avoid (:609-611). The saving from amortizing would be
~0.4 s/cell. Reusing the still-open variant pool is also wrong: it forks
at :743 before `null_by_id` and the top-gated pick exist (:770-777), so
`null_sharpes` would need per-task pickling and the two pools' lifetimes
would couple for a ~0.1 s saving.

**Verdict: holds.** The sketch's "pool over `range(n_cal)`" per taxonomy
is the correct topology; the design records that per-cell pooling is
**ruled out by fork-snapshot semantics**, not by taste (B3).

### Q10. Chunking 200 draws across 6 workers

**Grilling.** CPython `Pool._map_async` default:
`chunksize, extra = divmod(200, 6*4) = (8, 8)` → chunksize 9 (verified
against the installed interpreter via `inspect.getsource`). That yields
23 chunks of ~9.9 s each (at 1.1 s/draw); with dynamic dispatch 5
workers run a 4th chunk → makespan ~39.4 s vs 36.5 s ideal (~+8%),
worse if per-draw cost varies (TE's committed pick
`P-BTC-DIR-TE-E2-follow_unwind_sym-0.5-ts6` carries the slow Python
time-stop). With chunksize=1: makespan = ceil(200/6)=34 draws ~37.2 s
(~+2%); per-task IPC is one int arg + one int return, sub-ms vs a 1.1 s
draw (probe: 12 draws × 6 workers at chunksize=1 ran 3.0 s incl.
~0.08 s pool startup, 4.37x over serial 13.1 s at only 2 draws/worker).

**Verdict: holds, with amendment (B3).** Pass explicit `chunksize=1` to
`pool.map`; do not accept the default. Keep `pool.map` (ordered) rather
than `imap_unordered` — the sum is order-free either way, but `map`
keeps the structural-equivalence argument one sentence long.

### Q11. n_cal=0 / no active folds — frozen early return verbatim

**Grilling.** The frozen early return is `lab/sweep_w.py:533-535`:
`active = [...]; if n_cal <= 0 or not active: return {"draws": 0,
"full_gate_pass_rate": None, "mc_se": None}`. `run_w_sweep` guarantees
`n_cal = min(calibration_draws, draws)` (:645) and `_cell_calibration`
has exactly one production call site (:774, parent process only; tests
only read the artifact key, `tests/test_sweep_w.py:296`).

**Verdict: holds, with amendment (B2/B5).** The guarded parallel branch
goes strictly AFTER line 535 so degenerate cells take the frozen dict
verbatim with no pool ever created. Engage only when jobs > 1 and
n_cal > 1; pool size `min(jobs, n_cal)` — mirroring the variant pool's
guards at :726 and :743 (toy cells run n_cal as low as a handful of
draws; 6 idle forks for 2 draws is waste and a new code path for
nothing).

### Q12. Interaction with the variant pool (no nesting)

**Grilling.** The variant pool is a with-block at `sweep_w.py:743-745`
and `_MP_CTX_W` is reset at :746; `_cell_calibration` is called at :774,
after the block exits — the calibration pool can only ever be created
from the parent with zero workers alive. Defense in depth is free: Pool
workers are daemonic, so if a future refactor ever invoked the guarded
branch inside a worker, `mp.Pool()` raises ("daemonic processes are not
allowed to have children") — a loud crash, never silent nesting. The
per-draw body (:537-558) has no prints and no cross-draw state except
`passes`; unlike `_null_sharpes_w` there is no `itertools.cycle` (:275)
— hot masks come from `fc` per fold (:543) — so draw independence is
real at the code level, not just asserted.

**Verdict: holds.** Use a SEPARATE module global (`_CAL_CTX_W`), not
`_MP_CTX_W`, so the :746 reset invariant of the variant pool is never
entangled with the calibration seam (B1).

### Q13. Flag plumbing: `W_CAL_JOBS` env vs reusing the `workers` arg

**Grilling.** Reusing `workers` is disqualified twice over: (a) every
existing production invocation already passes `--jobs 6`
(`sweep_w.py:954-956` default `min(8, cpus)`;
`scripts/prove_null_fast.sh` JOBS default 6; `calibration_w.py --jobs`),
so piggybacking would auto-enable the new path with the flag
conceptually "unset" — violating the default-OFF /
character-for-character constraint; (b) the registered docstring defines
`workers`' meaning narrowly ("workers > 1 evaluates each cell's variants
in a fork pool", :636-637) — widening it silently rewrites a registered
scheduling-only claim. The W_NULL_FAST precedent is an env flag read at
the exact seam (:268) with no signature ripple; an env flag likewise
reaches `_cell_calibration` without touching
`run_w_sweep`/`run_calibration_cell` signatures or any frozen file.

**Verdict: holds.** Env `W_CAL_JOBS`, read inside `_cell_calibration`
after the :535 early return; engage iff jobs > 1 and n_cal > 1; one-line
stdout provenance banner when engaged (null-fast design §6 / A7
precedent — stdout only, never the artifact) (B2/B6).

### Q14. Reduction correctness under the pool (bit-identity of the cal block)

**Grilling.** `passes` is an order-free integer sum of
`int(verdict.passed)` (:558); rate and mc_se (:559-562) are pure float
functions of `(passes, n_cal)`, so parallel return order cannot perturb
a bit. Production variation is real — committed cell of record
`artifacts/w/calibration/P-BTC_5bps`: TG full_gate_pass_rate 0.015
(3/200), TH 0.01 (2/200), TD/TE/TF 0.0 — so the sum is live, not
vacuous. Probe confirmed serial_rate == parallel_rate on a 12-draw
prefix, but that check was degenerate (0==0: zeroed `null_sharpes` per
the sketch's §4 methodology makes the gate's null clause unpassable).

**Verdict: holds, with amendment (B7).** Layer-1 equality tests must use
toys (or a real-cell prefix with the REAL `null_sharpes` vector) where
`verdict.passed` actually varies across draws — the committed TG/TH
cells prove such variation exists at production scale; a 0==0 equality
is not evidence. Made an explicit acceptance condition.

---

## Lens C — scope and registration posture

### Q15. Diff shape: guarded branch vs editing the serial body — auditability of "default unset ⇒ character-for-character"

**Grilling.** Precedent diff inspected: commit 4575ab6 edits
`lab/sweep_w.py::_null_sharpes_w` as a PURE INSERTION (docstring lines +
4-line early-return guard) with every pre-existing line untouched —
auditable by an insertion-only git diff. Current serial calibration:
`lab/sweep_w.py:518-562`; the per-draw body (537-558) carries no
cross-draw state. A fork worker requires a module-level function +
fork-shared context (the `_MP_CTX_W` pattern, :612-621), so the per-draw
body cannot be both "verbatim in the worker" and "shared with the serial
loop" without hoisting — and hoisting the loop body into a helper called
by the serial path would change the default path's code, voiding the
sketch's own §2 promise.

**Verdict: holds, with amendment (B1).** Pin the minimal diff shape:
(1) one inserted early-return guarded branch in `_cell_calibration`
(after reading `W_CAL_JOBS`), exactly the 4575ab6 shape; (2) a NEW
module-level worker (`_mp_cal_draw`) + parallel twin + its own
`_CAL_CTX_W` fork-shared dict, the twin's per-draw body a VERBATIM COPY
of `sweep_w.py:538-558`; (3) a coupling note on the new code mirroring
`lab/null_fast.py:40-52` — any edit to the serial body re-opens the
equivalence claim and the proof battery re-runs. Refactoring/hoisting
the serial loop is explicitly forbidden.

### Q16. Structural soundness of the scheduling-only claim

**Grilling.** Draw `i` consumes `shuffles[f.name][i]` (:543);
`lab/hooks_w.py:92/104/142` show `_EpisodeShufflesW` stores ALL
permutation orders at construction and `__getitem__` is a pure, uncached
function of `i` — process- and order-independent, so fork workers
reproduce each draw exactly. `passes` is an exact integer sum of
per-draw ints (order-free; :558), and rate/mc_se (:559-562) are pure
functions of `(passes, n_cal)`. No nested pools (:743-746 closes before
:774). The per-draw body contains no prints, so no stdout interleaving
from workers.

**Verdict: holds, with amendment (B2/B3).** The §2 watch item "pool fork
cost per taxonomy (5 pools/cell — amortize or reuse)" loses its "reuse"
half: pool REUSE across taxonomies is incompatible with the
fork-shared-context mechanism — workers snapshot parent memory at fork
time, and each taxonomy's shuffles are built (:714-719) and deleted
(:780) per taxonomy, so a reused pool would hold a stale snapshot. One
fresh pool per taxonomy is the only correct shape. Flag parsing is
pinned: malformed `W_CAL_JOBS` values raise loudly (A3 spirit: never a
silent fallback) — see B2 for the exact posture.

### Q17. Registration constraints (§8, §9) on calibration mechanics

**Grilling.** Registration §8
(`2026-06-10-widening-preregistration.md:410-415`) fixes only the
statistical content of the per-cell full-gate calibration: per-(panel,
taxonomy) cell, ≥200 common null draws (prefix), top train-ranked
Variant (pinned to GATED/non-annex by amendment 29(d), :673-674), full
8-clause gate, rate + Monte-Carlo SE disclosed. It says nothing about
execution scheduling. §9's "performance shortcut" (:449-457) is a
SPECIFIC numeric shortcut — OOS-window restriction of null-draw
backtests — with its own two-condition proof; draw-parallel scheduling
is not that shortcut. The controlling precedent is amendment 29(g)
(:679-682): the driver "may parallelize Variant evaluation with a fork
pool … pure scheduling over pre-generated common draws, output
byte-identical, pinned by an on/off determinism test", plus the
post-contact lazy-shuffle note (:684-697) establishing the "29(g) class:
no registered constant, clause, seed, draw value, or evaluation order
changed". But 29(g) literally covers VARIANT evaluation, not calibration
draws — the sketch's claim that `run_w_sweep(workers=N)` "already
registers" this posture is loose: the registration document registers
the variant pool only.

**Verdict: holds, with amendment (B10).** The design (1) cites 29(g) +
the 29(g)-class note precisely, stating the calibration pool is a NEW
claim of the same class that earns its own on/off determinism pin
(Layers 1–2), not a literally pre-sanctioned mechanism; (2) resolves the
posture ambiguity: production runs keep `W_CAL_JOBS` unset until a
future lane's pre-registration cites this design + the proof artifacts —
the same closure path as `W_NULL_FAST` (null-fast design §6/§9).
Justification: the two flags will be cited together by the same future
lane, one posture for both keeps the record unambiguous, and the
conservative path costs nothing (proof reruns are off-production
anyway). The 29(g) dated-note path remains available to that lane; it is
not exercised unilaterally here.

### Q18. Stdout provenance line and artifact config-blindness

**Grilling.** The null kernel prints one provenance line per process
when live (`lab/null_fast.py:76-82`, amendment A7); grill Q7
(`2026-06-12-null-fast-grill.md:180-183`) records its rationale: an
ambient env var silently flipping a production run. The identical risk
applies to an ambient `W_CAL_JOBS` (repo `.env` probed: only
CMC_MCP_API_KEY and CLICKHOUSE_URL; no W_ flags anywhere in
`.env*`/scripts except `prove_null_fast.sh`'s intentional
W_NULL_FAST=1). Artifact config-blindness verified on the committed cell
of record: `artifacts/w/calibration/P-BTC_5bps/sweep_results_w.json`
globals keys = [calibration_draws, cost_rungs_bps, crash_day_groups,
embargo_bars, era_split_at, gate_cost_bps, n_draws, panels, r3,
seed_map]; substring probe for "jobs"/"worker"/"wall"/"seconds"/
"W_NULL_FAST"/"W_CAL" all False. `sweep_w.py:77-78` pins "No wall-time
field — the artifact is byte-deterministic; main() prints timing to
stdout only." The Layer-2 `cmp` self-enforces this: any artifact trace
of the flag would break byte identity against the pre-flag committed
reference.

**Verdict: holds, with amendment (B6).** The flag prints an A7-style
provenance line — exactly once per process, from the PARENT (the
per-draw worker body has no prints and must stay print-free), stdout
only, citing the cal-fast design doc. The design states explicitly that
the artifact gains no field, no key, no whitespace — structurally
enforced by the `cmp` proof, stated as a constraint, not left as a
consequence.

### Q19. Layer-2 proof plan soundness (rerun P-BTC_5bps with both flags, `cmp`)

**Grilling.** Reference provenance is sound: all 9 calibration cells
were committed in fbf728d, which precedes the kernel commit 4575ab6
(2026-06-12 01:49Z; git log order confirmed), so the reference is
frozen-path for BOTH flags by construction; P-BTC_5bps additionally
carries the proven W_NULL_FAST byte-identity (null-fast design §9:
sha256 f08342f0… matched, gate passes 12/81), so a both-flags rerun that
differs attributes cleanly to the new flag. `scripts/prove_null_fast.sh`
already enforces scratch-root isolation (refuses any path resolving
under `$REPO/artifacts`) and reads the reference cell as input only.
SENSITIVITY GAP measured: P-BTC_5bps per-cell calibration pass rates are
TD 0.0, TE 0.0, TF 0.0, TG 0.015, TH 0.01 — only 5 passing draws in 2 of
5 taxonomies. Any count-preserving bug (off-by-one draw indexing, draws
evaluated twice/skipped where all fail) is byte-invisible in the three
all-fail cells, and the sketch's Layer-1 plan ("parallel result dict ==
serial result dict") compares only the AGGREGATED (draws, rate, mc_se)
dict, which has the same blindness. P-BTC_10bps has nonzero rates in all
5 taxonomies (0.005/0.015/0.005/0.005/0.005).

**Verdict: holds, with amendment (B7/B9).** Layer 1 strengthened:
compare the ORDERED per-draw verdict vector (list of booleans, parallel
vs serial) — not just the summed dict — on at least one fixture with a
non-constant pass pattern, plus a toy `run_w_sweep` artifact
byte-identity test covering W_CAL_JOBS off/on and combined with
W_NULL_FAST=1 and workers>1 (mirroring the 29(g) determinism pin and the
existing null-fast seam test). Layer 2 keeps P-BTC_5bps as primary
target (clean attribution vs the null-fast proof); the per-draw-vector
Layer-1 test carries value sensitivity (P-BTC_10bps optional second
target). The proof script is a SIBLING (`scripts/prove_cal_fast.sh`),
not an edit of `prove_null_fast.sh` — mutating the committed proof
procedure would change what the null-fast §9 evidence note refers to.
Scratch-root guard retained verbatim.

### Q20. Scope containment and repo vocabulary

**Grilling.** The sketch correctly self-gates Phase 2 behind an operator
entry criterion (§2), and the null-fast grill Q6 verdict already rules a
fast calibration/trade path a separate design with its own proof battery
— Phase 1 as drafted touches no numeric path, only scheduling, so it
does not collide with that verdict. Frozen six untouched: the only code
edit lands in `lab/sweep_w.py`, which is not in the frozen list and
holds the W_NULL_FAST precedent (:268-271). Vocabulary: the sketch uses
"full-gate calibration" and "8-clause gate" (qualified per
`CONTEXT.md:70/147/160`); no banned terms found.

**Verdict: holds.**

---

## Lens D — completeness

### Q21. Consumers of `_cell_calibration` — single call site, three downstream readers

**Grilling.** Repo-wide grep: `_cell_calibration` is defined at
`lab/sweep_w.py:518` and called exactly once, at :774 inside
`run_w_sweep`'s per-taxonomy loop (after the variant pool closes at
:746, before `del shuffles` at :780). Its dict lands in cal_block →
`globals.r3.per_cell_calibration` (:833). Downstream readers:
`tests/test_sweep_w.py:296-311` (pins keys {variant_id, draws,
full_gate_pass_rate, mc_se}, draws == min(200, draws), the mc_se
formula, and P-BTC/TF rate == 0.0); `demo/run_demo.py:44+321` and
`docs/report/REPORT.md:837` read only the COMMITTED
`artifacts/w/sweep_results_w.json`. `lab/lock_w.py`,
`lab/deep_replay.py`, `lab/gate_w.py`, `lab/band_recon.py`,
`lab/report_figs.py` never touch the calibration block (grep for
per_cell_calibration/full_gate_pass_rate/mc_se: zero hits outside
sweep_w, test_sweep_w, REPORT.md, the plans). Committed cell of record
confirms shape: calibration_draws=200, 5 cells P-BTC/{TD,TE,TF,TG,TH} —
5 calibration pools per cell, matching the sketch's watch item.

**Verdict: holds.** The design records this consumer census (B12) so
the implementer knows any new dict key or numpy-typed value in the
parallel twin breaks both the pinned test and byte-identity.

### Q22. `run_calibration_cell` / `run_w_calibration.sh` plumbing — env flag is FORCED, not stylistic

**Grilling.** `lab/calibration_w.py:249-273`: `run_calibration_cell`
forwards draws→draws and jobs→workers but does NOT pass
calibration_draws, so any run through `lab.calibration_w` always gets
`n_cal = min(CAL_DRAWS_W=200, draws)` (`sweep_w.py:645`).
`scripts/prove_null_fast.sh:43` and `scripts/run_w_calibration.sh:34`
both invoke `python -m lab.calibration_w`. The hard constraint allows
code edits ONLY in `lab/sweep_w.py` — `lab/calibration_w.py` and both
shell scripts are off-limits. Therefore a kwarg or CLI knob CANNOT be
plumbed to the calibration pool; the only reachable knob through the
Layer-2 proof path is an environment variable read inside
`lab/sweep_w.py`, which propagates through
`W_CAL_JOBS=6 uv run … -m lab.calibration_w` with zero plumbing.
Consequences: (a) the Layer-2 rerun always executes the full 200-draw
calibration — exactly what the committed P-BTC_5bps artifact contains,
so the proof is apples-to-apples; (b) there is no cheap reduced-n_cal
smoke via that CLI — quick prefix probes drive
`run_w_sweep`/`_cell_calibration` directly (sketch §4 already does);
(c) `scripts/run_w_calibration.sh` needs NO change and is inert anyway
(it skips cells whose results exist, :29-31, and all 9 committed cells
exist).

**Verdict: holds, with amendment (B2/B12).** "e.g. `W_CAL_JOBS=6`" is
promoted from a suggestion to a requirement: the flag MUST be an env var
read at the sweep_w seam, because the edit boundary forbids plumbing a
parameter through `lab/calibration_w.py`. Recorded:
`run_calibration_cell`'s non-forwarding of calibration_draws is
intentional and means Layer-2 always proves the full 200-draw block.

### Q23. Proof script — "prove_null_fast.sh extended or sibling" half-violates the edit boundary

**Grilling.** Sketch line: "`scripts/prove_null_fast.sh` extended or
sibling script". `scripts/prove_null_fast.sh` is an EXISTING script; the
constraint allows new scripts only — extending it is a forbidden edit.
The sibling must replicate its discipline: scratch-root guard against
`$REPO/artifacts` (prove_null_fast.sh:25-30), cell-of-record as
read-only REF (:32-36), env-flagged invocation of `lab.calibration_w`
(:43-44), `cmp` (:48-53). The cal-fast sibling sets BOTH `W_NULL_FAST=1`
and `W_CAL_JOBS=N` (justified: null-fast is already independently proven
by commits 4575ab6/d39e119/dd1f068, so a combined-flags run is
attributable and avoids an ~8,800 s frozen-null rerun).

**Verdict: BROKEN as written — resolved by amendment (B9).** The design
of record specifies a NEW sibling script (`scripts/prove_cal_fast.sh`)
and drops the "extended" option. It byte-cmps the scratch P-BTC_5bps
`sweep_results_w.json` against
`artifacts/w/calibration/P-BTC_5bps/sweep_results_w.json` with
`W_NULL_FAST=1 W_CAL_JOBS=N` in the environment. With this amendment the
finding no longer blocks promotion.

### Q24. Where the parallel branch lives — a new lab module is NOT allowed this time

**Grilling.** The null-fast precedent put the fast path in a NEW module
`lab/null_fast.py` with a 2-line guard in sweep_w. This task's edit set
is narrower: "lab/sweep_w.py, new test files, new scripts, docs/plans/*"
— a new `lab/cal_fast.py` is none of those. Additionally, fork-context
`Pool.map` still pickles the callable, so the worker must be a
module-level function (precedent: `_mp_eval_w` at `sweep_w.py:615` +
module global `_MP_CTX_W` at :612). And "default unset ⇒
character-for-character" means the serial loop at :536-562 must remain
literally untouched, so the per-draw body (:538-558) gets DUPLICATED
into the parallel twin — duplication drift is exactly what the Layer-1
equality battery and Layer-2 `cmp` exist to catch. The guard mirrors the
`_null_sharpes_w` pattern. `os` and `multiprocessing` are already
imported in sweep_w (used at :268, :742).

**Verdict: holds, with amendment (B1).** All new code lives in
`lab/sweep_w.py` — guarded branch in `_cell_calibration`, a module-level
per-draw worker fn, a parallel twin, and a second fork-shared context
global. Name pinned: `_CAL_CTX_W`, SEPARATE from `_MP_CTX_W` (Q12
ruling; `_MP_CTX_W` is empty at calibration time and could in principle
be reused, but the :746 reset invariant stays untangled). The serial
body is duplicated verbatim, not factored out.

### Q25. Edge cases the parallel twin must mirror — early returns, pool sizing, flag parsing

**Grilling.** `sweep_w.py:533-535`: the early-return dict
(`{"draws": 0, "full_gate_pass_rate": None, "mc_se": None}` — None
serializes as null in the artifact) must be reproduced exactly; pool
sizing precedent `min(workers, len(cell_variants))` (:743) → twin uses
`min(jobs, n_cal)`. The sketch never defines parsing for `W_CAL_JOBS`
(malformed "abc", "0", "1", negative). The body itself is provably
order-free: it consumes only precomputed `shuffles[f.name][i]` (lazy
`_EpisodeShufflesW` indexing), `fc["hot"]`, bars/funding, and pure
frozen functions; contributes `int(verdict.passed)` to an integer sum
(:558); rate and mc_se are pure functions of `(passes, n_cal)`
(:559-562); no RNG, no prints (`gate_w.py` has zero print statements —
probed), no shared-state mutation. `_strategy_w` (:176-190) is pure. So
`Pool.map` chunking/order cannot perturb the result.

**Verdict: holds, with amendment (B2/B5/B8).** Pinned: exact
early-return parity, pool size `min(jobs, n_cal)`, and the flag-parsing
posture in B2 — non-integer values raise loudly (`int()` ValueError,
never a silent fallback, A3 spirit); integer values ≤ 1 (including unset
⇒ 0) are a meaningful "off" and take the serial path
(W_NULL_FAST-precedent default-OFF). Layer-1 tests cover the
early-return toys.

### Q26. Ambient-flag risk and test-suite exposure — grill Q7/A7 obligations carry over

**Grilling.** Null-fast grill Q7 named the residual risk "an ambient
W_NULL_FAST=1 in the environment flipping production runs silently",
mitigated by A7's provenance stdout line (pinned by
`test_null_fast.py:419-436`) and by the flag-unset standing guard
`test_flag_unset_never_imports_kernel` (`test_null_fast.py:439-453`,
subprocess with the flag scrubbed from env). The sketch says nothing
about provenance for `W_CAL_JOBS`. Existing-suite exposure: no test in
the repo sets or scrubs `W_CAL_JOBS`, so an ambient value during a
pytest run would silently route every toy sweep's calibration through
the pool (`test_sweep_w.py` sweep_run fixture :107-110,
`test_calibration_w.py:380`, `test_null_fast.py:419`) — they would stay
green if the twin is correct, but the serial path would be silently
unexercised. Existing test files cannot be edited to add scrubs.

**Verdict: holds, with amendment (B6/B8).** (1) provenance stdout line
when the parallel calibration path activates (once per parent process,
A7-style — stdout only, never the artifact); (2) in the NEW test file,
explicit `monkeypatch.delenv`/`setenv` of `W_CAL_JOBS` around every
equality case, plus a flag-unset standing guard (subprocess with
`W_CAL_JOBS` scrubbed asserting no calibration Pool is created /
provenance line absent), mirroring `test_null_fast.py:439`.

### Q27. Fixture reuse for Layer-1 equality tests — mirror, don't import

**Grilling.** `tests/` has no `__init__.py` (probed), and the
established precedent is mirroring, not cross-importing
(`test_null_fast.py:24` "Fixtures mirror tests/test_sweep_w.py's toy
conventions"). Reusable patterns for the new test file:
(a) `test_null_fast.py:96-111` `_ctx()` builds (fold_ctx, shuffles)
"exactly as run_w_sweep wires them" — ideal for direct
`_cell_calibration` serial-vs-parallel dict-equality cases, including
ts/vb variants (:56-63), all-na/empty-OOS folds, and the T-F always-flat
family; (b) `test_null_fast.py:410-416` `_toy_sweep` +
`test_sweep_w.py:57-104` `_toy_panel`/TOY_BOUNDARIES for the
full-artifact byte-equality test flag-off vs flag-on vs
flag-on+workers=4 (the workers=4 leg matters because calibration pools
fork from a parent that just ran the variant pool);
(c) `test_calibration_w.py:362-377` `_toy_panel_300` for a
`run_calibration_cell`-seam case proving env propagation through
`lab.calibration_w` with zero plumbing; (d) the env-gated real-cell
prefix test mirrors `test_null_fast.py:456-499` (the
W_NULL_FAST_REALPANEL pattern: skipif unless `W_CAL_FAST_REALPANEL=1`,
rebuild the P-BTC planted panel via `build_planted_panel` — read-only
import of `lab.calibration_w` is fine — and compare `_cell_calibration`
serial vs parallel at an n_cal prefix on the committed pick
`P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0`, per sketch §4 but with
the REAL null vector). `tests/test_hooks_w.py` and
`tests/test_rules_w.py` pin shuffle/time-stop internals already proven —
not needed for this layer.

**Verdict: holds.** The design lists these four concrete test shapes
(B8) so the implementer doesn't invent new toy conventions.

### Q28. `structural_feasibility_readout`, lock/era paths, W-B chain script — no calibration contact

**Grilling.** `structural_feasibility_readout` (`sweep_w.py:862-931`) is
TRAIN-side only and never reaches `_cell_calibration` or the cal_block.
`_evaluate_lock` (:286+) and `_era_split` run inside `_eval_variant_w`
(:504-515) per variant, BEFORE the per-cell calibration at :774, and
consume the null VECTOR only — disjoint from the calibration loop.
`scripts/run_w_calibration.sh:29-31` skips any cell whose
`sweep_results_w.json` exists; all 9 cells are committed, so the chain
script is inert and, per the registration posture (B10), is not edited
to export the flag.

**Verdict: holds.**

### Q29. Implementer's touch list (must-touch vs must-not-touch)

**Grilling.** Derived from all findings above; recorded as the file
manifest in the design (B13).

**Verdict: holds, with amendment (B13)** — the promoted design carries
the explicit manifest; the sketch named only `lab/sweep_w.py` and
gestured at "extended or sibling" for the rest.

---

## Amendments adopted into the design of record (Phase 1)

- **B1 — Diff shape pinned.** Pure-insertion guarded branch in
  `_cell_calibration` (4575ab6 shape), placed strictly AFTER the frozen
  early return at :535. New module-level worker `_mp_cal_draw` +
  parallel twin `_cell_calibration_parallel` + fork-shared global
  `_CAL_CTX_W` (separate from `_MP_CTX_W`), all in `lab/sweep_w.py`
  (a new lab module is outside the permitted edit set). The twin's
  per-draw body is a VERBATIM COPY of `sweep_w.py:538-558`; hoisting or
  refactoring the serial loop is forbidden. Coupling note on the new
  code mirroring `lab/null_fast.py:40-52`: any edit to the serial body
  re-opens the equivalence claim and the proof battery re-runs.
- **B2 — Flag pinned.** Env var `W_CAL_JOBS` (FORCED: the edit boundary
  forbids plumbing through `lab/calibration_w.py`), read inside
  `_cell_calibration` after the early return:
  `jobs = int(os.environ.get("W_CAL_JOBS", "0") or 0)`. Non-integer
  values raise loudly (ValueError — A3 spirit, never a silent
  fallback); integer values ≤ 1 (incl. unset) ⇒ the serial path
  (default-OFF). Parallel branch engages iff `jobs > 1 and n_cal > 1`.
- **B3 — Pool topology pinned.** One fresh fork pool per taxonomy
  (per-cell pooling ruled out by fork-snapshot semantics; reuse of the
  variant pool ruled out by lifetime/pickling — Q9); do not amortize
  (~0.1 s/pool, measured noise — Q7). Pool size `min(jobs, n_cal)`;
  ordered `pool.map` with explicit `chunksize=1`; workers return
  per-draw ints only; the worker body stays print-free.
- **B4 — Context hygiene.** `_CAL_CTX_W` is set immediately before Pool
  creation and reset to `{}` before `_cell_calibration` returns,
  mirroring `_MP_CTX_W`'s reset at :746 — otherwise
  `del shuffles, null_by_id` at :780 is defeated (~320 MB of orders
  retained per taxonomy, ~1.6 GB parent growth per cell).
- **B5 — Early-return parity.** Degenerate cells (n_cal ≤ 0 / no active
  folds) take the frozen dict
  `{"draws": 0, "full_gate_pass_rate": None, "mc_se": None}` verbatim
  with no pool ever created.
- **B6 — Provenance + artifact blindness.** When the parallel path
  engages, the PARENT prints one A7-style stdout line per process citing
  this design doc; the artifact gains no field, no key, no whitespace
  (stated constraint; the Layer-2 `cmp` enforces it structurally).
- **B7 — Layer-1 sensitivity.** Equality cases must include a fixture
  where `verdict.passed` varies across draws (real or toy null vector —
  a 0==0 equality is not evidence; committed TG/TH cells prove variation
  exists at production scale). Compare the ORDERED per-draw verdict
  vector, not just the summed dict. Add one cold-vs-warm pandas
  `Index._cache` seam case (fresh-process draw k vs after a prefix,
  exact comparison).
- **B8 — Test file shapes.** New `tests/test_cal_fast.py` (mirror, don't
  import): (a) direct `_cell_calibration` serial-vs-parallel equality on
  toys incl. ts/vb, all-na/empty-OOS, early-return toys; (b) toy
  `run_w_sweep` artifact byte-identity off vs on vs on+workers=4 vs
  on+W_NULL_FAST=1; (c) `run_calibration_cell`-seam env-propagation
  case; (d) env-gated real-cell prefix test (`W_CAL_FAST_REALPANEL=1`)
  with the REAL null vector. Every case `monkeypatch`es `W_CAL_JOBS`
  explicitly; plus a flag-unset standing guard (subprocess, flag
  scrubbed: no calibration pool, no provenance line).
- **B9 — Sibling proof script (resolves the one broken finding).** NEW
  `scripts/prove_cal_fast.sh`; `scripts/prove_null_fast.sh` is NOT
  edited (it is the committed proof procedure the null-fast §9 note
  refers to). Same discipline: scratch-root guard verbatim, committed
  cell read-only, `W_NULL_FAST=1 W_CAL_JOBS=N` invocation of
  `lab.calibration_w`, byte `cmp` of scratch P-BTC_5bps vs
  `artifacts/w/calibration/P-BTC_5bps/sweep_results_w.json`. P-BTC_5bps
  is the primary target (clean attribution: its null-fast byte-identity
  is already proven); value sensitivity is carried by B7's per-draw
  vector test (P-BTC_10bps optional second cmp target).
- **B10 — Registration posture resolved.** The calibration pool is a NEW
  claim of the amendment-29(g) class (scheduling-only, byte-identical,
  pinned by its own on/off determinism test) — 29(g) itself covers
  Variant evaluation only and is cited as precedent, not sanction.
  Production runs keep `W_CAL_JOBS` unset until a future lane's
  pre-registration cites this design + the proof artifacts (same closure
  path as `W_NULL_FAST`; one posture for both flags).
- **B11 — Environment fact recorded.** pandas 3.0.3 lazily populates
  `DatetimeIndex._cache` on the fold OOS indexes during the first
  `Index.intersection` — the one observable side effect of the draw body
  on shared state; probed value-transparent (cold vs warm bit-equal) and
  pinned by B7's seam case.
- **B12 — Consumer census recorded.** Single call site
  (`sweep_w.py:774`); dict structure pinned by
  `tests/test_sweep_w.py:296` (no new keys, no numpy-typed values in the
  twin's return). `run_calibration_cell` does not forward
  calibration_draws — intentional; Layer 2 therefore always proves the
  full 200-draw block.
- **B13 — File manifest.** MUST TOUCH: `lab/sweep_w.py` (guard + worker
  + twin + `_CAL_CTX_W` + provenance), `tests/test_cal_fast.py` (new),
  `scripts/prove_cal_fast.sh` (new), `docs/plans/*` (this grill + the
  promoted sketch). MUST NOT TOUCH: the frozen six (`lab/engine.py`,
  `lab/hooks.py`, `lab/hooks_w.py`, `lab/rules.py`, `lab/rules_w.py`,
  `lab/sweep.py`); `lab/calibration_w.py`; `lab/null_fast.py`;
  `scripts/prove_null_fast.sh`; `scripts/run_w_calibration.sh`; existing
  test files (`tests/test_sweep_w.py`, `tests/test_calibration_w.py`,
  `tests/test_null_fast.py`, `tests/test_hooks_w.py`,
  `tests/test_rules_w.py`); `artifacts/w/sweep_results_w.json` and
  `artifacts/w/calibration/*` (inputs of record — proof reruns to
  scratch out-roots only); `demo/run_demo.py`, `docs/report/*`.

Everything else in the sketch's Phase 1 stands as written. Phase 2 was
not grilled and is not promoted.
