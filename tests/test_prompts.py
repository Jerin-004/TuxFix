"""Tests for all five prompt strategy templates."""
from __future__ import annotations

import pytest

from tuxfix.prompts import (
    PromptStrategy,
    assemble_full_prompt,
    build_prompt,
    build_zero_shot_prompt,
    build_role_based_prompt,
    build_few_shot_prompt,
    build_constraint_based_prompt,
    build_iterative_refinement_prompt,
    STRATEGY_DESCRIPTIONS,
    OUTPUT_SCHEMA_DESCRIPTION,
)
from tuxfix.schemas import ProblemCategory, TroubleshootingInput


@pytest.fixture
def dns_input():
    return TroubleshootingInput(
        distro="Ubuntu 22.04",
        kernel_version="5.15.0",
        problem_category=ProblemCategory.NETWORKING,
        error_message="ping: google.com: Temporary failure in name resolution",
        symptoms="DNS lookups fail. IP ping works.",
        expected_behavior="DNS should work.",
        attempted_actions="Rebooted.",
        additional_context="Home network.",
    )


class TestZeroShotPrompt:
    def test_returns_tuple(self, dns_input):
        sys_p, usr_p = build_zero_shot_prompt(dns_input)
        assert isinstance(sys_p, str)
        assert isinstance(usr_p, str)

    def test_contains_error_message(self, dns_input):
        _, usr_p = build_zero_shot_prompt(dns_input)
        assert "Temporary failure in name resolution" in usr_p

    def test_contains_output_schema(self, dns_input):
        _, usr_p = build_zero_shot_prompt(dns_input)
        assert "problem_summary" in usr_p

    def test_no_examples_in_zero_shot(self, dns_input):
        sys_p, usr_p = build_zero_shot_prompt(dns_input)
        # Zero-shot should not contain worked examples
        assert "EXAMPLE 1" not in usr_p
        assert "EXAMPLE 2" not in usr_p

    def test_system_prompt_not_empty(self, dns_input):
        sys_p, _ = build_zero_shot_prompt(dns_input)
        assert len(sys_p.strip()) > 0


class TestRoleBasedPrompt:
    def test_persona_in_system_prompt(self, dns_input):
        sys_p, _ = build_role_based_prompt(dns_input)
        assert "senior" in sys_p.lower() or "experienced" in sys_p.lower()

    def test_contains_context(self, dns_input):
        _, usr_p = build_role_based_prompt(dns_input)
        assert "Ubuntu 22.04" in usr_p

    def test_system_prompt_different_from_zero_shot(self, dns_input):
        sys_z, _ = build_zero_shot_prompt(dns_input)
        sys_r, _ = build_role_based_prompt(dns_input)
        assert sys_z != sys_r


class TestFewShotPrompt:
    def test_examples_present(self, dns_input):
        _, usr_p = build_few_shot_prompt(dns_input)
        assert "EXAMPLE 1" in usr_p
        assert "EXAMPLE 2" in usr_p

    def test_actual_problem_present(self, dns_input):
        _, usr_p = build_few_shot_prompt(dns_input)
        assert "NOW DIAGNOSE" in usr_p or "Temporary failure" in usr_p

    def test_examples_are_json(self, dns_input):
        import json
        _, usr_p = build_few_shot_prompt(dns_input)
        # The prompt embeds JSON examples — check for typical keys
        assert '"problem_summary"' in usr_p
        assert '"root_causes"' in usr_p


class TestConstraintBasedPrompt:
    def test_constraint_rules_present(self, dns_input):
        _, usr_p = build_constraint_based_prompt(dns_input)
        assert "EVIDENCE RULE" in usr_p
        assert "RISK RULE" in usr_p

    def test_system_says_no_prose(self, dns_input):
        sys_p, _ = build_constraint_based_prompt(dns_input)
        assert "no prose" in sys_p.lower() or "ONLY" in sys_p

    def test_schema_in_prompt(self, dns_input):
        _, usr_p = build_constraint_based_prompt(dns_input)
        assert "diagnostic_commands" in usr_p

    def test_system_prompt_different_from_role(self, dns_input):
        sys_r, _ = build_role_based_prompt(dns_input)
        sys_c, _ = build_constraint_based_prompt(dns_input)
        assert sys_r != sys_c


class TestIterativeRefinementPrompt:
    def test_first_iteration_no_history(self, dns_input):
        sys_p, usr_p = build_iterative_refinement_prompt(dns_input)
        assert "ITERATION 1" in usr_p or "initial" in usr_p.lower()

    def test_second_iteration_includes_previous(self, dns_input):
        prev = '{"problem_summary": "DNS issue", "root_causes": []}'
        sys_p, usr_p = build_iterative_refinement_prompt(
            dns_input, previous_diagnosis=prev, new_evidence="cat /etc/resolv.conf showed no nameserver"
        )
        assert "PREVIOUS DIAGNOSIS" in usr_p
        assert "NEW DIAGNOSTIC EVIDENCE" in usr_p
        assert "cat /etc/resolv.conf showed no nameserver" in usr_p

    def test_new_evidence_preserved(self, dns_input):
        evidence = "nameserver 127.0.0.53 only"
        _, usr_p = build_iterative_refinement_prompt(
            dns_input, previous_diagnosis="prev", new_evidence=evidence
        )
        assert evidence in usr_p


class TestBuildPromptDispatcher:
    def test_all_strategies_return_tuples(self, dns_input):
        for strategy in PromptStrategy:
            result = build_prompt(strategy, dns_input)
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_strategies_produce_different_prompts(self, dns_input):
        prompts = []
        for strategy in PromptStrategy:
            if strategy == PromptStrategy.ITERATIVE_REFINEMENT:
                continue  # Skip — different by design
            _, usr_p = build_prompt(strategy, dns_input)
            prompts.append(usr_p)
        # All user prompts should be unique
        assert len(set(prompts)) == len(prompts), "Strategies produced identical prompts!"

    def test_invalid_strategy_raises(self, dns_input):
        with pytest.raises(ValueError):
            build_prompt("nonexistent_strategy", dns_input)  # type: ignore

    def test_all_strategies_have_descriptions(self):
        for strategy in PromptStrategy:
            assert strategy in STRATEGY_DESCRIPTIONS
            assert len(STRATEGY_DESCRIPTIONS[strategy]) > 20


class TestAssemblePrompt:
    def test_both_parts_present(self):
        result = assemble_full_prompt("system text", "user text")
        assert "system text" in result
        assert "user text" in result
        assert "[SYSTEM]" in result
        assert "[USER]" in result
