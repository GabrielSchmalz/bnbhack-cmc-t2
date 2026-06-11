# Lane W-B — planted-edge power calibration: LAUNCH NOTE (readout pending)

**Status: LAUNCHED 2026-06-11 07:14 UTC.** This note records the design,
the alignment map, the rung set, the execution plan, and the readout
protocol BEFORE any calibration result exists. The readout happens in a
later session, against this note. Nothing here reads a calibration
output; the only numbers below are plant-construction stats printed at
panel build time and production-sweep wall times used for budgeting.

**Question.** The committed W-sweep
(`artifacts/w/sweep_results_w.json`, 183 evaluated, 4 gate passes — all
`P-BTC-DIR-TD-D1-fade_extremes_graded_sym` dressings, all family-locked,
`ship_eligible_count = 0`) is only interpretable if the unmodified W
machinery would DETECT a known regime-conditional edge of the same shape
on these panels. Registration §9 pins this calibration: lane-2 style,
once per panel, drift aligned with a registered map, labels/funding
untouched, rungs 5/10/25 bps/bar.

Binding spec: `docs/plans/2026-06-10-widening-preregistration.md` §6,
§7, §9. Frozen method replicated:
`docs/report/adversarial/lane2_gate_calibration.md` §1.

## 1. Design (lane-2 §1 mechanics, extended to the graded symmetric map)

- **Substrate:** the three REAL registered W panels (P-BTC / P-ETH /
  P-SOL spans per §1), rebuilt from the committed CSVs.
- **Aligned variant family:** T-D D1 `fade_extremes_graded_sym`
  (pos-mid 0, pos-hi −0.5, pos-x −1.0, neg-mid 0, neg-hi +0.5,
  neg-x +1.0) — the map behind all four committed gate passes.
- **Injection mask (decision-bar aligned):** T-D labels computed ONCE
  from FULL-WINDOW cuts of the unperturbed panel
  (c_hi = q60(|funding_rate_8h|), c_x = q90 — lane-2's mask convention).
  Bar t is masked iff label[t−1] is hot, mirroring the `rules.apply`
  1-bar lag (lane-2 probe (iii): the detection tent peaks at shift 1).
  T-D depends only on `funding_rate_8h`, which the price perturbation
  never touches, so the mask and labels are invariant under injection
  (asserted in tests and re-verified on the real P-BTC panel at launch).
- **Alignment map:**

  | decision-bar label (t−1) | D1 position at t | drift at t | leg earns |
  |---|---|---|---|
  | pos-hi / pos-x | short (−0.5 / −1.0) | −m_t (price down) | short |
  | neg-hi / neg-x | long (+0.5 / +1.0) | +m_t (price up) | long |
  | pos-mid / neg-mid | flat | 0 | — |

  The drift magnitude is FLAT across the hi/x rungs; only the variant's
  exposure is graded. D1's graded capture and D2's x-only capture are
  therefore both partially aligned; the readout records which dressing
  ranks where.
- **Drift draws:** m_t ~ Normal(edge, edge), `default_rng(99)` (lane-2
  seed, verbatim; noise sd = mean), one draw per masked bar in index
  order; d_t = +m_t on pos-masked bars, −m_t on neg-masked bars, 0
  elsewhere. Price multiplied by (1 − d_t).
- **Price path (lane-2 verbatim):** M_open[t] = Π_{s<t}(1−d_s),
  M_close[t] = M_open[t]·(1−d_t); open′ = open·M_open,
  close′ = close·M_close (the whole bar-t drift lands inside bar t);
  high/low scaled by M_close then enveloped to contain open′/close′.
  Engine identity r′[t] = (1+r[t])(1−d_t)−1 holds on the engine's
  open-to-open convention (test-pinned to 1e-12).
- **Fully consistent world:** the perturbation is applied to the RAW
  bars rows (warmup rows keep multiplier 1; post-span rows carry the
  final product and are trimmed) and the panel is REBUILT through the
  unmodified `panels_w.build_w_panel` with the original funding/fg/oi
  sources. pc_24h, rsi14_1d and close_vs_sma200_1d are therefore
  recomputed from perturbed closes; funding_rate, funding_rate_8h, fg,
  oi and volume are byte-identical to the committed panels.
- **Pipeline under test:** the UNMODIFIED `lab.sweep_w.run_w_sweep`
  through its documented `panel_loader` injection point — registered
  boundaries, all of the panel's registered taxonomies, per-fold R1
  thresholds, D = 1000 common draws, 200 per-cell calibration draws,
  full 8-clause gate, §6 lock layers, §8 era splits. One (panel, rung)
  per run.

Code: `lab/calibration_w.py` (toy-TDD, `tests/test_calibration_w.py`,
21 tests). Runner: `scripts/run_w_calibration.sh`.

## 2. Rung set and run matrix

Rungs (§9 registered): **5, 10, 25 bps/bar** of true conditional edge.
Cells: (P-BTC, P-ETH, P-SOL) × (5, 10, 25) = **9 sequential runs**,
`--jobs 6` each, output to
`artifacts/w/calibration/P-<ASSET>_<rung>bps/sweep_results_w.json`.
The committed `artifacts/w/sweep_results_w.json` is never written
(runner guard `_assert_isolated_out_dir`, test-pinned). The **0-rung
anchor is the committed sweep artifact itself** (lane-2 convention:
baseline contamination is disclosed, not hidden — every rung sits on
top of whatever real pattern produced the four locked passes).

Plant stats measured at launch (P-BTC, printed by the first cell):
**6,558 pos-masked + 246 neg-masked of 13,566 bars**; full-window cuts
c_hi = 1.000e-4, c_x = 2.223e-4; net log drift −3.184 at 5 bps/bar
(−6.37 at 10 bps from the pre-launch smoke).

## 3. Known consequences and adversarial caveats (stated before readout)

1. **Mask density ≈ 50%** — far denser than frozen lane-2's 18.2%. The
   q60 cut is inclusive and lands exactly on the Binance default rate
   (1e-4), so every default-rate funding bar is pos-hi. This is faithful
   to how the registered D1 actually trades (the committed passers hold
   roughly half of all bars), but it means the planted "conditional"
   edge is closer to a conditional carry than a rare-event edge.
2. **Severe leg asymmetry on BTC (6,558 vs 246 bars):** funding is
   overwhelmingly positive, so this calibration measures the SHORT
   leg's detectability almost exclusively. The long (neg-x/neg-hi) leg
   is essentially unpowered — a disclosed limitation, not fixable
   without deviating from the real funding history.
3. **Secular downtrend artifact:** net log drift −3.2/−6.4/−15.9 at
   5/10/25 bps over the P-BTC span (planted close ends at ×0.0017 of
   real at 10 bps). Per-bar this is small (≈ −2.4/−4.7/−11.7 bps/bar
   unconditional vs ≈ 120 bps/bar 4h noise), but pooled over years it
   mechanically (i) degrades HODL → beats_hodl becomes trivial,
   (ii) creates a trend that follow-the-downtrend shapes (T-G G1/G3
   legs, short-side ladders) can legitimately capture — lane-2's TB
   confound finding, expected to be stronger here. The readout MUST
   census which non-aligned variants pass, not just whether anything
   does.
4. **T-G/T-H labels shift in the planted world** (recomputed from
   perturbed closes). Consistent-world choice, same as lane-2's RSI/SMA
   recomputation; their per-fold thresholds and embargo E may differ
   from the committed run's. T-D/T-E/T-F labels are invariant.
5. **Single drift seed (99) per rung** — lane-2 limitation carried
   forward verbatim. Marginal passes at the smallest rung are edges of
   detectability, not reliable power.
6. **Tripwire scope:** the registered OOS-contact event already
   happened (committed artifact). These runs evaluate planted
   derivative worlds of the same rows; the sweep CLI tripwire is not
   re-armed, and `run_w_sweep` is called via its documented injection
   point exactly as the frozen lane-2 called `run_sweep`.

**Pre-stated prediction (falsifiable at readout):** even at 25 bps/bar,
any aligned passer should remain **family-locked by §6 layer 2** —
the twin neutralizes exactly the reference positive-extremity bars that
carry ~96% of the planted drift, so a TRUE in-family edge cannot
unlock. If a planted passer comes out ship-eligible, that is a defect
in the lock, not a success. The calibration therefore measures GATE
power (clauses 1–8 + train rank); lock behavior is a separate,
secondary observation about quarantine severity.

## 4. Execution record

- Module: `lab/calibration_w.py`; one cell =
  `uv run --no-sync python -m lab.calibration_w --asset <A> --rung <R>
  --jobs 6` (draws default 1000, cal 200 — registered values).
- Chain: `scripts/run_w_calibration.sh` — 9 cells sequentially in the
  order BTC{5,10,25}, ETH{…}, SOL{…}; **resumable** (a cell whose
  results file exists is skipped); all progress appends to
  `/tmp/w_cal_run.log`; exits nonzero if any cell failed so systemd
  retries only the unfinished cells.
- Detached unit (survives session death):

  ```
  systemd-run --user --unit=bnbhack-wcal --collect \
    -p WorkingDirectory=/home/arista/src/bnbhack-cmc-t2 -p Nice=10 \
    -p Restart=on-failure -p RestartSec=120 \
    -p StandardOutput=append:/tmp/w_cal_run.log \
    -p StandardError=append:/tmp/w_cal_run.log \
    bash scripts/run_w_calibration.sh
  ```

  Launched 2026-06-11 07:14:04 UTC, invocation
  `34319f5e2d9f4a4487638176e6d07816`; verified active in cgroup
  `/user.slice/user-1001.slice/user@1001.service/app.slice/bnbhack-wcal.service`
  with the fork pool up and memory ≈ 0.73 GB on the first cell (the
  lab/hooks_w.py lazy-draw materialization applies automatically; the
  production sweep peaked at 0.83 GB under the same settings).
- Monitor: `tail -f /tmp/w_cal_run.log`,
  `systemctl --user status bnbhack-wcal`. Stop:
  `systemctl --user stop bnbhack-wcal` (then re-launch the same
  command to resume).

**Wall budget.** Production per-panel cell walls (jobs 6, same box):
P-BTC 9,119 s, P-ETH 4,264 s, P-SOL 4,441 s → one full rung across the
three panels ≈ 4.95 h, × 3 rungs ≈ 14.9 h, plus per-run panel-rebuild
overhead → **expect ≈ 15–18 h total** (T-G/T-H cell times may drift in
the planted worlds; the budget is indicative, not binding). Expected
completion: 2026-06-11 late evening UTC.

## 5. Readout protocol (the numbers to extract, per (panel, rung))

From each `artifacts/w/calibration/P-<A>_<R>bps/sweep_results_w.json`,
compared against the committed 0-rung artifact:

1. **Aligned-variant train rank:** rank of the best D1 dressing (and of
   each of the four committed passer ids on P-BTC) among the cell's
   GATED variants by the §7 rank key, vs its 0-rung rank. Detection is
   credible when the aligned family reaches #1 (lane-2 standard:
   robust ≥ 10 bps).
2. **Gate clause margins for the top D1 dressing:** all 8 clauses with
   margins — net@10 (clause 1), Sharpe − HODL Sharpe (2),
   unguarded Sharpe − null_p95 / − null_p99 (3/6), top5 net (4),
   net@20 (5), trades / nonzero bars / covered-fold fraction /
   max fold contribution (7), topK net and K (8).
3. **Detection verdict per rung:** PASS iff ≥ 1 D1-aligned variant
   passes all 8 clauses; recorded alongside whether it is the cell's
   top train rank. Power statement in lane-2 form: "the W gate detects
   ≥ X bps/bar robustly / Y bps/bar marginally on panel P".
4. **Confound census:** every non-D1 gate passer (taxonomy, map,
   panel), interpreted against caveat 3 (secular-trend capture); count
   of T-D risk-ladder and T-G trend passers separately.
5. **Lock behavior on planted passers:** layer-1/2/3 verdicts; twin
   Sharpe and twin net deltas vs the passer; test of the §3 prediction
   (true in-family edge stays locked; ship_eligible must remain 0).
6. **R3 stability:** per-cell full-gate null-calibration rate and
   observed null p95/p99 exceedance rates at each rung vs the
   committed run (lane-2 found the null machine calibration unchanged
   by planting; null_p95 is expected to RISE with the rung — the
   episode-shuffle null inherits part of a window-wide edge, biasing
   toward false negatives, never false positives).
7. **Per-fold sanity:** flat-ish per-fold train Sharpes for the aligned
   variant (window-wide plant), F-coverage of the OOS capture, and the
   threshold-mismatch haircut (per-fold cuts vs the mask's full-window
   cuts).

Run by: adversarial lane W-B, 2026-06-11. Tests green at launch:
**498 passed** (477 baseline + 21 new toy tests). Nothing under
`artifacts/w/` outside `calibration/` is written; nothing was
committed to git (lane instruction).
