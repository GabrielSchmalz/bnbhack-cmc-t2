# DoraHacks Submission Package — Track 2

Paste-ready content for the DoraHacks form (`https://dorahacks.io/hackathon/bnbhack-twt-cmc`).
**Operator action required: submit before 2026-06-21 12:00 UTC (target: by Jun 19).**
**Completion gate (FREEZE-W amendment 5): SATISFIED 2026-06-12** — the
gate-power text below is filled from the `bnbhack-wcal` readout
(`docs/report/adversarial/w_lane2_power_readout.md`), produced against the
pre-registered protocol in `docs/report/adversarial/w_lane2_launch_note.md` §5.

## Form fields

**Project name:** BTC Funding-Regime Monitor — a falsification-first Track 2 entry

**Track:** Track 2 — Strategy Skills (no on-chain step)

**Repo URL:** https://github.com/GabrielSchmalz/bnbhack-cmc-t2

**Demo video:** https://github.com/GabrielSchmalz/bnbhack-cmc-t2/blob/main/docs/demo/demo.mp4
(live CMC MCP call → frozen classifier → regime + monitor block, then the
falsification figures. Or run it yourself: `uv sync` then
`uv run --no-sync python demo/run_demo.py`.
The committed video covers the floor cycle; re-rendering it to the two-layer
story is an operator step — see checklist.)

**One-paragraph pitch:**

> Most backtest-driven entries will show you their best curve. We pre-registered
> a shipping gate — out-of-sample beats HODL and flat after 10 bps costs, and
> survives a regime-shuffle null, top-trade removal, and a cost ladder — swept
> 36 regime-switching variants on a purged, embargoed walk-forward over 14
> months of 4h BTC data, and got an honest null: **zero passed**, verified by a
> bit-for-bit independent re-implementation and a planted-edge calibration.
> Then, instead of submitting the null, we widened: ~5× the variants (183
> evaluated), three assets (BTC/ETH/SOL), ~5–6-year multi-regime panels
> (pooled OOS ≈ 4.3–4.8 years per panel), the **same gate plus three
> stricter clauses** — pre-registered
> before any OOS contact, with a quarantine lock on the one hypothesis family
> our own deep replay had already burned. The widened gate found exactly **one
> effective passer** — that same burned fade family wearing its registered
> symmetric mirror — and the pre-registered lock **refused to ship it**: 88–92%
> of its PnL sits on the quarantined leg, its extremity-neutralized twin loses
> money, and it loses money outright on ETH and SOL. Everything else: a wider
> null — 31 of 32 effective hypotheses cleared nothing, on ~6.7× the original
> sample. What ships is a live CMC-MCP regime monitor whose every output
> carries `"validated": false`, plus every locked candidate published in full
> as falsification evidence. A shipping gate you obey when it says no —
> **twice** — is the product.

**Strategy explanation (longer field, maps to the 4 judging criteria):**

> **Technical execution.** A TDD-built backtest lab (498 tests green at the
> W-B calibration launch) over real multi-asset derivatives history: Binance funding and klines
> for BTC/ETH/SOL (one source per feature, end-to-end), bybit open interest and
> long/short snapshots, Deribit DVOL, CMC's own Fear & Greed series on the same
> key as the live Skill. Both sweeps reproduce from committed CSVs — no
> database, no API key needed: the floor in ~5 minutes
> (`uv run --no-sync python -m lab.sweep`), the 183-variant widening in ~5
> hours (`W_SWEEP_CONFIRM=registered uv run --no-sync python -m lab.sweep_w`
> — the env-var
> tripwire marks the registration's OOS-contact event). The Skill is
> live-validated against the CMC MCP: every `allowed-tools` entry resolves,
> every referenced field exists in live payloads (`demo/validate_skill.py`,
> exit 0, validation record committed).
>
> **Methodology (the differentiator).** Select-on-train / gate-on-OOS (ADR-001)
> on pre-registered W-panels (ADR-002): variants rank on train Sharpe only; OOS
> is a binary pass/fail through an 8-clause gate — the floor's five plus
> null-p99, a min-active-sample clause (≥ 60 trades, fold coverage, no single
> fold over 50% of PnL), and top-K-trade removal. Thresholds re-derive per fold on
> train slices only; the embargo is sized in regime episodes (E = 42
> everywhere); the headline sample unit is OOS regime episodes — 1,502 on the
> headline panel vs the floor's 225. Multiple testing is disclosed in advance
> and checked after: 175 gated variants ≈ 32 effective hypotheses; expected
> 0.32 effective null-p99 exceedances, observed 3 — all in the quarantined
> family's neighborhood, exactly the registered contamination signature. The
> hypothesis-family lock (predicate, counterfactual twin, PnL-share backstop)
> was registered before contact and fired on the only passer: twin net-negative
> in every dressing, 88–92% of PnL on the quarantined leg, 7-of-8-clause
> failures on both sibling assets. Three adversarial W lanes are committed: an
> independent re-implementation matching 731 artifact scalars at
> max |diff| = 0.0, an R3/era/null-mechanics audit, and a planted-edge power
> calibration of the W-panel gate — nine cells (3 panels × 5/10/25 bps/bar)
> through the unmodified pipeline: **BTC detects a planted conditional edge
> at 5 bps/bar robustly** (all four aligned dressings pass all 8 clauses and
> the aligned family holds top train rank, every rung), ETH and SOL only at
> 25 bps/bar marginally — so
> the entry reports its ETH/SOL nulls as constraining only ≳ 25 bps/bar
> edges, never as the absence of smaller ones. The calibration's one adverse
> finding is disclosed rather than buried: in a planted ETH world an
> out-of-family trend variant came out ship-eligible with no lock layer
> firing, so the family quarantine alone is not proof against secular-drift
> capture — the era-split and counterfactual disclosures are the blocking
> checks (`docs/report/adversarial/w_lane2_power_readout.md`).
>
> **Originality.** This is the judges' own example — "regime-detection Skill
> that switches strategy based on derivatives positioning" — taken seriously
> twice. The first cycle reported that the strategy-switching edge did not
> validate. When the operator asked for a winning edge, the second cycle
> widened the search under a *harder* gate instead of a softer one — and then
> obeyed its own pre-registered lock when the only passer turned out to be the
> burned family in a symmetric coat. The entry's wedge is falsification
> machinery that holds under the pressure of wanting a winner.
>
> **Real-world relevance.** A self-custody trader's agent can consume the
> monitor's JSON block (regime, signal snapshot, degraded flag, train-period
> expected-behavior notes — all `validated: false`) as context, with
> disclaimers machine-readable. The falsification chapter publishes every
> locked candidate with the exact lock layer that caught it, and a forward
> registration (24 variants, OOS from 2026-06-11 00:00 UTC, evaluable
> 2027-07-01 at the earliest) states exactly what evidence would make the
> locked family shippable. The protocol is the deliverable: it is what stops
> an agent from trading a burned signal that still looks good in-sample.
>
> **Demo.** `demo/run_demo.py` — one command: live CMC MCP fetch → frozen
> classifier → current regime + monitor block + the report figures. The video
> shows a real run.

**Special prize checkbox:** Best Use of Agent Hub — the Skill consumes ≥ 7
verified CMC tools with honest roles (classifier inputs are Gate-0-verified
Features only; derivatives/narratives/macro-event reads appear as labeled
display context — FREEZE-W §3), with the Gate-0 field-dump audit trail
(`docs/gate0/`); the F&G series is CMC end-to-end (Pro REST history backfill +
live MCP read, one vendor for lab and Skill).

## Operator checklist

- [x] **Completion gate (FREEZE-W amendment 5): DONE 2026-06-12.** All four
      gate-power slots (here, README "Cycle 2" results, REPORT §7.5, SKILL.md
      §7) are filled from the `bnbhack-wcal` readout, produced against the
      protocol in `docs/report/adversarial/w_lane2_launch_note.md` §5 and
      committed as `docs/report/adversarial/w_lane2_power_readout.md`
      (9/9 cells, zero failed runs, zero unit restarts).
- [ ] Regenerate the funding-basis calibration table in
      `skills/btc-funding-regime-monitor/reference_table.md` from
      `data/backfill/funding_calibration.csv` shortly before submitting (the
      cron appends 3×/day; the committed table reflects only the first five
      polls — the table itself prescribes this refresh), and re-assess the D1
      sign-disagreement trigger on the accumulated sample.
- [ ] Re-render the demo video to the two-layer story (the committed
      `docs/demo/demo.mp4` shows the floor cycle only); replace the file, or
      keep the floor video and say so in the form note. Optional: human-voiced.
- [ ] Submit on DoraHacks (form fields above) — **before Jun 19 for buffer**.
- [ ] Confirm repo is public and renders (README, figures, video).
- [ ] After the event: **rotate the CMC API key** (it transited a plaintext
      prompt) — per the standing secrets protocol.
- [ ] After the event: remove the calibration cron (same protocol) —
      `crontab -l | grep -v bnbhack-t2-calibration | crontab -`

## Residual disclosures (operator awareness, decided by builder agent)

- Git history retains the pre-scrub CONTEXT.md text (sibling-project names;
  no secrets — full-history scan clean, key never committed). HEAD is scrubbed.
  History was kept because the commit trail is build evidence for the panel —
  including the widening's pre-registration-before-OOS-contact commit order
  (feasibility flags at `6df12bb` before the sweep artifact at `74e6417`);
  rewriting it was judged worse than the mild name disclosure. Veto = rewrite
  history before submitting.
- The CoinGlass-relay convention-switch analysis is intentionally public as
  data-integrity evidence (see `docs/DATA_PROVENANCE.md`).
