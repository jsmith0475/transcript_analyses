# Transcript Analysis Tool - User Guide

This guide explains how to install, configure, and run the Transcript Analysis Tool, including the phased pipeline (Stage A transcript analyses → Stage B results analyses → Meeting Notes + Composite Report) and dated outputs.

## Web App Quick Start (Docker)

Most users will run the web app via Docker:

1. Copy env template and set server variables (you can set your API key in-app later):

   cp .env.template .env

2. Start the stack (app, worker, redis):

   docker compose up -d --build

3. Open the UI and set your key (if not configured server-wide):

   http://localhost:5001

At the top of the page, the “Your OpenAI API Key” field shows dots if a valid server key is present (masked). Delete the dots and paste your key to override for your session. You can Clear to revert to the server key.

## Table of Contents
1. Quick Start
2. Installation
3. Running the Tool
4. Outputs (Dated)
5. Configuration
6. Understanding the Analyses
7. Troubleshooting
8. Examples
9. FAQ

## 1) Quick Start (CLI)

From the project root, you can use the test runner for an end-to-end run:

```bash
# With a specific transcript (quote paths with spaces)
python3 test_pipeline.py "example transcripts/example transcript - with names.md"
python3 test_pipeline.py "example transcripts/example transcript - without names.md"

# Default (uses example transcripts/test_short.md)
python3 test_pipeline.py
```

This will:
- Process the transcript
- Run Stage A (transcript-only analyzers) in parallel
- Run Stage B (results-only analyzers) in parallel, using only combined Stage A results
- Generate Meeting Notes and a Composite Report with date-prefixed filenames in output/

Example outputs:
- output/YYYY-MM-DD_{base}_meeting_notes.md
- output/YYYY-MM-DD_{base}_composite_report.md
- output/YYYY-MM-DD_{base}_pipeline_result.json

## 2) Installation (CLI)

Prerequisites:
- Python 3.10+
- OpenAI API key (or other configured provider)
- Internet connection for LLM API calls

Install dependencies:
```bash
pip install -r requirements.txt
```

Set up environment variables:
```bash
cp .env.template .env
# Edit .env (add your API key, model, etc.)
# OPENAI_API_KEY=sk-...
```

Verify setup:
```bash
python verify_setup.py
```

## 3) Running the Tool (CLI)

You can use either the test runner (recommended during development) or the CLI.

### 3.1 Test Runner (Development)
```bash
# Specific transcript:
python3 test_pipeline.py "path/to/transcript.md"

# Default:
python3 test_pipeline.py
```

### 3.2 CLI (Click-based)
```bash
# Process a single transcript
python -m src.transcript_analyzer.cli process "path/to/transcript.md" -o output -f obsidian -v

# Batch process a directory (pattern specified via -p)
python -m src.transcript_analyzer.cli batch "example transcripts" -p "*.md" -o output

# Interactive step-through
python -m src.transcript_analyzer.cli interactive "path/to/transcript.md"

# List available analyzers
python -m src.transcript_analyzer.cli list_analyzers
```

 Notes:
 - Stage A analyzers read only the transcript.
 - Stage B analyzers read the combined Stage A results (context); transcript can be injected optionally.
 - Meeting Notes consume both the formatted transcript and combined A+B results.
 - Options: Stage B and Final include an “Include Transcript” toggle with Mode (full/summary) and Max Characters.
   - Full: injects the raw transcript (capped by Max Characters)
   - Summary: injects a synthesized summary (map→reduce for long inputs), bounded and cached
 - Web UI: The bottom Inter‑Stage Context panel shows the exact context passed from Stage A → Stage B and from Stage B → Final (copy/download supported).

## 4) Outputs (Dated)

All key outputs use date-prefixed filenames. Meeting Notes include a dated H1 title.

- Meeting Notes (Markdown, Obsidian-friendly):
  - File: output/YYYY-MM-DD_{base}_meeting_notes.md
  - Title: `# YYYY-MM-DD - Meeting Notes` (or provided title)
- Composite Report (Markdown):
  - File: output/YYYY-MM-DD_{base}_composite_report.md
  - Title: `YYYY-MM-DD - Composite Report`
  - Contents: Meeting Notes → (optional) Challenge.gov Results aggregation → per-analysis sections (structured summary, top insights, key concepts, raw output)
- Pipeline JSON:
  - File: output/YYYY-MM-DD_{base}_pipeline_result.json
  - Contains token usage and timings per analyzer

Inter‑Stage Context (Web/Celery runs):
- `output/jobs/{jobId}/intermediate/stage_b_context.txt` (Stage A → Stage B)
- `output/jobs/{jobId}/final/context_combined.txt` (Stage B → Final)

Insights Dashboard (Web UI)
- After Final completes, the app writes `output/jobs/{jobId}/final/insight_dashboard.{json,md,csv}`.
- The UI loads `/api/insights/<jobId>` to render Actions, Decisions, and Risks with filtering and export.
- The panel clears on app start, reset, and run start to avoid showing stale data.

## 6.5 Prompt Templates (Jinja) — Quick Primer

Prompt templates are Markdown files under `prompts/` rendered with Jinja2 variables:
- Stage A templates must include `{{ transcript }}`
- Stage B templates must include `{{ context }}`; they may also include `{{ transcript }}` (optional)
- Final templates must include `{{ context }}`; `{{ transcript }}` is optional

Final Prompt Output Structure for Insights
- To produce a complete, machine-readable Insights dashboard, Final prompts (Meeting Notes, Composite Note) include:
  - Explicit sections: “Decisions”, “Action Items”, and “Risks” (single-line bullets per item)
  - A fenced `INSIGHTS_JSON` block mapping the bullets to `{ actions:[], decisions:[], risks:[] }`
    - Dates: `YYYY-MM-DD` format (normalize any relative dates)
    - Optional `anchor`: a transcript link token like `#seg-123` to support evidence linking in the UI

At runtime, the app fills:
- `context`: combined analysis results for the stage
- `transcript`: either raw transcript (Full) or a synthesized summary (Summary), when enabled

You can conditionally include sections:
```
{% if transcript %}
---
TRANSCRIPT
{{ transcript }}
{% endif %}
```

## 5) Configuration

Environment (.env):
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5
TRANSCRIPT_ANALYZER_REASONING_EFFORT=medium   # minimal|low|medium|high
TRANSCRIPT_ANALYZER_TEXT_VERBOSITY=medium     # low|medium|high
TRANSCRIPT_ANALYZER_MAX_TOKENS=8000
TRANSCRIPT_ANALYZER_OUTPUT_DIR=./output
TRANSCRIPT_ANALYZER_FORMAT=obsidian           # obsidian|markdown|json
TRANSCRIPT_ANALYZER_PARALLEL=true
```

Programmatic:
- `AppConfig.from_env()` reads from .env
- `AppConfig.from_yaml(path)` reads from YAML

## 6) Understanding the Analyses

Stage A — Transcript Analyses (prompt source: prompts/stage a transcript analyses/*)
1. Say-Means: Explicit vs implied meaning, subtext
2. Perspective-Perception: Subjective vs objective viewpoints and biases
3. Premises-Assertions: Logical structure, assertions, dependencies
4. Postulate-Theorem: Fundamental propositions, derived conclusions

Stage B — Results Analyses (prompt source: prompts/stage b results analyses/*)
- Results-only prompts (override `format_prompt`), consume combined Stage A results (no raw transcript):
5. Competing Hypotheses (ACH): Hypotheses, evidence, rankings (override implemented)
6. First Principles: Core truths and irreducible components
7. Determining Factors: Controllable vs uncontrollable factors
8. Patentability: Potentially patentable ideas and categorization

Final Synthesis
- Meeting Notes Analyzer (prompts/final output stage/9 meeting notes.md): Consumes transcript + combined A+B results

## 7) Troubleshooting

- No API key:
  - Set OPENAI_API_KEY in .env or export in your shell.
- Token usage too high:
  - Use shorter transcripts, reduce verbosity/reasoning effort, or run on the short sample first.
- Long transcripts:
  - The pipeline already reduces Stage B prompt sizes by not injecting the raw transcript in Stage B. For very long inputs, consider chunking (see roadmap).
- Errors in a specific analyzer:
  - Use the CLI `-v` flag for verbose logs.
  - Inspect `output/*_pipeline_result.json` for details.

## 8) Examples

Short sample:
```bash
python3 test_pipeline.py
# Generates dated meeting notes and composite report in output/
```

Longer sample:
```bash
python3 test_pipeline.py "example transcripts/example transcript - with names.md"
```

Results-only ACH confirmation:
- In logs, ACH Stage B prompt tokens should be small (e.g., ~1k) compared to Stage A transcript prompts.

## 9) FAQ

Q: Where are outputs saved?
A: In output/, with date-prefixed filenames. Meeting Notes and Composite Report include dated titles as well.

Q: How do I add a new analysis?
A: Create a subclass of `BaseAnalyzer`, add a prompt under prompts/{transcript analyses|results analyses}, and register it in `ANALYZER_REGISTRY`. If it’s Stage B, override `format_prompt` to use only the results context.

Q: Can I run on non-English transcripts?
A: Yes, though prompts are in English. Results quality may vary; you can localize prompts if needed.

Q: How can I reduce costs?
A: Use the short sample for testing, set lower reasoning effort/text verbosity, and avoid re-running unchanged inputs.
