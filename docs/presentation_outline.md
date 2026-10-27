# TuxFix — Presentation Outline
**Slide-by-Slide Content | ~8–10 Minutes**

---

## Slide 1: Title

**Title:** TuxFix: A Prompt Engineering-Based Linux Troubleshooting Assistant

**Subtitle:** Investigating How Prompt Engineering Strategies Affect LLM Diagnostic Quality

**Presenter:** [Your Name]
**Course:** [Course Name]
**Date:** [Date]

**Speaker notes:**
> Good [morning/afternoon]. Today I'll present TuxFix — a system I built to investigate a specific research question about prompt engineering and its effect on LLM-generated Linux diagnostic output. This is not just a chatbot — it's a controlled experimental platform.

---

## Slide 2: Problem Statement & Motivation

**Title:** The Problem

**Content:**
- Linux errors are often cryptic: `error while loading shared libraries: libssl.so.1.1`
- Users must already understand the problem to search for it effectively
- LLMs can generate diagnostic advice — but output quality varies wildly
- The same model, same problem, different prompts → different quality

**Key observation:**
> A model might confidently suggest `rm -rf /var/lib/pgsql/data` without explaining this destroys all data — or it might carefully explain the risk. The difference is often in the prompt.

**Visual:** Side-by-side comparison of two responses to the same DNS problem — one generic, one evidence-grounded.

**Speaker notes:**
> The core motivation is this: LLMs are sensitive to how you ask. A vague prompt produces a vague answer. A carefully structured prompt with explicit constraints produces a more structured, safer answer. TuxFix makes this comparison systematic.

---

## Slide 3: Research Question & Objectives

**Title:** What Are We Investigating?

**Research Question:**
> "How do different prompt engineering strategies affect the quality and reliability of LLM-generated Linux troubleshooting recommendations?"

**Objectives:**
1. Implement 5 structurally distinct prompt strategies
2. Build a structured output schema with automated validation
3. Create a safety layer independent of model output
4. Design a benchmark dataset of 8 realistic scenarios
5. Develop an honest evaluation framework

**Speaker notes:**
> This is a prompt engineering study, not just a chatbot. The same underlying model is used for all strategies — the only variable is how we construct the prompt.

---

## Slide 4: Existing Limitations & Proposed Solution

**Title:** Why Existing Solutions Fall Short

**Existing tools:**
| Tool | Gap |
|------|-----|
| man pages, web search | Require pre-diagnosis; return docs, not reasoning |
| Generic chatbots | Unstructured output, no risk classification, cloud-dependent |
| LLM wrappers | Single prompt strategy, no comparison, no safety eval |

**TuxFix adds:**
- ✅ Structured validated output (Pydantic schema)
- ✅ 5 prompt strategies, side-by-side comparison
- ✅ Independent command risk classification
- ✅ Local inference (no API key, no data leaves your machine)
- ✅ Demo mode for offline presentation

**Speaker notes:**
> Every feature in TuxFix exists to address a specific gap. The safety layer is particularly important — we classify command risk using our own rule-based system, not by trusting the model.

---

## Slide 5: System Architecture

**Title:** Architecture

**Diagram:**
```
┌────────────────────────────────────┐
│         Streamlit UI (6 tabs)       │
└──────────────┬─────────────────────┘
               │
┌──────────────▼─────────────────────┐
│     Diagnostics Orchestrator        │
│  scan → prompt → LLM → parse → safe │
└──────┬──────┬─────────┬────────────┘
       │      │         │
  Prompts  LLM Client  Schemas
  (5 strat) (Ollama/  (Pydantic
             Demo)      v2)
       │      │         │
┌──────▼──────▼─────────▼────────────┐
│    Safety Module + Evaluation       │
│  classify_command() | metrics       │
└────────────────────────────────────┘
```

**Key points:**
- Modular: UI, prompting, LLM, safety are independent layers
- Safety runs independently of model output
- User input is never trusted as instructions

**Speaker notes:**
> The architecture has a clean separation of concerns. The safety module doesn't trust the model's risk classifications — it re-classifies every command using its own regex rules and upgrades the risk level if the model under-reported it.

---

## Slide 6: The Five Prompt Engineering Strategies

**Title:** Five Distinct Strategies

| # | Strategy | Key Technique |
|---|----------|--------------|
| 1 | Zero-Shot | Task description + schema only |
| 2 | Role-Based | Expert persona + evidence requirements |
| 3 | Few-Shot | 2 worked examples before the problem |
| 4 | Constraint-Based | 7 numbered explicit rules |
| 5 | Iterative Refinement | Multi-turn with new evidence |

**Prompt Lab tab**: Users can inspect the exact assembled prompt for any strategy.

**Visual:** Show a snippet of the Constraint-Based prompt's rules section:
```
1. EVIDENCE RULE: Every root cause MUST reference specific text...
2. ORDERING RULE: Steps must be ordered least-invasive to most-invasive...
3. RISK RULE: Every command must have risk_level set...
```

**Speaker notes:**
> These are not just label changes — each strategy produces a structurally different prompt. Zero-shot is minimal; constraint-based has 7 explicit numbered rules. The prompt lab lets you see exactly what is sent to the model.

---

## Slide 7: Application Demo

**Title:** TuxFix in Action

**Demo flow (live or screenshots):**

1. **Input**: Enter a DNS resolution error (`ping: google.com: Temporary failure in name resolution`)
2. **Strategy**: Select Constraint-Based
3. **Inspect**: Show the assembled prompt in the Prompt Lab tab
4. **Output**: Show the structured diagnostic report
   - Root causes with confidence levels
   - Ordered diagnostic commands with risk badges
   - Safety disclaimer visible
5. **Compare**: Show the Strategy Comparison dashboard with metrics table

**Screenshot captions:**
- "Risk classification: 🟢 Read-only commands first"
- "Evidence-grounded root cause: cited from input text"
- "Safety disclaimer always visible"

**Speaker notes:**
> Notice that all commands show a risk badge. Green means read-only — safe to run. The orange and red commands modify system state and require careful review. TuxFix never runs any of these automatically.

---

## Slide 8: Benchmark Design & Evaluation Metrics

**Title:** How We Evaluate

**Benchmark:** 8 documented Linux scenarios
- DNS failure, package repo error, service won't start, USB not detected,
  permission denied, disk full, missing library, no network connectivity

**Three evaluation layers:**

| Layer | Type | Example Metric |
|-------|------|---------------|
| Structural | Automated, objective | Schema valid? Field completeness? |
| Safety | Rule-based | Risk flags accurate? Disclaimer present? |
| Quality | Heuristic only | Evidence linking, step ordering |

**Key honesty principle:**
> "Valid JSON ≠ correct diagnosis. Heuristic scores are labelled heuristic throughout."

**Speaker notes:**
> We're very careful about what we claim. Structural metrics are objective. Quality metrics are heuristics — they measure structural proxies for quality, not whether the diagnosis is actually right. Correctness requires human review.

---

## Slide 9: Results

**Title:** Experimental Results

> **Note to presenter**: Run the benchmark before the presentation and insert actual results here. The tables below are templates.

**Structural metrics table** (populate from benchmark export):
| Strategy | Valid JSON | Field Completeness | Avg Latency |
|----------|-----------|-------------------|-------------|
| Zero-Shot | | | |
| Role-Based | | | |
| Few-Shot | | | |
| Constraint-Based | | | |
| Iterative Refinement | | | |

**Key observations** (fill after running):
- Which strategy achieved highest schema validity?
- Which strategy had the best evidence linking?
- Which strategy was fastest / slowest?
- Any strategy that consistently failed to produce valid JSON?

**Speaker notes:**
> These results come from running all five strategies on all eight benchmark cases using [model name]. Remember that the quality scores are heuristics — they tell us about structure, not correctness.

---

## Slide 10: Limitations, Future Work & Conclusion

**Title:** Limitations & What's Next

**Limitations:**
- Single model (codegemma:2b) — results may not generalise
- 8 benchmark cases — too small for statistical conclusions
- Heuristic quality ≠ diagnostic correctness
- No user study conducted

**Future enhancements:**
- Dynamic few-shot example selection (embeddings-based)
- Multi-model comparison
- Ground-truth benchmark with expert review
- Fine-tuning on Linux troubleshooting data
- User study with novice Linux users

**Conclusion:**
> TuxFix shows that prompt engineering strategy measurably affects the structural quality, safety information, and evidence grounding of LLM diagnostic output — even with the same model. The system provides a complete, testable platform for further prompt engineering research.

**Final message:**
> "Ask better questions → get better diagnoses."

**Speaker notes:**
> To summarise: TuxFix is a complete, working system with 143 passing tests, a documented evaluation framework, and honest reporting. It demonstrates that how you ask matters — and gives us the infrastructure to measure exactly how much.

---

## Appendix Slides (if time allows)

### A: Test Results
- 143 tests, 0 failures
- Test categories: schemas, prompts, safety, llm_client, diagnostics, evaluation, benchmark, demo, config

### B: Safety Architecture Detail
- `classify_command()` regex rules
- `detect_prompt_injection()` patterns
- Conservative risk merging (never downgrade)

### C: JSON Schema Structure
Show the `DiagnosticReport` Pydantic schema fields and their types

### D: Demo Mode Architecture
Explain how DemoProvider works and why it's important for offline presentation
