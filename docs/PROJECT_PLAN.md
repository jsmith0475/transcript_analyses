# Transcript Analysis Tool — Project Plan

## Executive Summary
The Transcript Analysis Tool converts raw meeting transcripts into comprehensive, actionable insights using a phased, parallel analysis pipeline and prompt-driven analyzers. Outputs include Obsidian-friendly Meeting Notes and a Composite Report, both with dated titles and filenames for traceability. The current version enforces a results-only strategy for Stage B to reduce token usage and improve performance on long transcripts.

## Vision
Deliver a robust, extensible analysis system that:
- Ingests transcripts (with or without named speakers)
- Runs multiple transcript analyses in parallel (Stage A)
- Runs results-synthesis analyses in parallel on combined Stage A outputs (Stage B), without re-reading the raw transcript
- Produces high-quality meeting notes and a composite report suitable for knowledge management and decision support

## Core Value Proposition
- Parallelized, cost-aware analysis pipeline with prompt modularity
- Clear separation of concerns (transcript-only vs results-only phases)
- Obsidian-ready outputs and composite reporting
- Extensible analyzers via simple prompt and class additions

## Scope

### In Scope (Phase 1)
1. Transcript processing (with/without speaker names)
2. Eight analytical frameworks (4 Stage A transcript-only + 4 Stage B results-only)
3. Phased parallel pipeline orchestration with isolation per analyzer
4. Meeting notes generation (Obsidian-friendly, dated title)
5. Composite report generation (dated title; optional Challenge.gov aggregation)
6. Configurable prompts and LLM parameters via .env / YAML
7. Batch, interactive, and single-run CLI
8. Local test runner script (simple DX)

### Out of Scope (Phase 1)
1. Real-time/transcript capture
2. Audio/video transcription
3. Multi-language prompt localization
4. Web UI
5. Hosted/cloud deployment

## Technical Architecture Overview

- Stage A (Transcript Analyses; parallel)
  - say_means, perspective_perception, premises_assertions, postulate_theorem
  - Prompt sources: `prompts/stage a transcript analyses/*`
  - Input: formatted transcript only

- Stage B (Results Analyses; parallel, results-only)
  - competing_hypotheses (ACH), first_principles, determining_factors, patentability
  - Prompt sources: `prompts/stage b results analyses/*`
  - Input: combined Stage A results only (no raw transcript)
  - ACH override implemented to enforce results-only prompt

- Final Synthesis
  - MeetingNotesAnalyzer consumes transcript + combined A+B results
  - Composite Report builder composes a single document:
    - Meeting Notes → Challenge.gov Aggregation (if present) → All analyses (structured summary, insights, concepts, raw output)

## Technology Stack

- Language: Python 3.10+
- LLM Integration:
  - OpenAI GPT‑5 (Responses API with reasoning.effort, text.verbosity)
  - Anthropic (optional)
  - Ollama (optional)
- Key Libraries:
  - pydantic, click, rich, jinja2, tiktoken, tenacity, python-dotenv
- Not Used: langchain (removed from plan)

## Current Status (Completed)

- Phased pipeline implemented (Stage A + Stage B) with bounded parallelism
- Stage B results-only prompts enforced (including ACH override)
- Meeting Notes generator (Obsidian-friendly; dated H1 title)
- Composite report builder (dated title; Challenge.gov aggregation hook)
- Dated filenames for Meeting Notes, Composite Report, and Pipeline JSON
- CLI commands (process, batch, interactive, list_analyzers)
- Test runner (`test_pipeline.py`) with transcript argument support
- Documentation refreshed (Architecture, Technical Spec, Workflow, User Guide, Quick Start, README)
- Verified on example transcripts

## Milestones & Timeline

### M1 (Next 2–3 days): Challenge.gov Evaluation + CLI Convenience
- Implement `ChallengeGovEvaluator` post-processing hook to populate `structured_data["challenge_results"]` for all analyses
- Add a CLI verb (e.g., `run`) to generate Meeting Notes and Composite report directly (mirrors test runner UX)
- Update docs, add unit tests for evaluator

### M2 (Next 4–5 days): Chunked Stage A (Map–Reduce) + Guardrails
- Chunk transcript into configurable sizes (Map)
- Run Stage A per chunk in parallel; merge outputs deterministically (Reduce)
- Add token budget guardrails to detect over-budget prompts and auto-switch to chunked mode
- Tests, metrics, and documentation

### M3 (Next 3–4 days): Disk Cache + Structured Data Contracts
- Optional persistent cache for LLM responses (opt-in, TTL)
- Document minimal structured_data schema per analyzer and add validators/normalizers
- Update docs and provide examples

## Deliverables

### Already Delivered
1. Phased, parallel pipeline with results-only Stage B
2. Meeting Notes (dated title) and Composite Report (dated title)
3. Dated filenames for outputs
4. Analyzer registry and phase groupings
5. Test runner and CLI with standard commands
6. Comprehensive documentation refresh

### Upcoming Deliverables
1. ChallengeGovEvaluator and aggregated Composite section
2. CLI “run” command for end-to-end generation
3. Chunked Stage A + merge with guardrails
4. Disk cache and structured_data contracts
5. Regression examples/golden outputs

## Risks & Mitigations

- Token overrun on long transcripts
  - Mitigation: Stage B results-only (done), Stage A chunking, budget guardrails
- LLM output variability
  - Mitigation: robust parsing in BaseAnalyzer, schema normalization (M3)
- Performance/Cost
  - Mitigation: prompt compaction, low verbosity/effort settings, caching (M3)

## Success Metrics

- Functional: End-to-end run time, stability, error rate
- Cost: Total token usage per transcript; Stage B usage remains small vs Stage A
- Output quality: Human-reviewed insight density and actionability
- Adoption: Ease of running via test runner/CLI; documentation clarity

## Run Commands (Summary)

- Test runner:
  ```bash
  python3 test_pipeline.py "example transcripts/example transcript - with names.md"
  python3 test_pipeline.py "example transcripts/example transcript - without names.md"
  python3 test_pipeline.py
  ```
- CLI:
  ```bash
  python -m src.transcript_analyzer.cli process "path/to/transcript.md" -o output -f obsidian -v
  python -m src.transcript_analyzer.cli batch "example transcripts" -p "*.md" -o output
  python -m src.transcript_analyzer.cli interactive "path/to/transcript.md"
  python -m src.transcript_analyzer.cli list_analyzers
  ```

## Documentation Map

- Architecture: `docs/ARCHITECTURE.md`
- Technical Specification: `docs/TECHNICAL_SPECIFICATION.md`
- Analysis Workflow: `docs/ANALYSIS_WORKFLOW.md`
- Implementation Roadmap: `docs/IMPLEMENTATION_ROADMAP.md`
- User Guide: `docs/USER_GUIDE.md`
- Quick Start: `QUICKSTART.md`
- README overview: `README.md`

## Next Steps

1. Implement ChallengeGovEvaluator and CLI convenience verb
2. Design and implement chunked Stage A + merge and add guardrails
3. Add optional disk cache and structured_data contracts
4. Extend documentation with golden outputs and more examples
