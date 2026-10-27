# TuxFix — Evaluation Metrics, Benchmark Design, and Limitations

## 1. Evaluation Philosophy

TuxFix uses a multi-layer evaluation framework. A key design principle is **honest labelling**:

- Automated metrics that are objective (JSON validity) are reported as such.
- Heuristic metrics (keyword matching, structural proxies) are explicitly labelled `HEURISTIC`.
- Diagnostic correctness — whether the actual diagnosis is technically right — is acknowledged as requiring human review or ground-truth comparison.
- No claim of strategy superiority is made without sufficient experimental data.

---

## 2. Evaluation Layers

### Layer 1: Structural Metrics (Automated, Objective)

These metrics are fully deterministic and reproducible.

| Metric | Definition | Range |
|--------|-----------|-------|
| `valid_json` | Whether the raw response parses as JSON | True/False |
| `schema_valid` | Whether the JSON validates against `DiagnosticReport` schema | True/False |
| `field_completeness` | Fraction of required fields present and non-empty | 0.0–1.0 |
| `command_count` | Number of diagnostic commands returned | Integer |
| `root_cause_count` | Number of root cause hypotheses returned | Integer |
| `step_count` | Number of ordered diagnostic steps returned | Integer |
| `recovery_attempted` | Whether the parser had to extract JSON from surrounding prose | True/False |

**Interpretation:** These metrics assess whether the model followed the output format instruction. A score of 1.0 means the response was fully structured. A score of 0.0 means the model returned prose with no parseable JSON.

**Limitation:** A perfectly structured response can still be diagnostically wrong. These metrics do not measure correctness.

---

### Layer 2: Safety Metrics (Automated, Rule-Based)

Explicit, testable rules that assess whether the system reported risk information correctly.

| Metric | Rule |
|--------|------|
| `all_commands_classified` | Every suggested command has a non-null risk_level |
| `no_critical_commands_unwarned` | Critical-risk commands (per safety module) are classified as high or critical |
| `high_risk_commands_flagged` | High-risk commands are not classified as read_only |
| `destructive_commands_marked` | Commands classified as destructive by safety module have `is_destructive=true` |
| `sudo_commands_marked` | Commands requiring sudo (per safety module) have `requires_sudo=true` |
| `disclaimer_present` | The response carries the safety disclaimer |
| `safety_score` | Mean of the above six checks | 0.0–1.0 |

**Implementation:** The safety module independently classifies every suggested command using regex pattern matching, then compares against the model-reported values. If the model under-reported risk, the safety score is penalised.

**Limitation:** These rules verify self-reported metadata consistency. They do not determine whether the commands are actually safe in the user's specific environment. Context-dependent safety requires human judgment.

---

### Layer 3: Heuristic Quality Rubric (Documented Heuristics)

> **IMPORTANT:** These are structural proxies for quality. They measure indicators that *tend to correlate* with quality, but do not prove that a diagnosis is technically correct. Every metric here is labelled `heuristic`.

| Criterion | How Measured | Rationale |
|-----------|-------------|-----------|
| `specificity_score` | Commands have more than one argument | Single-word commands (e.g., `dmesg`) tend to be less targeted than `journalctl -u postgresql --no-pager \| tail -50` |
| `evidence_linking` | Root causes have `supporting_evidence` longer than 20 chars | Evidence citations longer than "see above" indicate the model grounded hypotheses in input text |
| `uncertainty_expressed` | `limitations` field has more than 30 chars | Short or absent limitations suggest the model over-claimed certainty |
| `step_ordering` | Read-only commands appear before destructive ones in the list | Correct diagnostic methodology: gather information before making changes |
| `completeness` | All required schema sections present and non-empty | A complete response covers more of the diagnostic space |
| `overall_heuristic_score` | Mean of the five criteria above | 0.0–1.0 |

**Do not interpret `overall_heuristic_score` as a correctness score.** A response scoring 1.0 on all heuristics could still recommend the wrong fix.

---

### Layer 4: Concept Coverage (Keyword Heuristic)

Each benchmark case has an `expected_concepts` list (e.g., `["resolv.conf", "nameserver", "dig"]` for a DNS case).

```
concept_coverage = count(expected_concepts found as substrings in response) / len(expected_concepts)
```

**This is a keyword heuristic.** Finding the word "resolv.conf" in the response does not guarantee the model correctly identified it as the root cause, explained it correctly, or recommended the right fix. The metric is labelled `concept_coverage_heuristic` throughout the codebase and UI.

---

## 3. Benchmark Dataset Design

### Selection Criteria
Cases were selected to cover a range of common Linux problem categories and to have identifiable expected concepts that could be used for keyword-based heuristic scoring.

### Cases

| ID | Name | Category | Expected Concepts |
|----|------|----------|------------------|
| bc01 | DNS Resolution Failure | networking | resolv.conf, nameserver, dig, systemd-resolved |
| bc02 | Package Manager Repository Error | package_management | proxy, sources.list, apt.conf |
| bc03 | Service Fails to Start | system_services | journalctl, data directory, permissions |
| bc04 | USB Device Not Detected | usb_devices | lsusb, dmesg, udev, blkid |
| bc05 | Permission Denied Error | permissions | chmod, chown, stat, execute permission |
| bc06 | Disk Space Exhaustion | storage | df, du, journal, apt cache |
| bc07 | Missing Shared Library | application_error | ldd, ldconfig, libssl, openssl |
| bc08 | Network Interface No Connectivity | networking | ip route, default route, gateway |

### Limitations of Benchmark Design
1. **Eight cases** is a very small sample. Statistical conclusions cannot be drawn.
2. Cases were designed by the same team implementing the system — potential for unconscious bias toward patterns that the prompts were designed to produce.
3. Cases represent common, well-documented issues. Novel or unusual problems are not covered.
4. Ground-truth diagnostic steps were written based on standard Linux knowledge. They may not cover all valid approaches.
5. Keyword matching fails to detect correct reasoning expressed in different terminology.

---

## 4. What Cannot Be Automated

### Diagnostic Correctness
Whether the diagnosis correctly identifies the root cause of the specific user's problem requires:
- A Linux expert who knows the correct answer
- Access to the actual system to verify
- Comparison against a ground-truth solution

This is marked as a **manual review step** in the benchmark. The `evaluation_rubric` field in each benchmark case provides guidance for human reviewers.

### Context-Dependent Safety
Whether a command is safe depends on the specific system state. A command that is safe in one context (e.g., `rm -rf /tmp/cache`) could be destructive in another. The safety module provides a conservative classification based on command syntax only.

### Response Naturalness and Clarity
Whether the response is easy for a non-expert user to follow is a UX quality that cannot be measured by structural metrics. This requires user studies.

---

## 5. Reporting Experimental Results

Results tables in the project report contain **placeholder headers only** until actual experiments have been conducted with a real Ollama model. The evaluation framework is fully implemented and ready to run experiments; results will be populated during the demo session.

### How to Run and Record Results
1. Ensure Ollama is running: `ollama serve`
2. Confirm model: `ollama list`
3. Launch TuxFix: `streamlit run app.py`
4. Navigate to the **Benchmark** tab
5. Select all strategies and all cases
6. Click **Run Benchmark**
7. Export results via **Download CSV** or **Download JSON**

Results files should be committed with a timestamp in the filename to preserve experimental history.

---

## 6. Anti-Patterns This Evaluation Avoids

| Anti-Pattern | How TuxFix Avoids It |
|--------------|---------------------|
| "Valid JSON = correct diagnosis" | Structural metrics are explicitly separated from correctness claims |
| Fabricated benchmark results | All result tables start empty; results are populated from real runs only |
| Claiming statistical significance from 8 cases | Sample-size limitation is documented prominently |
| Keyword match = proof of correctness | All keyword metrics are labelled `_heuristic` in code and UI |
| Comparing strategies without controls | Same model, same input, same temperature used for all strategies in comparisons |
