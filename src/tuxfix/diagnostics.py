"""
TuxFix diagnostics orchestration.

Coordinates: input validation → safety scan → prompt building → LLM call → parsing → safety enrichment.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from .config import TuxFixConfig, get_config
from .llm_client import BaseLLMProvider, LLMError, LLMResponse, get_provider
from .prompts import PromptStrategy, assemble_full_prompt, build_prompt
from .safety import SAFETY_DISCLAIMER, classify_command, detect_prompt_injection
from .schemas import DiagnosticReport, ParseResult, RiskLevel, TroubleshootingInput, parse_model_response

logger = logging.getLogger(__name__)


@dataclass
class DiagnosisResult:
    """Full result of a single diagnosis run."""
    strategy: PromptStrategy
    parse_result: ParseResult
    llm_response: Optional[LLMResponse] = None
    llm_error: Optional[str] = None
    assembled_prompt: str = ""
    injection_warnings: list[str] = field(default_factory=list)
    safety_disclaimer: str = SAFETY_DISCLAIMER
    total_time_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.parse_result.success

    @property
    def report(self) -> Optional[DiagnosticReport]:
        return self.parse_result.report


def _enrich_commands_with_safety(report: DiagnosticReport) -> DiagnosticReport:
    """
    Re-classify each command's risk using the safety module, overriding model-provided values
    if the model under-reported risk. Model over-reporting is kept (conservative).
    """
    risk_order = ["read_only", "low", "medium", "high", "critical"]

    def max_risk(a: str, b: str) -> str:
        ia = risk_order.index(a) if a in risk_order else 0
        ib = risk_order.index(b) if b in risk_order else 0
        return risk_order[max(ia, ib)]

    for cmd in report.diagnostic_commands:
        classification = classify_command(cmd.command)
        # Upgrade risk if safety module says higher; never downgrade
        merged_risk = max_risk(cmd.risk_level.value if hasattr(cmd.risk_level, "value") else str(cmd.risk_level),
                               classification.risk_level.value)
        cmd.risk_level = RiskLevel(merged_risk)
        if classification.is_destructive:
            cmd.is_destructive = True
        if classification.requires_sudo:
            cmd.requires_sudo = True

    for step in report.remediation_steps:
        for cmd in step.commands:
            classification = classify_command(cmd.command)
            merged_risk = max_risk(cmd.risk_level.value if hasattr(cmd.risk_level, "value") else str(cmd.risk_level),
                                   classification.risk_level.value)
            cmd.risk_level = RiskLevel(merged_risk)

    return report


def run_diagnosis(
    inp: TroubleshootingInput,
    strategy: PromptStrategy,
    provider: Optional[BaseLLMProvider] = None,
    config: Optional[TuxFixConfig] = None,
    previous_diagnosis: Optional[str] = None,
    new_evidence: str = "",
) -> DiagnosisResult:
    """
    Run a full diagnosis for the given input and strategy.

    Args:
        inp: Validated troubleshooting input.
        strategy: Prompt engineering strategy to use.
        provider: LLM provider (defaults to get_provider()).
        config: Configuration (defaults to get_config()).
        previous_diagnosis: Previous JSON diagnosis for iterative refinement.
        new_evidence: New evidence text for iterative refinement.

    Returns:
        DiagnosisResult containing the parsed report or error details.
    """
    cfg = config or get_config()
    prov = provider or get_provider(cfg)
    start_total = time.monotonic()

    # 1. Safety scan on user input
    all_text = " ".join([
        inp.error_message, inp.symptoms, inp.additional_context, inp.attempted_actions
    ])
    injection_warnings = detect_prompt_injection(all_text)
    if injection_warnings:
        logger.warning("Prompt injection patterns detected in user input: %s", injection_warnings)

    # 2. Build prompt
    system_prompt, user_prompt = build_prompt(
        strategy, inp,
        previous_diagnosis=previous_diagnosis,
        new_evidence=new_evidence,
    )
    assembled = assemble_full_prompt(system_prompt, user_prompt)

    # 3. Call LLM
    llm_response: Optional[LLMResponse] = None
    llm_error: Optional[str] = None

    try:
        llm_response = prov.generate(user_prompt, system_prompt=system_prompt)
        raw_text = llm_response.text
    except LLMError as e:
        llm_error = str(e)
        logger.error("LLM call failed: %s", llm_error)
        total = time.monotonic() - start_total
        return DiagnosisResult(
            strategy=strategy,
            parse_result=ParseResult(success=False, error_message=llm_error),
            llm_error=llm_error,
            assembled_prompt=assembled,
            injection_warnings=injection_warnings,
            total_time_seconds=total,
        )

    # 4. Parse and validate response
    parse_result = parse_model_response(raw_text)

    # 5. Enrich commands with safety classification
    if parse_result.success and parse_result.report:
        parse_result.report = _enrich_commands_with_safety(parse_result.report)

    total = time.monotonic() - start_total

    return DiagnosisResult(
        strategy=strategy,
        parse_result=parse_result,
        llm_response=llm_response,
        assembled_prompt=assembled,
        injection_warnings=injection_warnings,
        total_time_seconds=total,
    )


def run_comparison(
    inp: TroubleshootingInput,
    strategies: list[PromptStrategy],
    provider: Optional[BaseLLMProvider] = None,
    config: Optional[TuxFixConfig] = None,
) -> dict[PromptStrategy, DiagnosisResult]:
    """
    Run diagnosis with multiple strategies on the same input.
    Uses the same provider and input for fair comparison.
    Returns dict mapping strategy → DiagnosisResult.
    """
    cfg = config or get_config()
    prov = provider or get_provider(cfg)
    results: dict[PromptStrategy, DiagnosisResult] = {}

    for strategy in strategies:
        logger.info("Running comparison strategy: %s", strategy.value)
        result = run_diagnosis(inp, strategy, provider=prov, config=cfg)
        results[strategy] = result

    return results
