"""
TuxFix benchmark execution module.

Loads benchmark cases from data/benchmark_cases.json, runs them through
one or more prompt strategies, and records structured evaluation results.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .config import TuxFixConfig, get_config
from .diagnostics import run_diagnosis
from .evaluation import EvaluationRecord, evaluate_result
from .llm_client import BaseLLMProvider, get_provider
from .prompts import PromptStrategy
from .schemas import ProblemCategory, TroubleshootingInput

logger = logging.getLogger(__name__)

DEFAULT_BENCHMARK_PATH = Path(__file__).parent.parent.parent / "data" / "benchmark_cases.json"


@dataclass
class BenchmarkCase:
    """A single benchmark test case."""
    id: str
    name: str
    description: str
    distro: str
    kernel_version: str
    problem_category: str
    error_message: str
    symptoms: str
    expected_behavior: str
    attempted_actions: str
    additional_context: str
    expected_concepts: list[str]        # concepts we expect the diagnosis to address
    evaluation_rubric: str              # documented criteria for human review
    ground_truth_commands: list[str]    # commands that should appear (for keyword check)

    def to_input(self) -> TroubleshootingInput:
        try:
            cat = ProblemCategory(self.problem_category)
        except ValueError:
            cat = ProblemCategory.OTHER
        return TroubleshootingInput(
            distro=self.distro,
            kernel_version=self.kernel_version,
            problem_category=cat,
            error_message=self.error_message,
            symptoms=self.symptoms,
            expected_behavior=self.expected_behavior,
            attempted_actions=self.attempted_actions,
            additional_context=self.additional_context,
        )


def load_benchmark_cases(path: Optional[Path] = None) -> list[BenchmarkCase]:
    """Load benchmark cases from JSON file."""
    p = path or DEFAULT_BENCHMARK_PATH
    if not p.exists():
        raise FileNotFoundError(f"Benchmark file not found: {p}")
    with open(p) as f:
        raw = json.load(f)
    cases = []
    for item in raw:
        cases.append(BenchmarkCase(
            id=item["id"],
            name=item["name"],
            description=item["description"],
            distro=item.get("distro", ""),
            kernel_version=item.get("kernel_version", ""),
            problem_category=item.get("problem_category", "other"),
            error_message=item["error_message"],
            symptoms=item["symptoms"],
            expected_behavior=item.get("expected_behavior", ""),
            attempted_actions=item.get("attempted_actions", ""),
            additional_context=item.get("additional_context", ""),
            expected_concepts=item.get("expected_concepts", []),
            evaluation_rubric=item.get("evaluation_rubric", ""),
            ground_truth_commands=item.get("ground_truth_commands", []),
        ))
    return cases


@dataclass
class BenchmarkResult:
    """Result of running a benchmark case through a strategy."""
    case_id: str
    case_name: str
    strategy: str
    evaluation: EvaluationRecord
    concept_coverage: float             # fraction of expected_concepts found (HEURISTIC)
    concept_coverage_note: str = (
        "HEURISTIC: keyword match only — not proof of diagnostic correctness"
    )
    assembled_prompt_length: int = 0
    raw_response_excerpt: str = ""

    def to_dict(self) -> dict:
        d = self.evaluation.to_dict()
        d.update({
            "case_id": self.case_id,
            "case_name": self.case_name,
            "concept_coverage_heuristic": round(self.concept_coverage, 3),
            "concept_coverage_note": self.concept_coverage_note,
            "prompt_length_chars": self.assembled_prompt_length,
        })
        return d


def _compute_concept_coverage(report_text: str, expected_concepts: list[str]) -> float:
    """
    HEURISTIC: check what fraction of expected concepts appear as keywords.
    This is NOT proof of diagnostic correctness — labelled accordingly.
    """
    if not expected_concepts:
        return 1.0
    lower = report_text.lower()
    found = sum(1 for concept in expected_concepts if concept.lower() in lower)
    return found / len(expected_concepts)


def run_benchmark(
    strategies: Optional[list[PromptStrategy]] = None,
    cases: Optional[list[BenchmarkCase]] = None,
    provider: Optional[BaseLLMProvider] = None,
    config: Optional[TuxFixConfig] = None,
    benchmark_path: Optional[Path] = None,
    progress_callback=None,
) -> list[BenchmarkResult]:
    """
    Run benchmark cases through the given strategies.

    Args:
        strategies: List of strategies to run. Defaults to all five.
        cases: Benchmark cases. Defaults to loading from benchmark_cases.json.
        provider: LLM provider. Defaults to get_provider().
        config: Configuration. Defaults to get_config().
        benchmark_path: Path to benchmark JSON.
        progress_callback: Optional callable(case_id, strategy, current, total) for progress updates.

    Returns:
        List of BenchmarkResult records.
    """
    cfg = config or get_config()
    prov = provider or get_provider(cfg)
    strategies = strategies or list(PromptStrategy)
    cases = cases or load_benchmark_cases(benchmark_path)

    results: list[BenchmarkResult] = []
    total = len(cases) * len(strategies)
    count = 0

    for case in cases:
        inp = case.to_input()
        for strategy in strategies:
            count += 1
            logger.info(
                "[%d/%d] Benchmark: case=%s strategy=%s",
                count, total, case.id, strategy.value
            )
            if progress_callback:
                progress_callback(case.id, strategy.value, count, total)

            diag = run_diagnosis(inp, strategy, provider=prov, config=cfg)
            evaluation = evaluate_result(diag)

            # Concept coverage heuristic
            report_text = diag.parse_result.raw_text
            coverage = _compute_concept_coverage(report_text, case.expected_concepts)

            results.append(BenchmarkResult(
                case_id=case.id,
                case_name=case.name,
                strategy=strategy.value,
                evaluation=evaluation,
                concept_coverage=coverage,
                assembled_prompt_length=len(diag.assembled_prompt),
                raw_response_excerpt=report_text[:300] if report_text else "",
            ))

    return results


def export_benchmark_csv(results: list[BenchmarkResult], output_path: Path) -> None:
    """Export benchmark results to CSV."""
    if not results:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r.to_dict() for r in results]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Benchmark results exported to %s", output_path)


def export_benchmark_json(results: list[BenchmarkResult], output_path: Path) -> None:
    """Export benchmark results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    logger.info("Benchmark results exported to %s", output_path)
