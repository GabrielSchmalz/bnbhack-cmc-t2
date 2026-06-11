"""Unit tests for the demo's pure helpers (independent-review finding 5).

Covers, with hand-computed expectations and no network:
  - run_demo.classify / validate_skill.classify: the frozen TC decision
    table — all four regimes, boundary values, and the deterministic
    missing/NaN default (neg-mild, D4.3) with its degraded flag;
  - run_demo.parse_funding_pct_string / validate_skill.parse_funding_pct_string:
    the SKILL.md §3.1 %-string -> decimal conversion (+/-, whitespace,
    garbage -> None error path);
  - validate_skill.build_spec_block + check_spec_block: the monitor spec
    block structural check — passing block, missing top-level key,
    "validated": true MUST fail, top-level "degraded" must be a boolean.
"""

import sys
from pathlib import Path

import pytest

# repo root on sys.path: the project is not installed as a package (same
# pattern as the other tests).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo import run_demo, validate_skill  # noqa: E402

THR = validate_skill.FUNDING_HI_ABS  # 8.385600000000002e-05, frozen


# ---------------------------------------------------------------------------
# classify — frozen TC decision table
# ---------------------------------------------------------------------------

class TestClassify:
    @pytest.mark.parametrize("f,expected", [
        (1.5866e-05, "pos-mild"),       # |f| < thr, f >= 0
        (9.1e-05, "pos-extreme"),       # |f| >= thr, f >= 0
        (-1.5866e-05, "neg-mild"),      # |f| < thr, f < 0
        (-9.1e-05, "neg-extreme"),      # |f| >= thr, f < 0
    ])
    def test_all_four_regimes(self, f, expected):
        assert run_demo.classify(f, THR) == expected
        assert validate_skill.classify(f) == expected

    def test_boundaries(self):
        # f == 0 -> sign clause TRUE (f >= 0) -> pos
        assert run_demo.classify(0.0, THR) == "pos-mild"
        # |f| == threshold -> extremity clause TRUE (>=)
        assert run_demo.classify(THR, THR) == "pos-extreme"
        assert run_demo.classify(-THR, THR) == "neg-extreme"
        assert validate_skill.classify(THR) == "pos-extreme"

    def test_missing_is_deterministic_neg_mild(self):
        # D4.3: missing Feature -> both clauses FALSE -> neg-mild
        assert run_demo.classify(None, THR) == "neg-mild"
        assert validate_skill.classify(None) == "neg-mild"

    def test_nan_is_deterministic_neg_mild(self):
        # NaN comparisons are FALSE -> both clauses FALSE -> neg-mild
        assert run_demo.classify(float("nan"), THR) == "neg-mild"
        assert validate_skill.classify(float("nan")) == "neg-mild"

    def test_degraded_flag_from_unparseable_funding(self):
        # the demo computes degraded = (parsed funding is None); a garbage
        # fetch therefore flags degraded AND falls to the neg-mild default
        f = run_demo.parse_funding_pct_string("not-a-rate")
        degraded = f is None
        assert degraded is True
        assert run_demo.classify(f, THR) == "neg-mild"

    def test_parsed_funding_is_not_degraded(self):
        f = run_demo.parse_funding_pct_string("+0.0015866%")
        degraded = f is None
        assert degraded is False
        assert run_demo.classify(f, THR) == "pos-mild"


# ---------------------------------------------------------------------------
# parse_funding_pct_string — SKILL.md §3.1 unit conversion
# ---------------------------------------------------------------------------

PARSERS = [run_demo.parse_funding_pct_string,
           validate_skill.parse_funding_pct_string]


class TestParseFundingPctString:
    @pytest.mark.parametrize("parse", PARSERS)
    def test_positive_gate0_example(self, parse):
        # the §3.1 worked example: "+0.0015866%" -> 1.5866e-05 decimal
        assert parse("+0.0015866%") == pytest.approx(1.5866e-05)

    @pytest.mark.parametrize("parse", PARSERS)
    def test_negative(self, parse):
        assert parse("-0.0091%") == pytest.approx(-9.1e-05)

    @pytest.mark.parametrize("parse", PARSERS)
    def test_no_sign(self, parse):
        assert parse("0.0015866%") == pytest.approx(1.5866e-05)

    @pytest.mark.parametrize("parse", PARSERS)
    @pytest.mark.parametrize("raw", [
        "  +0.0015866%  ",   # surrounding whitespace
        "+0.0015866 %",      # space before the % sign
    ])
    def test_whitespace_tolerated(self, parse, raw):
        assert parse(raw) == pytest.approx(1.5866e-05)

    @pytest.mark.parametrize("parse", PARSERS)
    @pytest.mark.parametrize("raw", [
        None,            # missing field
        12.3,            # non-string
        "0.0015866",     # no % sign
        "abc%",          # garbage number
        "%",             # empty number
        "--0.1%",        # malformed sign
        "nan%",          # parses to NaN -> rejected
        "inf%",          # parses to inf -> rejected
        "",              # empty string
    ])
    def test_garbage_returns_none(self, parse, raw):
        assert parse(raw) is None


# ---------------------------------------------------------------------------
# validate_skill spec-block structural check
# ---------------------------------------------------------------------------

def _valid_snapshot() -> dict:
    """A snapshot dict with every key check_spec_block requires (Gate-0
    dump values, SKILL.md §5 worked example)."""
    return {
        "leverage.funding_rate.average.current": "+0.0015866%",
        "funding_rate_decimal": 1.5866e-05,
        "funding_threshold_abs": THR,
        "global_metrics_last_updated": "10 June 2026 12:00 AM UTC+0",
        "sentiment.fear_greed.current.index": 15,
        "btc_price_usd": 61820.477784763956,
        "btc_percent_change_24h": 0.03458382,
        "derivatives.fundingRate.current_unit_unresolved": "0.00069614",
        "btc_liquidations.total_usd_4h": {
            "total": "17.91 M", "long": "1.64 M", "short": "16.27 M"},
        "status": "ok",
    }


def _build(degraded: bool = False, regime: str = "pos-mild") -> dict:
    return validate_skill.build_spec_block(
        regime, "2026-06-10T12:00:00Z", _valid_snapshot(), degraded)


def _check(spec: dict) -> list[str]:
    mismatches: list[str] = []
    validate_skill.check_spec_block(spec, mismatches)
    return mismatches


class TestCheckSpecBlock:
    def test_passing_block(self):
        assert _check(_build()) == []

    def test_passing_degraded_block(self):
        spec = _build(degraded=True, regime="neg-mild")
        assert spec["degraded"] is True
        assert any("deterministic missing-data default" in d
                   for d in spec["disclaimers"])
        assert _check(spec) == []

    def test_seven_required_top_level_keys(self):
        assert sorted(_build()) == sorted(
            ["regime", "degraded", "as_of_utc", "signal_snapshot",
             "expected_behavior", "validation", "disclaimers"])

    @pytest.mark.parametrize("missing", [
        "regime", "degraded", "as_of_utc", "signal_snapshot",
        "expected_behavior", "validation", "disclaimers"])
    def test_missing_top_level_key_fails(self, missing):
        spec = _build()
        del spec[missing]
        assert any(f"'{missing}'" in m for m in _check(spec))

    def test_unexpected_top_level_key_fails(self):
        spec = _build()
        spec["active_ruleset"] = {}  # FREEZE amendment 2: must never appear
        assert any("unexpected top-level keys" in m for m in _check(spec))

    def test_validated_true_must_fail(self):
        spec = _build()
        spec["expected_behavior"]["validated"] = True
        assert any("validated MUST be exactly false" in m
                   for m in _check(spec))

    @pytest.mark.parametrize("bad", ["false", 0, 1, None, "true"])
    def test_degraded_must_be_bool(self, bad):
        spec = _build()
        spec["degraded"] = bad
        assert any("degraded" in m and "not a boolean" in m
                   for m in _check(spec))

    def test_build_spec_block_degraded_is_bool(self):
        assert _build(degraded=False)["degraded"] is False
        assert _build(degraded=True)["degraded"] is True

    def test_regime_outside_enum_fails(self):
        spec = _build()
        spec["regime"] = "crowded-long"  # placeholder name, not the enum
        assert any("not in frozen enum" in m for m in _check(spec))

    def test_anchor_ref_is_the_real_github_slug(self):
        # Pin updated 2026-06-11 (FREEZE-W §3: ref now spans both
        # falsification layers — floor §3 and the W-sweep §7 chapter).
        from demo.validate_skill import VALIDATED_METRICS_REF
        ref = _build()["expected_behavior"]["validated_metrics_ref"]
        assert ref == VALIDATED_METRICS_REF
        assert ref.startswith("docs/report/REPORT.md#3-falsification-chapter")
        assert "W-sweep" in ref
