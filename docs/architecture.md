# TuxFix — Architecture and Data Flow

## Overview

TuxFix is a modular, layered application. Each layer has a single responsibility and communicates through well-defined interfaces. The design makes it straightforward to swap the LLM provider, add new prompt strategies, or extend the evaluation framework.

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                  │
│  Troubleshoot │ Iterative │ Prompt Lab │ Compare │ Bench  │
└────────────────────────┬────────────────────────────────-┘
                         │ TroubleshootingInput
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Diagnostics Orchestrator                     │
│              (src/tuxfix/diagnostics.py)                  │
│  1. Safety scan (injection detection)                     │
│  2. Build prompt (strategy selection)                     │
│  3. Call LLM provider                                     │
│  4. Parse & validate response                             │
│  5. Enrich commands with safety classification            │
└──────┬──────────────┬────────────────┬───────────────────┘
       │              │                │
       ▼              ▼                ▼
┌──────────┐  ┌─────────────┐  ┌──────────────┐
│  Prompts │  │  LLM Client │  │   Schemas    │
│ (5 strat)│  │  (Ollama /  │  │  (Pydantic)  │
│          │  │   Demo)     │  │              │
└──────────┘  └─────────────┘  └──────────────┘
       │              │                │
       ▼              ▼                ▼
┌─────────────────────────────────────────────────────────┐
│              Safety Module (safety.py)                    │
│  Command risk classification │ Injection detection        │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│         Evaluation & Benchmark (evaluation.py,           │
│                               benchmark.py)              │
│  Structural │ Safety │ Heuristic Quality │ Export         │
└─────────────────────────────────────────────────────────┘
```

---

## Module Responsibilities

### `app.py`
Streamlit application entry point. Renders six tabs:
1. **Troubleshoot** — single-strategy diagnosis
2. **Iterative Refinement** — multi-turn evidence-based refinement
3. **Prompt Lab** — inspect assembled prompts for all strategies
4. **Compare Strategies** — run all strategies on the same input, display metrics
5. **Benchmark** — run the documented benchmark dataset
6. **Evaluation** — methodology and rubric documentation

The UI never executes commands, never stores raw diagnostic logs by default, and never exposes environment variables.

### `src/tuxfix/config.py`
Reads configuration from environment variables (with `.env` file support via `python-dotenv`). Provides a `TuxFixConfig` dataclass and `get_config()` / `load_config()` factory functions. The `as_display_dict()` method returns a safe dict for UI display — no credentials exposed.

### `src/tuxfix/schemas.py`
Pydantic v2 models for all structured data:
- `TroubleshootingInput` — validated user input with length checks
- `DiagnosticReport` — the full structured diagnosis
- `DiagnosticCommand` — individual command with risk metadata
- `RootCause`, `RemediationStep` — typed sub-components
- `ParseResult` — result of attempting to validate a model response
- `parse_model_response()` — robust parser with two-stage recovery (direct JSON → JSON extraction from prose)

### `src/tuxfix/llm_client.py`
Provider abstraction:
- `BaseLLMProvider` — abstract interface (`generate`, `is_available`, `list_models`)
- `OllamaProvider` — calls the local Ollama REST API; surfaces all errors as `LLMError` with human-readable messages
- `DemoProvider` — returns clearly labelled pre-written responses; never claims to be a real LLM
- `get_provider(config)` — factory that selects Demo or Ollama based on config

### `src/tuxfix/prompts.py`
Five genuinely distinct prompt strategy implementations:

| Strategy | Key Differentiator |
|----------|-------------------|
| Zero-Shot | Minimal framing — task description only |
| Role-Based | Explicit senior Linux engineer persona + context structure |
| Few-Shot | Two worked examples embedded before the problem |
| Constraint-Based | Explicit numbered rules — evidence, ordering, risk, uncertainty |
| Iterative Refinement | Previous diagnosis + new evidence; asks for change explanation |

All strategies share the same output JSON schema definition. Trusted system instructions are kept separate from untrusted user-supplied content.

### `src/tuxfix/safety.py`
- `classify_command(cmd)` — regex-based risk classification (read_only / low / medium / high / critical)
- `detect_prompt_injection(text)` — scans user input for injection patterns
- `sanitize_for_export(data)` — redacts credential-looking values from exported data
- `SAFETY_DISCLAIMER` — visible advisory notice shown in every diagnosis

### `src/tuxfix/diagnostics.py`
Orchestrates the full diagnosis pipeline. `run_diagnosis()` and `run_comparison()` coordinate the other modules. After parsing, `_enrich_commands_with_safety()` re-classifies commands using the safety module, upgrading risk levels if the model under-reported them (conservative — never downgrades).

### `src/tuxfix/evaluation.py`
Three evaluation layers:
1. **StructuralMetrics** — automated, objective (JSON validity, field completeness)
2. **SafetyMetrics** — explicit rule-based (risk flags, destructive markers, disclaimer)
3. **QualityRubric** — documented heuristics only; labelled `HEURISTIC` throughout

### `src/tuxfix/benchmark.py`
Loads `data/benchmark_cases.json`, runs strategies, records `BenchmarkResult` records, exports to CSV/JSON. Includes concept-coverage heuristic (keyword matching — explicitly labelled as not proof of correctness).

### `src/tuxfix/demo.py`
Pre-written diagnostic responses for offline use. Every response includes `DEMO_NOTICE` in the `limitations` field. Selects the most relevant pre-written response by keyword matching the prompt.

---

## Data Flow: Single Diagnosis

```
User Input (UI form)
       │
       ▼  validate
TroubleshootingInput (Pydantic)
       │
       ▼  detect_prompt_injection()
[Injection warnings if any]
       │
       ▼  build_prompt(strategy, input)
(system_prompt, user_prompt)
       │
       ▼  provider.generate(user_prompt, system_prompt)
raw_text  ←── Ollama API or DemoProvider
       │
       ▼  parse_model_response(raw_text)
ParseResult
  ├── success=True  → DiagnosticReport
  │        │
  │        ▼  _enrich_commands_with_safety()
  │   DiagnosticReport (risk levels confirmed/upgraded)
  │
  └── success=False → error_message + raw_text for display
       │
       ▼
DiagnosisResult (strategy, parse_result, llm_response,
                 assembled_prompt, injection_warnings,
                 total_time_seconds)
       │
       ▼  evaluate_result()
EvaluationRecord (structural + safety + quality metrics)
```

---

## Security Architecture

- **No command execution**: The application never calls `subprocess`, `os.system`, or any shell execution. Commands are display-only.
- **Input separation**: User-supplied text is injected into prompts with clear delimiters (`[ERROR OUTPUT START]` / `[END]`), not interpolated into system instructions.
- **Injection scanning**: Every diagnosis run scans the input for prompt injection patterns before building the prompt.
- **Risk classification**: Every suggested command is independently classified by the safety module, regardless of what the model reported.
- **Export sanitisation**: Exported data is scanned for credential-looking values before download.

---

## Extension Points

- **New LLM provider**: Implement `BaseLLMProvider` in `llm_client.py`.
- **New prompt strategy**: Add to `PromptStrategy` enum, implement builder function, register in `build_prompt()` dispatcher in `prompts.py`.
- **New evaluation metric**: Add to `EvaluationRecord` and `to_dict()` in `evaluation.py`.
- **New benchmark case**: Add entry to `data/benchmark_cases.json`.
