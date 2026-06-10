# BNB HACK 2026 — Track 2: Regime-Switched Derivatives-Positioning CMC Skill

A Track 2 entry for the BNB HACK: AI Trading Agent Edition. Three units:

1. **Backtest Lab** (`lab/`, `tests/`) — a TDD'd, fully reproducible backtest harness over committed CSV data; variant sweep selected on train, gated on a purged/embargoed walk-forward (see `docs/adr/001`).
2. **The Skill** (`skills/`) — a `SKILL.md` strategy spec driven exclusively by live-verified CoinMarketCap MCP fields, with frozen, walk-forward-validated thresholds.
3. **Demo + Report** (`demo/`, `docs/report/`) — live CMC MCP regime classification → strategy spec block, plus the validation report with its falsification chapter.

Domain vocabulary: `CONTEXT.md`. Methodology: `docs/adr/001-select-on-train-gate-on-oos.md`. Build plan: `docs/plans/2026-06-10-bnbhack-t2-build-plan.md`.

Full README (quickstart, results, reproduction) lands with the final submission.
