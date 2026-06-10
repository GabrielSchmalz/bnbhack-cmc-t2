# ADR-002 — Deep panels become gating domains for fully-covered Variant families

Date: 2026-06-10 · Status: accepted (widening cycle) · Supersedes part of
CONTEXT.md "Deep-history window" scope · Companion:
`docs/plans/2026-06-10-widening-preregistration.md`

## Context

CONTEXT.md (frozen build) pins: *"Deep-history window … robustness replay
only, never a selection or gating domain."* That rule existed for one
reason: the frozen build's Variants consumed positioning Features (intraday
OI/LS) that simply do not exist before 2025-04, so any pre-2025 replay of a
Winner's rules was **a different strategy by construction** — gating there
would have validated something other than the shipped thing (G1 violation).

The widening registers new Variant families whose **entire** Feature set
(funding sign/extremity bands, daily-OI change, F&G, RSI14, SMA200, price
percent-changes) has single-source coverage from 2020 onward. For these
families the constructive reason for the ban dissolves: the thing evaluated
on 2020–2026 is exactly the thing that would ship.

The alternative — keep gating only on the 14-month full-stack window — is
strictly worse on every axis the first build itself flagged: a
bear-dominated OOS, a near-vacuous beats-HODL clause, taxonomy-level
honest-N of ~225 episodes, and a low-power active-sample for any sparse
candidate (REPORT §6.1). Re-sweeping new variants on the same already-
published OOS would also compound multiple testing on one small window.

## Decision

1. A **W-panel** (widening panel) is a (asset, bar-grid, span, Feature-set)
   tuple in which every registered Feature of every Variant gated on it has
   one consistent source across the panel's full span (R-SRC), and every
   Feature is point-in-time live-computable from Gate-0-verified CMC fields.
2. W-panels ARE selection and gating domains: ADR-001 (select-on-train,
   gate-on-OOS; R1 train-only thresholds; R2 purged/embargoed walk-forward
   with regime-episode honest-N; R3 disclosure) applies to them unchanged.
3. CONTEXT.md's "Deep-history window" term keeps its meaning **for the
   frozen build's artifacts only** (the H8 deep replay remains falsification
   context, never a track record). New prose must say "W-panel" for the
   widening's gating domains.
4. The fade-pos-extreme **family lock stands**: REPORT §6.2 pre-committed
   that this BTC hypothesis family becomes shippable only on data created
   after 2026-06-09 20:00 UTC. No W-panel result can ship a Variant inside
   the lock predicate (exact predicate in the pre-registration §8). The
   lock is the published falsification protocol holding under pressure —
   it is not negotiable for a better-looking widening.

## Why gating on 2020–2026 history is honest here

- **No prior selection on it.** No variant was ever selected or gated on
  pre-2025-04 data; the single prior evaluation contact (the frozen-cut H8
  deep replay, REPORT §5) is published, family-locked, and disclosed in the
  pre-registration's prior-contact register.
- **Same protections as the frozen build.** The frozen build also gated on
  history it already possessed (2025-04→2026-06). The defense was never
  "the data is new"; it was pre-registration before OOS evaluation,
  mechanical clauses, train-only thresholds, and disclosed denominators.
  All of it carries over, plus three strictly-added clauses.
- **Hindsight-bias mitigation.** Era knowledge (2021 top, 2022 bear, 2024
  bull) is mitigated structurally, not rhetorically: families enter as
  mechanically-enumerated grids (no hand-picked parameter points), every
  threshold derives per-fold on train only, ~21 quarterly folds force any
  Survivor to earn its pass across bull, bear, and chop, and the
  min-active-sample clause kills single-era curves (no fold > 50% of net
  PnL).

## Consequences

- CONTEXT.md gains a qualifier under "Deep-history window" pointing here.
- The beats-HODL clause becomes a real bar again (the W-panel OOS includes
  bull years; HODL is strongly positive over 2021→2026) — the gate gets
  harder, which is the direction the widening contract demands.
- Honest-N rises from ~225 pooled-OOS episodes to an order of magnitude
  more (reported exactly after the sweep, per taxonomy and panel).
- A Survivor on a W-panel is a validated edge claim over 4–5 years of OOS
  segments under an 8-clause gate; a null over the same space is a much
  harder null than the frozen 0/36.
