"""Tests for schema validation and JSON parsing."""
from __future__ import annotations

import json
import pytest

from tuxfix.schemas import (
    DiagnosticReport,
    ParseResult,
    ProblemCategory,
    RiskLevel,
    TroubleshootingInput,
    extract_json_from_text,
    parse_model_response,
)


class TestTroubleshootingInput:
    def test_valid_input(self):
        inp = TroubleshootingInput(
            error_message="some error occurred here",
            symptoms="system crashes",
        )
        assert inp.error_message == "some error occurred here"

    def test_error_message_too_short(self):
        with pytest.raises(Exception):
            TroubleshootingInput(error_message="err", symptoms="x")

    def test_error_message_too_long(self):
        with pytest.raises(Exception):
            TroubleshootingInput(error_message="x" * 8001, symptoms="some symptom")

    def test_symptoms_not_empty(self):
        with pytest.raises(Exception):
            TroubleshootingInput(error_message="valid error message", symptoms="ab")

    def test_to_context_dict_omits_empty(self):
        inp = TroubleshootingInput(
            error_message="a valid error message",
            symptoms="something goes wrong",
            distro="",
        )
        ctx = inp.to_context_dict()
        assert "distro" not in ctx

    def test_problem_category_default(self):
        inp = TroubleshootingInput(
            error_message="valid error",
            symptoms="valid symptom text",
        )
        assert inp.problem_category == ProblemCategory.OTHER


class TestParseModelResponse:
    def test_valid_json(self, valid_report_json, valid_report_json_str):
        result = parse_model_response(valid_report_json_str)
        assert result.success is True
        assert result.report is not None
        assert result.report.problem_summary == valid_report_json["problem_summary"]

    def test_json_in_prose(self, valid_report_json_str):
        text = f"Here is my analysis:\n\n{valid_report_json_str}\n\nHope that helps!"
        result = parse_model_response(text)
        assert result.success is True
        assert result.recovery_attempted is True

    def test_json_in_code_fence(self, valid_report_json_str):
        text = f"```json\n{valid_report_json_str}\n```"
        result = parse_model_response(text)
        assert result.success is True

    def test_completely_invalid(self):
        result = parse_model_response("I am not JSON at all. Just a sentence.")
        assert result.success is False
        assert "No valid JSON" in result.error_message

    def test_valid_json_invalid_schema(self):
        bad = json.dumps({"problem_summary": "", "problem_category": "networking"})
        result = parse_model_response(bad)
        assert result.success is False

    def test_missing_required_field(self):
        # Missing root_causes
        data = {
            "problem_summary": "something broke",
            "problem_category": "networking",
            "root_causes": [],  # empty list → validation error
            "diagnostic_steps": ["step one"],
        }
        result = parse_model_response(json.dumps(data))
        assert result.success is False


class TestExtractJson:
    def test_plain_json(self, valid_report_json_str):
        assert extract_json_from_text(valid_report_json_str) is not None

    def test_json_in_text(self, valid_report_json_str):
        text = f"Blah blah {valid_report_json_str} more text"
        extracted = extract_json_from_text(text)
        assert extracted is not None
        json.loads(extracted)  # should be parseable

    def test_no_json(self):
        assert extract_json_from_text("no json here") is None


class TestDiagnosticReport:
    def test_valid_report(self, valid_report_json):
        report = DiagnosticReport.model_validate(valid_report_json)
        assert report.problem_summary
        assert len(report.root_causes) >= 1
        assert len(report.diagnostic_steps) >= 1

    def test_empty_problem_summary_rejected(self, valid_report_json):
        data = dict(valid_report_json)
        data["problem_summary"] = "   "
        with pytest.raises(Exception):
            DiagnosticReport.model_validate(data)

    def test_risk_level_enum(self, valid_report_json):
        report = DiagnosticReport.model_validate(valid_report_json)
        for cmd in report.diagnostic_commands:
            assert cmd.risk_level in RiskLevel
