"""
TuxFix — Prompt Engineering-Based Linux Troubleshooting Assistant
Streamlit application entry point.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tuxfix.config import load_config, get_config
from tuxfix.demo import DEMO_NOTICE
from tuxfix.diagnostics import run_comparison, run_diagnosis
from tuxfix.evaluation import evaluate_result
from tuxfix.llm_client import DemoProvider, OllamaProvider, get_provider
from tuxfix.prompts import (
    STRATEGY_DESCRIPTIONS,
    PromptStrategy,
    assemble_full_prompt,
    build_prompt,
)
from tuxfix.safety import SAFETY_DISCLAIMER, classify_command
from tuxfix.schemas import (
    DiagnosticReport,
    ProblemCategory,
    RiskLevel,
    TroubleshootingInput,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TuxFix — Linux Troubleshooting Assistant",
    page_icon="🐧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "config_loaded": False,
        "demo_mode": False,
        "ollama_url": "http://localhost:11434",
        "ollama_model": "codegemma:2b",
        "ollama_timeout": 120,
        "last_diagnosis": None,
        "comparison_results": None,
        "benchmark_results": None,
        "iterative_history": [],
        "active_tab": "Troubleshoot",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Helpers ───────────────────────────────────────────────────────────────────

RISK_COLORS = {
    "read_only": "🟢",
    "low": "🟡",
    "medium": "🟠",
    "high": "🔴",
    "critical": "💀",
}

RISK_LABELS = {
    "read_only": "Read-only (safe)",
    "low": "Low risk",
    "medium": "Medium risk",
    "high": "HIGH RISK — review carefully",
    "critical": "CRITICAL — do not run without expert review",
}

CATEGORY_LABELS = {
    "networking": "🌐 Networking",
    "package_management": "📦 Package Management",
    "boot_failure": "🔄 Boot Failure",
    "permissions": "🔒 Permissions",
    "storage": "💾 Storage",
    "system_services": "⚙️ System Services",
    "usb_devices": "🔌 USB Devices",
    "graphics": "🖥️ Graphics",
    "application_error": "🐛 Application Error",
    "other": "❓ Other",
}


def _get_config():
    return load_config(
        ollama_base_url=st.session_state.ollama_url,
        ollama_model=st.session_state.ollama_model,
        ollama_timeout=st.session_state.ollama_timeout,
        demo_mode=st.session_state.demo_mode,
    )


def _get_provider():
    cfg = _get_config()
    return get_provider(cfg)


def _render_risk_badge(risk: str) -> str:
    icon = RISK_COLORS.get(risk, "⚪")
    label = RISK_LABELS.get(risk, risk)
    return f"{icon} **{label}**"


def _render_command_card(cmd, idx: int):
    risk = cmd.risk_level.value if hasattr(cmd.risk_level, "value") else str(cmd.risk_level)
    icon = RISK_COLORS.get(risk, "⚪")
    with st.expander(f"{icon} `{cmd.command}`", expanded=(idx == 0)):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Purpose:** {cmd.purpose}")
            st.markdown(f"**Expected output:** {cmd.expected_output}")
            st.markdown(f"**Interpretation:** {cmd.interpretation_guide}")
        with col2:
            st.markdown(f"**Risk:** {_render_risk_badge(risk)}")
            if cmd.is_destructive:
                st.warning("⚠️ Modifies system state")
            if cmd.requires_sudo:
                st.info("🔑 Requires elevated privileges")
        st.code(cmd.command, language="bash")
        st.caption("⚠️ Review before running. TuxFix never executes commands automatically.")


def _render_report(report: DiagnosticReport, is_demo: bool = False):
    if is_demo:
        st.warning(f"🎭 {DEMO_NOTICE}")

    st.info(f"**Summary:** {report.problem_summary}")

    cat = report.problem_category.value if hasattr(report.problem_category, "value") else str(report.problem_category)
    st.markdown(f"**Category:** {CATEGORY_LABELS.get(cat, cat)}")

    # Root causes
    st.subheader("🔍 Possible Root Causes")
    st.caption("⚠️ These are hypotheses based on the provided information, not confirmed facts.")
    for i, rc in enumerate(report.root_causes, 1):
        conf_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rc.confidence, "⚪")
        confirmed = "✅ Confirmed" if rc.is_confirmed else "❓ Hypothesis"
        with st.expander(f"Cause {i}: {rc.description[:80]}...", expanded=(i == 1)):
            st.markdown(f"**Evidence:** {rc.supporting_evidence}")
            st.markdown(f"**Confidence:** {conf_color} {rc.confidence.upper()} | {confirmed}")

    # Diagnostic steps
    st.subheader("🪜 Diagnostic Steps")
    for step in report.diagnostic_steps:
        st.markdown(f"- {step}")

    # Commands
    if report.diagnostic_commands:
        st.subheader("💻 Suggested Commands")
        st.caption(SAFETY_DISCLAIMER)
        for i, cmd in enumerate(report.diagnostic_commands):
            _render_command_card(cmd, i)

    # Remediation
    if report.remediation_steps:
        st.subheader("🔧 Remediation Steps")
        for step in report.remediation_steps:
            risk = step.risk_level.value if hasattr(step.risk_level, "value") else str(step.risk_level)
            icon = RISK_COLORS.get(risk, "⚪")
            with st.expander(f"Step {step.step_number}: {step.description[:70]}", expanded=False):
                st.markdown(f"**Risk level:** {icon} {risk}")
                if step.notes:
                    st.info(step.notes)
                for cmd in step.commands:
                    st.code(cmd.command, language="bash")

    # Missing info
    if report.missing_information:
        st.subheader("❓ Information That Would Improve This Diagnosis")
        for item in report.missing_information:
            st.markdown(f"- {item}")

    # Limitations
    if report.limitations:
        st.subheader("⚠️ Limitations & Uncertainty")
        st.warning(report.limitations)

    st.caption(report.disclaimer)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.title("🐧 TuxFix")
        st.caption("Prompt Engineering-Based Linux Troubleshooting")
        st.divider()

        st.subheader("⚙️ Settings")
        st.session_state.demo_mode = st.toggle(
            "Demo Mode",
            value=st.session_state.demo_mode,
            help="Use pre-written sample responses. No real LLM needed.",
        )
        if st.session_state.demo_mode:
            st.info("🎭 Demo mode active — responses are pre-written examples.")

        st.session_state.ollama_url = st.text_input(
            "Ollama URL",
            value=st.session_state.ollama_url,
            disabled=st.session_state.demo_mode,
        )
        st.session_state.ollama_timeout = st.slider(
            "Request Timeout (s)",
            10, 300,
            value=st.session_state.ollama_timeout,
            disabled=st.session_state.demo_mode,
        )

        if not st.session_state.demo_mode:
            if st.button("🔍 Detect Available Models"):
                with st.spinner("Connecting to Ollama..."):
                    prov = OllamaProvider(_get_config())
                    if prov.is_available():
                        models = prov.list_models()
                        if models:
                            st.session_state.ollama_model = st.selectbox(
                                "Select model", models, key="_model_select_sidebar"
                            )
                            st.success(f"✅ Found {len(models)} model(s)")
                        else:
                            st.warning("No models installed. Run: ollama pull <model>")
                    else:
                        st.error("❌ Cannot reach Ollama. Is it running?")

            st.session_state.ollama_model = st.text_input(
                "Model name",
                value=st.session_state.ollama_model,
            )

            if st.button("🏓 Test Connection"):
                with st.spinner("Testing..."):
                    prov = OllamaProvider(_get_config())
                    if prov.is_available():
                        st.success("✅ Ollama is reachable")
                    else:
                        st.error("❌ Cannot reach Ollama at that URL")

        st.divider()
        st.caption("⚠️ TuxFix is an advisory tool only. It never executes commands.")
        st.caption("v1.0.0 | Academic Project")


# ── Tab: Troubleshoot ─────────────────────────────────────────────────────────

def render_troubleshoot_tab():
    st.header("🔧 Linux Troubleshooting")
    st.caption("Describe your Linux problem and select a prompt strategy to get diagnostic suggestions.")

    with st.form("troubleshoot_form"):
        col1, col2 = st.columns(2)
        with col1:
            distro = st.text_input(
                "Linux Distribution & Version",
                placeholder="e.g. Ubuntu 22.04 LTS, Arch Linux, Fedora 39",
            )
            kernel = st.text_input(
                "Kernel Version (optional)",
                placeholder="e.g. 5.15.0-91-generic  (run: uname -r)",
            )
        with col2:
            category = st.selectbox(
                "Problem Category",
                options=[c.value for c in ProblemCategory],
                format_func=lambda x: CATEGORY_LABELS.get(x, x),
            )
            strategy_name = st.selectbox(
                "Prompt Strategy",
                options=[s.value for s in PromptStrategy],
                format_func=lambda x: x.replace("_", " ").title(),
            )

        st.markdown(f"**Strategy description:** *{STRATEGY_DESCRIPTIONS[PromptStrategy(strategy_name)]}*")

        error_msg = st.text_area(
            "Error Message / Terminal Output *",
            placeholder="Paste the exact error message or terminal output here.\n\nExample:\n  bash: /usr/bin/python3: No such file or directory",
            height=150,
        )
        symptoms = st.text_area(
            "Observed Symptoms *",
            placeholder="What do you observe? e.g. 'Application crashes on launch, no output shown'",
            height=80,
        )
        col3, col4 = st.columns(2)
        with col3:
            expected = st.text_area(
                "Expected Behaviour",
                placeholder="What should happen instead?",
                height=80,
            )
        with col4:
            attempted = st.text_area(
                "Actions Already Attempted",
                placeholder="What have you already tried?",
                height=80,
            )
        extra = st.text_area(
            "Additional Context (optional)",
            placeholder="Hardware, network topology, recent changes, etc.",
            height=60,
        )

        show_prompt = st.checkbox("🔍 Show assembled prompt before submitting", value=False)
        submitted = st.form_submit_button("🚀 Diagnose", type="primary", use_container_width=True)

    if submitted:
        # Validate input
        try:
            inp = TroubleshootingInput(
                distro=distro,
                kernel_version=kernel,
                problem_category=ProblemCategory(category),
                error_message=error_msg,
                symptoms=symptoms,
                expected_behavior=expected,
                attempted_actions=attempted,
                additional_context=extra,
            )
        except Exception as e:
            st.error(f"⚠️ Input validation error: {e}")
            return

        strategy = PromptStrategy(strategy_name)

        if show_prompt:
            sys_p, usr_p = build_prompt(strategy, inp)
            with st.expander("📋 Assembled Prompt (for inspection)", expanded=True):
                st.code(assemble_full_prompt(sys_p, usr_p), language="text")

        with st.spinner(f"Running {strategy_name.replace('_',' ').title()} diagnosis..."):
            cfg = _get_config()
            prov = _get_provider()
            result = run_diagnosis(inp, strategy, provider=prov, config=cfg)

        st.session_state.last_diagnosis = result

        if result.injection_warnings:
            for w in result.injection_warnings:
                st.warning(f"🛡️ {w}")

        if result.llm_error:
            st.error(f"❌ LLM Error: {result.llm_error}")
            if not st.session_state.demo_mode:
                st.info("💡 Tip: Enable Demo Mode in the sidebar to see sample responses without Ollama.")
            return

        if not result.success:
            st.error("❌ Could not parse model response into a structured report.")
            st.caption("Raw model output:")
            st.code(result.parse_result.raw_text[:2000], language="text")
            st.caption(f"Parse error: {result.parse_result.error_message}")
            return

        is_demo = result.llm_response.is_demo if result.llm_response else False
        latency = result.total_time_seconds
        model = result.llm_response.model if result.llm_response else "unknown"

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("⏱️ Latency", f"{latency:.2f}s")
        col_b.metric("🤖 Model", model)
        col_c.metric("📊 Strategy", strategy_name.replace("_", " ").title())

        _render_report(result.report, is_demo=is_demo)


# ── Tab: Iterative Refinement ─────────────────────────────────────────────────

def render_iterative_tab():
    st.header("🔁 Iterative Refinement")
    st.caption(
        "Submit a problem, then provide new diagnostic output to refine the analysis. "
        "Each iteration builds on the previous diagnosis."
    )

    if not st.session_state.iterative_history:
        st.info("Start with an initial diagnosis below.")

    with st.form("iterative_initial_form"):
        col1, col2 = st.columns(2)
        with col1:
            distro = st.text_input("Distribution", placeholder="e.g. Ubuntu 22.04")
        with col2:
            category = st.selectbox(
                "Category",
                options=[c.value for c in ProblemCategory],
                format_func=lambda x: CATEGORY_LABELS.get(x, x),
                key="iter_cat",
            )
        error_msg = st.text_area("Error Message *", height=120, key="iter_error")
        symptoms = st.text_area("Symptoms *", height=80, key="iter_symptoms")
        submitted_init = st.form_submit_button("🚀 Initial Diagnosis", type="primary")

    if submitted_init:
        try:
            inp = TroubleshootingInput(
                distro=distro,
                problem_category=ProblemCategory(category),
                error_message=error_msg,
                symptoms=symptoms,
            )
        except Exception as e:
            st.error(f"Validation error: {e}")
            return
        with st.spinner("Generating initial diagnosis..."):
            result = run_diagnosis(inp, PromptStrategy.ITERATIVE_REFINEMENT,
                                   provider=_get_provider(), config=_get_config())
        st.session_state.iterative_history = [{"inp": inp, "result": result, "evidence": ""}]

    # Show history
    for i, entry in enumerate(st.session_state.iterative_history):
        result = entry["result"]
        with st.expander(f"Iteration {i + 1}", expanded=(i == len(st.session_state.iterative_history) - 1)):
            if entry["evidence"]:
                st.markdown(f"**New evidence:** `{entry['evidence'][:100]}`")
            if result.success:
                _render_report(result.report,
                               is_demo=result.llm_response.is_demo if result.llm_response else False)
            elif result.llm_error:
                st.error(f"LLM Error: {result.llm_error}")
            else:
                st.error(f"Parse error: {result.parse_result.error_message}")
                st.code(result.parse_result.raw_text[:500])

    # Refinement input
    if st.session_state.iterative_history:
        st.subheader("➕ Provide New Evidence")
        with st.form("iterative_refine_form"):
            new_evidence = st.text_area(
                "New diagnostic output",
                placeholder="Paste output from the suggested commands here...",
                height=150,
                key="iter_new_evidence",
            )
            refine = st.form_submit_button("🔄 Refine Diagnosis", type="primary")

        if refine and new_evidence.strip():
            last = st.session_state.iterative_history[-1]
            inp = last["inp"]
            prev_report = last["result"].parse_result.raw_text
            with st.spinner("Refining diagnosis with new evidence..."):
                result = run_diagnosis(
                    inp,
                    PromptStrategy.ITERATIVE_REFINEMENT,
                    provider=_get_provider(),
                    config=_get_config(),
                    previous_diagnosis=prev_report,
                    new_evidence=new_evidence,
                )
            st.session_state.iterative_history.append({
                "inp": inp,
                "result": result,
                "evidence": new_evidence,
            })
            st.rerun()

        if st.button("🗑️ Clear History"):
            st.session_state.iterative_history = []
            st.rerun()


# ── Tab: Prompt Lab ───────────────────────────────────────────────────────────

def render_prompt_lab_tab():
    st.header("🧪 Prompt Engineering Laboratory")
    st.caption(
        "Inspect and compare how each of the five prompt strategies assembles a different prompt "
        "from the same input. Submit to the model to see how strategy affects output."
    )

    with st.form("lab_form"):
        col1, col2 = st.columns(2)
        with col1:
            distro = st.text_input("Distribution", value="Ubuntu 22.04 LTS", key="lab_distro")
        with col2:
            category = st.selectbox(
                "Category",
                options=[c.value for c in ProblemCategory],
                format_func=lambda x: CATEGORY_LABELS.get(x, x),
                key="lab_cat",
            )
        error_msg = st.text_area(
            "Error Message",
            value="ping: google.com: Temporary failure in name resolution",
            height=100,
            key="lab_error",
        )
        symptoms = st.text_area(
            "Symptoms",
            value="DNS lookups fail. Direct IP ping works.",
            height=60,
            key="lab_symptoms",
        )
        submitted = st.form_submit_button("🔍 Inspect All Prompt Strategies", use_container_width=True)

    if submitted:
        try:
            inp = TroubleshootingInput(
                distro=distro,
                problem_category=ProblemCategory(category),
                error_message=error_msg,
                symptoms=symptoms,
            )
        except Exception as e:
            st.error(f"Validation error: {e}")
            return

        for strategy in PromptStrategy:
            sys_p, usr_p = build_prompt(strategy, inp)
            full = assemble_full_prompt(sys_p, usr_p)
            with st.expander(
                f"**{strategy.value.replace('_', ' ').title()}** — {len(full)} chars",
                expanded=(strategy == PromptStrategy.ZERO_SHOT),
            ):
                st.markdown(f"*{STRATEGY_DESCRIPTIONS[strategy]}*")
                st.markdown("**System Prompt:**")
                st.code(sys_p, language="text")
                st.markdown("**User Prompt:**")
                st.code(usr_p, language="text")


# ── Tab: Compare Strategies ───────────────────────────────────────────────────

def render_compare_tab():
    st.header("📊 Prompt Strategy Comparison")
    st.caption(
        "Submit the same problem to multiple strategies and compare structural metrics. "
        "Uses the same model and input for a fair comparison."
    )
    st.warning(
        "⚠️ Automated metrics measure structural quality only, not diagnostic correctness. "
        "See the Evaluation tab for the full rubric and limitations."
    )

    with st.form("compare_form"):
        col1, col2 = st.columns(2)
        with col1:
            distro = st.text_input("Distribution", value="Ubuntu 22.04 LTS", key="cmp_distro")
        with col2:
            category = st.selectbox(
                "Category",
                options=[c.value for c in ProblemCategory],
                format_func=lambda x: CATEGORY_LABELS.get(x, x),
                key="cmp_cat",
            )
        error_msg = st.text_area(
            "Error Message",
            value="ping: google.com: Temporary failure in name resolution",
            height=100,
            key="cmp_error",
        )
        symptoms = st.text_area(
            "Symptoms",
            value="DNS lookups fail. Direct IP ping works. Issue started after system update.",
            height=60,
            key="cmp_symptoms",
        )
        strategies_selected = st.multiselect(
            "Strategies to compare",
            options=[s.value for s in PromptStrategy],
            default=[s.value for s in PromptStrategy],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        compare_btn = st.form_submit_button("🚀 Run Comparison", type="primary", use_container_width=True)

    if compare_btn:
        if not strategies_selected:
            st.error("Select at least one strategy.")
            return
        try:
            inp = TroubleshootingInput(
                distro=distro,
                problem_category=ProblemCategory(category),
                error_message=error_msg,
                symptoms=symptoms,
            )
        except Exception as e:
            st.error(f"Validation error: {e}")
            return

        strategies = [PromptStrategy(s) for s in strategies_selected]

        progress = st.progress(0, text="Running strategies...")
        results = {}
        for i, strategy in enumerate(strategies):
            progress.progress((i) / len(strategies), text=f"Running {strategy.value}...")
            cfg = _get_config()
            prov = _get_provider()
            result = run_diagnosis(inp, strategy, provider=prov, config=cfg)
            results[strategy] = result
        progress.progress(1.0, text="Done!")

        st.session_state.comparison_results = results

    if st.session_state.comparison_results:
        results = st.session_state.comparison_results
        _render_comparison_results(results)


def _render_comparison_results(results: dict):
    # Build metrics table
    rows = []
    for strategy, result in results.items():
        ev = evaluate_result(result)
        rows.append({
            "Strategy": strategy.value.replace("_", " ").title(),
            "Valid JSON": "✅" if ev.structural.valid_json else "❌",
            "Schema Valid": "✅" if ev.structural.schema_valid else "❌",
            "Field Completeness": f"{ev.structural.field_completeness:.0%}",
            "Safety Score": f"{ev.safety.safety_score:.0%}",
            "Quality (Heuristic)": f"{ev.quality.overall_heuristic_score:.0%}",
            "Latency (s)": f"{ev.latency_seconds:.2f}",
            "Commands": ev.structural.command_count,
            "Root Causes": ev.structural.root_cause_count,
            "Error": ev.llm_error or "",
        })

    st.subheader("📈 Metrics Summary")
    st.caption("'Quality' is a heuristic structural score — not a measure of diagnostic correctness.")
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # Charts
    if any(r.success for r in results.values()):
        chart_data = pd.DataFrame([
            {
                "Strategy": s.value.replace("_", " ").title(),
                "Field Completeness": evaluate_result(r).structural.field_completeness,
                "Safety Score": evaluate_result(r).safety.safety_score,
                "Heuristic Quality": evaluate_result(r).quality.overall_heuristic_score,
            }
            for s, r in results.items()
        ])
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Field Completeness by Strategy")
            st.bar_chart(chart_data.set_index("Strategy")["Field Completeness"])
        with col2:
            st.subheader("Heuristic Quality by Strategy")
            st.bar_chart(chart_data.set_index("Strategy")["Heuristic Quality"])

    # Side-by-side output inspection
    st.subheader("🔍 Side-by-Side Output Inspection")
    cols = st.columns(min(len(results), 3))
    for i, (strategy, result) in enumerate(results.items()):
        with cols[i % len(cols)]:
            st.markdown(f"**{strategy.value.replace('_', ' ').title()}**")
            if result.success:
                st.success(f"✅ Schema valid | {result.total_time_seconds:.2f}s")
                with st.expander("Report"):
                    _render_report(
                        result.report,
                        is_demo=result.llm_response.is_demo if result.llm_response else False,
                    )
            elif result.llm_error:
                st.error(f"❌ {result.llm_error[:100]}")
            else:
                st.error(f"Parse error: {result.parse_result.error_message[:100]}")
                with st.expander("Raw output"):
                    st.code(result.parse_result.raw_text[:500])

    # Export
    st.subheader("💾 Export Results")
    export_data = []
    for strategy, result in results.items():
        ev = evaluate_result(result)
        export_data.append(ev.to_dict())
    export_json = json.dumps(export_data, indent=2)
    st.download_button(
        "⬇️ Download results as JSON",
        data=export_json,
        file_name="tuxfix_comparison_results.json",
        mime="application/json",
    )


# ── Tab: Benchmark ────────────────────────────────────────────────────────────

def render_benchmark_tab():
    st.header("🏋️ Benchmark Evaluation")
    st.caption(
        "Run the benchmark dataset through prompt strategies and record evaluation metrics. "
        "Results are honest and clearly distinguish structural metrics from diagnostic correctness."
    )
    st.warning(
        "⚠️ Running all 8 cases × 5 strategies = 40 LLM calls. "
        "This may take several minutes depending on your hardware and model."
    )

    from tuxfix.benchmark import (
        BenchmarkCase,
        export_benchmark_csv,
        export_benchmark_json,
        load_benchmark_cases,
        run_benchmark,
    )

    # Load cases info
    try:
        cases = load_benchmark_cases()
        st.success(f"✅ Loaded {len(cases)} benchmark cases")
        with st.expander("📋 View benchmark cases"):
            for c in cases:
                st.markdown(f"- **{c.id}**: {c.name} — _{c.description}_")
    except Exception as e:
        st.error(f"Could not load benchmark cases: {e}")
        return

    col1, col2 = st.columns(2)
    with col1:
        selected_strategies = st.multiselect(
            "Strategies to benchmark",
            options=[s.value for s in PromptStrategy],
            default=[PromptStrategy.CONSTRAINT_BASED.value, PromptStrategy.ROLE_BASED.value],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        selected_cases = st.multiselect(
            "Cases to run (all = run all)",
            options=[c.id for c in cases],
            default=[c.id for c in cases[:2]],
            format_func=lambda x: next((c.name for c in cases if c.id == x), x),
        )
    with col2:
        st.info(
            "**Evaluation includes:**\n"
            "- Structural metrics (JSON validity, field completeness)\n"
            "- Safety score (command classification)\n"
            "- Heuristic quality rubric\n"
            "- Concept coverage (keyword heuristic — NOT correctness proof)"
        )

    run_btn = st.button("🚀 Run Benchmark", type="primary")

    if run_btn:
        if not selected_strategies:
            st.error("Select at least one strategy.")
            return

        strategies = [PromptStrategy(s) for s in selected_strategies]
        filtered_cases = [c for c in cases if c.id in selected_cases] if selected_cases else cases

        progress = st.progress(0, "Starting benchmark...")
        results_container = []
        total = len(filtered_cases) * len(strategies)
        count = [0]

        def progress_cb(case_id, strategy, current, total_):
            count[0] = current
            progress.progress(current / total_, text=f"Case {case_id} | {strategy} ({current}/{total_})")

        from tuxfix.benchmark import run_benchmark as _run_benchmark
        with st.spinner("Running benchmark..."):
            results_list = _run_benchmark(
                strategies=strategies,
                cases=filtered_cases,
                provider=_get_provider(),
                config=_get_config(),
                progress_callback=progress_cb,
            )
        progress.progress(1.0, "Complete!")
        st.session_state.benchmark_results = results_list

    if st.session_state.benchmark_results:
        results_list = st.session_state.benchmark_results
        _render_benchmark_results(results_list)


def _render_benchmark_results(results_list):
    import pandas as pd

    rows = [r.to_dict() for r in results_list]
    df = pd.DataFrame(rows)

    st.subheader("📊 Benchmark Results")
    st.caption(
        "Concept coverage is a keyword heuristic — NOT proof of diagnostic correctness. "
        "All scores require human review for correctness assessment."
    )
    st.dataframe(df[[
        "case_id", "case_name", "strategy", "valid_json", "schema_valid",
        "completeness_score", "safety_score", "heuristic_quality_score",
        "concept_coverage_heuristic", "latency_seconds", "llm_error"
    ]], use_container_width=True)

    # Pivot table
    if len(df) > 1:
        st.subheader("Heuristic Quality by Case × Strategy")
        try:
            pivot = df.pivot_table(
                values="heuristic_quality_score",
                index="case_name",
                columns="strategy",
                aggfunc="mean",
            )
            st.dataframe(pivot.round(2), use_container_width=True)
        except Exception:
            pass

    # Export
    st.subheader("💾 Export")
    col1, col2 = st.columns(2)
    with col1:
        csv_str = df.to_csv(index=False)
        st.download_button("⬇️ Download CSV", data=csv_str,
                           file_name="tuxfix_benchmark_results.csv", mime="text/csv")
    with col2:
        json_str = json.dumps(rows, indent=2)
        st.download_button("⬇️ Download JSON", data=json_str,
                           file_name="tuxfix_benchmark_results.json", mime="application/json")


# ── Tab: Evaluation ───────────────────────────────────────────────────────────

def render_evaluation_tab():
    st.header("📐 Evaluation Methodology")
    st.markdown("""
### Metrics Overview

TuxFix uses a multi-layer evaluation framework. All limitations are documented here.

---

#### 1. Structural Metrics (Automated, Objective)
| Metric | What it measures |
|--------|-----------------|
| Valid JSON | Whether the model produced parseable JSON |
| Schema Valid | Whether the JSON matches the DiagnosticReport schema |
| Field Completeness | Fraction of required fields present and non-empty |
| Command Count | Number of diagnostic commands suggested |
| Root Cause Count | Number of hypotheses generated |

**Limitation:** JSON validity is *not* a proxy for diagnostic correctness.

---

#### 2. Safety Metrics (Automated, Rule-Based)
Safety evaluation uses explicit, testable rules:
- All commands have a risk level assigned
- Critical-risk commands are flagged appropriately
- Destructive commands are marked `is_destructive=true`
- Commands requiring sudo are marked `requires_sudo=true`
- Safety disclaimer is present

**Limitation:** These rules test whether the system *reports* risk correctly, not whether the underlying command is safe in all contexts.

---

#### 3. Heuristic Quality Rubric (Automated, Documented Heuristics)
| Criterion | How measured |
|-----------|-------------|
| Specificity | Commands have more than one argument (not overly generic) |
| Evidence Linking | Root causes reference specific text from the input |
| Uncertainty Expressed | Limitations field is substantive (>30 chars) |
| Step Ordering | Read-only commands appear before destructive ones |
| Completeness | All required sections present |

> **IMPORTANT:** These are structural proxies for quality. They do **not** prove that a diagnosis is technically correct. Correctness assessment requires human review against ground-truth cases.

---

#### 4. Concept Coverage (Keyword Heuristic)
Each benchmark case has a list of expected concepts (e.g. "resolv.conf", "nameserver").
Coverage = fraction of concepts appearing as keywords in the response.

> **This is a heuristic.** Finding the keyword "resolv.conf" does not guarantee the model correctly diagnosed the issue. Label: `concept_coverage_heuristic`.

---

#### 5. What This Project Does NOT Claim
- That one strategy is definitively superior without sufficient experimental data.
- That automated scores reflect real-world diagnostic accuracy.
- That keyword matching equals diagnostic correctness.

---

#### 6. Ground-Truth Assessment
For rigorous correctness evaluation, benchmark results should be reviewed by a Linux expert against the `evaluation_rubric` field in each benchmark case. This is documented as a future/manual step.
""")


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    render_sidebar()

    st.title("🐧 TuxFix")
    st.markdown(
        "**A Prompt Engineering-Based Linux Troubleshooting Assistant** | "
        "*Academic Project — Prompt engineering strategies compared and evaluated*"
    )
    st.divider()

    tabs = st.tabs([
        "🔧 Troubleshoot",
        "🔁 Iterative Refinement",
        "🧪 Prompt Lab",
        "📊 Compare Strategies",
        "🏋️ Benchmark",
        "📐 Evaluation",
    ])

    with tabs[0]:
        render_troubleshoot_tab()
    with tabs[1]:
        render_iterative_tab()
    with tabs[2]:
        render_prompt_lab_tab()
    with tabs[3]:
        render_compare_tab()
    with tabs[4]:
        render_benchmark_tab()
    with tabs[5]:
        render_evaluation_tab()


if __name__ == "__main__":
    main()
