# demo/run_demo.py — the judge-facing one-command demo (W upgrade: the
# FREEZE-W §3 seven-tool surface; floor classifier untouched).
#
#   uv run --no-sync python demo/run_demo.py
#
# Does five things, live:
#   (a) fetches the seven verified CMC MCP tools and prints a human-readable
#       BTC funding-regime report (frozen TC taxonomy — classification from
#       the single funding field, exactly as on the floor);
#   (b) prints the fenced JSON monitor spec block exactly as SKILL.md §5
#       specifies — schema unchanged from the floor freeze (FREEZE-W §3
#       amendment 6); no active_ruleset / entry / exit / sizing — ever;
#   (c) prints the clearly-separated MARKET CONTEXT display section (labeled
#       context only, never branched on: quotes, TA, derivatives OI/liqs,
#       dominance/altseason, narratives, macro events, headlines);
#   (d) prints the two-layer validation headline — floor null
#       (artifacts/sweep_summary.md, 0/36) AND the W-sweep outcome
#       (artifacts/w/sweep_results_w.json globals.r3: 4 of 183 = 1 effective
#       hypothesis, family-locked, 0 ship-eligible, no Winner) — plus the
#       measured W gate-power statement (FREEZE-W §3 amendment 5, discharged
#       2026-06-12 by docs/report/adversarial/w_lane2_power_readout.md);
#   (e) locates the report figures (equity curves etc.) and prints their paths.
#
# The frozen threshold is parsed from SKILL.md (the contract of record); the
# inline fallback constant is verbatim from docs/FREEZE.md §2.2 (F4-train q80
# of |funding_rate_8h|, frozen 2026-06-10). Every tool call degrades per
# SKILL.md §6 — a failed tool produces a degradation message, never a
# traceback. Never print the API key.

from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SKILL_MD = REPO / "skills" / "btc-funding-regime-monitor" / "SKILL.md"
SWEEP_SUMMARY = REPO / "artifacts" / "sweep_summary.md"
SWEEP_W_JSON = REPO / "artifacts" / "w" / "sweep_results_w.json"
FIGS_DIR = REPO / "docs" / "report" / "figs"

# Fallback frozen constant — provenance: docs/FREEZE.md §2.2 (F4-train,
# verbatim full precision). SKILL.md §3 carries the same number; we parse it
# from there so the demo executes the Skill's literal contract.
FUNDING_HI_ABS_FREEZE = 8.385600000000002e-05
REGIME_ENUM = ("pos-mild", "pos-extreme", "neg-mild", "neg-extreme")

EB_SOURCE = ("F4-train descriptive statistics (2025-04-03..2026-04-01, "
             "2178 bars; next-bar open-to-open convention)")
# F4-train descriptive statistics — docs/FREEZE.md §2.3 / SKILL.md §4,
# verbatim; the ONLY numbers the notes may cite; all "validated": false.
EXPECTED_BEHAVIOR = {
    "pos-mild": {
        "bars": 1356, "share_pct": 62.3, "episodes": 184,
        "median_episode_len_bars": 4,
        "next_bar_mean_return_pct": -0.005, "next_bar_median_return_pct": 0.019,
        "pct_negative": 48.8, "annualized_vol": 0.41,
        "train_funding_range": "+3.2e-07 .. +8.379e-05",
        "note": ("Modal state; train next-bar drift indistinguishable from "
                 "noise (mean -0.005%, median +0.019%, 48.8% negative). "
                 "Train-period description, not a validated edge."),
    },
    "pos-extreme": {
        "bars": 410, "share_pct": 18.8, "episodes": 88,
        "median_episode_len_bars": 2,
        "next_bar_mean_return_pct": -0.066, "next_bar_median_return_pct": -0.041,
        "pct_negative": 53.4, "annualized_vol": 0.38,
        "train_funding_range": "+8.39e-05 .. +1.0e-04",
        "note": ("Train next-bar mean -0.066% (median -0.041%, 53.4% "
                 "negative). This negative drift is precisely the pattern "
                 "whose tradable form (fade positive funding extremes, "
                 "DIR-TC-H8) FAILED the pre-registered shipping gate - see "
                 "the falsification chapter, docs/report/REPORT.md. Do not "
                 "read this note as an actionable fade."),
    },
    "neg-mild": {
        "bars": 386, "share_pct": 17.7, "episodes": 100,
        "median_episode_len_bars": 2,
        "next_bar_mean_return_pct": 0.067, "next_bar_median_return_pct": 0.032,
        "pct_negative": 48.7, "annualized_vol": 0.47,
        "train_funding_range": "-8.326e-05 .. -6e-08",
        "note": ("Train next-bar mean +0.067% (median +0.032%). A "
                 "train-period description, not a validated edge."),
    },
    "neg-extreme": {
        "bars": 26, "share_pct": 1.2, "episodes": 9,
        "median_episode_len_bars": 2,
        "next_bar_mean_return_pct": -0.159, "next_bar_median_return_pct": -0.256,
        "pct_negative": 69.2, "annualized_vol": 0.63,
        "train_funding_range": "-1.518e-04 .. -8.417e-05",
        "note": ("26 bars / 9 episodes in F4-train: insufficient sample to "
                 "characterize. The tabulated statistics are reported for "
                 "completeness only and support no inference."),
    },
}

DISCLAIMERS = [
    ("Walk-forward provenance: pre-registered purged/embargoed walk-forward, "
     "2025-04-03..2026-06-09, 4 folds. Taxonomy-level honest_N = 225 "
     "pooled-OOS regime episodes - a taxonomy-level count, not a strategy "
     "sample. The single near-miss candidate (DIR-TC-H8, FAILED) had an "
     "active sample of only 30 OOS trades / 92 nonzero-position OOS bars / "
     "3 of 4 folds."),
    ("Funding basis: live value is the CMC global cross-venue average "
     "(leverage.funding_rate.average.current, % string, decimal = value/100); "
     "the frozen threshold derives from Binance BTCUSDT 8h funding history. "
     "Sign and extremity-band comparisons only - never raw-magnitude "
     "arithmetic across the two bases."),
    ("No strategy cleared our pre-registered shipping gate (0/36 variants; "
     "expected null-clause pass-rate 0.0500). Expected-behavior notes are "
     "train-period descriptions with validated: false."),
    # W layer (docs/FREEZE-W.md §1/§2/§3 amendment 2 — verbatim numbers)
    ("Widened validation layer (W-freeze 2026-06-11, docs/FREEZE-W.md): 183 "
     "registered Variants evaluated across 3 assets (~5-6-year panel spans, "
     "multi-regime pooled OOS) under an 8-clause pre-registered gate; "
     "4 passes = 1 effective "
     "hypothesis, quarantined by the pre-registered hypothesis-family locks "
     "(ship_eligible_count = 0, no Winner); 31 of 32 effective hypotheses "
     "cleared nothing on any panel. Locked candidates are published as "
     "falsification evidence only, validated: false. Forward registration "
     "active: 24 Variants, OOS 2026-06-11 onward, earliest evaluation "
     "2027-07-01."),
    "Not financial advice.",
]

# Two-layer validation block values (floor FREEZE §6 + FREEZE-W §4 numbers)
VALIDATION_GATE = ("floor: 0/36 variants passed; W-sweep: 4 of 183 evaluated "
                   "= 1 effective hypothesis, family-locked; "
                   "ship_eligible_count = 0; no Winner")
VALIDATED_METRICS_REF = ("docs/report/REPORT.md#3-falsification-chapter and "
                         "§7 (W-sweep falsification chapter)")

FIG_CAPTIONS = {
    "fig1_pooled_oos_equity.png": "pooled-OOS equity curves (variants vs HODL/flat)",
    "fig2_h8_concentration.png": "DIR-TC-H8 top-5 trade concentration (the gate-caught FAILED candidate)",
    "fig3_null_distribution.png": "episode-shuffle null distribution vs observed Sharpe",
    "fig4_gate_power.png": "gate power: planted-edge calibration",
    "fig5_regime_ribbon.png": "TC regime ribbon over the full-stack window",
    "fig6_deep_replay.png": "failed-candidate deep-history replay (falsification context, not a track record)",
}


def load_env_key() -> None:
    """Load CMC_MCP_API_KEY from .env if not already set. Never printed."""
    if os.environ.get("CMC_MCP_API_KEY"):
        return
    env_path = REPO / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("CMC_MCP_API_KEY=") and not line.startswith("#"):
                os.environ["CMC_MCP_API_KEY"] = line.split("=", 1)[1].strip()
                return


def load_frozen_threshold() -> float:
    """Parse funding_hi_abs from SKILL.md §3 (the shipped contract)."""
    try:
        text = SKILL_MD.read_text()
        m = re.search(r"funding_hi_abs\s*=\s*([0-9][0-9.eE+-]*)", text)
        if m:
            val = float(m.group(1))
            if val != FUNDING_HI_ABS_FREEZE:
                print(f"  WARNING: SKILL.md threshold {val!r} differs from "
                      f"FREEZE.md constant {FUNDING_HI_ABS_FREEZE!r} - "
                      f"re-validation trigger (G7); using SKILL.md value.")
            return val
    except OSError:
        pass
    print("  WARNING: could not parse threshold from SKILL.md; using the "
          "FREEZE.md §2.2 constant.")
    return FUNDING_HI_ABS_FREEZE


def get(payload, path: str):
    """Walk a dotted path; '[0]' indexes an array root. None if absent."""
    cur = payload
    for part in path.split("."):
        if part == "[0]":
            if isinstance(cur, list) and cur:
                cur = cur[0]
            else:
                return None
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def parse_funding_pct_string(raw):
    """SKILL.md §3.1: '+0.0015866%' -> 1.5866e-05 decimal; None if bad."""
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s.endswith("%"):
        return None
    try:
        f = float(s[:-1].strip().lstrip("+")) / 100.0
    except ValueError:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def classify(f, threshold: float) -> str:
    """Frozen TC decision table; missing/NaN clause evaluates FALSE (D4.3)."""
    sign_pos = (f is not None) and (f >= 0)
    extreme = (f is not None) and (abs(f) >= threshold)
    return ("pos" if sign_pos else "neg") + "-" + ("extreme" if extreme else "mild")


# The SKILL.md §2 workflow: seven verified tools (FREEZE-W §3 / registration
# §11). Steps 1-3 feed classification + spec block; steps 4-7 feed ONLY the
# market-context display and are never branched on.
TOOL_CALLS = [
    ("get_global_metrics_latest", {}),
    ("get_crypto_quotes_latest", {"id": "1"}),
    ("get_global_crypto_derivatives_metrics", {}),
    ("get_crypto_technical_analysis", {"id": "1"}),
    ("trending_crypto_narratives", {}),
    ("get_upcoming_macro_events", {}),
    ("get_crypto_latest_news", {"id": "1", "limit": 5}),
]


def fetch_payloads():
    """Call the seven allowed tools; per-tool graceful degradation (§6)."""
    payloads = {name: None for name, _ in TOOL_CALLS}
    failures = []
    try:
        from scripts.mcp_client import McpClient
        client = McpClient()
        init = client.initialize()
        if not (isinstance(init, dict) and "result" in init):
            raise ValueError(f"initialize returned {str(init)[:120]}")
    except Exception as e:
        failures.append(f"MCP handshake failed ({type(e).__name__}); all "
                        f"seven tools unavailable")
        return payloads, failures

    for name, args in TOOL_CALLS:
        try:
            msg = client.call(name, args)
            result = msg["result"]
            if result.get("isError"):
                raise ValueError("tool returned isError")
            payloads[name] = json.loads(result["content"][0]["text"])
        except Exception as e:
            failures.append(f"{name} unavailable ({type(e).__name__}) - "
                            f"degrading per SKILL.md §6")
    return payloads, failures


def table_rows(payload, table_path: str, columns: list[str], limit: int):
    """Extract up to `limit` rows' named columns from a headers/rows table
    payload (narratives / macro events / news). Returns list of dicts, or
    None if the shape is absent (graceful failure)."""
    base = get(payload, table_path) if table_path else payload
    if not isinstance(base, dict):
        return None
    headers, rows = base.get("headers"), base.get("rows")
    if not (isinstance(headers, list) and isinstance(rows, list)):
        return None
    try:
        idx = [headers.index(c) for c in columns]
    except ValueError:
        return None
    out = []
    for row in rows[:limit]:
        if isinstance(row, list) and len(row) == len(headers):
            out.append({c: row[i] for c, i in zip(columns, idx)})
    return out


def print_sweep_headline() -> None:
    print("=" * 72)
    print("VALIDATION LAYER 1 (floor) - a rigorous NULL (0/36)")
    print("=" * 72)
    if not SWEEP_SUMMARY.exists():
        print(f"  (artifacts/sweep_summary.md not found at {SWEEP_SUMMARY}; "
              f"see docs/FREEZE.md §6 for the frozen numbers)")
        return
    text = SWEEP_SUMMARY.read_text()
    wanted = [
        (r"- variants swept: .*", None),
        (r"- gate passes: .*", None),
        (r"- expected pass-rate of the null clause.*", None),
        (r"- FULL-gate pass rate over 200 null draws.*", None),
    ]
    print("  0/36 variants passed the pre-registered shipping gate.")
    print("  The Skill therefore ships as a regime MONITOR - no entry/exit/")
    print("  sizing is emitted, ever. R3 disclosure (artifacts/sweep_summary.md):")
    for pattern, _ in wanted:
        m = re.search(pattern, text)
        if m:
            print(f"    {m.group(0).lstrip('- ')}")
    m = re.search(r"\| TC \|[^\n]*\|", text)
    if m:
        print(f"    TC taxonomy row (embargo / honest_N / OOS bars / episodes "
              f"/ HODL):\n      {m.group(0)}")
    m = re.search(r"## Survivors.*?\n- (.*)", text)
    if m:
        print(f"    survivors: {m.group(1)}")
    print("  Gate power (docs/FREEZE.md §6): the unmodified pipeline passes a")
    print("  planted edge of >= 10 bps/bar robustly, 5 bps/bar marginally -")
    print("  the null is evidence about the data, not the machinery.")
    print("  Near-miss DIR-TC-H8: FAILED the pre-registered top-5-removal")
    print("  clause (its 5 best trades carried >100% of the OOS gain); see")
    print("  the falsification chapter, docs/report/REPORT.md.")


def print_w_headline() -> None:
    """Layer 2: the W-sweep outcome, read from the committed artifact's R3
    block (artifacts/w/sweep_results_w.json globals.r3) plus FREEZE-W-frozen
    context. Per FREEZE-W §3 amendment 3 (lane W-C I1), the artifact's
    observed_null_p95_rate / observed_null_p99_rate are draw-bookkeeping
    identities and are NEVER printed as observed clause rates."""
    print("=" * 72)
    print("VALIDATION LAYER 2 (W-sweep) - widened search, family-locked, "
          "NO WINNER")
    print("=" * 72)
    if not SWEEP_W_JSON.exists():
        print(f"  (artifacts/w/sweep_results_w.json not found at "
              f"{SWEEP_W_JSON}; see docs/FREEZE-W.md for the frozen numbers)")
        return
    try:
        r3 = json.loads(SWEEP_W_JSON.read_text())["globals"]["r3"]
        reg, swept = r3["registered"], r3["swept"]
    except (ValueError, KeyError) as e:
        print(f"  (could not parse the R3 block: {type(e).__name__}; see "
              f"docs/FREEZE-W.md for the frozen numbers)")
        return
    print(f"  Registered denominator: {reg['n_gated']} gated Variants "
          f"(~{reg['effective_hypotheses']} effective hypotheses) + "
          f"{reg['n_annex']} locked-annex, across 3 assets, ~5-6-year")
    print(f"  panel spans (multi-regime pooled OOS), 8-clause gate; "
          f"{reg['n_forward_recorded_not_evaluated']} forward Variants "
          f"recorded, never evaluated.")
    print(f"  Outcome (artifact R3): {swept['n_variants']} evaluated -> "
          f"{swept['gate_pass_count']} gate passes = 1 effective hypothesis;")
    print(f"  family_locked_count = {swept['family_locked_count']}, "
          f"ship_eligible_count = {swept['ship_eligible_count']} -> "
          f"NO Winner.")
    print(f"  Expected clause-6 null passers across the gated set: "
          f"{reg['expected_clause6_null_passers']} (rate "
          f"{reg['expected_clause6_rate']}); observed clause-level")
    print("  exceedances are disclosed in REPORT.md §7 (clause-3 23/175 = "
          "13.1%, clause-6")
    print("  8/175 nominal = 3 effective - FREEZE-W §3 amendment 3; the "
          "artifact's")
    print("  observed_null_p9x_rate fields are bookkeeping identities, not "
          "observed rates).")
    print(f"  Structural-feasibility flags (train-side, pre-OOS): "
          f"{swept['structurally_flagged_count']} of 175 -> effective")
    print("  denominator 110; 31 of 32 effective hypotheses cleared nothing "
          "on any panel.")
    print("  The one effective passer (P-BTC, T-D D1 symmetric funding fade) "
          "was quarantined")
    print("  by the pre-registered locks: its extremity-neutralized twin "
          "goes net-negative")
    print("  (layer 2) and 88.3-92.4% of its PnL sits on the locked "
          "short-leg (layer 3).")
    print('  The story, verbatim: "the gate found something it refuses to '
          'ship until its')
    print('  own published protocol is satisfiable."')
    print("  Forward registration (active): 24 Variants, OOS 2026-06-11 "
          "00:00 UTC onward,")
    print("  quarterly folds, 8-clause gate; earliest evaluation 2027-07-01 "
          "- this cycle")
    print("  reports the registration itself, not a result.")
    print("  W gate power (measured 2026-06-12, planted-edge calibration, 9 "
          "cells through")
    print("  the unmodified pipeline): P-BTC detects a planted 5 bps/bar "
          "edge robustly")
    print("  (all 8 clauses, every rung); P-ETH/P-SOL only at 25 bps/bar, "
          "marginally -")
    print("  so the ETH/SOL nulls constrain only edges >= ~25 bps/bar, "
          "never smaller")
    print("  ones. Readout: docs/report/adversarial/"
          "w_lane2_power_readout.md.")


def print_figures() -> None:
    print("=" * 72)
    print("REPORT FIGURES (pre-rendered by lab/report_figs.py)")
    print("=" * 72)
    if not FIGS_DIR.is_dir():
        print(f"  (figures directory not found: {FIGS_DIR} - run "
              f"`uv run python -m lab.report_figs` to render)")
        return
    figs = sorted(FIGS_DIR.glob("*.png"))
    if not figs:
        print(f"  (no .png figures in {FIGS_DIR})")
        return
    for fig in figs:
        caption = FIG_CAPTIONS.get(fig.name, "report figure")
        try:
            shown = fig.relative_to(REPO)
        except ValueError:
            shown = fig
        print(f"  {shown}  - {caption}")


def main() -> int:
    as_of_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("=" * 72)
    print("BTC FUNDING REGIME MONITOR - live demo "
          "(skills/btc-funding-regime-monitor)")
    print("=" * 72)
    print("Loading frozen thresholds from SKILL.md ...")
    load_env_key()
    threshold = load_frozen_threshold()
    print(f"  funding_hi_abs = {threshold!r} (q80 of |funding_rate_8h|, "
          f"F4-train, frozen 2026-06-10, docs/FREEZE.md §2.2)")
    print(f"  regime enum: {', '.join(REGIME_ENUM)}")

    print("\nCalling the live CMC MCP server (7 verified tools - SKILL.md §2;"
          "\nonly get_global_metrics_latest is load-bearing) ...")
    payloads, failures = fetch_payloads()
    for name in payloads:
        status = "ok" if payloads[name] is not None else "UNAVAILABLE"
        print(f"  {name}: {status}")
    for fmsg in failures:
        print(f"  DEGRADED: {fmsg}")

    gm = payloads["get_global_metrics_latest"]
    quotes = payloads["get_crypto_quotes_latest"]
    deriv = payloads["get_global_crypto_derivatives_metrics"]
    ta = payloads["get_crypto_technical_analysis"]
    narratives = payloads["trending_crypto_narratives"]
    macro = payloads["get_upcoming_macro_events"]
    news = payloads["get_crypto_latest_news"]

    raw_funding = get(gm, "leverage.funding_rate.average.current")
    f = parse_funding_pct_string(raw_funding)
    degraded = f is None
    regime = classify(f, threshold)

    # F&G is context from get_global_metrics_latest: display it whenever that
    # tool succeeded, even if the funding field itself was unparseable.
    fg_index = get(gm, "sentiment.fear_greed.current.index") if gm is not None else None
    last_updated = get(gm, "last_updated")
    btc_dominance = get(gm, "dominance.btc.current")
    altseason_idx = get(gm, "rotation.altcoin_season.current.index")
    btc_price = get(quotes, "[0].price")
    btc_chg = get(quotes, "[0].percent_change_24h")
    btc_chg_7d = get(quotes, "[0].percent_change_7d")
    sec_funding = get(deriv, "fundingRate.current")
    oi_current = get(deriv, "totalOpenInterest.current")
    oi_chg_24h = get(deriv, "totalOpenInterest.percentage_change_24h")
    liq = get(deriv, "btc_liquidations.total_usd_4h")
    liq_block = ({"total": liq.get("total"), "long": liq.get("long"),
                  "short": liq.get("short")} if isinstance(liq, dict) else None)
    rsi14 = get(ta, "rsi.rsi14")
    sma200 = get(ta, "moving_averages.simple_moving_average_200_day")
    # Derived DISPLAY line only (never a clause): price side vs SMA200.
    sma200_side = None
    if isinstance(sma200, str) and btc_price is not None:
        try:
            sma200_side = ("above" if float(btc_price) >
                           float(sma200.replace(",", "")) else "below")
        except ValueError:
            sma200_side = None
    narrative_rows = table_rows(narratives, "categoryList",
                                ["trendingRank", "categoryName"], 3)
    macro_rows = table_rows(macro, "upcomingEventNews",
                            ["title", "eventDate"], 3)
    news_rows = table_rows(news, "", ["title", "publishedAt"], 3)

    # ----- (a) human-readable regime report (SKILL.md §5.1) --------------
    print()
    print("=" * 72)
    headline = f"BTC funding regime: {regime}"
    if degraded:
        headline = "DEGRADED - " + headline
    print(headline)
    print("=" * 72)
    if degraded:
        print("  Primary funding field unavailable or unparseable. Sign and")
        print("  extremity clauses both evaluate FALSE (frozen rule D4.3), so")
        print("  the label is the deterministic missing-data default "
              "(neg-mild),")
        print("  NOT a market reading.")
        if raw_funding is not None:
            print(f"  Raw failed value (echoed for diagnosis): {raw_funding!r}")
    else:
        sign = "pos" if f >= 0 else "neg"
        band = "extreme" if abs(f) >= threshold else "mild"
        cmp_op = ">=" if abs(f) >= threshold else "<"
        print(f"  Live funding (CMC global average): {raw_funding}  ->  "
              f"decimal {f:.6g}")
        print(f"  Sign clause:      f = {f:.6g} {'>= 0' if f >= 0 else '< 0'}"
              f"  ->  {sign}")
        print(f"  Extremity clause: |{f:.6g}| {cmp_op} {threshold:.6g}"
              f"  ->  {band}")
    print()
    eb = EXPECTED_BEHAVIOR[regime]
    print(f"  Expected behavior for {regime} (F4-train statistics, "
          f'"validated": false):')
    print(f"    {eb['bars']} bars ({eb['share_pct']}% of F4-train), "
          f"{eb['episodes']} episodes, median episode "
          f"{eb['median_episode_len_bars']} bars")
    print(f"    next-bar mean {eb['next_bar_mean_return_pct']:+.3f}% / median "
          f"{eb['next_bar_median_return_pct']:+.3f}% / "
          f"{eb['pct_negative']}% negative / ann. vol {eb['annualized_vol']}")
    print(f"    note: {eb['note']}")
    print()
    print("  Funding basis: live value is the CMC global cross-venue average;")
    print("  the frozen threshold derives from Binance BTCUSDT 8h history.")
    print("  Sign + extremity-band comparison only (D1).")
    print()
    print("  Validation: two layers, nothing shippable - floor 0/36 variants")
    print("  passed the pre-registered shipping gate; W-sweep 183 Variants")
    print("  evaluated on 3 assets under an 8-clause gate, 4 passes = 1")
    print("  effective hypothesis, family-locked, 0 ship-eligible, no Winner.")
    print("  Nothing here is a validated edge. See docs/report/REPORT.md")
    print("  §3 and §7.")

    # ----- (b) fenced JSON monitor spec block (SKILL.md §5.2) ------------
    snapshot = {
        "leverage.funding_rate.average.current": raw_funding,
        "funding_rate_decimal": f,
        "funding_threshold_abs": threshold,
        "global_metrics_last_updated": last_updated,
        "sentiment.fear_greed.current.index": fg_index,
        "btc_price_usd": btc_price,
        "btc_percent_change_24h": btc_chg,
        "derivatives.fundingRate.current_unit_unresolved": sec_funding,
        "btc_liquidations.total_usd_4h": liq_block,
        "status": ("ok" if not degraded
                   else "degraded: primary funding field unavailable"),
    }
    disclaimers = list(DISCLAIMERS)
    if degraded:
        disclaimers.append("Label is the deterministic missing-data default "
                           "(neg-mild), not a market reading.")
    spec = {
        "regime": regime,
        "degraded": degraded,
        "as_of_utc": as_of_utc,
        "signal_snapshot": snapshot,
        "expected_behavior": {
            "source": EB_SOURCE,
            **eb,
            "validated": False,
            "validated_metrics_ref": VALIDATED_METRICS_REF,
        },
        "validation": {
            "status": "null-result",
            "gate": VALIDATION_GATE,
            "ref": "docs/report/REPORT.md",
        },
        "disclaimers": disclaimers,
    }
    print()
    print("Monitor spec block (machine-readable - schema unchanged from the")
    print("floor freeze; the new context tools never appear in this block):")
    print("```json")
    print(json.dumps(spec, indent=2))
    print("```")
    print()

    # ----- (c) market-context display (SKILL.md §5.3) --------------------
    def show(v, suffix: str = ""):
        return (f"{v}{suffix}" if v is not None
                else "unavailable (tool degraded)")

    print("=" * 72)
    print("MARKET CONTEXT (display only - never branched on; nothing below")
    print("feeds the classifier, the spec block, or any clause)")
    print("=" * 72)
    print("  Price / momentum (get_crypto_quotes_latest):")
    print(f"    BTC price (USD):            {show(btc_price)}")
    print(f"    BTC 24h change (% points):  {show(btc_chg)}")
    print(f"    BTC 7d change (% points):   {show(btc_chg_7d)}")
    print("  Daily technicals (get_crypto_technical_analysis, daily-only):")
    print(f"    RSI-14 (1d):                {show(rsi14)}")
    print(f"    SMA-200 (1d, USD):          {show(sma200)}"
          + (f"  [price {sma200_side} SMA200 - display line, not a clause]"
             if sma200_side else ""))
    print("  Derivatives (get_global_crypto_derivatives_metrics):")
    print(f"    Global open interest:       {show(oi_current)}"
          f"  (24h change {show(oi_chg_24h)})")
    print(f"    BTC liquidations (4h):      {show(liq_block)}")
    print(f"    Secondary funding field:    {show(sec_funding)}"
          f"  [unit unresolved (OPEN-1) - never used in a comparison]")
    print("  Global sentiment / rotation (get_global_metrics_latest):")
    print(f"    Fear & Greed index:         {show(fg_index)}")
    print(f"    BTC dominance:              {show(btc_dominance)}"
          f"  [Gate-0 §9: rejected as classifier input; display only]")
    print(f"    Altcoin season index:       {show(altseason_idx)}"
          f"  [display only]")
    print(f"    global_metrics last_updated: {show(last_updated)}"
          f"  [daily stamp - no intraday freshness claim]")
    print("  Trending narratives (trending_crypto_narratives, optional):")
    if narrative_rows:
        for r in narrative_rows:
            print(f"    #{r['trendingRank']}  {r['categoryName']}")
    else:
        print("    unavailable (optional context tool degraded - omitted)")
    print("  Upcoming macro/regulatory events (get_upcoming_macro_events, "
          "optional):")
    if macro_rows:
        for r in macro_rows:
            print(f"    {r['eventDate']}: {str(r['title'])[:70]}")
    else:
        print("    unavailable (optional context tool degraded - omitted)")
    print("  Latest BTC headlines (get_crypto_latest_news, optional):")
    if news_rows:
        for r in news_rows:
            print(f"    {str(r['publishedAt'])[:20]}: {str(r['title'])[:64]}")
    else:
        print("    unavailable (optional context tool degraded - omitted)")
    print()

    # ----- (d) two-layer validation headline ------------------------------
    print_sweep_headline()
    print()
    print_w_headline()
    print()

    # ----- (e) report figures ---------------------------------------------
    print_figures()
    print()
    print("Done. This monitor emits no entry/exit/sizing - the floor gate")
    print("refused to validate any (0/36), the widened 8-clause gate then")
    print("locked the one effective passer it found (0 ship-eligible), and")
    print("that refusal is the point.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
