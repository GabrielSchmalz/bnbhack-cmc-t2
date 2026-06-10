# demo/run_demo.py — plan Task 4.2: the judge-facing one-command demo.
#
#   uv run --no-sync python demo/run_demo.py
#
# Does four things, live:
#   (a) fetches the Gate-0-verified CMC MCP fields and prints a human-readable
#       BTC funding-regime report (frozen TC taxonomy);
#   (b) prints the fenced JSON monitor spec block exactly as SKILL.md §5
#       specifies (no active_ruleset / entry / exit / sizing — ever);
#   (c) prints the headline null result + gate stats from
#       artifacts/sweep_summary.md (0/36 variants passed; that IS the result);
#   (d) locates the report figures (equity curves etc.) and prints their paths.
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
    "Not financial advice.",
]

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


def fetch_payloads():
    """Call the three allowed tools; per-tool graceful degradation (§6)."""
    payloads = {"get_global_metrics_latest": None,
                "get_crypto_quotes_latest": None,
                "get_global_crypto_derivatives_metrics": None}
    failures = []
    try:
        from scripts.mcp_client import McpClient
        client = McpClient()
        init = client.initialize()
        if not (isinstance(init, dict) and "result" in init):
            raise ValueError(f"initialize returned {str(init)[:120]}")
    except Exception as e:
        failures.append(f"MCP handshake failed ({type(e).__name__}); all "
                        f"three tools unavailable")
        return payloads, failures

    for name, args in [("get_global_metrics_latest", {}),
                       ("get_crypto_quotes_latest", {"id": "1"}),
                       ("get_global_crypto_derivatives_metrics", {})]:
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


def print_sweep_headline() -> None:
    print("=" * 72)
    print("VALIDATION HEADLINE - the result of record is a rigorous NULL")
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

    print("\nCalling the live CMC MCP server (3 Gate-0-verified tools) ...")
    payloads, failures = fetch_payloads()
    for name in payloads:
        status = "ok" if payloads[name] is not None else "UNAVAILABLE"
        print(f"  {name}: {status}")
    for fmsg in failures:
        print(f"  DEGRADED: {fmsg}")

    gm = payloads["get_global_metrics_latest"]
    quotes = payloads["get_crypto_quotes_latest"]
    deriv = payloads["get_global_crypto_derivatives_metrics"]

    raw_funding = get(gm, "leverage.funding_rate.average.current")
    f = parse_funding_pct_string(raw_funding)
    degraded = f is None
    regime = classify(f, threshold)

    # F&G is context from get_global_metrics_latest: display it whenever that
    # tool succeeded, even if the funding field itself was unparseable.
    fg_index = get(gm, "sentiment.fear_greed.current.index") if gm is not None else None
    last_updated = get(gm, "last_updated")
    btc_price = get(quotes, "[0].price")
    btc_chg = get(quotes, "[0].percent_change_24h")
    sec_funding = get(deriv, "fundingRate.current")
    liq = get(deriv, "btc_liquidations.total_usd_4h")
    liq_block = ({"total": liq.get("total"), "long": liq.get("long"),
                  "short": liq.get("short")} if isinstance(liq, dict) else None)

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
    print("  Context (display only, never branched on):")
    print(f"    BTC price (USD):            "
          f"{btc_price if btc_price is not None else 'unavailable (tool degraded)'}")
    print(f"    BTC 24h change (% points):  "
          f"{btc_chg if btc_chg is not None else 'unavailable (tool degraded)'}")
    print(f"    Fear & Greed index:         "
          f"{fg_index if fg_index is not None else 'unavailable (tool degraded)'}")
    print(f"    BTC liquidations (4h):      "
          f"{liq_block if liq_block is not None else 'unavailable (tool degraded)'}")
    print(f"    Secondary funding field:    "
          f"{sec_funding if sec_funding is not None else 'unavailable (tool degraded)'}"
          f"  [unit unresolved (OPEN-1) - never used in a comparison]")
    print(f"    global_metrics last_updated: "
          f"{last_updated if last_updated is not None else 'unavailable'}"
          f"  [daily stamp - no intraday freshness claim]")
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
    print("  Validation: null result - 0/36 variants passed the pre-registered")
    print("  shipping gate; nothing here is a validated edge. See "
          "docs/report/REPORT.md.")

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
            "validated_metrics_ref":
                "docs/report/REPORT.md#3-falsification-chapter",
        },
        "validation": {
            "status": "null-result",
            "gate": "0/36 variants passed",
            "ref": "docs/report/REPORT.md",
        },
        "disclaimers": disclaimers,
    }
    print()
    print("Monitor spec block (machine-readable):")
    print("```json")
    print(json.dumps(spec, indent=2))
    print("```")
    print()

    # ----- (c) headline null-result + gate stats --------------------------
    print_sweep_headline()
    print()

    # ----- (d) report figures ---------------------------------------------
    print_figures()
    print()
    print("Done. This monitor emits no entry/exit/sizing - the shipping gate")
    print("refused to validate any (0/36), and that refusal is the point.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
