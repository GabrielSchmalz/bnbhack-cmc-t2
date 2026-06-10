# BNB HACK T2 — Regime-Derivatives Skill

Bounded context for the BNB HACK 2026 Track 2 entry: a backtest lab, a distilled
regime classifier, and a CMC Skill submission artifact. Spec of record:
`hermes/docs/superpowers/specs/2026-06-10-bnbhack-t2-regime-derivatives-skill-design.md`
(decisions G1–G10). This vocabulary is NOT cryptarista's or hermes's — qualify
on contact (see Flagged ambiguities).

## Language

**Regime**:
The shipped classifier's output label — a composite of a positioning-stress
axis and a direction axis, computed from verified CMC MCP fields into a small
closed enum (3–5 labels; names frozen at parameter freeze).
_Avoid_: band (that's the lab training label), market regime (cryptarista
engine sense), regime_router (polymarket sizing config)

**Band**:
An rm17-derivs tercile label (region01/02/03 = balanced / squeeze_prone /
stressed) from `regime_matrix_labels` — direction-less (`|ln(LS)|`), lab-side
training label only, never shipped.
_Avoid_: regime (for bands), region (bare — always qualify with `run_version`)

**Lab classifier**:
The discovery-phase model trained against Bands on ClickHouse data — any form,
throwaway, never shipped or claimed.
_Avoid_: the classifier (bare — ambiguous with distilled), prototype model

**Distilled classifier**:
The closed set of CMC-computable rules with frozen absolute thresholds — the
only classifier validated end-to-end (the shipping gate runs on it) and the
only one shipped.
_Avoid_: live classifier, production classifier

**Threshold freeze**:
The event after the variant sweep when distilled thresholds and ruleset
parameters lock; any change after it requires full re-validation.
_Avoid_: parameter lock, calibration

**Reference table**:
The lab-derived percentile→absolute mapping shipped in the Skill folder with a
documented refresh procedure — a maintenance artifact for humans; the Skill
NEVER consults it at runtime.
_Avoid_: lookup table, runtime table

**Family**:
One of exactly two top-level partitions of variant space: the direction family
(crowded→fade, trending→follow) or the risk-switching family (exposure/carry
switching, direction-agnostic).
_Avoid_: rule family (polymarket sense: directional/scalper/arb), strategy type

**Variant**:
One complete candidate strategy — `(family, regime taxonomy, per-regime
ruleset, parameter vector)` — evaluated end-to-end through the fixed G8
execution model; the atomic unit that passes or fails the shipping gate.
_Avoid_: strategy (overloaded everywhere), config, candidate (research-scaffold
sense)

**Survivor**:
A variant that passed the shipping gate.
_Avoid_: winner (reserved for the one that ships), passing variant

**Honesty hooks**:
The falsification battery run on a variant: regime-shuffle null, top-5-trade
removal, cost ladder {5, 10, 20} bps.
_Avoid_: falsification section (that's the report chapter that PRESENTS them),
robustness checks

**Shipping gate**:
The binary predicate a variant must pass to ship: OOS beats HODL AND beats
flat after 10 bps RT AND all honesty hooks pass. Evaluated on OOS only.
_Avoid_: gate (bare — cryptarista has four other gate senses), G4 (spec
shorthand, not a term)

**Winner**:
The single survivor that ships in the Skill — the highest train-ranked
survivor, NOT the best OOS curve (see ADR-001).
_Avoid_: best variant, champion

**Gate 0**:
The day-1 field dump of all 12 CMC MCP tools that freezes the distilled
classifier's input set to verified fields only.
_Avoid_: data audit, recon

**Full-stack window**:
2025-04→2026-06 with the complete positioning field set — the ONLY domain for
sweep, selection, and the shipping gate.
_Avoid_: Tier 1 (collides with Public API billing tiers), primary data

**Deep-history window**:
2021→2026 with the reduced field set (funding, DVOL, CVD, price) — robustness
replay only, never a selection or gating domain.
_Avoid_: Tier 2, multi-year backtest (implies the Winner ran there — it can't)

**Deep-history proxy**:
The Winner's rules restricted to deep-history fields — a DIFFERENT strategy
from the Winner by construction; its results are robustness evidence, never
the Winner's track record.
_Avoid_: the Winner on Tier 2, extended backtest, long-run curve

**The Skill**:
Our submission artifact — the `SKILL.md` folder consumed client-side by any
MCP-capable agent pointed at the CMC MCP. The folder name is a **placeholder**
until threshold freeze — do NOT bake a family (e.g. "…-momentum") into it before
the sweep picks the Winner's family.
_Avoid_: "backtestable strategy spec" (contest-brief external alias), Hub
skill, agent (the Skill has no runtime of its own)

**Hub skill**:
A CMC-hosted Skill-Hub skill (reached via `find_skill`/`execute_skill`) — we
recon them for differentiation; our entry is NOT one.
_Avoid_: hosted skill, CMC skill (ambiguous with The Skill)

**Design spec**:
The locked design document (G1–G10) at
`hermes/docs/superpowers/specs/2026-06-10-bnbhack-t2-regime-derivatives-skill-design.md`
— lives outside this repo.
_Avoid_: the spec (bare — collides with strategy spec block), plan

**Strategy spec block**:
The fenced JSON object the Skill emits at runtime: `{regime, signal_snapshot,
active_ruleset, entry/exit/sizing, dd_guard, validated_metrics_ref,
disclaimers}`.
_Avoid_: output spec, trade spec, the spec (bare)

**Feature**:
One CMC-computable classifier input (funding z-score, OI change, F&G, price
TA, …) — frozen to Gate-0-verified fields.
_Avoid_: signal (five conflicting senses across cryptarista — banned in this
repo), indicator, factor

**Signal snapshot**:
The set of feature values fetched live at invocation time, echoed verbatim in
the strategy spec block. Fixed JSON key `signal_snapshot` — a field name, not
license to say "signal" elsewhere.
_Avoid_: market snapshot, signals (plural, bare)

**Operator**:
The human (Gabriel): owns decisions, registration, submission. NOTE the
cross-repo flip — in hermes docs "operator" means the agent; here it means the
human (see Flagged ambiguities).
_Avoid_: executor (cryptarista exchange adapters + our fill simulator), user

**Consuming agent**:
Any MCP-capable agent (Claude, Cursor, Trust Wallet Agent Kit) that invokes
the Skill against the CMC MCP.
_Avoid_: the agent (bare), client

**End trader**:
The self-custody trader persona who operates a consuming agent — the
"real-world relevance" user the panel scores against.
_Avoid_: customer, end user

**Lab**:
Unit 1 — the local backtest apparatus over read-only ClickHouse: harness,
sweep, validation. Throwaway relative to the submission; its OUTPUT (the
Winner's frozen parameters + report) is what matters.
_Avoid_: research scaffold (cryptarista context with a different evidence bar)

**Execution model**:
The fixed G8 trade mechanics shared by every variant: signal at close →
next-bar-open fill, 8h-aligned funding accrual, cost ladder, sizing bounds
0–1× equity, DD guard.
_Avoid_: market simulator, broker model

**DD guard**:
The trailing max-drawdown stop — fixed plumbing, one pre-registered structure
and threshold identical across all variants, never swept. Re-entry semantics:
open design detail for harness TDD.
_Avoid_: stop loss (per-trade concept; this is equity-curve-level), risk
parameter (implies sweepable)

**Benchmark**:
One of the fixed trio {HODL, flat, vol-target}, each computed under the SAME
execution model — vol-target trades and therefore pays the same costs and
funding.
_Avoid_: baseline (vague)

**Regime episode**:
One maximal run of consecutive bars sharing a regime label — the honest
sample-size unit (~102 episodes per 6yr at 4h in Phase-2 data; trades and bars
overstate N).
_Avoid_: regime instance, sample (bare)

## Relationships

- A **Regime** is distilled FROM **Bands** plus a direction axis; **Bands**
  never appear in the shipped Skill.
- The **Lab classifier** discovers structure; the **Distilled classifier** is
  its CMC-computable translation. The shipping gate validates ONLY the
  **Distilled classifier** — validated thing ≡ shipped thing (G1).
- After **Threshold freeze**, the **Distilled classifier** is immutable; the
  **Reference table** documents how a human would re-derive thresholds
  post-event, outside the Skill's runtime.
- A **Variant** belongs to exactly one **Family**. The sweep enumerates
  **Variants** on the **Full-stack window** ONLY; the **Deep-history window**
  is a robustness replay applied after selection, never a selection axis. The
  G8 execution model is fixed across all **Variants** — only rules and
  parameters vary.
- The **Deep-history proxy** replays on the **Deep-history window**; its curve
  and the **Winner**'s curve are reported separately, clearly labeled, and
  NEVER merged. The "multi-year" claim attaches to the proxy, phrased as
  rule-family consistency — never as the Winner's return history.
- The report discloses the total **Variant** count swept (the honesty story
  requires the denominator).
- **Honesty hooks** are a component of the **Shipping gate** (gate = OOS
  performance bar ∧ hooks). **Gate 0** is upstream of everything: it freezes
  the input fields the **Distilled classifier** may use.
- Selection is on train, gating is on OOS: the **Winner** is the highest
  train-ranked **Survivor** (ADR-001) — OOS is never a ranking key. ADR-001's
  2026-06-10 refinements bind: distillation thresholds are **train-only** (R1,
  anti-leakage vs the rm17 full-sample cuts), the gate runs on a
  **purged/embargoed walk-forward** with the OOS **Regime episode** count as the
  headline honest-N (R2), and gate multiple-testing is disclosed (R3).
- **Feature source-consistency:** each **Feature** uses ONE source across the
  full train+OOS span. The CoinGlass freeze (2026-05-18) and cg_cvd staleness
  (2026-05-29) fall INSIDE the OOS — prefer Binance-native series
  (`oi_snapshots`/`long_short_snapshots`) that span both; a mid-window source
  swap is a data-integrity hazard (it can mimic a regime shift), not a free fill.
- **The Skill** reads **Features** via CMC MCP tools, classifies a **Regime**,
  and emits a human-readable report plus a **Strategy spec block** whose
  `validated_metrics_ref` points at the **Winner**'s validation report — the
  Skill never computes or claims metrics of its own.
- The **DD guard** and **Benchmarks** belong to the **Execution model** —
  fixed across variants, never swept. Benchmarks pay the same costs and
  funding as variants.
- The **Lab** deliberately uses the contest evidence bar (shipping gate), NOT
  cryptarista's research-scaffold bar (Bonferroni/FDR) — locked in G3.
  Phase-2 nulls under the stricter bar are cited openly in the report, not
  hidden.

## Example dialogue

> **Dev:** "The sweep found a variant with a monster OOS Sharpe — ship it?"
> **Domain expert:** "Is it the highest TRAIN-ranked survivor? OOS is a gate,
> not a ranking key (ADR-001). If a lower-OOS survivor outranks it on train,
> that one is the Winner."
>
> **Dev:** "Can the Skill nudge its thresholds when funding regimes drift? The
> reference table is right there in the folder."
> **Domain expert:** "No. The distilled classifier is frozen at threshold
> freeze — the validated thing IS the shipped thing. The reference table is
> for a human refresh after the event, never consulted at runtime."
>
> **Dev:** "The deep-history curve since 2021 looks great — lead with it?"
> **Domain expert:** "That's the deep-history proxy, not the Winner — intraday
> OI doesn't exist before 2025-04. Two labeled curves, never merged; the
> multi-year claim is rule-family consistency, not the Winner's returns."
>
> **Dev:** "Which regime is BTC in? The band says squeeze_prone."
> **Domain expert:** "Bands are lab training labels — direction-less and never
> shipped. The Skill's regime is the distilled label computed from
> Gate-0-verified CMC features."

## Flagged ambiguities

- **"Operator" flips across repos.** In hermes, operator = Hermes-the-agent
  and the person is "human". In THIS repo, operator = the human (Gabriel) —
  there is no agent-operator here. The design spec physically lives in hermes
  docs but uses the bnbhack sense. When writing hermes-side docs about this
  project, say "human"; here, "operator" is correct.
- **"Executor" is banned in this repo.** The design spec header says
  "Executor: Claude Fable 5" (the building agent); cryptarista owns
  `ClobExecutor`/`FuturesExecutor`; our backtest harness will contain a fill
  simulator. Say **builder agent** for Fable 5, **fill simulator** for the
  harness component.

- Spec §5's `{crowded-long, crowded-short, trending, ranging}` are
  **placeholder names**, not the frozen taxonomy. The final enum is decided at
  parameter freeze from what the data supports. Bands alone cannot yield
  directional labels (absolute value kills the long/short sign).
- "regime" exists in three cryptarista senses (engine `regime/classifier.py`
  price-only labels, `regime_matrix_labels` regions, polymarket `regime_router`
  sizing config). In this repo, bare "regime" ALWAYS means the shipped
  distilled label.
