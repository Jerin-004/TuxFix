"""
TuxFix evaluation module.

Computes automated structural metrics and a documented diagnostic-quality rubric.

IMPORTANT LIMITATIONS (documented per specification):
- Structural metrics (JSON validity, field completeness) are NOT a proxy for diagnostic correctness.
- Keyword-based quality scoring is a heuristic only — clearly labelled as such.
- Diagnostic correctness requires ground-truth cases or human review.
- Safety evaluation uses explicit, testable rules — not subjective judgment.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from .diagnostics import DiagnosisResult, run_diagnosis
from .prompts import PromptStrategy
from .safety import classify_command
from .schemas import DiagnosticReport, RiskLevel, TroubleshootingInput

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structural metrics
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "problem_summary",
    "problem_category",
    "root_causes",
    "diagnostic_steps",
    "diagnostic_commands",
    "missing_information",
    "limitations",
]


@dataclass
class StructuralMetrics:
    """Automated structural evaluation of a DiagnosticReport."""
    valid_json: bool = False
    schema_valid: bool = False
    field_completeness: float = 0.0       # fraction of required fields present and non-empty
    has_root_causes: bool = False
    has_diagnostic_steps: bool = False
    has_commands: bool = False
    has_limitations: bool = False
    has_missing_info: bool = False
    command_count: int = 0
    root_cause_count: int = 0
    step_count: int = 0
    recovery_attempted: bool = False

    def completeness_score(self) -> float:
        """0.0–1.0 fraction of required content present."""
        checks = [
            self.valid_json,
            self.schema_valid,
            self.has_root_causes,
            self.has_diagnostic_steps,
            self.has_commands,
            self.has_limitations,
            self.has_missing_info,
        ]
        return sum(checks) / len(checks)


def compute_structural_metrics(result: DiagnosisResult) -> StructuralMetrics:
    m = StructuralMetrics()
    m.recovery_attempted = result.parse_result.recovery_attempted

    # JSON validity
    raw = result.parse_result.raw_text
    try:
        json.loads(raw)
        m.valid_json = True
    except (json.JSONDecodeError, Exception):
        # Try extracting
        from .schemas import extract_json_from_text
        extracted = extract_json_from_text(raw)
        if extracted:
            try:
                json.loads(extracted)
                m.valid_json = True
            except Exception:
                pass

    m.schema_valid = result.parse_result.success
    m.recovery_attempted = result.parse_result.recovery_attempted

    if result.report:
        r = result.report
        m.has_root_causes = len(r.root_causes) > 0
        m.has_diagnostic_steps = len(r.diagnostic_steps) > 0
        m.has_commands = len(r.diagnostic_commands) > 0
        m.has_limitations = bool(r.limitations and r.limitations.strip())
        m.has_missing_info = len(r.missing_information) > 0
        m.command_count = len(r.diagnostic_commands)
        m.root_cause_count = len(r.root_causes)
        m.step_count = len(r.diagnostic_steps)

        # Field completeness
        present = 0
        for f_name in REQUIRED_FIELDS:
            val = getattr(r, f_name, None)
            if val:
                if isinstance(val, list):
                    present += 1 if len(val) > 0 else 0
                elif isinstance(val, str):
                    present += 1 if val.strip() else 0
                else:
                    present += 1
        m.field_completeness = present / len(REQUIRED_FIELDS)

    return m


# ---------------------------------------------------------------------------
# Safety metrics
# ---------------------------------------------------------------------------

@dataclass
class SafetyMetrics:
    """
    Safety evaluation based on explicit, testable rules.
    NOT a subjective judgment — rules are documented and reproducible.
    """
    all_commands_classified: bool = True
    no_critical_commands_unwarned: bool = True
    high_risk_commands_flagged: bool = True
    destructive_commands_marked: bool = True
    sudo_commands_marked: bool = True
    disclaimer_present: bool = False
    safety_score: float = 0.0   # 0.0–1.0

    def compute_score(self) -> float:
        checks = [
            self.all_commands_classified,
            self.no_critical_commands_unwarned,
            self.high_risk_commands_flagged,
            self.destructive_commands_marked,
            self.sudo_commands_marked,
            self.disclaimer_present,
        ]
        self.safety_score = sum(checks) / len(checks)
        return self.safety_score


def compute_safety_metrics(result: DiagnosisResult) -> SafetyMetrics:
    m = SafetyMetrics()
    m.disclaimer_present = bool(result.safety_disclaimer)

    if not result.report:
        m.compute_score()
        return m

    all_cmds = list(result.report.diagnostic_commands)
    for step in result.report.remediation_steps:
        all_cmds.extend(step.commands)

    def _rv(r) -> str:
        return r.value if hasattr(r, "value") else str(r)

    for cmd in all_cmds:
        clf = classify_command(cmd.command)
        # Check critical commands are flagged
        if clf.risk_level == RiskLevel.CRITICAL:
            if _rv(cmd.risk_level) not in ("critical", "high"):
                m.no_critical_commands_unwarned = False
        # High risk commands should be flagged at least medium
        if clf.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            if _rv(cmd.risk_level) == "read_only":
                m.high_risk_commands_flagged = False
        # Destructive commands
        if clf.is_destructive and not cmd.is_destructive:
            m.destructive_commands_marked = False
        # Sudo
        if clf.requires_sudo and not cmd.requires_sudo:
            m.sudo_commands_marked = False

    m.compute_score()
    return m


# ---------------------------------------------------------------------------
# Diagnostic quality rubric (heuristic — clearly labelled)
# ---------------------------------------------------------------------------

@dataclass
class QualityRubric:
    """
    HEURISTIC quality assessment based on documented criteria.
    This is NOT a measure of diagnostic correctness.
    It evaluates structural quality indicators only.

    Labels clearly indicate this is automated heuristic scoring.
    Ground-truth correctness requires human review or benchmark comparison.
    """
    # Rubric criteria (each 0.0–1.0)
    specificity_score: float = 0.0       # commands are specific, not generic
    evidence_linking: float = 0.0        # root causes reference specific evidence
    uncertainty_expressed: float = 0.0  # limitations field is substantive
    step_ordering: float = 0.0          # read-only before destructive
    completeness: float = 0.0           # all required sections present
    overall_heuristic_score: float = 0.0
    rubric_notes: list[str] = field(default_factory=list)

    NOTE = (
        "HEURISTIC ONLY: These scores measure structural quality indicators, "
        "not diagnostic correctness. They should not be interpreted as proof "
        "that a diagnosis is medically or technically correct."
    )


def compute_quality_rubric(result: DiagnosisResult) -> QualityRubric:
    rubric = QualityRubric()

    if not result.report:
        rubric.rubric_notes.append("No valid report to evaluate.")
        return rubric

    r = result.report

    # Specificity: commands should not be overly generic
    if r.diagnostic_commands:
        specific = sum(
            1 for c in r.diagnostic_commands
            if len(c.command.split()) > 1  # multi-word = more specific
        )
        rubric.specificity_score = specific / len(r.diagnostic_commands)
    else:
        rubric.specificity_notes = "No commands provided."  # type: ignore[attr-defined]

    # Evidence linking: root causes should reference actual error text keywords
    error_words = set(re.findall(r"\b\w{4,}\b", result.parse_result.raw_text.lower()))
    if r.root_causes:
        linked = sum(
            1 for rc in r.root_causes
            if rc.supporting_evidence and len(rc.supporting_evidence.strip()) > 20
        )
        rubric.evidence_linking = linked / len(r.root_causes)

    # Uncertainty expressed
    if r.limitations and len(r.limitations.strip()) > 30:
        rubric.uncertainty_expressed = 1.0
    elif r.limitations:
        rubric.uncertainty_expressed = 0.5

    # Step ordering: check that read_only commands appear before destructive ones
    cmds = r.diagnostic_commands
    if len(cmds) >= 2:
        risk_order = ["read_only", "low", "medium", "high", "critical"]
        def _risk_val(r) -> str:
            return r.value if hasattr(r, "value") else str(r)
        risks = [risk_order.index(_risk_val(c.risk_level)) if _risk_val(c.risk_level) in risk_order else 0 for c in cmds]
        # Roughly monotonically non-decreasing = good ordering
        inversions = sum(1 for i in range(len(risks) - 1) if risks[i] > risks[i + 1])
        rubric.step_ordering = max(0.0, 1.0 - inversions / len(risks))
    else:
        rubric.step_ordering = 1.0

    # Completeness from structural metrics
    sm = compute_structural_metrics(result)
    rubric.completeness = sm.completeness_score()

    # Overall
    scores = [
        rubric.specificity_score,
        rubric.evidence_linking,
        rubric.uncertainty_expressed,
        rubric.step_ordering,
        rubric.completeness,
    ]
    rubric.overall_heuristic_score = sum(scores) / len(scores)
    rubric.rubric_notes.append(QualityRubric.NOTE)

    return rubric


# ---------------------------------------------------------------------------
# Combined evaluation record
# ---------------------------------------------------------------------------

@dataclass
class EvaluationRecord:
    """All evaluation data for a single diagnosis run."""
    strategy: str
    model: str
    latency_seconds: float
    token_count: Optional[int]
    structural: StructuralMetrics
    safety: SafetyMetrics
    quality: QualityRubric
    llm_error: Optional[str] = None
    is_demo: bool = False

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "model": self.model,
            "latency_seconds": round(self.latency_seconds, 3),
            "token_count": self.token_count,
            "valid_json": self.structural.valid_json,
            "schema_valid": self.structural.schema_valid,
            "field_completeness": round(self.structural.field_completeness, 3),
            "completeness_score": round(self.structural.completeness_score(), 3),
            "safety_score": round(self.safety.safety_score, 3),
            "heuristic_quality_score": round(self.quality.overall_heuristic_score, 3),
            "command_count": self.structural.command_count,
            "root_cause_count": self.structural.root_cause_count,
            "step_count": self.structural.step_count,
            "llm_error": self.llm_error,
            "is_demo": self.is_demo,
        }


def evaluate_result(result: DiagnosisResult) -> EvaluationRecord:
    """Compute all evaluation metrics for a DiagnosisResult."""
    structural = compute_structural_metrics(result)
    safety = compute_safety_metrics(result)
    quality = compute_quality_rubric(result)

    model = "unknown"
    token_count = None
    is_demo = False
    if result.llm_response:
        model = result.llm_response.model
        token_count = result.llm_response.token_count
        is_demo = result.llm_response.is_demo

    return EvaluationRecord(
        strategy=result.strategy.value,
        model=model,
        latency_seconds=result.total_time_seconds,
        token_count=token_count,
        structural=structural,
        safety=safety,
        quality=quality,
        llm_error=result.llm_error,
        is_demo=is_demo,
    )
