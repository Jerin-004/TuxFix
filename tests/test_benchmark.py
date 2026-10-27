"""Tests for benchmark loading and execution — LLM calls mocked."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tuxfix.benchmark import (
    BenchmarkCase,
    export_benchmark_csv,
    export_benchmark_json,
    load_benchmark_cases,
    run_benchmark,
)
from tuxfix.llm_client import LLMResponse
from tuxfix.prompts import PromptStrategy


SAMPLE_CASES = [
    {
        "id": "t01",
        "name": "Test DNS Case",
        "description": "DNS resolution fails",
        "distro": "Ubuntu 22.04",
        "kernel_version": "5.15.0",
        "problem_category": "networking",
        "error_message": "ping: google.com: Temporary failure in name resolution",
        "symptoms": "DNS fails",
        "expected_behavior": "DNS works",
        "attempted_actions": "Rebooted",
        "additional_context": "Home network",
        "expected_concepts": ["resolv.conf", "dns"],
        "evaluation_rubric": "Should mention resolv.conf",
        "ground_truth_commands": ["cat /etc/resolv.conf"],
    }
]


@pytest.fixture
def benchmark_file(tmp_path):
    p = tmp_path / "benchmark.json"
    p.write_text(json.dumps(SAMPLE_CASES))
    return p


class TestLoadBenchmarkCases:
    def test_loads_from_real_file(self):
        """Test that the real benchmark file loads without error."""
        cases = load_benchmark_cases()
        assert len(cases) >= 8  # We defined 8 cases

    def test_loads_from_temp_file(self, benchmark_file):
        cases = load_benchmark_cases(benchmark_file)
        assert len(cases) == 1
        assert cases[0].id == "t01"
        assert cases[0].name == "Test DNS Case"

    def test_case_to_input(self, benchmark_file):
        cases = load_benchmark_cases(benchmark_file)
        inp = cases[0].to_input()
        assert inp.error_message == "ping: google.com: Temporary failure in name resolution"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_benchmark_cases(tmp_path / "nonexistent.json")

    def test_all_required_fields_loaded(self, benchmark_file):
        cases = load_benchmark_cases(benchmark_file)
        c = cases[0]
        assert c.id
        assert c.name
        assert c.error_message
        assert c.symptoms
        assert isinstance(c.expected_concepts, list)
        assert isinstance(c.ground_truth_commands, list)


class TestRunBenchmark:
    def test_runs_with_mock_provider(self, benchmark_file, mock_provider):
        cases = load_benchmark_cases(benchmark_file)
        results = run_benchmark(
            strategies=[PromptStrategy.ZERO_SHOT],
            cases=cases,
            provider=mock_provider,
        )
        assert len(results) == 1
        assert results[0].case_id == "t01"
        assert results[0].strategy == "zero_shot"

    def test_multiple_strategies(self, benchmark_file, mock_provider):
        cases = load_benchmark_cases(benchmark_file)
        strategies = [PromptStrategy.ZERO_SHOT, PromptStrategy.ROLE_BASED]
        results = run_benchmark(
            strategies=strategies,
            cases=cases,
            provider=mock_provider,
        )
        assert len(results) == 2

    def test_progress_callback_called(self, benchmark_file, mock_provider):
        cases = load_benchmark_cases(benchmark_file)
        calls = []
        def cb(case_id, strategy, current, total):
            calls.append((case_id, strategy, current, total))
        run_benchmark(
            strategies=[PromptStrategy.ZERO_SHOT],
            cases=cases,
            provider=mock_provider,
            progress_callback=cb,
        )
        assert len(calls) == 1

    def test_concept_coverage_range(self, benchmark_file, mock_provider):
        cases = load_benchmark_cases(benchmark_file)
        results = run_benchmark(
            strategies=[PromptStrategy.ZERO_SHOT],
            cases=cases,
            provider=mock_provider,
        )
        for r in results:
            assert 0.0 <= r.concept_coverage <= 1.0


class TestExportBenchmark:
    def test_export_csv(self, benchmark_file, mock_provider, tmp_path):
        cases = load_benchmark_cases(benchmark_file)
        results = run_benchmark(
            strategies=[PromptStrategy.ZERO_SHOT],
            cases=cases,
            provider=mock_provider,
        )
        output = tmp_path / "results.csv"
        export_benchmark_csv(results, output)
        assert output.exists()
        content = output.read_text()
        assert "case_id" in content
        assert "t01" in content

    def test_export_json(self, benchmark_file, mock_provider, tmp_path):
        cases = load_benchmark_cases(benchmark_file)
        results = run_benchmark(
            strategies=[PromptStrategy.ZERO_SHOT],
            cases=cases,
            provider=mock_provider,
        )
        output = tmp_path / "results.json"
        export_benchmark_json(results, output)
        assert output.exists()
        data = json.loads(output.read_text())
        assert isinstance(data, list)
        assert data[0]["case_id"] == "t01"
