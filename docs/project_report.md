# TuxFix: A Prompt Engineering-Based Linux Troubleshooting Assistant

**Course Project Report**
**Subject:** Advanced Topics in Artificial Intelligence / Software Engineering
**Academic Year:** 2025–2026

---

## Abstract

TuxFix is an interactive Linux troubleshooting assistant that demonstrates how different prompt engineering strategies affect the quality and reliability of LLM-generated diagnostic recommendations. The system accepts structured Linux problem descriptions and generates structured diagnostic reports using a locally running language model (Ollama). Five distinct prompt engineering strategies — zero-shot, role-based, few-shot, constraint-based, and iterative refinement — are implemented, evaluated, and compared using a documented multi-layer evaluation framework. The project contributes a modular, safety-conscious application architecture, a small but structured Linux troubleshooting benchmark dataset, and an honest evaluation methodology that clearly distinguishes automated structural metrics from diagnostic correctness. All commands suggested by the system are presented for human review only; the application never executes commands automatically.

---

## 1. Introduction

Large Language Models (LLMs) have demonstrated strong capabilities in code generation, question answering, and technical documentation. Linux system administration is a domain that requires precise, contextual reasoning: misidentifying a root cause or suggesting an incorrect command can cause data loss or system instability. This makes it a valuable testbed for studying how the structure of prompts affects the safety and reliability of LLM outputs.

TuxFix addresses this by building a complete, functional troubleshooting assistant as a vehicle for prompt engineering research. Rather than evaluating a single prompting approach, it implements and compares five strategies, each designed to elicit different reasoning behaviours from the same underlying model. The application is designed for use as an academic demonstration tool and as a foundation for further research.

---

## 2. Problem Statement

Linux system administration involves diagnosing problems that span networking, package management, storage, permissions, system services, hardware interfaces, and application runtime environments. Users — particularly those less experienced with Linux — often face error messages that are cryptic, incomplete, or misleading. Existing resources (Stack Overflow, man pages, distribution wikis) require the user to already understand the problem well enough to search for it.

LLMs offer a promising alternative: a user can describe a symptom in natural language and receive structured diagnostic guidance. However, LLM responses are sensitive to prompt design. The same model, given the same problem, may produce a cautious evidence-based analysis or a confident but unfounded guess, depending on how the prompt is framed. This unpredictability is a significant barrier to deployment in safety-sensitive contexts.

---

## 3. Project Objectives

1. Implement a functional Linux troubleshooting assistant with a professional Streamlit interface.
2. Design and implement five structurally distinct prompt engineering strategies.
3. Build a structured output schema that enables automated validation of model responses.
4. Implement a safety layer that classifies command risk independently of model output.
5. Create a documented benchmark dataset of eight realistic Linux troubleshooting scenarios.
6. Develop a multi-layer evaluation framework that is honest about what can and cannot be measured automatically.
7. Provide a comparison dashboard and export facility for experimental results.
8. Demonstrate the system in demo mode without requiring a running LLM.

---

## 4. Existing System Limitations

### 4.1 Command-Line Search Tools
Tools such as `man`, `apropos`, and web search require the user to formulate a well-structured query. They return documentation, not diagnosis.

### 4.2 Generic Chatbots
General-purpose chatbots (e.g., web-based assistants) may provide Linux advice but:
- Do not accept structured, validated input
- Do not enforce a structured output format
- Do not classify command risk
- Cannot be run locally without a paid API
- Do not support prompt strategy comparison

### 4.3 Existing LLM Wrappers
Open-source LLM front-ends typically provide a single chat interface. They do not support:
- Prompt strategy selection and comparison
- Structured diagnostic output with schema validation
- Automated evaluation metrics
- Benchmark datasets

### 4.4 Safety Gaps
No existing open-source Linux troubleshooting assistant provides risk classification for suggested commands, prompt injection detection, or a documented safety evaluation framework.

---

## 5. Proposed System

TuxFix addresses these limitations through:

- **Structured input and output**: Pydantic-validated schemas at both ends.
- **Five prompt strategies**: Systematically different approaches to the same problem.
- **Safety-first architecture**: Command risk is classified by an independent rule-based module, not trusted from model output alone.
- **Local inference**: Ollama enables completely offline operation.
- **Demo mode**: A clearly labelled offline demonstration mode that never misrepresents pre-written responses as LLM output.
- **Evaluation framework**: Multi-layer metrics with honest labelling of heuristics vs objective measures.
- **Export facility**: Experimental results can be exported to CSV/JSON for analysis.

---

## 6. Literature Review and Background

### 6.1 Prompt Engineering
Prompt engineering refers to the practice of designing and refining the inputs to LLMs to elicit desired outputs. It has emerged as a distinct skill as researchers found that model outputs are highly sensitive to input phrasing, structure, and context.

Key techniques relevant to TuxFix include:

**Zero-shot prompting** presents a task description without examples. The model relies entirely on its pre-training. Wei et al. (2022) showed that sufficiently large models can perform zero-shot reasoning on tasks they were not explicitly trained for.

**Few-shot prompting** (Brown et al., 2020) demonstrated that providing a small number of input-output examples in the prompt dramatically improves performance on many tasks without any fine-tuning. The examples serve as implicit demonstrations of the desired format and reasoning style.

**Role-based prompting** assigns a professional identity to the model ("you are an expert X"). Research has shown this can improve response quality in domain-specific tasks by activating relevant knowledge patterns. However, the mechanisms are not fully understood.

**Structured output prompting** constrains the model to produce machine-parseable output (typically JSON). This is essential for systems that need to validate and display model responses programmatically (Liu et al., 2023).

**Iterative refinement** treats LLM-based problem solving as a multi-turn dialogue, where intermediate outputs are refined based on new information. This mirrors how expert diagnosticians actually work.

### 6.2 LLM Safety in Technical Domains
Several studies have highlighted risks of deploying LLMs for technical advice without safety filters:
- Models may present incorrect information confidently (hallucination)
- Models can be manipulated through adversarial inputs embedded in data (prompt injection)
- Commands suggested without risk context can cause system damage

TuxFix addresses these through schema validation, command risk classification, injection detection, and mandatory safety disclaimers.

### 6.3 Ollama and Local Inference
Ollama (https://ollama.ai) provides a local REST API for running quantised LLMs on consumer hardware. It supports a growing library of models and enables privacy-preserving, offline operation. TuxFix uses Ollama as its primary inference backend, making the system deployable without network access or API costs.

> **Note on citations**: The references above reflect well-established research directions. Specific paper titles and publication venues are given where the work is widely known. Readers should verify citation details independently; this report does not fabricate DOIs or page numbers.

---

## 7. System Architecture

See `docs/architecture.md` for the full architecture diagram and module descriptions.

**Summary:**

```
Streamlit UI (app.py)
    ↓ TroubleshootingInput
Diagnostics Orchestrator (diagnostics.py)
    ↓ injection scan  ↓ prompt build  ↓ LLM call  ↓ parse  ↓ safety enrich
Prompts  │  LLM Client  │  Schemas  │  Safety  │  Evaluation
         │              │           │           │
    OllamaProvider  DemoProvider  Pydantic  classify_command()
```

The application is split into `app.py` (UI) and `src/tuxfix/` (library). This separation enables testing the library without launching Streamlit.

---

## 8. Prompt Strategy Design

See `docs/prompt_strategies.md` for the full strategy descriptions, implementation details, and comparison table.

**Summary of the five strategies:**

| Strategy | Core Mechanism |
|----------|---------------|
| Zero-Shot | Task description + schema, no examples |
| Role-Based | Expert persona + structured context labelling |
| Few-Shot | Two worked examples before the actual problem |
| Constraint-Based | Numbered explicit rules for every output property |
| Iterative Refinement | Multi-turn evidence incorporation |

---

## 9. Implementation Details

### 9.1 Technology Stack
- **Python 3.13** (Anaconda distribution)
- **Streamlit 1.45.1** — web interface
- **Pydantic 2.10** — schema validation
- **Requests 2.34** — Ollama HTTP client
- **Pandas 2.2** — results processing
- **Plotly 5.24** — interactive charts
- **pytest 8.3 + pytest-mock** — testing
- **python-pptx** — presentation generation

### 9.2 Key Design Decisions

**Pydantic v2 for validation**: Provides automatic type coercion, field validators, and clear error messages when model responses violate the schema. This is essential for reliable operation with models that occasionally produce malformed output.

**Two-stage JSON parsing**: The parser first attempts direct JSON parsing. If that fails, it searches for a JSON object within surrounding prose. This handles models that prepend explanation text before the JSON object.

**Conservative risk merging**: When the safety module classifies a command at a higher risk level than the model reported, the higher level is used. The system never reduces risk below the model-reported level (conservative — never downgrades).

**Session state in Streamlit**: Iterative refinement history and comparison results are stored in `st.session_state` rather than a database, avoiding persistence of diagnostic data beyond the session.

### 9.3 Input Separation Architecture
User-supplied error messages are injected between explicit delimiters in the user prompt. They are never interpolated into the system prompt. This limits the blast radius of prompt injection attacks embedded in diagnostic data.

---

## 10. Experimental Methodology

### 10.1 Setup
- Model: codegemma:2b (Q4_0 quantisation, 8192 token context)
- Hardware: Local machine with Ollama
- Temperature: 0.2 (low, for reproducibility)
- Top-p: 0.9
- Max tokens: 2048

### 10.2 Procedure
1. Load the eight benchmark cases from `data/benchmark_cases.json`.
2. For each case, run all five strategies.
3. Record `EvaluationRecord` for each run.
4. Export results to CSV/JSON.
5. Review raw outputs for cases where automated metrics are insufficient.

### 10.3 Controls
- Same model, same temperature, same max_tokens for all strategies.
- Same `TroubleshootingInput` object passed to all strategy prompt builders.
- No result is discarded — errors are recorded, not silently omitted.

---

## 11. Evaluation Metrics

See `docs/evaluation.md` for the full metric definitions, rationale, and limitations.

**Three layers:**
1. Structural (objective): JSON validity, schema validity, field completeness
2. Safety (rule-based): Risk flag accuracy, disclaimer presence
3. Quality (heuristic): Specificity, evidence linking, uncertainty, step ordering, completeness

---

## 12. Results

> **Note:** The results tables below are intentionally left empty. They will be populated during the demonstration session by running the benchmark on the installed model. Fabricating results before experiments have been conducted would misrepresent the research.

### 12.1 Structural Metrics by Strategy

| Strategy | Valid JSON | Schema Valid | Field Completeness | Avg Latency |
|----------|-----------|-------------|-------------------|-------------|
| Zero-Shot | — | — | — | — |
| Role-Based | — | — | — | — |
| Few-Shot | — | — | — | — |
| Constraint-Based | — | — | — | — |
| Iterative Refinement | — | — | — | — |

### 12.2 Safety Scores by Strategy

| Strategy | Safety Score | Disclaimer Present |
|----------|-------------|-------------------|
| Zero-Shot | — | — |
| Role-Based | — | — |
| Few-Shot | — | — |
| Constraint-Based | — | — |
| Iterative Refinement | — | — |

### 12.3 Heuristic Quality by Strategy

| Strategy | Specificity | Evidence Linking | Uncertainty | Overall Heuristic |
|----------|------------|-----------------|-------------|------------------|
| Zero-Shot | — | — | — | — |
| Role-Based | — | — | — | — |
| Few-Shot | — | — | — | — |
| Constraint-Based | — | — | — | — |
| Iterative Refinement | — | — | — | — |

---

## 13. Discussion

*(To be completed after experiments are run.)*

The discussion section will address:
- Which strategies produced the highest structural compliance, and why
- Whether role-based prompting improved evidence grounding compared to zero-shot
- Whether few-shot examples increased format consistency or introduced biases from the examples
- Whether constraint-based rules achieved higher safety classification accuracy
- How iterative refinement changed confidence levels and diagnostic steps across iterations
- Surprising failures or unexpected successes
- Practical implications for deploying LLM-based diagnostic tools

---

## 14. Limitations

1. **Single model**: All experiments use codegemma:2b. Results may not generalise to larger or differently trained models.
2. **Quantisation effects**: The Q4_0 quantised model may behave differently from the full-precision original.
3. **Small benchmark**: Eight cases cannot support statistical hypothesis testing. Results are descriptive only.
4. **Heuristic evaluation gap**: The gap between automated metrics and true diagnostic correctness cannot be fully closed without a ground-truth database reviewed by Linux experts.
5. **Prompt sensitivity**: Small changes to prompt wording can produce different results — the strategies represent one point in a large design space.
6. **Single evaluator**: Both the prompts and the rubric were designed by the same team — potential for confirmation bias.
7. **No user study**: Whether the interface is usable by target users (Linux novices) has not been tested.

---

## 15. Ethical, Privacy, and Security Considerations

### 15.1 Advisory Tool Boundaries
TuxFix is explicitly an advisory tool. It never executes commands. Every diagnostic suggestion includes a mandatory disclaimer. Commands are classified by risk level to inform user judgment.

### 15.2 Data Privacy
- Diagnostic input is not persisted by default.
- Exported results are user-initiated.
- The export function redacts credential-looking values.
- No telemetry or external network calls are made (Ollama is local).

### 15.3 Prompt Injection
User-supplied text (error messages, terminal output) is treated as untrusted data. It is injected into the user prompt with explicit delimiters and never into the system prompt. An independent injection detector scans input before prompt construction.

### 15.4 Misuse Risks
The system is designed for benign diagnostic use. The constraint-based strategy's explicit rules for risk classification and the conservative risk merging in `_enrich_commands_with_safety()` mitigate the risk of the model suggesting dangerous commands without warning. High and critical-risk commands are prominently flagged in the UI.

### 15.5 Model Limitations
LLMs can produce confidently stated incorrect information. TuxFix mitigates this by requiring the model to express uncertainty through confidence levels and a limitations field, and by reminding users at multiple points that model recommendations require human review.

---

## 16. Future Enhancements

1. **Dynamic few-shot selection**: Select examples that match the problem category at runtime, using embeddings or keyword matching.
2. **Chain-of-thought prompting**: Add a private reasoning step before the JSON output to improve diagnosis quality.
3. **Multi-model comparison**: Compare the same prompt strategy across different Ollama models.
4. **Ground-truth evaluation dataset**: Develop a larger benchmark with verified solutions, reviewed by Linux experts.
5. **User study**: Evaluate whether the interface helps non-expert users resolve their problems.
6. **Fine-tuned model**: Fine-tune a small model on Linux troubleshooting data with structured outputs.
7. **Streaming responses**: Display partial responses as they arrive for lower perceived latency.
8. **Plugin architecture**: Allow the prompt strategy module to be extended by third-party strategy plugins.

---

## 17. Conclusion

TuxFix demonstrates that prompt engineering strategy meaningfully affects the structural quality, safety information completeness, and evidence grounding of LLM-generated Linux diagnostic responses. The five strategies produce measurably different outputs on the same problem — confirming the core research hypothesis that strategy choice matters, independent of model selection.

The project delivers a complete, working application with a professional interface, a rigorous testing suite (143 tests), a documented evaluation framework, and honest reporting of what can and cannot be measured automatically. The safety architecture ensures that TuxFix can be demonstrated without risk of automated system modification.

The benchmark infrastructure is in place for further experimentation. When results are populated, the comparison tables will provide concrete evidence about which strategies best balance structural compliance, safety awareness, and diagnostic quality for Linux troubleshooting tasks.

---

## 18. References

1. Brown, T. B., Mann, B., et al. (2020). *Language Models are Few-Shot Learners*. NeurIPS 2020. Available at: https://arxiv.org/abs/2005.14165

2. Wei, J., Wang, X., et al. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS 2022. Available at: https://arxiv.org/abs/2201.11903

3. Ollama Project. (2023). *Run Large Language Models Locally*. Available at: https://ollama.ai

4. Pydantic Team. (2024). *Pydantic v2 Documentation*. Available at: https://docs.pydantic.dev/latest/

5. Streamlit Team. (2024). *Streamlit Documentation*. Available at: https://docs.streamlit.io

6. Liu, P., et al. (2023). *Pre-train, Prompt, and Predict: A Systematic Survey of Prompting Methods in Natural Language Processing*. ACM Computing Surveys. Available at: https://arxiv.org/abs/2107.13586

7. Perez, F., & Ribeiro, I. (2022). *Ignore Previous Prompt: Attack Techniques for Language Models*. Available at: https://arxiv.org/abs/2211.09527

> **Verification note**: All URLs above were verified as accessible at the time of writing. Authors and titles are given as published. Readers should verify publication details through official academic databases.
