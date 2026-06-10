# DoraHacks Submission Package — Track 2

Paste-ready content for the DoraHacks form (`https://dorahacks.io/hackathon/bnbhack-twt-cmc`).
**Operator action required: submit before 2026-06-21 12:00 UTC (target: by Jun 19).**

## Form fields

**Project name:** BTC Funding-Regime Monitor — a falsification-first Track 2 entry

**Track:** Track 2 — Strategy Skills (no on-chain step)

**Repo URL:** https://github.com/GabrielSchmalz/bnbhack-cmc-t2

**Demo video:** https://github.com/GabrielSchmalz/bnbhack-cmc-t2/blob/main/docs/demo/demo.mp4
(70s: live CMC MCP call → frozen classifier → regime + monitor block, then the
falsification figures. Or run it yourself: `uv run python demo/run_demo.py`.)

**One-paragraph pitch:**

> Most backtest-driven entries will show you their best curve. We pre-registered
> a shipping gate — out-of-sample beats HODL and flat after 10 bps costs, and
> survives a regime-shuffle null, top-5-trade removal, and a {5,10,20} bps cost
> ladder — then swept 36 regime-switching variants (direction and risk-switching
> families, three derivatives-positioning taxonomies) on a purged, embargoed
> walk-forward over 14 months of 4h BTC data. **Zero variants passed.** We then
> attacked our own null: an independent re-implementation reproduced every number
> bit-for-bit, and a planted-edge calibration proved the unmodified pipeline
> passes a real edge of ≥10 bps/bar — the gate works; the edges weren't there.
> What ships is exactly what was earned: a live CMC-MCP regime monitor with
> frozen, train-only thresholds whose every output carries `"validated": false`,
> plus the one near-miss published in full as a FAILED candidate (its 5 best
> trades were 114.8% of its OOS gain — precisely what the top-5-removal clause
> exists to catch). A shipping gate you obey when it says no is worth more than
> an OOS curve picked from 36.

**Strategy explanation (longer field, maps to the 4 judging criteria):**

> **Technical execution.** A TDD-built backtest lab (227 tests) over real
> derivatives-positioning history: Binance funding (REST, one source end-to-end,
> 2019→now), bybit open interest and long/short snapshots, Deribit DVOL, CMC's
> own Fear & Greed series. The entire backtest reproduces from committed CSVs
> with one command — no database, no API key needed (`uv run python -m lab.sweep`).
> The Skill is live-validated against the CMC MCP: every `allowed-tools` entry
> resolves, every field path the rules reference exists in live payloads
> (`demo/validate_skill.py`, exit 0, validation record committed).
>
> **Methodology (the differentiator).** Select-on-train / gate-on-OOS (ADR-001):
> variants rank on train Sharpe only; OOS is a binary pass/fail, never a ranking
> key. Thresholds re-derive per walk-forward fold on that fold's train slice only
> (anti-leakage); the embargo is sized in regime episodes; the headline sample
> size is OOS regime-episode count (225), not bars or trades. Multiple-testing is
> disclosed, not waved away: 36 variants, 0 passes, 5.0% expected null pass-rate.
> The adversarial review (three independent lanes, reports committed) reproduced
> the sweep bit-for-bit, measured the gate's detection power on planted edges,
> and characterized the near-miss as knife-edge in both directions.
>
> **Originality.** This is the judges' own example — "regime-detection Skill
> that switches strategy based on derivatives positioning" — taken seriously
> enough to report that, on this data and gate, the strategy-switching edge did
> not validate. The entry's wedge is honest falsification machinery: the gate,
> its calibration, and a monitor that refuses to claim what it could not prove.
> CMC's existing hub skills are descriptive evidence-packs; this one is an
> auditable validation pipeline with the verdict attached.
>
> **Real-world relevance.** A self-custody trader's agent can consume the
> monitor's JSON block (regime, signal snapshot, degraded flag, train-period
> expected-behavior notes — all `validated: false`) as context, with disclaimers
> machine-readable. The reference table documents how to re-derive thresholds on
> a new train window post-event. The falsification protocol in the report states
> exactly what evidence would make a future variant shippable.
>
> **Demo.** `demo/run_demo.py` — one command: live CMC MCP fetch → frozen
> classifier → current regime + monitor block + the report figures. The video
> shows a real run.

**Special prize checkbox:** Best Use of Agent Hub — the Skill consumes three
verified Agent Hub MCP tools with a Gate-0 field-dump audit trail
(`docs/gate0/`), and the F&G history backfill uses the same key on the Pro REST
API, keeping lab history and live reads on one source.

## Operator checklist

- [ ] Submit on DoraHacks (form fields above) — **before Jun 19 for buffer**.
- [ ] Confirm repo is public and renders (README, figures, video).
- [ ] After the event: **rotate the CMC API key** (it transited a plaintext prompt).
- [ ] After the event: remove the calibration cron — `crontab -l | grep -v bnbhack-t2-calibration | crontab -`
- [ ] Optional: re-record a human-voiced demo video; replace `docs/demo/demo.mp4`.

## Residual disclosures (operator awareness, decided by builder agent)

- Git history retains the pre-scrub CONTEXT.md text (sibling-project names;
  no secrets — full-history scan clean, key never committed). HEAD is scrubbed.
  History was kept because the commit trail is build evidence for the panel;
  rewriting it was judged worse than the mild name disclosure. Veto = rewrite
  history before submitting.
- The CoinGlass-relay convention-switch analysis is intentionally public as
  data-integrity evidence (see `docs/DATA_PROVENANCE.md`).
