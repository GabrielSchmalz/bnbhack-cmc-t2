# Fast null kernel — design + bitwise-equivalence proof plan

**Status:** IMPLEMENTED 2026-06-12 (kernel `lab/null_fast.py`, guarded
branch in `lab/sweep_w.py::_null_sharpes_w`, default OFF; frozen modules
untouched). Grilled before implementation — verdicts and adopted
amendments A1-A8: `docs/plans/2026-06-12-null-fast-grill.md`. Proof
battery green; measured results in §9 below (the §9-of-the-registration
equivalence note).
**Motivation:** the W-sweep's pooled null is ~85% of every cell's wall
time. The lane W-B calibration chain (9 cells, unmodified machinery)
cost ~26 h on 6 workers. The widening cycle will re-run this machinery;
§9 of the registration records "NO performance shortcut" *because the
equivalence proofs do not exist*. This design produces the kernel AND
the proofs, so future lanes can register the fast path instead of
being barred from it.

## 1. Where the time goes (measured 2026-06-11, profile of one
## BTC/TD ts6 variant, 20 draws x 21 folds, cProfile)

Per (draw, fold) iteration of `_null_sharpes_w` →
`shuffle_null_pooled`:

| segment | share | nature of waste |
|---|---|---|
| `engine._extract_trades` | ~32% | trades are built and **discarded** — the null consumes only the Sharpe of `bar_returns` |
| `rules_w.apply_time_stop` | ~29% | Python bar-loop with `pd.isna` + pandas scalar `__getitem__` per bar (`_same_label`: 3.4M calls / 420 iterations) |
| `hooks_w._EpisodeShufflesW.__getitem__` | ~23% | object-dtype `np.repeat`/`concatenate` + full `pd.Series` construction per draw per fold |
| `rules.apply` + `_restrict` + `sharpe` + engine vector part | ~16% | `labels.map` over object arrays; `Index.intersection` recomputed per draw though fold OOS positions are constant |

Loop count per variant: `draws(1000) x active_folds(21) = 21,000`
full-panel (13,566-bar) iterations. The vectorized engine math itself
is ~5 ms; everything around it is pandas/object overhead.

## 2. Scope

**In scope:** the pooled-null path only — the
`_null_sharpes_w` → `shuffle_null_pooled_w` call chain inside
`lab/sweep_w.py`. One new module, `lab/null_fast.py`, opt-in via
`W_NULL_FAST=1`, default OFF (unset ⇒ byte-identical behavior, the
frozen path runs).

**Out of scope (stays frozen, unconditionally):**
- `lab/engine.py`, `lab/hooks.py`, `lab/hooks_w.py`, `lab/rules.py`,
  `lab/rules_w.py` — not edited at all.
- The variant's own guarded evaluations (steps 4–9), `_cell_calibration`
  (it consumes trades + the full 8-clause gate; only 200 draws x 3 rungs
  per cell), lock layers, era splits.
- The frozen 36-variant sweep (`lab/sweep.py`) — untouched.
- Lane W-B: its registered claim is "UNMODIFIED run_w_sweep"; completed
  cells are never re-run with the flag for production purposes.

## 3. Why the null path is exactly re-derivable

In the null path, invariants the frozen code recomputes 21,000 times
per variant are actually constant:

- `w.index == bars.index == panel.index` for every draw (labels are
  whole-index, shuffles are on `labels.index`).
- `r` (period returns) and `fund` (stamp-masked funding) depend only on
  the panel.
- Each fold's `_restrict` intersection — hence the OOS **positions** in
  the panel index — depends only on the fold.
- The pooled `concat(segments).sort_index()` ordering depends only on
  the active-fold list.
- The shuffled label series is fully determined by
  (`_EpisodeShufflesW` arrays, `orders[i]`) — episode labels, lengths,
  na mask, and the per-draw permutation. No per-draw object work is
  forced.

## 4. Kernel design (`lab/null_fast.py`)

### 4.1 Precomputation

Per **panel** (once per cell):
```
opens  = bars["open"].astype(float);  closes = bars["close"].astype(float)
r_full = opens.shift(-1) / opens - 1.0;  r_full.iloc[-1] = closes.iloc[-1]/opens.iloc[-1] - 1.0
fund   = funding.reindex(idx).fillna(0.0).astype(float).where(_is_8h_stamp(idx), 0.0)
```
— the **identical frozen expressions**, evaluated once; kept as float64
numpy arrays `r_v`, `fund_v`.

Per **fold** (once per (panel, taxonomy)):
- `oos_pos`: integer positions of
  `bars.index.intersection(fold.oos_idx)` in panel order (the exact
  `_restrict` result, positionalized).
- `hot_v`: the fold's vol-band hot mask as a bool array
  (`hot_mask.reindex(idx).eq(True)` semantics: NaN/missing ⇒ cold).
- Label codes: factorize the union of `_EpisodeShufflesW._base` and
  `._ep_labels` into shared integer codes once (`NaN` label → its own
  reserved code, preserving `_same_label`'s NaN==NaN semantics).
  Stored: `base_codes` (bar-level, used for frozen na positions),
  `ep_codes`, `ep_lengths`, `non_na`, `na_mask`, `orders` (read from
  the existing `_EpisodeShufflesW` instance — same draws, same RNG
  stream, nothing regenerated).
- Pooled ordering: run `pd.concat([...]).sort_index()` ONCE over
  per-fold `arange` payloads on the OOS indices to capture the exact
  output index and the permutation that maps concatenated fold segments
  to it. (Walk-forward OOS windows are disjoint, so this is a plain
  sort; capturing it from the frozen ops makes that an implementation
  detail we don't have to assume.)

Per **variant** (once):
- `act_by_code[c] = float(action_map.get(label_c, 0.0))`, NaN label
  ⇒ 0.0 — the exact `labels.map(action_map).astype(float).fillna(0.0)`
  scalar path, applied per unique label instead of per bar.
- `base_act`: bar-level actions of the frozen (na-position) labels.

### 4.2 Per (draw, fold) — all numpy, no pandas

1. **Labels → codes:** `bar_codes = base_codes.copy();`
   `bar_codes[~na_mask] = repeat(ep_codes[non_na[order]], ep_lengths[non_na[order]])`.
2. **`rules.apply`:** `w_raw = act_by_code[bar_codes]`; lag:
   `w = concat(([0.0], w_raw[:-1]))` (== `.shift(1).fillna(0.0)`).
3. **`apply_time_stop`** (ts6 variants only): the same state machine,
   ported verbatim to int codes — `lagged_codes = [NAN_CODE] + bar_codes[:-1]`,
   `_same_label(a,b)` ⇒ `lagged_codes[t] == lagged_codes[t-1]`,
   `_act(label) != 0` ⇒ `act_by_code[lagged_codes[t]] != 0.0`. Same
   branch structure, same outputs, no pandas scalars. (A run-length
   formulation over label-runs is a possible later 10x on this segment;
   NOT in v1 — one equivalence argument at a time.)
4. **`apply_vol_band`** (vb variants only):
   `w = np.where(hot_v, w * 0.5, w)`.
5. **Engine, returns-only:** preserve the frozen expression order
   exactly:
   ```
   dw = w - concat(([0.0], w[:-1]))          # diff with dw[0] = w[0]
   growth = (1.0 - np.abs(dw) * per_side) * (1.0 - w * fund_v) * (1.0 + w * r_v)
   seg = (growth - 1.0)[oos_pos]
   ```
   No equity cumprod, no trades, no turnover — none are consumed here.
6. **Pooling + Sharpe:** concatenate fold segments in active-fold
   order, apply the precomputed sort permutation, build ONE
   `pd.Series(values, index=pooled_index)` per draw, and call the
   **frozen `lab.metrics.sharpe`** on it. Empty active list ⇒
   `np.zeros(draws)` (frozen behavior).

### 4.3 Why this is bit-identical, not just close

- Every float64 value is produced by the same elementary operations in
  the same order on the same inputs (IEEE-754 determinism); we change
  *when* invariant subexpressions are evaluated, never *what* they are.
- Integer label codes change dict-lookup bookkeeping, not float values:
  each unique label goes through the identical
  `action_map.get → float → fillna` path exactly once.
- The final reduction (`mean`/`std(ddof=0)`) runs through the frozen
  `sharpe` on a Series with identical values in identical order —
  pandas' pairwise-summation behavior is therefore identical too.
- The RNG stream is untouched: we consume the already-constructed
  `_EpisodeShufflesW._orders`.

The two genuinely non-trivial equivalence claims — the time-stop port
and the pooling order — are exactly what the proof battery below
hammers.

## 5. Proof battery (the §9 "equivalence proofs")

Layer 1 — **unit bit-equality** (`tests/test_null_fast.py`):
- Property-style: randomized synthetic label/price panels (seeded),
  including adversarial shapes — episodes of length 1, all-na folds,
  empty OOS folds, NaN labels, k-boundary re-entry collisions (the
  rules_w boundary convention), zero-std OOS segments.
- For each: `np.array_equal(fast, frozen)` on the full `null_sharpes`
  vector — exact, zero tolerance.
- Real-panel spot check (marked slow): all registered variants on
  P-BTC/P-ETH/P-SOL, first 5 common draws, exact equality.

Layer 2 — **full-cell byte-diff** (`scripts/prove_null_fast.sh`):
re-run one completed calibration cell (P-BTC_5bps) with `W_NULL_FAST=1`
into a scratch out-root; `cmp` its `sweep_results_w.json` byte-for-byte
against the committed lane W-B artifact. The artifact is
byte-deterministic by construction, so this is a one-command proof over
81 variants x 1000 draws x 21 folds. With the fast path this rerun
costs ~25 min, not 2.4 h.

Layer 3 — **standing guard:** the Layer-1 suite runs in the normal
test run; `sweep_w` with the flag unset never imports the kernel, so
the frozen path cannot be perturbed by a kernel bug.

Acceptance = all three layers green. Any byte difference anywhere is a
kernel bug by definition — there is no "close enough" tier.

## 6. Integration

- `lab/sweep_w.py::_null_sharpes_w` gains a guarded branch:
  `if os.environ.get("W_NULL_FAST") == "1": return null_fast.pooled_null_sharpes(...)`.
  Flag unset ⇒ the existing code path, character-for-character.
- stdout (not the artifact) prints
  `[sweep_w] null path: fast (proof: docs/plans/2026-06-12-null-fast-design.md)`
  when enabled, so logs disclose provenance.
- Registration posture: after Layers 1–2 are green and committed, a
  future lane's pre-registration can cite this document + the proof
  artifacts and register the fast path explicitly, closing the §9 gap.
  Until a lane does that, production runs keep the flag unset.

## 7. Expected effect

Measured baseline ~30 ms per (draw, fold) iteration (non-profiled).
Kernel estimate: ~0.3 ms (plain variants) / ~2.5 ms (ts6, bar-loop
time-stop), Series+sharpe ~0.3 ms per draw. Per-cell null phase drops
from ~5.5 CPU-hours to ~10–20 CPU-minutes (~20–40x); cell wall time
becomes dominated by the untouched guarded evals + cell calibration —
roughly 3 h → 20–30 min per cell, the 9-cell chain ~26 h → ~3–4 h.

## 8. Risks

- **Time-stop port divergence** — highest-risk item; mitigated by the
  adversarial Layer-1 cases and by porting the loop branch-for-branch
  rather than "optimizing" its logic in the same change.
- **Pandas version drift** could change `sort_index`/reduction
  internals between proof time and use time — mitigated: `uv.lock`
  pins the environment; Layer 2 re-runs cheaply after any bump.
- **Scope creep** — the kernel must never grow gate/trade logic; if a
  future lane needs fast trades, that is a separate design with its own
  proof.

## 9. Proof results (2026-06-12) — the equivalence note

Registration context: the widening pre-registration §9 records "NO
performance shortcut — the §9 equivalence proofs do not exist". They now
exist. This section is the equivalence note a future lane's
pre-registration cites to register the fast path (`W_NULL_FAST=1`)
explicitly; until a lane does that, production runs keep the flag unset.
The registration document itself is not amended (it is the frozen record
of what was true at OOS contact).

**Layer 1 — unit bit-equality** (`tests/test_null_fast.py`): green.
Covers plain/ts/vb/combined Variants, na-frozen episodes,
genuine-NaN + unknown labels, length-1 episodes, empty-OOS and all-na
folds, zero-std segments, randomized property sweeps (5 panel seeds, 8
time-stop seeds), the time-stop port branch battery (boundary-convention
collision, k=1, all-na, NaN transitions), the frozen ValueError
mirroring, the index-mismatch refusal, and the integration seam (toy
`run_w_sweep` artifact byte-identical flag-on vs flag-off vs
flag-on+fork-pool). Real-panel spot check (env-gated
`W_NULL_FAST_REALPANEL=1`): all 183 registered Variants on
P-BTC/P-ETH/P-SOL, first 5 common draws — frozen vs fast bit-identical
(`checked == 183` asserted; run 2026-06-12, `1 passed in 484.73s`).
Full repo suite green with the flag unset (539 passed, 1 skipped — the
skip is this env-gated check). An independent fresh-context verifier
pass re-ran the battery and its own differently-seeded probes: same
verdict.

**Layer 2 — full-cell byte-diff** (`scripts/prove_null_fast.sh`): the
lane W-B P-BTC_5bps calibration cell re-run with `W_NULL_FAST=1` into a
/tmp scratch root, `cmp` against the cell of record
(`artifacts/w/calibration/P-BTC_5bps/sweep_results_w.json`, 81 Variants
x 1000 draws x 21 folds). Reference provenance: that cell was produced
2026-06-11 07:14-09:40 UTC by the lane W-B chain — BEFORE this kernel
or the `W_NULL_FAST` branch existed in the tree — and the committed
blob (commit fbf728d) is sha256-identical to the on-disk reference
(f08342f090b2857c578de1806cd434a849add27388e71957cc1d0dee093eb545), so
the reference is frozen-path by construction.

Result (run 2026-06-12, `scripts/prove_null_fast.sh BTC 5 6`):

```
[prove] start 2026-06-12T01:53:08Z
[w-cal] P-BTC 5bps done in 1343.6s: gate passes 12/81 ->
        <scratch>/P-BTC_5bps/sweep_results_w.json
[prove] end 2026-06-12T02:15:32Z
[prove] BYTE-IDENTICAL: cmp silent for <scratch>/P-BTC_5bps/
        sweep_results_w.json vs artifacts/w/calibration/P-BTC_5bps/
        sweep_results_w.json
```

Verified independently of the script: a second `cmp` returned rc=0 and
both files hash to the same sha256
(f08342f090b2857c578de1806cd434a849add27388e71957cc1d0dee093eb545).
Gate passes 12/81 — identical to the cell of record, as the byte
identity requires.

**Layer 3 — standing guard:** with the flag unset, `lab.sweep_w` never
imports the kernel (subprocess-pinned in the Layer-1 suite); the frozen
path runs character-for-character.

**Measured speedup** (this VPS, 2026-06-12, real P-BTC panel, TD cell,
21 active folds, single process; frozen timed over 20 draws, fast over
200; bit-equality asserted on the common prefix):

| Variant (registered id) | frozen ms/draw | fast ms/draw | speedup |
|---|---|---|---|
| `P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0` | 565.7 | 3.3 | ~169x |
| `P-BTC-DIR-TD-D1-fade_extremes_graded_sym-1.0-ts6` | 904.7 | 29.6 | ~31x |
| `P-BTC-RISK-TD-ladder-1_0.5_0_1_0.5_0-vb` | 388.0 | 3.8 | ~102x |

Per-Variant 1000-draw null phase: ~6-15 min -> ~3-30 s. The §7 estimate
(~20-40x) was conservative for plain/vb Variants; ts6 lands in-range
(the verbatim bar-loop port dominates, as designed — the run-length
reformulation remains future work with its own proof).

**Cell wall time:** the committed P-BTC_5bps cell cost 8,803 s
(2h26m43s, `--jobs 6`, 2026-06-11 chain log 07:14:04Z -> 09:40:47Z).
Fast-path rerun, same `--jobs 6` on the same VPS: **1,343.6 s (22m24s)
— 6.6x at the cell level** (per-taxonomy: TD 333.5s / TE 530.9s /
TF 123.3s / TG 200.1s / TH 155.6s). Both runs carried this box's usual
background load; the rerun additionally overlapped ~2 min of a test-
suite execution. Residual time is the untouched out-of-scope work — the
guarded per-Variant evaluations and the §8 cell calibration (serial,
frozen path) now dominate, per §2/§7; a 9-cell chain at this rate is
~3.4 h vs the measured ~26 h.
