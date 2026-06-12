# Fast null kernel — autonomous grill of the design of record

**Subject:** `docs/plans/2026-06-12-null-fast-design.md`
**Mode:** autonomous grill (interviewer and designer are the same agent;
every branch closed in writing with evidence, no human in the loop).
**Date:** 2026-06-12. Environment snapshot for every verdict below:
pandas 3.0.3, numpy 2.4.6, `bottleneck` NOT installed, `numexpr` NOT
installed (checked in the repo venv) — pandas arithmetic and reductions
run plain numpy code paths; `uv.lock` pins all of it.

Probe script: `/tmp/nf_scratch/nf_grill_float_checks.py` (scratch; its
load-bearing checks are re-expressed as standing tests in
`tests/test_null_fast.py`). All 9 probes passed bit-exact.

---

## Q1. Time-stop port — does "port verbatim" survive a line-by-line read of `lab/rules_w.py:76`?

**Grilling.** The frozen loop's per-bar work is three predicates and a
counter: (a) `transition = t > 0 and not _same_label(labs[t], labs[t-1])`,
(b) `_act(labs[t], action_map) != 0.0`, (c) `u = wv[t]; u == 0.0`. The
state is `(run_len, stopped)`. Branch order matters: the `stopped` block
runs FIRST and either `continue`s (forced flat — `out[t]` stays 0.0) or
falls through into the run logic at the SAME bar (the pinned boundary
convention: re-entry shares the stop/transition bar). `out` starts as
`np.zeros`, so a skipped bar emits +0.0 regardless of `wv[t]`'s sign bit
— the port must preserve that (it does: same zeros-init + assign-only-
on-run structure).

Sub-branches checked against the source:

- **NaN lagged label at t=0:** `stopped` is initialized False, so the
  transition predicate is unreachable at t=0; the NaN only matters
  through `wv[0]` which `rules.apply` already forced to 0.0 (bar 0 flat).
  In codes: `lagged_codes[0] = NAN_CODE`, `act_by_code[NAN_CODE] = 0.0`.
  Equivalent on every path.
- **`_same_label` NaN semantics:** NaN==NaN is True, NaN!=value. An
  equality-faithful factorization that maps EVERY na value (np.nan, None)
  to one reserved code reproduces this exactly: code equality ≡
  `_same_label`. `pd.factorize`'s NA sentinel uses the same NA predicate
  family as `pd.isna`. Closed.
- **Re-entry colliding with the stop bar:** pure branch-order property;
  the port keeps the branch order. Pinned by a dedicated Layer-1 case
  replicating the test-pinned convention from `tests/test_rules_w.py`.
- **Label change mid-run without a flat bar:** run logic consumes only
  `u != 0`; labels don't enter it. The run continues — identical, because
  the port's run logic also consumes only `u`.
- **k=1 degenerate / all-na series:** k=1 stops every isolated nonzero
  bar at entry; all-na gives all-zero `wv` and the loop never opens a
  run. Both are pure consequences of the shared branch structure;
  Layer-1 cases pin them anyway.
- **`wv = np.where(np.isnan(wv), 0.0, wv)` defensive line:** kept in the
  port even though the kernel's `w` cannot be NaN — verbatim means
  verbatim.
- **k validation:** the frozen `int(k) != k or int(k) < 1` raise is
  mirrored, so toy tests hitting bad k diverge in neither path.

**Verdict: design holds, with one amendment (A4).** The port may
precompute the per-bar predicates (a) and (b) as numpy arrays BEFORE the
loop — they are pure functions of the constant lagged-code array, not of
loop state — while the loop keeps the exact branch skeleton. This is
bookkeeping, not logic change; every branch maps 1:1. The run-length
reformulation stays out of v1, as the design says.

## Q2. Float-op ordering — empirical, not argued

**Grilling.** Walked every §4.2 expression against the frozen source and
ran bit-level probes (13,566 elements, adversarial values incl. -0.0,
NaN labels, zero returns):

| frozen expression | kernel port | probe |
|---|---|---|
| `w.diff(); dw.iloc[0] = w.iloc[0]` | `dw[0]=w[0]; dw[1:]=w[1:]-w[:-1]` | PASS (bit-exact) |
| same | design's `w - concat(([0.0], w[:-1]))` | PASS (incl. -0.0: `-0.0 - 0.0 == -0.0`) |
| `(1-dw.abs()*ps)*(1-w*fund)*(1+w*r)` Series ops | same ops on ndarrays | PASS |
| `growth - 1.0` then restrict | restrict then `- 1.0` | PASS (elementwise op commutes with gather) |
| `wf.mask(hot, wf*0.5)` | `np.where(hot_v, w*0.5, w)` | PASS |
| `labels.map(amap).astype(float).fillna(0).shift(1).fillna(0)` | `act_by_code[codes]` + shift port | PASS (NaN + unknown labels included) |

pandas would only diverge from numpy here via numexpr (not installed,
and below its element threshold anyway) or bottleneck (not installed).
Both facts recorded above; `uv.lock` freezes them.

**Verdict: design holds; amendment (A1)** — implement `dw` as the direct
`diff` port (`dw[0]=w[0]; dw[1:]=w[1:]-w[:-1]`) rather than the
concat-with-zero formulation. Both probed bit-equal; the direct port has
zero argument surface (same subtractions, same operands).

## Q3. Pooled ordering — close the disjointness hedge

**Grilling.** `w_folds` geometry (`lab/panels_w.py:178`): every fold's
`oos_idx` is a SLICE of the panel index — `panel_index[b_pos+E : next]`
with monotonic boundary positions — so OOS windows are disjoint, ordered,
duplicate-free by construction. But the design hedges ("capturing it from
the frozen ops makes that an implementation detail"). The hedge closes by
making capture-from-frozen-ops cover BOTH order-sensitive steps:

1. **Restrict:** per fold, run the frozen `_restrict` once over an
   `arange` payload series — the values ARE the panel positions, in the
   exact order `Index.intersection` emits them.
2. **Pool:** run the frozen `pd.concat(...).sort_index()` once over
   per-fold `arange` payloads on those restricted indices — the values
   ARE the permutation, the index IS the pooled index.

Both permutations depend only on indices (constant across draws), and
the frozen ops are deterministic functions of their inputs, so replaying
the captured permutation per draw is exact even if intersection or
sort_index internals do something surprising with ties. Probe 7/8: a
3-fold pooled series rebuilt this way is bit-identical and frozen
`sharpe` agrees to the last bit.

**Verdict: design improved (A2).** Capture the restrict positions AND
the sort permutation from the frozen ops on arange payloads. No
disjointness assumption survives in the kernel (it would be correct even
on overlapping folds).

## Q4. Sharpe reduction — can an equal-values/equal-order Series diverge?

**Grilling.** `lab.metrics.sharpe` consumes `len`, `.std(ddof=0)`,
`.mean()`. Those reductions read only the float64 values array — index
dtype, index identity, and Series name never enter (probe 9: sharpe on a
RangeIndex/unnamed clone of the pooled series is bit-identical).
Backend risk (bottleneck) is empirically absent and lock-pinned. The
kernel nevertheless builds the per-draw Series on the CAPTURED pooled
DatetimeIndex — fidelity is cheap (one shared index object).

**Verdict: design holds.** No doubt survives; pinned by probe and by a
standing Layer-1 test.

## Q5. `_EpisodeShufflesW` private-attr coupling

**Grilling.** Options: (i) read `_orders`/`_ep_labels`/`_ep_lengths`/
`_non_na`/`_na_mask`/`_base`/`_index` directly; (ii) add a read-only
accessor to `lab/hooks_w.py`. Option (ii) edits a frozen file — the
handoff names exactly ONE permitted existing-file edit
(`sweep_w._null_sharpes_w`), so (ii) is out, full stop. Is (i) sound?
The class is repo-internal, `__slots__`-pinned (any rename breaks the
kernel loudly with AttributeError, not silently), its attribute
semantics are documented in its own module docstring, and the kernel
consumes them read-only (one `.copy()` per draw on `_base`-derived
codes, never mutating the shared arrays). The kernel validates the
coupling at precompute time: `_index` must equal `bars.index`, and the
draw-list lengths must agree (frozen ValueError mirrored).

**Verdict: read the private attrs; no accessor.** Justification: frozen-
file discipline outranks style; failure mode is loud; coupling is
documented on the kernel side (`lab/null_fast.py` docstring).

## Q6. Scope temptation — `_cell_calibration` and guarded evals stay slow?

**Grilling.** After the kernel, a cell's wall time is dominated by the
untouched parts: per-Variant guarded evaluations (~6 full backtests x 21
folds each, with trades) and the per-cell §8 full-gate calibration (200
draws x 3 rungs x active folds, serial in the parent). Tempting — the
same returns-only trick does NOT apply: the calibration consumes trades,
turnover, the full 8-clause shipping gate, and the DD guard, which are
exactly the things the kernel proves it can skip for the null. A fast
trade path is a NEW equivalence argument (trade segmentation, guard
state machine) — a separate design with its own proof battery, as §8 of
the design already says.

**Verdict: out-of-scope verdict stands.** For the leaderboard timeline
the null kernel alone turns a ~26 h chain into a few hours, which is
sufficient for the remaining lanes. A follow-up design may target the
calibration path; it must not ride this one.

## Q7. Completeness — other consumers, tests the flag could trip

**Grilling.** Greped the repo: `shuffle_null_pooled_w` is imported and
called ONLY by `lab/sweep_w.py::_null_sharpes_w`. `lab/gate_w.py`
mentions it in prose only; `lab/lock_w.py` and `lab/deep_replay.py`
consume the null VECTOR (quantiles), never the null path itself.
`lab/sweep.py` and `lab/report_figs.py` call the frozen
`shuffle_null_pooled` directly — the frozen 36-Variant path, untouched
by this change (the guarded branch lives in `sweep_w` only). Tests:
`tests/test_hooks_w.py` pins `shuffle_null_pooled_w IS
lab.hooks.shuffle_null_pooled` (identity) — unaffected, `hooks_w` is not
edited. No test pins wall-time. No test sets `W_NULL_FAST`; the flag
default-OFF means the existing suite exercises the frozen path
unchanged. One residual risk — an ambient `W_NULL_FAST=1` in the
environment flipping production runs silently — is mitigated by the
provenance stdout line (A7) and by `.env`/shell audit (not set anywhere
in the repo).

**Verdict: complete.** Single consumer, single seam, no tripped tests.

## Q8 (self-added). Fork-pool and memory interaction

Per-Variant kernel precompute (codes, positions, permutation) runs
inside the fork worker evaluating that Variant — no cross-process cache,
no new shared state, determinism unaffected (pinned by the existing
serial-vs-parallel byte-identity test, re-run under the flag in
Layer 1). Memory: per-Variant precompute is ~2-3 MB of int64 codes per
fold set; the fast path never materializes the per-draw object-dtype
label Series at all, so it strictly tightens the lazy-shuffle memory fix
(commit 61930da). The provenance line prints once per process.

## Q9 (self-added). `n`/`draws` semantics and degenerate folds

The frozen `_null_sharpes_w` returns `np.zeros(draws)` when NO fold has
OOS bars; otherwise `shuffle_null_pooled` derives `n` from the draw-list
lengths (raising `ValueError("fold shuffle lists differ in length: …")`
on mismatch) and `draws` is not consulted. The kernel mirrors BOTH
behaviors exactly, including the ValueError message. An all-na fold
(every draw == the original series, e.g. the T-F toy) is just a constant
draw — no special case anywhere; pinned by a Layer-1 case.

---

## Amendments adopted into the implementation

- **A1** `dw` as the direct diff port (`dw[0]=w[0]; dw[1:]=w[1:]-w[:-1]`).
- **A2** Capture per-fold restrict positions AND the pooled sort
  permutation by running the frozen `_restrict` / `concat.sort_index`
  ops once over arange payloads. No index-geometry assumptions.
- **A3** Checked preconditions, not trusted invariants: the kernel
  asserts `shuffles[fold]._index` equals `bars.index` and refuses
  (raises) otherwise — never a silent fallback to the frozen path.
- **A4** Time-stop predicates precomputed as arrays; loop branch
  skeleton preserved 1:1; k-validation mirrored.
- **A5** Private-attr read of `_EpisodeShufflesW`, documented kernel-side;
  no accessor (frozen file).
- **A6** `n` from draw-list lengths with the frozen ValueError;
  `np.zeros(draws)` for the no-active-folds case.
- **A7** Provenance stdout line printed once per process from
  `lab/null_fast.py` on first kernel call.
- **A8** Environment facts (no bottleneck/numexpr; pandas 3.0.3 / numpy
  2.4.6) recorded here as part of the equivalence evidence; `uv.lock`
  pins them. Layer 2 re-runs cheaply after any bump.

Everything else in the design stands as written.
