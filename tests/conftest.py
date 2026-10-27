"""
Shared fixtures for TuxFix tests.
All LLM calls are mocked — tests never require a real Ollama instance.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tuxfix.llm_client import LLMResponse
from tuxfix.schemas import ProblemCategory, TroubleshootingInput


VALID_REPORT_JSON = {
    "problem_summary": "DNS resolution is failing while IP connectivity works.",
    "problem_category": "networking",
    "root_causes": [
        {
            "description": "resolv.conf is missing nameserver entries.",
            "supporting_evidence": "Name resolution fails but direct IP ping succeeds.",
            "confidence": "high",
            "is_confirmed": False,
        }
    ],
    "diagnostic_steps": [
        "Check /etc/resolv.conf for valid nameserver lines.",
        "Check systemctl status systemd-resolved.",
    ],
    "diagnostic_commands": [
        {
            "command": "cat /etc/resolv.conf",
            "purpose": "Inspect DNS configuration.",
            "expected_output": "Lines starting with 'nameserver'.",
            "interpretation_guide": "Missing nameserver lines explain the failure.",
            "risk_level": "read_only",
            "is_destructive": False,
            "requires_sudo": False,
        }
    ],
    "remediation_steps": [
        {
            "step_number": 1,
            "description": "Add a working nameserver to resolv.conf.",
            "commands": [],
            "risk_level": "medium",
            "notes": "Use nameserver 8.8.8.8 as a temporary fix.",
        }
    ],
    "missing_information": ["Output of cat /etc/resolv.conf"],
    "limitations": "Without actual resolv.conf content, this is a hypothesis.",
}


@pytest.fixture
def valid_report_json():
    return VALID_REPORT_JSON


@pytest.fixture
def valid_report_json_str():
    return json.dumps(VALID_REPORT_JSON)


@pytest.fixture
def sample_input():
    return TroubleshootingInput(
        distro="Ubuntu 22.04",
        kernel_version="5.15.0-91-generic",
        problem_category=ProblemCategory.NETWORKING,
        error_message="ping: google.com: Temporary failure in name resolution",
        symptoms="DNS lookups fail. Direct IP ping works.",
        expected_behavior="DNS resolution should work.",
        attempted_actions="Rebooted once.",
        additional_context="Home LAN, router at 192.168.1.1.",
    )


@pytest.fixture
def mock_llm_response(valid_report_json_str):
    return LLMResponse(
        text=valid_report_json_str,
        model="test-model",
        provider="mock",
        latency_seconds=0.5,
        token_count=100,
    )


@pytest.fixture
def mock_provider(mock_llm_response):
    """A mock LLM provider that returns a valid report JSON."""
    provider = MagicMock()
    provider.generate.return_value = mock_llm_response
    provider.is_available.return_value = True
    provider.list_models.return_value = ["test-model"]
    return provider
