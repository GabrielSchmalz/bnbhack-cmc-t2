# Phase-5 independent entry review — pre-merge / pre-publication audit

**Review commit:** `1673ac2` (HEAD of `widening` at review start;
reviewed that committed state only — the parallel session's null-fast
work, including the commits it landed on top of `1673ac2` while this
review ran (`4575ab6`, `d39e119`), is out of scope and was untouched).
**Date:** 2026-06-12.
**Lane independence:** this review was produced by a fresh-context lane
with no authorship stake in any reviewed document, artifact, or code
path. Method: every headline number in README.md, docs/SUBMISSION.md,
skills/btc-funding-regime-monitor/SKILL.md, docs/report/REPORT.md §7,
docs/FREEZE-W.md, docs/report/w_r3_supplement.md and the W lane reports
was traced to a committed artifact by direct JSON inspection
(`uv run --no-sync python`, scratch script since deleted); git-history
ordering, secrets, link targets, figures, demo commands, and the test
suite were checked independently. Findings ordered by severity.

---

## BLOCKER

**None found.** Specifically checked and clean:

- **No secrets at HEAD or in history.** No CMC key value anywhere
  (header *name* `X-CMC-MCP-API-KEY` appears only as documentation);
  full-history `-G` scans for key assignments and UUID-shaped strings
  are clean (only PNG binaries false-positive); ClickHouse references
  are credential-free `http://localhost:8123`; `.env` is gitignored
  (`.env.*` with `!.env.example`); `.env.example` contains an empty key
  slot only. The SUBMISSION residual-disclosure claim ("full-history
  scan clean, key never committed") is corroborated.
- **No honesty-contract violation.** Pre-registration order is provable
  from `git log`: registration `b76c324` → critic amendments `1790f30`
  … `28d7f77` → feasibility flags `6df12bb` → sweep artifact `74e6417`
  (strong order, exactly as claimed in SUBMISSION and REPORT §7.2).
  Gate clauses only ever added (artifact `reasons` carry exactly the
  floor's 5 + the 3 registered additions). Honest-N is quoted as regime
  episodes everywhere it appears. Every published candidate and every
  Skill emission path carries `"validated": false`. No placeholder
  power statement survives anywhere — all four FREEZE-W amendment-5
  slots are filled from the landed readout, and the freeze text itself
  was discharged additively (bracketed notes, frozen text unchanged).
- **No fabricated or drifted number found.** Every spot-checked scalar
  in the four gate-power slots, the Cycle-1/Cycle-2 results tables, the
  passer/lock/era/transfer blocks, and the lane-W-B readout matched the
  committed artifacts exactly (verification appendix below).

## MAJOR

### M1 — Stale lane-report enumerations: "readout pending" survives at HEAD in two places

The power readout landed and is correctly announced in README's Results
blockquote and REPORT §7.5 — but two enumerations authored before it
landed (commit `8e39245`) were not updated by the slot-filling commit
(`1673ac2`) and now contradict the same documents:

1. **README.md:254–259 (Methodology section):** says
   "`docs/report/adversarial/` — **six** committed lane reports: …
   `w_lane2_launch_note.md` (W-panel power-calibration design + readout
   protocol; **readout pending**), and `w_lane3_r3_audit.md` …".
   At HEAD there are **seven** committed lane reports, and the readout
   is not pending — it landed 2026-06-12 and is quoted 50 lines earlier
   in the same README (line 203 blockquote). A judge who reads
   top-to-bottom sees the entry announce a readout and then call it
   pending.
   **Fix:** "seven committed lane reports: … `w_lane2_launch_note.md`
   (power-calibration design + readout protocol, committed before any
   result existed), `w_lane2_power_readout.md` (the 9/9-cell readout
   against that protocol), and `w_lane3_r3_audit.md` …".
2. **docs/report/REPORT.md:527–531 (§7 intro):** "Every number below is
   re-derivable from `artifacts/w/sweep_results_w.json` …, the **three**
   lane reports under `docs/report/adversarial/`
   (`w_lane1_reproduction.md`, `w_lane2_launch_note.md`,
   `w_lane3_r3_audit.md`), or the evidence supplement …". This
   provenance claim is now false: the §7.5 gate-power numbers derive
   from `w_lane2_power_readout.md`, which is absent from the list (the
   launch note deliberately contains no results).
   **Fix:** add the readout — "the four lane reports … and
   `w_lane2_power_readout.md`".

Severity rationale: not a number error and not contract-violating
(the stale text under-claims rather than over-claims), but it is an
internal contradiction in the two most judge-read documents and it
mislabels the entry's single newest piece of evidence as missing. Must
fix before push; the fix is two sentences.

## MINOR

### m1 — "~5–6 years of multi-regime OOS" conflates panel span with OOS span

Panel spans are 6.19y (P-BTC/P-ETH) and 5.69y (P-SOL). The OOS itself
is smaller: calendar span of the OOS segments ≈ 5.2y (BTC/ETH, first
OOS bar 2021-04-08) and ≈ 4.7y (SOL); pooled OOS duration is 10,494
bars ≈ 4.8y (BTC/ETH) and 9,480 bars ≈ 4.3y (SOL). ADR-002's own
phrasing — "W-panels (three assets, ~5–6-year **spans**)" — is the
accurate form; the judge-facing docs morphed it into "~5–6 years of
multi-regime **OOS**":

- README.md:25 ("~5–6 years of multi-regime OOS")
- SKILL.md:44 (description), :340 (disclaimer string), :390 (§7)
- docs/SUBMISSION.md:33–34 (pitch), :68 (implied via "headline panel")
- docs/report/REPORT.md:659, :976, :984

A hostile judge who multiplies 10,494 × 4h will get 4.8 years and ding
the precision of an entry whose entire wedge is precision.
**Fix (pick one, apply consistently in non-frozen docs):** "~5 years of
pooled multi-regime OOS on ~6-year panels", or keep "~5–6-year panels"
and say "pooled OOS ≈ 4.3–4.8 years (19–21 quarterly folds)".
FREEZE-W §2 carries the same phrase but is frozen — leave it; the
freeze quotes episode counts as the binding sample unit anyway.

### m2 — "all four aligned dressings pass all 8 clauses … train rank #1" invites a distributive misread

In the BTC cells the four D1 dressings hold train ranks 1/4/2/3 at
5 bps but 1/2/6/7 at 10 bps and 1/2/11/10 at 25 bps — only the 1.0
dressing is ever #1; the correct claim (readout headline, REPORT §7.5)
is "all four dressings pass all 8 clauses **and the aligned family
holds train rank #1** in all three cells". Three compressions read as
if each dressing ranked #1:

- README.md:200 (table row: "all four aligned dressings pass all 8
  clauses at every rung {5, 10, 25}, train rank #1") and :207–209
  (blockquote: "all four aligned dressings pass all 8 clauses with
  train rank #1 at every rung")
- SKILL.md:427–429 ("all four aligned dressings pass all 8 clauses at
  every rung, train rank #1")
- docs/SUBMISSION.md:80–82 ("all aligned dressings pass all 8 clauses,
  top train rank, every rung")

All underlying facts verified true; only the wording over-compresses.
**Fix:** adopt the readout's phrasing ("… and the aligned family holds
train rank #1 at every rung") in all four spots.

### m3 — reference_table.md prescribes a pre-submission step the operator checklist omits

`skills/btc-funding-regime-monitor/reference_table.md:153–154`: "…this
table should be regenerated from the CSV before submission." That step
appears nowhere in the SUBMISSION.md operator checklist (which does
carry the post-event cron-removal and key-rotation steps). The cron is
still appending (~3×/day), so the committed 5-poll snapshot will be
visibly stale by submission day.
**Fix:** either add a checklist line ("regenerate the
reference-table calibration snapshot from
`data/backfill/funding_calibration.csv` before submitting") or soften
the reference-table sentence to the post-event refresh framing the rest
of the file uses. Note: regenerating means committing the cron-appended
CSV — coordinate with the parallel session that currently owns the
working-tree changes to that file.

## NIT

### n1 — `uv run python` vs `uv run --no-sync python`

docs/SUBMISSION.md uses `uv run python …` (lines 20, 55, 56–57) where
README/REPORT consistently use `uv run --no-sync python …` after an
explicit `uv sync`. Both work; pick one form (README's pairing is the
deliberate one).

### n2 — README.md:27–29 phrasing

"…a hypothesis-family quarantine registered in advance on the one
family the first cycle had already **burned through evaluation**" —
garbled compression of "burned via evaluation contact (the H8 deep
replay)". Suggest rewording; a judge can parse it, but it reads like a
typo in the entry's third paragraph.

### n3 — Threshold rounding in README prose

README.md:223 quotes `funding_hi_abs = 8.3856e-05` (rounded) where the
frozen value is `8.385600000000002e-05` (SKILL.md, FREEZE.md, REPORT
quote it in full). Meaning is preserved and SKILL is the binding
surface; optionally add "(= 8.385600000000002e-05 frozen)" for exact
grep-ability.

---

## Verification appendix (what was checked and found CLEAN)

**Claims-vs-artifacts (all exact unless noted):**

- `artifacts/w/sweep_results_w.json`: 183 evaluated / 175 gated
  (73/51/51 per panel) / 8 annex / 24 forward-recorded / 32 effective
  hypotheses / 4 passes (the four D1 dressings) / family_locked_count 4
  / ship_eligible_count 0. Passer table (Sharpe 0.6769/0.6791/0.8108/
  0.8110; nets +39.21/+83.09/+31.15/+67.71%; trades 381/384/405/405;
  nz bars 4,492/4,482/1,541/1,541; top5/topK incl. the
  +0.000608205257158767 margin, K 8/8/9/9; max fold contribution
  0.4202/0.4326/0.4713/0.4898; null q95/q99 to 4 dp). Lock numbers
  (twin nets −0.0377/−0.0826/−0.0468/−0.0982; twin Sharpes
  −0.1593/−0.2302; layer-3 shares 0.8832/0.8845/0.9241/0.9241). Era
  split (8,094/2,400 bars; nets and 324–348/57 trades; pre/post clause
  fails exactly as REPORT §7.3 states, incl. "0.5 passes all 8 pre").
  Crash-day counts 1/1/1/3/1 = 7 for all four. Transfer: D1 fails 7/8
  clauses in all 8 ETH/SOL dressings, nets −1.04…−53.64% (ETH),
  −41.66…−45.23% (SOL). HODL benchmarks bit-exact
  (0.10295…/−0.37658…; 0.22331…/−0.41536…; 0.28391…/−0.57453…).
  honest_N table (1,502 headline + all 12 other cells), embargo E = 42
  in all 13 cells. R3: clause-3 23/175, clause-6 8 nominal = 3
  effective structures (D1, E2, E3 — all P-BTC), per-cell calibration
  13/13 values (nine 0.0, max 0.02, MC SE ≤ 0.0099). Annex: all-8-fail
  pattern incl. A2-0.5-ts6 failing only topk (−0.0538) and A2-0.5 fold
  concentration 0.5374.
- `artifacts/w/structural_feasibility.json`: 183 records, 65 flagged;
  breakdown T-F 30 / T-G 18 / T-H 10 / T-D 6 / T-E 1 — matches REPORT
  §7.2 and FREEZE-W §2; effective denominator 110.
- **Nine calibration artifacts:** cell pass counts 12/16/23 of 81 (BTC)
  · 0/2/8 of 51 (ETH) · 0/0/6 of 51 (SOL); ship_eligible 0 in eight
  cells, 1 in P-ETH_10bps. Aligned-passer census: 20 D1 passers, layer
  2 locks 13/20 (escapee identities match the readout), layer 3 locks
  20/20, SOL-25 1.0-ts6 share 0.500943. Train ranks: BTC-5 D1 ranks
  1/2/3/4 with rank keys to 5 dp; ETH-25 G2-0.5 3.24250 outranks D1
  2.98537; ETH-10 D1 ranks 3/7/30/32; SOL-25 top-5 ordering. Escapee
  `P-ETH-DIR-TG-G2-trend_crowding_filtered-1.0`: passes all 8 (Sharpe
  1.259864, net 11.17592, net@20 5.34617, 448 trades, topK 0.550344
  K=9, p95/p99 1.09888/1.25147), no lock layer fires (twin 1.33002
  passes; layer-3 share 0.459060), sister G2-0.5 locked at 0.547397;
  planted era split 7.18860/314 → 0.486935/134 with the five post-era
  clause fails; 0-rung counterfactual fails the gate (top5 −0.468209,
  topk −0.674496, max fold contribution 1.51025). Every number the
  readout, README, REPORT §7.5, SKILL §7 and SUBMISSION quote from this
  lane is exact.
- `artifacts/sweep_results.json` (floor): 36/0/0.0500 R3, top-variant
  null full-gate rate 0.015, TC honest_N 225 (TA 250, TB 105), HODL
  −2.0963/−45.90%, near-miss Sharpe 2.3763/2.3761, nets +7.56/+15.50%,
  30 trades, top5_net −1.03/−2.13%, null_p95 2.2589, ladder
  +17.25/+15.50/+12.09% — all as quoted in README/REPORT.

**Hygiene:**

- Internal links: every repo path referenced from the judge-facing docs
  resolves at HEAD; all six REPORT figures exist; `docs/demo/demo.mp4`
  committed (4.2 MB, real file). Demo/repro commands all reference
  committed entry points (incl. the `W_SWEEP_CONFIRM` tripwire, present
  in `HEAD:lab/sweep_w.py`).
- Key handling: `scripts/mcp_client.py` and `demo/run_demo.py` read the
  key from env/.env only and never print it (explicit comments to that
  effect); README Security section claims match the code.
- Tests: `uv run --no-sync python -m pytest -q` at review time → 539
  passed, 1 skipped (92 s). That includes 39 tests from the parallel
  session's uncommitted `tests/test_null_fast.py`; the committed-at-HEAD
  suite is therefore ~501 collected, all green. No document claims a
  current count; SUBMISSION's "498 tests green at the W-B calibration
  launch" is correctly time-stamped (matches the launch note).
- Agent Hub claim: SKILL `allowed-tools` lists exactly 7 tools; the
  live validation record `docs/gate0/skill_validation_run_w.json`
  verifies all 7 (`tool_results_ok` / `field_paths_ok` true); the
  "≥ 7 verified tools" phrasing is consistent across README, SUBMISSION,
  SKILL, FREEZE-W §3, REPORT §7.6.
- Story coherence: README leads with the two-layer story; the wider-null
  + power-qualification framing is consistent across README, SUBMISSION,
  SKILL, and REPORT §7; the BTC-informative-to-~5-bps result (the
  strongest sellable fact) is surfaced in all four power slots, and the
  P-ETH 10 bps escapee is disclosed as a lock-scope defect — with
  identical framing — in all four. Nothing oversells beyond the readout;
  nothing undersells the BTC null.

---

## Verdict

**Ready to merge/push after fixing M1** (the two stale lane-report
enumerations — README.md:254–259 and REPORT.md:527–531), with
m1–m3 (OOS-span precision, "train rank #1" phrasing, reference-table
checklist gap) strongly recommended in the same pass and n1–n3 at the
author's discretion. No blocker: claims trace to committed artifacts
exactly, the honesty contract is provable from git, and the repo is
secret-clean at HEAD and across history.
