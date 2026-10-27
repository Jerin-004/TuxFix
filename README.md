# 🐧 TuxFix — Prompt Engineering-Based Linux Troubleshooting Assistant

> **Academic Course Project** | Prompt Engineering Research | Python 3.11+ | Streamlit | Ollama

TuxFix is an interactive Linux troubleshooting assistant that demonstrates how different **prompt engineering strategies** affect the quality and reliability of LLM-generated diagnostic recommendations. It runs entirely locally using [Ollama](https://ollama.ai) and requires no paid API.

---

## Research Question

> "How do different prompt engineering strategies affect the quality and reliability of LLM-generated Linux troubleshooting recommendations?"

---

## Features

- **Five prompt engineering strategies**: Zero-Shot, Role-Based, Few-Shot, Constraint-Based, Iterative Refinement
- **Structured diagnostic reports**: Validated JSON output with root causes, ordered steps, risk-classified commands
- **Prompt Laboratory**: Inspect the assembled prompt for any strategy before submitting
- **Strategy Comparison Dashboard**: Run the same problem through multiple strategies and compare metrics
- **Benchmark Evaluation**: Eight documented Linux scenarios with automated and heuristic metrics
- **Safety layer**: Commands are risk-classified independently of model output; never auto-executed
- **Demo mode**: Fully functional offline with pre-written sample responses
- **Export**: Download results as CSV or JSON for further analysis

---

## Architecture

```
app.py (Streamlit UI)
└── src/tuxfix/
    ├── config.py        — Configuration and environment variables
    ├── schemas.py       — Pydantic models for input and output
    ├── llm_client.py    — Ollama provider + Demo provider
    ├── prompts.py       — 5 prompt strategy implementations
    ├── diagnostics.py   — Orchestration pipeline
    ├── safety.py        — Command risk classification + injection detection
    ├── evaluation.py    — Metrics: structural, safety, heuristic quality
    ├── benchmark.py     — Benchmark runner and export
    └── demo.py          — Pre-written demo responses
data/
└── benchmark_cases.json — 8 documented Linux troubleshooting scenarios
tests/                   — 143 unit tests (all pass)
docs/                    — Architecture, strategies, evaluation, project report
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | Tested on 3.13 (Anaconda) |
| [Ollama](https://ollama.ai) | Local LLM inference server |
| A pulled Ollama model | e.g. `ollama pull codegemma:2b` |

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd TuxFix
```

### 2. Install Ollama

Follow the instructions at https://ollama.ai for your operating system.

On Linux (quick install):
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 3. Pull a model

Check available models and pull one:
```bash
ollama list          # list installed models
ollama pull codegemma:2b   # ~1.5 GB — used during development
# or
ollama pull llama3.2       # larger, potentially higher quality
ollama pull mistral        # good general-purpose model
```

> **Tip**: Any model listed by `ollama list` can be used. Update `OLLAMA_MODEL` in `.env` to match.

### 4. Create and activate a virtual environment

#### Option A: venv (standard)
```bash
python3 -m venv venv
source venv/bin/activate      # Linux / macOS
```

#### Option B: Anaconda (used during development)
```bash
conda create -n tuxfix python=3.13
conda activate tuxfix
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

Key variables in `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434   # Ollama server URL
OLLAMA_MODEL=codegemma:2b               # Model to use (must be pulled)
OLLAMA_TIMEOUT=120                      # Request timeout in seconds
TUXFIX_DEMO_MODE=false                  # true = offline demo mode
```

---

## Running the Application

### Start Ollama (if not already running)

```bash
ollama serve
```

### Launch TuxFix

```bash
streamlit run app.py
```

The application opens at `http://localhost:8501`.

### Demo mode (no Ollama required)

```bash
TUXFIX_DEMO_MODE=true streamlit run app.py
```

Or toggle **Demo Mode** in the sidebar after launching. Demo mode uses pre-written sample responses and clearly labels them as non-LLM output.

---

## Running Tests

```bash
# All 143 tests — no Ollama required (all LLM calls are mocked)
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --tb=short

# Single module
python -m pytest tests/test_prompts.py -v
```

Expected output: **143 passed** in under 1 second.

---

## Running the Benchmark

### Via the UI

1. Launch `streamlit run app.py`
2. Navigate to the **Benchmark** tab
3. Select strategies and cases
4. Click **Run Benchmark**
5. Export results via **Download CSV** or **Download JSON**

### Via Python (headless)

```python
from src.tuxfix.benchmark import load_benchmark_cases, run_benchmark, export_benchmark_csv
from src.tuxfix.prompts import PromptStrategy
from pathlib import Path

cases = load_benchmark_cases()
results = run_benchmark(
    strategies=[PromptStrategy.ZERO_SHOT, PromptStrategy.CONSTRAINT_BASED],
    cases=cases,
)
export_benchmark_csv(results, Path("data/results/benchmark_results.csv"))
```

---

## Reproducing Experiments

For reproducible results:

1. Document your model: `ollama list` — note the exact model name and version
2. Use the same `.env` settings (especially temperature is hardcoded to 0.2 in `llm_client.py`)
3. Run the benchmark and export to a timestamped file
4. Commit the results file alongside the model name for traceability

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| `Cannot connect to Ollama` | Run `ollama serve` in a terminal |
| `model not found` | Run `ollama pull <model-name>` |
| `Request timed out` | Increase `OLLAMA_TIMEOUT` in `.env` or use a smaller model |
| `Schema validation failed` | The model returned malformed JSON — try a larger model or constraint-based strategy |
| Streamlit `ModuleNotFoundError` | Activate your venv/conda env before running |
| `No module named 'tuxfix'` | Run `streamlit run app.py` from the project root |
| Tests fail with import errors | Run `python -m pytest` from the project root, not from inside `tests/` |

---

## Safety Warnings

- TuxFix **never executes commands automatically**. All suggestions are for manual review only.
- Commands are risk-classified (read_only / low / medium / high / critical). Review the risk level before running any command.
- High and critical-risk commands require independent expert judgment — do not run them based on TuxFix output alone.
- LLM-generated diagnoses can be incorrect. Always verify before applying fixes to production systems.
- Do not paste passwords, API tokens, or private keys into the input fields.

---

## Project Limitations

- Diagnostic correctness is not automatically measurable — see `docs/evaluation.md`
- Heuristic quality scores are structural proxies, not correctness scores
- Benchmark has 8 cases — insufficient for statistical conclusions
- Results depend heavily on the model used; codegemma:2b is a small model
- No user study has been conducted

---

## Documentation

| File | Contents |
|------|---------|
| `docs/architecture.md` | System architecture and data flow |
| `docs/prompt_strategies.md` | Prompt engineering methodology |
| `docs/evaluation.md` | Metrics, benchmark design, limitations |
| `docs/project_report.md` | Full academic project report |
| `docs/presentation_outline.md` | Slide-by-slide presentation content |
| `presentation/TuxFix_Prompt_Engineering_Project.pptx` | PowerPoint presentation |

---

## Project Structure

```
TuxFix/
├── app.py                          # Streamlit application entry point
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── src/
│   └── tuxfix/
│       ├── __init__.py
│       ├── config.py
│       ├── schemas.py
│       ├── llm_client.py
│       ├── prompts.py
│       ├── diagnostics.py
│       ├── safety.py
│       ├── evaluation.py
│       ├── benchmark.py
│       └── demo.py
├── data/
│   └── benchmark_cases.json
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_schemas.py
│   ├── test_prompts.py
│   ├── test_llm_client.py
│   ├── test_safety.py
│   ├── test_diagnostics.py
│   ├── test_evaluation.py
│   ├── test_benchmark.py
│   └── test_demo.py
├── docs/
│   ├── architecture.md
│   ├── prompt_strategies.md
│   ├── evaluation.md
│   ├── project_report.md
│   └── presentation_outline.md
└── presentation/
    └── TuxFix_Prompt_Engineering_Project.pptx
```

---

## License

Academic use only. Not intended for production deployment without further safety review.
