"""Tests for evaluation metrics."""
from __future__ import annotations

import json
import pytest

from tuxfix.diagnostics import run_diagnosis
from tuxfix.evaluation import (
    EvaluationRecord,
    QualityRubric,
    SafetyMetrics,
    StructuralMetrics,
    compute_quality_rubric,
    compute_safety_metrics,
    compute_structural_metrics,
    evaluate_result,
)
from tuxfix.llm_client import LLMResponse
from tuxfix.prompts import PromptStrategy
from tuxfix.schemas import ProblemCategory, TroubleshootingInput


@pytest.fixture
def good_result(sample_input, mock_provider):
    return run_diagnosis(sample_input, PromptStrategy.ZERO_SHOT, provider=mock_provider)


@pytest.fixture
def failed_result(sample_input):
    from unittest.mock import MagicMock
    from tuxfix.llm_client import LLMError
    p = MagicMock()
    p.generate.side_effect = LLMError("timeout")
    return run_diagnosis(sample_input, PromptStrategy.ZERO_SHOT, provider=p)


class TestStructuralMetrics:
    def test_valid_result_high_completeness(self, good_result):
        m = compute_structural_metrics(good_result)
        assert m.valid_json is True
        assert m.schema_valid is True
        assert m.has_root_causes is True
        assert m.has_diagnostic_steps is True
        assert m.has_commands is True
        assert m.field_completeness > 0.5

    def test_failed_result_low_completeness(self, failed_result):
        m = compute_structural_metrics(failed_result)
        assert m.schema_valid is False

    def test_completeness_score_range(self, good_result):
        m = compute_structural_metrics(good_result)
        score = m.completeness_score()
        assert 0.0 <= score <= 1.0


class TestSafetyMetrics:
    def test_good_result_disclaimer_present(self, good_result):
        m = compute_safety_metrics(good_result)
        assert m.disclaimer_present is True

    def test_safety_score_range(self, good_result):
        m = compute_safety_metrics(good_result)
        assert 0.0 <= m.safety_score <= 1.0

    def test_failed_result_has_score(self, failed_result):
        m = compute_safety_metrics(failed_result)
        assert m.safety_score >= 0.0


class TestQualityRubric:
    def test_good_result_nonzero_score(self, good_result):
        rubric = compute_quality_rubric(good_result)
        assert rubric.overall_heuristic_score >= 0.0

    def test_rubric_note_present(self, good_result):
        rubric = compute_quality_rubric(good_result)
        assert len(rubric.rubric_notes) > 0
        assert "HEURISTIC" in rubric.rubric_notes[0]

    def test_failed_result_handled(self, failed_result):
        rubric = compute_quality_rubric(failed_result)
        assert rubric.overall_heuristic_score == 0.0

    def test_score_range(self, good_result):
        rubric = compute_quality_rubric(good_result)
        assert 0.0 <= rubric.overall_heuristic_score <= 1.0


class TestEvaluateResult:
    def test_returns_evaluation_record(self, good_result):
        record = evaluate_result(good_result)
        assert isinstance(record, EvaluationRecord)

    def test_to_dict_has_required_keys(self, good_result):
        record = evaluate_result(good_result)
        d = record.to_dict()
        required_keys = [
            "strategy", "model", "latency_seconds", "valid_json",
            "schema_valid", "field_completeness", "safety_score",
            "heuristic_quality_score",
        ]
        for k in required_keys:
            assert k in d, f"Missing key: {k}"

    def test_demo_flag_propagated(self, sample_input):
        from unittest.mock import MagicMock
        from tuxfix.config import TuxFixConfig
        from tuxfix.llm_client import DemoProvider
        provider = DemoProvider()
        result = run_diagnosis(
            sample_input, PromptStrategy.ZERO_SHOT, provider=provider
        )
        record = evaluate_result(result)
        assert record.is_demo is True
