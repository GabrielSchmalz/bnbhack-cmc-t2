# demo/validate_skill.py — plan Task 3.3: live validation of the Skill contract.
#
# Executes the SKILL.md workflow LITERALLY against the live CMC MCP server:
#   1. initialize + tools/list — assert every `allowed-tools` entry resolves;
#   2. call each tool the §2 workflow names, with the documented arguments;
#   3. assert every payload field path the rules reference EXISTS in the live
#      payloads (walks the documented paths, checks documented shapes);
#   4. run the frozen TC classification on the live values;
#   5. build the monitor spec block and validate it structurally
#      (hand-rolled schema check — required keys, types, "validated": false);
#   6. write docs/gate0/skill_validation_run.json.
#
# Exit nonzero on ANY mismatch. A field that drifted from the Gate-0 dump is a
# DRIFT mismatch: this script STOPS and reports — it never patches the Skill
# (freeze rule G7: any threshold/enum/schema change triggers full re-validation).
#
# Frozen constants below are verbatim from docs/FREEZE.md §2.2/§2.3 and
# skills/btc-funding-regime-monitor/SKILL.md §3/§4. Never print the API key.

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
OUT_PATH = REPO / "docs" / "gate0" / "skill_validation_run.json"
TOOL_PREFIX = "mcp__cmc-mcp__"

# ---------------------------------------------------------------------------
# Frozen constants (docs/FREEZE.md §2.2 — F4-train, verbatim full precision)
# ---------------------------------------------------------------------------
FUNDING_HI_ABS = 8.385600000000002e-05  # q80 of |funding_rate_8h|, F4-train
REGIME_ENUM = ("pos-mild", "pos-extreme", "neg-mild", "neg-extreme")

# F4-train descriptive statistics (docs/FREEZE.md §2.3 / SKILL.md §4 —
# the ONLY numbers the expected-behavior notes may cite; all "validated": false)
EB_SOURCE = ("F4-train descriptive statistics (2025-04-03..2026-04-01, "
             "2178 bars; next-bar open-to-open convention)")
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

# Documented field paths the SKILL.md §2 rules reference, per tool, with the
# shape each one had in the Gate-0 dump (docs/gate0/<tool>.json).
#   path syntax: dot-separated keys; a leading "[0]" indexes a JSON array root.
DOCUMENTED_PATHS = {
    "get_global_metrics_latest": [
        ("leverage.funding_rate.average.current", "pct_string"),
        ("sentiment.fear_greed.current.index", "int"),
        ("last_updated", "str"),
    ],
    "get_crypto_quotes_latest": [
        ("[0].price", "number"),
        ("[0].percent_change_24h", "number"),
        ("[0].last_updated_time", "str"),
    ],
    "get_global_crypto_derivatives_metrics": [
        ("fundingRate.current", "str"),
        ("btc_liquidations.total_usd_4h.total", "str"),
        ("btc_liquidations.total_usd_4h.long", "str"),
        ("btc_liquidations.total_usd_4h.short", "str"),
    ],
}

TOOL_ARGS = {
    "get_global_metrics_latest": {},
    "get_crypto_quotes_latest": {"id": "1"},
    "get_global_crypto_derivatives_metrics": {},
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


def parse_allowed_tools(skill_md: Path) -> list[str]:
    """Parse the `allowed-tools` list from SKILL.md front matter (no yaml dep)."""
    tools, in_block = [], False
    for line in skill_md.read_text().splitlines():
        if line.strip() == "allowed-tools:":
            in_block = True
            continue
        if in_block:
            m = re.match(r"\s+-\s+(\S+)", line)
            if m:
                tools.append(m.group(1))
            else:
                break
    return tools


def walk_path(payload, path: str):
    """Walk a documented dotted path. Returns (found: bool, value)."""
    cur = payload
    parts = path.split(".")
    for part in parts:
        if part == "[0]":
            if isinstance(cur, list) and len(cur) > 0:
                cur = cur[0]
            else:
                return False, None
        else:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return False, None
    return True, cur


def shape_ok(value, shape: str) -> bool:
    if shape == "pct_string":
        return isinstance(value, str) and value.strip().endswith("%")
    if shape == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if shape == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if shape == "str":
        return isinstance(value, str)
    return False


def parse_funding_pct_string(raw):
    """SKILL.md §3.1 unit conversion: '+0.0015866%' -> 1.5866e-05 (decimal).

    Returns float decimal, or None if missing/unparseable/NaN (D4.3)."""
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s.endswith("%"):
        return None
    s = s[:-1].strip().lstrip("+")
    try:
        f = float(s) / 100.0
    except ValueError:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def classify(f) -> str:
    """Frozen TC decision table (SKILL.md §3; FREEZE.md §2.2).

    NaN/missing clause evaluates FALSE (D4.3): f is None -> neg-mild."""
    sign_pos = (f is not None) and (f >= 0)
    extreme = (f is not None) and (abs(f) >= FUNDING_HI_ABS)
    return ("pos" if sign_pos else "neg") + "-" + ("extreme" if extreme else "mild")


def extract_text_payload(msg):
    """Gate-0 payload parsing rule: JSON string inside result.content[0].text."""
    if not isinstance(msg, dict) or "result" not in msg:
        raise ValueError(f"no result in response: {str(msg)[:200]}")
    result = msg["result"]
    if result.get("isError"):
        raise ValueError(f"tool returned isError: {str(result)[:200]}")
    text = result["content"][0]["text"]
    return json.loads(text)


def build_spec_block(regime: str, as_of_utc: str, snapshot: dict,
                     degraded_default: bool) -> dict:
    eb = dict(EXPECTED_BEHAVIOR[regime])
    eb_block = {
        "source": EB_SOURCE,
        **eb,
        "validated": False,
        "validated_metrics_ref": "docs/report/REPORT.md#falsification",
    }
    disclaimers = list(DISCLAIMERS)
    if degraded_default:
        disclaimers.append("Label is the deterministic missing-data default "
                           "(neg-mild), not a market reading.")
    return {
        "regime": regime,
        "as_of_utc": as_of_utc,
        "signal_snapshot": snapshot,
        "expected_behavior": eb_block,
        "validation": {
            "status": "null-result",
            "gate": "0/36 variants passed",
            "ref": "docs/report/REPORT.md",
        },
        "disclaimers": disclaimers,
    }


def check_spec_block(spec: dict, mismatches: list[str]) -> None:
    """Hand-rolled structural schema check of the monitor spec block."""
    def err(msg):
        mismatches.append(f"SPEC-SCHEMA: {msg}")

    required_top = ["regime", "as_of_utc", "signal_snapshot",
                    "expected_behavior", "validation", "disclaimers"]
    for k in required_top:
        if k not in spec:
            err(f"missing top-level key '{k}'")
    if set(spec) - set(required_top):
        err(f"unexpected top-level keys {sorted(set(spec) - set(required_top))}")

    if spec.get("regime") not in REGIME_ENUM:
        err(f"regime {spec.get('regime')!r} not in frozen enum {REGIME_ENUM}")
    if not isinstance(spec.get("as_of_utc"), str) or not re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", spec.get("as_of_utc", "")):
        err(f"as_of_utc {spec.get('as_of_utc')!r} not an ISO-8601 Z timestamp")

    snap = spec.get("signal_snapshot")
    snap_keys = ["leverage.funding_rate.average.current", "funding_rate_decimal",
                 "funding_threshold_abs", "global_metrics_last_updated",
                 "sentiment.fear_greed.current.index", "btc_price_usd",
                 "btc_percent_change_24h",
                 "derivatives.fundingRate.current_unit_unresolved",
                 "btc_liquidations.total_usd_4h", "status"]
    if not isinstance(snap, dict):
        err("signal_snapshot is not an object")
    else:
        for k in snap_keys:
            if k not in snap:
                err(f"signal_snapshot missing key '{k}'")
        if snap.get("funding_threshold_abs") != FUNDING_HI_ABS:
            err(f"funding_threshold_abs {snap.get('funding_threshold_abs')!r} "
                f"!= frozen {FUNDING_HI_ABS!r}")
        if not isinstance(snap.get("status"), str):
            err("signal_snapshot.status is not a string")

    eb = spec.get("expected_behavior")
    eb_keys = {"source": str, "bars": int, "share_pct": (int, float),
               "episodes": int, "median_episode_len_bars": int,
               "next_bar_mean_return_pct": (int, float),
               "next_bar_median_return_pct": (int, float),
               "pct_negative": (int, float), "annualized_vol": (int, float),
               "train_funding_range": str, "note": str, "validated": bool,
               "validated_metrics_ref": str}
    if not isinstance(eb, dict):
        err("expected_behavior is not an object")
    else:
        for k, t in eb_keys.items():
            if k not in eb:
                err(f"expected_behavior missing key '{k}'")
            elif not isinstance(eb[k], t):
                err(f"expected_behavior.{k} has type "
                    f"{type(eb[k]).__name__}, expected {t}")
        if eb.get("validated") is not False:
            err("expected_behavior.validated MUST be exactly false")

    val = spec.get("validation")
    if not isinstance(val, dict):
        err("validation is not an object")
    else:
        if val.get("status") != "null-result":
            err(f"validation.status {val.get('status')!r} != 'null-result'")
        if val.get("gate") != "0/36 variants passed":
            err(f"validation.gate {val.get('gate')!r} != '0/36 variants passed'")
        if not isinstance(val.get("ref"), str):
            err("validation.ref is not a string")

    dis = spec.get("disclaimers")
    if not (isinstance(dis, list) and len(dis) >= 4
            and all(isinstance(d, str) for d in dis)):
        err("disclaimers is not a list of >= 4 strings")
    else:
        if not any("Funding basis" in d for d in dis):
            err("mandatory D1 funding-basis disclaimer missing (SKILL.md §3.2)")
        if not any("0/36 variants" in d for d in dis):
            err("mandatory null-result disclaimer missing")


def main() -> int:
    as_of_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mismatches: list[str] = []
    tool_results_ok = True
    field_paths_ok = True

    load_env_key()
    if not os.environ.get("CMC_MCP_API_KEY"):
        mismatches.append("ENV: CMC_MCP_API_KEY not set and not found in .env")

    # -- (1) initialize + tools/list -------------------------------------
    allowed = parse_allowed_tools(SKILL_MD)
    if len(allowed) != 3:
        mismatches.append(f"SKILL: expected 3 allowed-tools entries, "
                          f"parsed {len(allowed)}: {allowed}")
    payloads: dict[str, object] = {}
    client = None
    if not mismatches or allowed:
        try:
            from scripts.mcp_client import McpClient
            client = McpClient()
            init = client.initialize()
            if not (isinstance(init, dict) and "result" in init):
                raise ValueError(f"initialize failed: {str(init)[:200]}")
            server_tools = {t["name"] for t in client.tools_list()}
            print(f"[1] initialize + tools/list ok "
                  f"({len(server_tools)} tools on server)")
            for entry in allowed:
                bare = entry.removeprefix(TOOL_PREFIX)
                if entry == bare:
                    mismatches.append(f"TOOLS: allowed-tools entry '{entry}' "
                                      f"lacks the '{TOOL_PREFIX}' prefix")
                if bare not in server_tools:
                    tool_results_ok = False
                    mismatches.append(f"TOOLS: '{entry}' does not resolve in "
                                      f"live tools/list (bare name '{bare}')")
                else:
                    print(f"    allowed-tool resolves: {entry}")
        except Exception as e:  # degradation message, not a traceback
            tool_results_ok = False
            client = None
            mismatches.append(f"MCP: handshake/tools-list failed: "
                              f"{type(e).__name__}: {e}")
            print(f"[1] DEGRADED: MCP handshake failed "
                  f"({type(e).__name__}) - cannot reach live server")

    # -- (2) call each tool the workflow names ----------------------------
    for bare, args in TOOL_ARGS.items():
        if client is None:
            payloads[bare] = None
            continue
        try:
            msg = client.call(bare, args)
            payloads[bare] = extract_text_payload(msg)
            print(f"[2] tools/call {bare}{json.dumps(args)} -> payload parsed")
        except Exception as e:
            payloads[bare] = None
            tool_results_ok = False
            mismatches.append(f"CALL: {bare} failed: {type(e).__name__}: {e}")
            print(f"[2] DEGRADED: {bare} failed ({type(e).__name__})")

    # -- (3) walk every documented field path ----------------------------
    live_values: dict[str, object] = {}
    for bare, paths in DOCUMENTED_PATHS.items():
        payload = payloads.get(bare)
        for path, shape in paths:
            if payload is None:
                field_paths_ok = False
                mismatches.append(f"PATH: {bare}:{path} unverifiable "
                                  f"(tool call failed)")
                continue
            found, value = walk_path(payload, path)
            if not found:
                field_paths_ok = False
                mismatches.append(
                    f"DRIFT: {bare}:{path} MISSING in live payload "
                    f"(present in Gate-0 dump docs/gate0/{bare}.json) - "
                    f"STOP: re-open freeze with the critic, do not patch "
                    f"the Skill")
            elif not shape_ok(value, shape):
                field_paths_ok = False
                mismatches.append(
                    f"DRIFT: {bare}:{path} shape changed - expected {shape}, "
                    f"got {type(value).__name__}: {str(value)[:80]!r} - "
                    f"STOP: re-open freeze with the critic, do not patch "
                    f"the Skill")
            else:
                live_values[f"{bare}:{path}"] = value
                print(f"[3] field path ok: {bare}:{path} = {str(value)[:60]}")

    # -- (4) frozen classification on the live values ---------------------
    raw_funding = live_values.get(
        "get_global_metrics_latest:leverage.funding_rate.average.current")
    f = parse_funding_pct_string(raw_funding)
    degraded_default = f is None
    regime = classify(f)
    if degraded_default and raw_funding is not None:
        mismatches.append(f"DRIFT: primary funding string unparseable under "
                          f"the §3.1 walkthrough: {raw_funding!r}")
    if f is not None:
        cmp = ">=" if abs(f) >= FUNDING_HI_ABS else "<"
        print(f"[4] classification: raw {raw_funding!r} -> decimal {f!r}; "
              f"sign {'pos' if f >= 0 else 'neg'}; "
              f"|{f!r}| {cmp} {FUNDING_HI_ABS!r} -> {regime}")
    else:
        print(f"[4] classification DEGRADED: funding missing/unparseable -> "
              f"deterministic default {regime} (D4.3)")

    # -- (5) build + structurally validate the monitor spec block ---------
    liq = live_values.get(
        "get_global_crypto_derivatives_metrics:btc_liquidations.total_usd_4h.total")
    liq_block = None
    if liq is not None:
        liq_block = {
            "total": live_values.get("get_global_crypto_derivatives_metrics:"
                                     "btc_liquidations.total_usd_4h.total"),
            "long": live_values.get("get_global_crypto_derivatives_metrics:"
                                    "btc_liquidations.total_usd_4h.long"),
            "short": live_values.get("get_global_crypto_derivatives_metrics:"
                                     "btc_liquidations.total_usd_4h.short"),
        }
    snapshot = {
        "leverage.funding_rate.average.current": raw_funding,
        "funding_rate_decimal": f,
        "funding_threshold_abs": FUNDING_HI_ABS,
        "global_metrics_last_updated":
            live_values.get("get_global_metrics_latest:last_updated"),
        "sentiment.fear_greed.current.index":
            live_values.get("get_global_metrics_latest:"
                            "sentiment.fear_greed.current.index"),
        "btc_price_usd": live_values.get("get_crypto_quotes_latest:[0].price"),
        "btc_percent_change_24h":
            live_values.get("get_crypto_quotes_latest:[0].percent_change_24h"),
        "derivatives.fundingRate.current_unit_unresolved":
            live_values.get("get_global_crypto_derivatives_metrics:"
                            "fundingRate.current"),
        "btc_liquidations.total_usd_4h": liq_block,
        "status": ("ok" if not degraded_default
                   else "degraded: primary funding field unavailable"),
    }
    spec = build_spec_block(regime, as_of_utc, snapshot, degraded_default)
    check_spec_block(spec, mismatches)
    print(f"[5] spec block built and schema-checked "
          f"({'no schema errors' if not any(m.startswith('SPEC-SCHEMA') for m in mismatches) else 'SCHEMA ERRORS'})")

    # -- (6) write the validation run record ------------------------------
    record = {
        "ts": as_of_utc,
        "tool_results_ok": tool_results_ok,
        "field_paths_ok": field_paths_ok,
        "regime": regime,
        "spec_block": spec,
        "mismatches": mismatches,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=2) + "\n")
    print(f"[6] wrote {OUT_PATH}")

    if mismatches:
        print(f"\nFAIL: {len(mismatches)} mismatch(es):")
        for m in mismatches:
            print(f"  - {m}")
        if any(m.startswith("DRIFT") for m in mismatches):
            print("\nDRIFT detected against the Gate-0 dumps: STOP. Re-open "
                  "the freeze with the critic lane (G7). Do NOT patch the "
                  "Skill.")
        return 1
    print(f"\nPASS: all allowed-tools resolve, all documented field paths "
          f"exist with documented shapes, classification = {regime}, spec "
          f"block schema-valid. 0 mismatches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
