"""
Pydantic schemas for TuxFix structured diagnostic reports.
All model responses are validated against these schemas before display.
"""
from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProblemCategory(str, Enum):
    NETWORKING = "networking"
    PACKAGE_MANAGEMENT = "package_management"
    BOOT_FAILURE = "boot_failure"
    PERMISSIONS = "permissions"
    STORAGE = "storage"
    SYSTEM_SERVICES = "system_services"
    USB_DEVICES = "usb_devices"
    GRAPHICS = "graphics"
    APPLICATION_ERROR = "application_error"
    OTHER = "other"


class DiagnosticCommand(BaseModel):
    """A single command suggested for diagnosis or remediation."""
    command: str = Field(..., description="The exact command string to run")
    purpose: str = Field(..., description="Why this command is useful")
    expected_output: str = Field(..., description="What kind of output to expect")
    interpretation_guide: str = Field(..., description="How to interpret the output")
    risk_level: RiskLevel = Field(..., description="Risk classification")
    is_destructive: bool = Field(False, description="True if this command modifies system state")
    requires_sudo: bool = Field(False, description="True if elevated privileges needed")

    @field_validator("command")
    @classmethod
    def command_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("command must not be empty")
        return v


class RootCause(BaseModel):
    """A possible root cause with supporting evidence."""
    description: str = Field(..., description="Description of the potential root cause")
    supporting_evidence: str = Field(..., description="Evidence from the input supporting this cause")
    confidence: str = Field(..., description="low / medium / high — reflects uncertainty honestly")
    is_confirmed: bool = Field(False, description="True only if definitively confirmed by evidence")


class RemediationStep(BaseModel):
    """A remediation action."""
    step_number: int
    description: str
    commands: list[DiagnosticCommand] = Field(default_factory=list)
    risk_level: RiskLevel = Field(RiskLevel.READ_ONLY)
    notes: str = ""


class DiagnosticReport(BaseModel):
    """
    Full structured diagnostic report produced by TuxFix.
    Every field is validated before display.
    """
    problem_summary: str = Field(..., description="Concise summary of the reported problem")
    problem_category: ProblemCategory = Field(..., description="Classified problem category")
    root_causes: list[RootCause] = Field(..., description="Possible root causes with evidence")
    diagnostic_steps: list[str] = Field(..., description="Ordered diagnostic steps")
    diagnostic_commands: list[DiagnosticCommand] = Field(default_factory=list)
    remediation_steps: list[RemediationStep] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list,
                                            description="Information that would improve the diagnosis")
    limitations: str = Field("", description="Relevant limitations and uncertainty")
    disclaimer: str = Field(
        "These recommendations are advisory only. Inspect all commands before running them. "
        "TuxFix does not execute commands automatically.",
        description="Safety disclaimer"
    )

    @field_validator("problem_summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("problem_summary must not be empty")
        return v.strip()

    @field_validator("root_causes")
    @classmethod
    def at_least_one_cause(cls, v: list) -> list:
        if not v:
            raise ValueError("root_causes must contain at least one entry")
        return v

    @field_validator("diagnostic_steps")
    @classmethod
    def at_least_one_step(cls, v: list) -> list:
        if not v:
            raise ValueError("diagnostic_steps must contain at least one entry")
        return v


class ParseResult(BaseModel):
    """Result of attempting to parse a model response into a DiagnosticReport."""
    success: bool
    report: Optional[DiagnosticReport] = None
    raw_text: str = ""
    error_message: str = ""
    recovery_attempted: bool = False


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Attempt to extract a JSON object from text that may contain surrounding prose.
    Returns the JSON string or None if no valid JSON block found.
    """
    # Try fenced code block first
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    # Try to find the outermost { ... }
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start: i + 1]
    return None


def parse_model_response(raw_text: str) -> ParseResult:
    """
    Parse and validate a raw model response into a DiagnosticReport.
    Attempts recovery from malformed JSON via partial extraction.
    """
    raw_text = raw_text.strip()

    # Attempt 1: direct JSON parse
    try:
        data = json.loads(raw_text)
        report = DiagnosticReport.model_validate(data)
        return ParseResult(success=True, report=report, raw_text=raw_text)
    except (json.JSONDecodeError, Exception):
        pass

    # Attempt 2: extract JSON substring
    json_str = extract_json_from_text(raw_text)
    if json_str:
        try:
            data = json.loads(json_str)
            report = DiagnosticReport.model_validate(data)
            return ParseResult(success=True, report=report, raw_text=raw_text, recovery_attempted=True)
        except (json.JSONDecodeError, Exception) as e:
            return ParseResult(
                success=False,
                raw_text=raw_text,
                error_message=f"JSON extracted but schema validation failed: {e}",
                recovery_attempted=True,
            )

    return ParseResult(
        success=False,
        raw_text=raw_text,
        error_message="No valid JSON object found in model response.",
        recovery_attempted=False,
    )


# ── Input schema ──────────────────────────────────────────────────────────────

class TroubleshootingInput(BaseModel):
    """Validated user input for a troubleshooting request."""
    distro: str = Field("", description="Linux distribution and version")
    kernel_version: str = Field("", description="Kernel version if known")
    problem_category: ProblemCategory = Field(ProblemCategory.OTHER)
    error_message: str = Field(..., description="Exact error message or terminal output")
    symptoms: str = Field(..., description="Observed symptoms")
    expected_behavior: str = Field("", description="Expected behaviour")
    attempted_actions: str = Field("", description="Actions already attempted")
    additional_context: str = Field("", description="Optional additional context")

    @field_validator("error_message")
    @classmethod
    def error_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("error_message must be at least 5 characters")
        if len(v) > 8000:
            raise ValueError("error_message is too long (max 8000 characters)")
        return v

    @field_validator("symptoms")
    @classmethod
    def symptoms_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("symptoms must be at least 5 characters")
        return v

    def to_context_dict(self) -> dict[str, str]:
        """Return a dict safe for prompt injection — omits empty fields."""
        d = self.model_dump()
        return {k: v for k, v in d.items() if v}
