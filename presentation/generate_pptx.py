"""
Generate TuxFix presentation PPTX using python-pptx.
Run: python presentation/generate_pptx.py
Output: presentation/TuxFix_Prompt_Engineering_Project.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt, Emu
except ImportError:
    print("ERROR: python-pptx not installed. Run: pip install python-pptx")
    sys.exit(1)

OUTPUT_PATH = Path(__file__).parent / "TuxFix_Prompt_Engineering_Project.pptx"

# ── Colour palette ─────────────────────────────────────────────────────────────
C_DARK_BG     = RGBColor(0x1E, 0x1E, 0x2E)   # dark navy
C_ACCENT      = RGBColor(0x89, 0xDC, 0xEB)   # teal/cyan
C_HEADING     = RGBColor(0xCD, 0xD6, 0xF4)   # light lavender
C_BODY        = RGBColor(0xCC, 0xC0, 0xB4)   # warm white
C_GREEN       = RGBColor(0xA6, 0xE3, 0xA1)   # success green
C_RED         = RGBColor(0xF3, 0x8B, 0xA8)   # alert red
C_YELLOW      = RGBColor(0xF9, 0xE2, 0xAF)   # warning yellow
C_WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
C_SUBTEXT     = RGBColor(0xA6, 0xAD, 0xC8)   # muted

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)


def _set_bg(slide, color: RGBColor):
    from pptx.oxml.ns import qn
    from lxml import etree
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_textbox(slide, left, top, width, height,
                 text, font_size=18, bold=False, color=None,
                 align=PP_ALIGN.LEFT, italic=False):
    from pptx.util import Pt
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color or C_BODY
    return txBox


def _add_bullet_box(slide, left, top, width, height,
                    bullets: list[tuple[str, int, RGBColor]],
                    font_size=16):
    """bullets: list of (text, indent_level, color)"""
    from pptx.util import Pt
    from pptx.oxml.ns import qn
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, (text, level, color) in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.level = level
        run = p.add_run()
        run.text = text
        run.font.size = Pt(font_size)
        run.font.color.rgb = color


def _add_divider(slide, y, color=None):
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    line = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.LINE is not directly available; use connector
        Inches(0.3), y, Inches(12.7), Inches(0.01)
    )
    line.fill.background()
    line.line.color.rgb = color or C_ACCENT
    line.line.width = Pt(1)
    return line


# ── Slide builders ─────────────────────────────────────────────────────────────

def slide_title(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _set_bg(slide, C_DARK_BG)

    # Penguin emoji title
    _add_textbox(slide, Inches(1), Inches(1.5), Inches(11), Inches(1.2),
                 "🐧 TuxFix", font_size=48, bold=True, color=C_ACCENT,
                 align=PP_ALIGN.CENTER)

    _add_textbox(slide, Inches(1), Inches(2.9), Inches(11), Inches(0.8),
                 "A Prompt Engineering-Based Linux Troubleshooting Assistant",
                 font_size=24, bold=False, color=C_HEADING, align=PP_ALIGN.CENTER)

    _add_textbox(slide, Inches(1), Inches(3.8), Inches(11), Inches(0.6),
                 "Investigating How Prompt Engineering Strategies Affect LLM Diagnostic Quality",
                 font_size=16, italic=True, color=C_SUBTEXT, align=PP_ALIGN.CENTER)

    _add_textbox(slide, Inches(1), Inches(5.5), Inches(11), Inches(0.5),
                 "Python 3.13 · Streamlit · Ollama · Pydantic v2 · 143 Tests Passing",
                 font_size=13, color=C_SUBTEXT, align=PP_ALIGN.CENTER)
    return slide


def slide_problem(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "The Problem", font_size=32, bold=True, color=C_ACCENT)

    bullets = [
        ("Linux errors are often cryptic and context-dependent", 0, C_BODY),
        ('  e.g.  "error while loading shared libraries: libssl.so.1.1"', 1, C_YELLOW),
        ("Users must already understand the problem to search effectively", 0, C_BODY),
        ("LLMs can generate diagnostic advice — but quality varies wildly", 0, C_BODY),
        ("", 0, C_BODY),
        ("The same model + same problem + different prompt → different quality:", 0, C_HEADING),
        ("  → Vague prompt: generic advice, no evidence, wrong risk levels", 1, C_RED),
        ("  → Structured prompt: evidence-grounded, ordered steps, risk-classified", 1, C_GREEN),
        ("", 0, C_BODY),
        ("Core insight: HOW you ask matters as much as WHAT you ask", 0, C_ACCENT),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(1.2), Inches(12.3), Inches(5.5),
                    bullets, font_size=17)
    return slide


def slide_objectives(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "Research Question & Objectives", font_size=32, bold=True, color=C_ACCENT)

    _add_textbox(slide, Inches(0.5), Inches(1.1), Inches(12.3), Inches(0.7),
                 '"How do different prompt engineering strategies affect the quality and',
                 font_size=18, italic=True, color=C_HEADING)
    _add_textbox(slide, Inches(0.5), Inches(1.65), Inches(12.3), Inches(0.7),
                 'reliability of LLM-generated Linux troubleshooting recommendations?"',
                 font_size=18, italic=True, color=C_HEADING)

    bullets = [
        ("Objectives:", 0, C_ACCENT),
        ("1.  Implement 5 structurally distinct prompt engineering strategies", 1, C_BODY),
        ("2.  Build a structured output schema with automated Pydantic validation", 1, C_BODY),
        ("3.  Create a safety layer that classifies command risk independently of model output", 1, C_BODY),
        ("4.  Design a benchmark dataset of 8 realistic Linux scenarios", 1, C_BODY),
        ("5.  Develop an honest evaluation framework (no fabricated results)", 1, C_BODY),
        ("6.  Build a professional Streamlit UI with 6 feature tabs", 1, C_BODY),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(2.5), Inches(12.3), Inches(4.2),
                    bullets, font_size=17)
    return slide


def slide_limitations_solution(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "Existing Limitations → Proposed Solution", font_size=30, bold=True, color=C_ACCENT)

    # Left column - existing
    _add_textbox(slide, Inches(0.5), Inches(1.1), Inches(5.8), Inches(0.5),
                 "Existing Tools Fall Short", font_size=18, bold=True, color=C_RED)
    existing = [
        ("man pages / web search", 0, C_BODY),
        ("  → Returns docs, not diagnosis", 1, C_SUBTEXT),
        ("Generic LLM chatbots", 0, C_BODY),
        ("  → Unstructured, cloud-dependent, unsafe", 1, C_SUBTEXT),
        ("LLM wrappers", 0, C_BODY),
        ("  → Single strategy, no safety eval", 1, C_SUBTEXT),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(1.7), Inches(5.8), Inches(4.0),
                    existing, font_size=16)

    # Right column - TuxFix
    _add_textbox(slide, Inches(7.0), Inches(1.1), Inches(5.8), Inches(0.5),
                 "TuxFix Adds", font_size=18, bold=True, color=C_GREEN)
    solution = [
        ("✅  Validated JSON output (Pydantic schema)", 0, C_GREEN),
        ("✅  5 prompt strategies, side-by-side comparison", 0, C_GREEN),
        ("✅  Independent command risk classification", 0, C_GREEN),
        ("✅  Local inference (Ollama — no API key)", 0, C_GREEN),
        ("✅  Prompt injection detection", 0, C_GREEN),
        ("✅  Demo mode for offline presentation", 0, C_GREEN),
        ("✅  143 automated tests", 0, C_GREEN),
    ]
    _add_bullet_box(slide, Inches(7.0), Inches(1.7), Inches(5.8), Inches(4.5),
                    solution, font_size=16)
    return slide


def slide_architecture(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "System Architecture", font_size=32, bold=True, color=C_ACCENT)

    arch = (
        "Streamlit UI (6 tabs)\n"
        "  │\n"
        "  ▼  TroubleshootingInput (Pydantic)\n"
        "  │\n"
        "Diagnostics Orchestrator\n"
        "  scan → build prompt → LLM call → parse → safety enrich\n"
        "  │              │              │\n"
        "Prompts      LLM Client     Schemas\n"
        "(5 strategies)  (Ollama/Demo)  (Pydantic v2)\n"
        "  │              │              │\n"
        "Safety Module + Evaluation Framework\n"
        "  classify_command() │ structural │ safety │ heuristic quality"
    )
    _add_textbox(slide, Inches(0.5), Inches(1.2), Inches(12.3), Inches(4.0),
                 arch, font_size=14, color=C_BODY)

    bullets = [
        ("Key properties:", 0, C_ACCENT),
        ("  Safety module is independent of model output — never trusts model-reported risk alone", 1, C_YELLOW),
        ("  User error text injected with delimiters, never into system prompt", 1, C_YELLOW),
        ("  Zero command execution — display only", 1, C_GREEN),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(5.3), Inches(12.3), Inches(1.8),
                    bullets, font_size=15)
    return slide


def slide_strategies(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "Five Prompt Engineering Strategies", font_size=32, bold=True, color=C_ACCENT)

    strategies = [
        ("1. Zero-Shot", "Task description + output schema only. No examples, no constraints.",
         C_SUBTEXT),
        ("2. Role-Based", "Expert persona: 'senior Linux engineer with 15 years experience'. "
                          "Emphasises evidence vs hypothesis separation.", C_BODY),
        ("3. Few-Shot", "2 worked examples (DNS + service failure) before the actual problem. "
                        "Demonstrates format and reasoning depth.", C_HEADING),
        ("4. Constraint-Based", "7 numbered explicit rules: EVIDENCE RULE, ORDERING RULE, RISK RULE, "
                                 "DESTRUCTIVE RULE, UNCERTAINTY RULE, COMPLETENESS RULE, FORMAT RULE.", C_ACCENT),
        ("5. Iterative Refinement", "Multi-turn: initial diagnosis → new evidence → refined analysis. "
                                     "Updates confidence, removes answered questions.", C_GREEN),
    ]

    y = Inches(1.1)
    for name, desc, color in strategies:
        _add_textbox(slide, Inches(0.5), y, Inches(3.0), Inches(0.55),
                     name, font_size=15, bold=True, color=color)
        _add_textbox(slide, Inches(3.6), y, Inches(9.2), Inches(0.55),
                     desc, font_size=14, color=C_BODY)
        y += Inches(1.05)

    _add_textbox(slide, Inches(0.5), Inches(6.6), Inches(12.3), Inches(0.5),
                 "Every strategy produces a structurally different prompt — not just a label change. "
                 "Inspect in the Prompt Lab tab.",
                 font_size=13, italic=True, color=C_SUBTEXT)
    return slide


def slide_demo(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "Application Demo", font_size=32, bold=True, color=C_ACCENT)

    flow = [
        ("Demo flow:", 0, C_ACCENT),
        ("1.  Enter a DNS resolution error in the Troubleshoot tab", 1, C_BODY),
        ('    Error: "ping: google.com: Temporary failure in name resolution"', 2, C_YELLOW),
        ("2.  Select Constraint-Based strategy → inspect assembled prompt in Prompt Lab", 1, C_BODY),
        ("3.  Submit → receive structured diagnostic report:", 1, C_BODY),
        ("       🔴 Root cause: resolv.conf missing nameserver  [confidence: high]", 2, C_RED),
        ("       🟢 cat /etc/resolv.conf                        [read_only]", 2, C_GREEN),
        ("       🟢 systemctl status systemd-resolved           [read_only]", 2, C_GREEN),
        ("       🟠 sudo systemctl restart systemd-resolved     [medium risk]", 2, C_YELLOW),
        ("4.  Navigate to Compare Strategies → same problem, all 5 strategies, metrics table", 1, C_BODY),
        ("", 0, C_BODY),
        ("Safety: Every command shows risk badge. TuxFix NEVER executes commands.", 0, C_GREEN),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(1.1), Inches(12.3), Inches(5.8),
                    flow, font_size=15)
    return slide


def slide_benchmark(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "Benchmark Design & Evaluation Metrics", font_size=30, bold=True, color=C_ACCENT)

    # Benchmark cases
    _add_textbox(slide, Inches(0.5), Inches(1.1), Inches(5.8), Inches(0.5),
                 "8 Benchmark Scenarios", font_size=18, bold=True, color=C_HEADING)
    cases = [
        ("DNS Resolution Failure", 0, C_BODY),
        ("Package Manager Repo Error", 0, C_BODY),
        ("Service Fails to Start", 0, C_BODY),
        ("USB Device Not Detected", 0, C_BODY),
        ("Permission Denied Error", 0, C_BODY),
        ("Disk Space Exhaustion", 0, C_BODY),
        ("Missing Shared Library", 0, C_BODY),
        ("Network Interface No Connectivity", 0, C_BODY),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(1.7), Inches(5.5), Inches(4.5),
                    cases, font_size=14)

    # Evaluation layers
    _add_textbox(slide, Inches(7.0), Inches(1.1), Inches(5.8), Inches(0.5),
                 "3 Evaluation Layers", font_size=18, bold=True, color=C_HEADING)
    metrics = [
        ("Structural (objective):", 0, C_ACCENT),
        ("  JSON valid, schema valid, field completeness", 1, C_BODY),
        ("Safety (rule-based):", 0, C_ACCENT),
        ("  Risk flags accurate, disclaimer present", 1, C_BODY),
        ("Quality (HEURISTIC only):", 0, C_YELLOW),
        ("  Evidence linking, step ordering, specificity", 1, C_BODY),
        ("", 0, C_BODY),
        ("⚠  Valid JSON ≠ correct diagnosis", 0, C_RED),
        ("All heuristic scores labelled _heuristic", 0, C_YELLOW),
    ]
    _add_bullet_box(slide, Inches(7.0), Inches(1.7), Inches(5.8), Inches(4.5),
                    metrics, font_size=14)
    return slide


def slide_results(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "Experimental Results", font_size=32, bold=True, color=C_ACCENT)

    _add_textbox(slide, Inches(0.5), Inches(1.1), Inches(12.3), Inches(0.6),
                 "Run benchmark before presentation and insert actual results below.",
                 font_size=14, italic=True, color=C_YELLOW)

    # Table header
    headers = ["Strategy", "Valid JSON", "Field Completeness", "Safety Score", "Heuristic Quality", "Latency"]
    x_positions = [0.5, 2.8, 4.5, 7.0, 9.0, 11.2]
    y = Inches(1.8)
    for i, (hdr, x) in enumerate(zip(headers, x_positions)):
        _add_textbox(slide, Inches(x), y, Inches(1.9), Inches(0.4),
                     hdr, font_size=12, bold=True, color=C_ACCENT)

    rows = [
        "Zero-Shot", "Role-Based", "Few-Shot", "Constraint-Based", "Iterative Refinement"
    ]
    for j, row in enumerate(rows):
        y = Inches(2.3 + j * 0.6)
        _add_textbox(slide, Inches(0.5), y, Inches(2.2), Inches(0.5),
                     row, font_size=13, color=C_BODY)
        for k in range(1, len(x_positions)):
            _add_textbox(slide, Inches(x_positions[k]), y, Inches(1.8), Inches(0.5),
                         "—", font_size=13, color=C_SUBTEXT, align=PP_ALIGN.CENTER)

    _add_textbox(slide, Inches(0.5), Inches(5.7), Inches(12.3), Inches(0.6),
                 "Note: Tables will be populated from live benchmark export during demo.",
                 font_size=13, italic=True, color=C_SUBTEXT)
    return slide


def slide_conclusion(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_DARK_BG)
    _add_textbox(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
                 "Limitations, Future Work & Conclusion", font_size=28, bold=True, color=C_ACCENT)

    # Limitations
    _add_textbox(slide, Inches(0.5), Inches(1.1), Inches(5.8), Inches(0.5),
                 "Limitations", font_size=18, bold=True, color=C_RED)
    limits = [
        ("Single model (codegemma:2b)", 0, C_BODY),
        ("8 benchmark cases — not statistically significant", 0, C_BODY),
        ("Heuristic quality ≠ diagnostic correctness", 0, C_BODY),
        ("No user study conducted", 0, C_BODY),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(1.7), Inches(5.8), Inches(2.5), limits, font_size=15)

    # Future work
    _add_textbox(slide, Inches(7.0), Inches(1.1), Inches(5.8), Inches(0.5),
                 "Future Enhancements", font_size=18, bold=True, color=C_GREEN)
    future = [
        ("Dynamic few-shot example selection", 0, C_BODY),
        ("Multi-model comparison", 0, C_BODY),
        ("Ground-truth benchmark with expert review", 0, C_BODY),
        ("Fine-tuning on Linux troubleshooting data", 0, C_BODY),
        ("User study with Linux novices", 0, C_BODY),
    ]
    _add_bullet_box(slide, Inches(7.0), Inches(1.7), Inches(5.8), Inches(2.5), future, font_size=15)

    # Conclusion
    _add_textbox(slide, Inches(0.5), Inches(4.4), Inches(12.3), Inches(0.5),
                 "Conclusion", font_size=20, bold=True, color=C_ACCENT)
    conclusion = [
        ("TuxFix demonstrates that prompt engineering strategy measurably affects", 0, C_BODY),
        ("structural quality, safety information, and evidence grounding of LLM diagnostics.", 0, C_BODY),
        ("143 tests pass. Complete evaluation framework. Honest reporting.", 0, C_GREEN),
        ("", 0, C_BODY),
        ('"Ask better questions → get better diagnoses."', 0, C_ACCENT),
    ]
    _add_bullet_box(slide, Inches(0.5), Inches(4.9), Inches(12.3), Inches(2.3),
                    conclusion, font_size=16)
    return slide


def build_presentation():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    print("Building slides...")
    slide_title(prs)
    print("  1/10 Title")
    slide_problem(prs)
    print("  2/10 Problem")
    slide_objectives(prs)
    print("  3/10 Objectives")
    slide_limitations_solution(prs)
    print("  4/10 Limitations/Solution")
    slide_architecture(prs)
    print("  5/10 Architecture")
    slide_strategies(prs)
    print("  6/10 Strategies")
    slide_demo(prs)
    print("  7/10 Demo")
    slide_benchmark(prs)
    print("  8/10 Benchmark")
    slide_results(prs)
    print("  9/10 Results")
    slide_conclusion(prs)
    print(" 10/10 Conclusion")

    prs.save(str(OUTPUT_PATH))
    print(f"\n✅ Presentation saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_presentation()
