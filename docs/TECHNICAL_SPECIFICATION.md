# Transcript Analysis Tool - Technical Specification

This document specifies the system architecture, core components, data models, analyzers, runtime behavior, configuration, CLI usage, outputs, and non-functional considerations for the Transcript Analysis Tool.

Version: 0.2 (Phased pipeline with Stage B results-only prompts; optional transcript injection; inter‑stage context panel; dated outputs enabled)

## 1) System Architecture

### 1.1 Design Principles
- Modularity: Analyzers are independent, swappable units with a common base class.
- Extensibility: New analyzers can be added with minimal wiring (registry + prompt).
- Configurability: Behavior is driven by prompt files and environment-driven config.
- Performance: Parallel stages (A and B); Stage B avoids re-sending the raw transcript.
- Robustness: Token counting, retries, defensive parsing, and structured outputs.
- Reproducibility: Prompts live in-repo; dated titles and filenames for outputs.

### 1.2 High-Level Flow (Phased Pipeline)
- Stage A (Transcript Analyses, parallel): Run analyzers that read ONLY the transcript text.
- Stage B (Results Analyses, parallel): Run analyzers that read ONLY the combined results from Stage A (not the raw transcript).
- Meeting Notes: A dedicated analyzer synthesizes final meeting notes from both the transcript and the combined (A+B) results.
- Composite Report: Builds a single document starting with the meeting notes, optionally aggregating Challenge.gov results (if present), then appending all analyses.

```
Raw Transcript ─▶ TranscriptProcessor ─▶ ProcessedTranscript
                                   │
                                   └▶ Pipeline.run_phased
                                        Stage A (parallel) ─▶ Combined Stage A Results (context)
                                        Stage B (parallel) ─▶ Combined A+B Context
                                        Meeting Notes (Transcript + A+B)
                                        Composite Report
```

## 2) Core Components

### 2.1 Transcript Processor (src/transcript_analyzer/transcript_processor.py)
- Parses input .md transcript into structured segments and speaker metadata.
- Produces a `ProcessedTranscript` with normalized segments, speakers, and metadata (e.g., counts, title/date if present).
- Handles transcripts both with and without explicit speaker names.

### 2.2 Base Analyzer (src/analyzers/base_analyzer.py)
- Abstract class providing:
- Prompt template loading (Jinja2 markdown files under `prompts/`)
- format_prompt:
  - Stage A: renders templates with `{{ transcript }}`
  - Stage B: builds fair‑share combined context from Stage A results into `{{ context }}`; optionally injects `{{ transcript }}` when UI toggle enabled
  - Final: sets `{{ context }}` from A+B results; optionally injects `{{ transcript }}` per UI toggle and cap
  - analyze: token counting, LLM call with retries, safe parsing, insight/concept extraction
  - parse_response: abstract—each analyzer returns structured_data dict
  - extract_insights / extract_concepts: safe defaults (can be overridden)
- LLM interaction via `LLMClient` with token counting and retry.

### 2.3 Analysis Pipeline (web parallel orchestrator: src/app/parallel_orchestration.py)
- `run_phased(processed, stage_a, stage_b, max_concurrent=3)`:
  - Stage A: transcript-only analyzers in parallel (isolated contexts)
  - Stage B: results analyzers in parallel using combined Stage A outputs (context only by default; transcript optional)
  - Aggregates usage metrics, timing, and errors; returns `PipelineResult`.

### 2.4 Report Generator (src/transcript_analyzer/report_generator.py)
- Produces structured `MeetingNotes` data from `PipelineResult`.
- Formats Obsidian-friendly markdown with dated H1 title: `# YYYY-MM-DD - {Title or Meeting Notes}`.

### 2.5 Composite Report (src/transcript_analyzer/composite_report.py)
- Emits a single markdown document:
  - Top-level dated title (e.g., `YYYY-MM-DD - Composite Report`)
  - Meeting Notes section (verbatim)
  - Optional Challenge.gov aggregation (if analyses set `structured_data["challenge_results"]`)
  - Each analysis: structured summary, top insights, key concepts, raw output

### 2.6 CLI and Test Runner
- CLI: `src/transcript_analyzer/cli.py` (Click-based)
- Test runner: `test_pipeline.py` supports a transcript path argument and saves dated outputs.

## 3) Data Models (src/transcript_analyzer/models.py)

### 2.7 Summarizer (src/utils/summarizer.py)
- Purpose: Generate a bounded, high‑quality summary for transcript injection when Summary mode is enabled.
- Modes:
  - Single‑pass for short transcripts (≤ `summary_single_pass_max_tokens`)
  - Map‑reduce for long transcripts: chunk → map summaries → reduce to global summary
- Controls (config.processing):
  - `summary_enabled`, `summary_map_chunk_tokens`, `summary_map_overlap_tokens`,
    `summary_stage_b_target_tokens`, `summary_final_target_tokens`,
    `summary_single_pass_max_tokens`, `summary_map_model`, `summary_reduce_model`
- Artifacts: intermediate/summaries/{chunk_###.md, summary.stage_*.single|reduce.md}

Pydantic BaseModel classes (selection):

- Transcript
  - `RawTranscript { content: str, filename: str, metadata: Dict[str, Any] }`
  - `TranscriptSegment { segment_id: int, speaker: Optional[str], text: str, timestamp: Optional[str] }`
  - `Speaker { id: str, name: Optional[str], segments_count: int }`
  - `TranscriptMetadata { filename, date, duration, title, description, word_count, segment_count }`
  - `ProcessedTranscript { segments: List[TranscriptSegment], speakers: List[Speaker], metadata: TranscriptMetadata, raw_text: str, has_speaker_names: bool }`

- Analyses
  - `AnalysisResult { analyzer_name, raw_output, structured_data: Dict, insights: List[Insight], concepts: List[Concept], processing_time, token_usage }`
  - `AnalysisContext { transcript: Optional[ProcessedTranscript], previous_analyses: Dict[str, AnalysisResult], accumulated_insights: List[Insight], identified_concepts: Set[str], metadata: Dict[str, Any] }`
  - `PipelineResult { transcript, analyses: Dict[str, AnalysisResult], meeting_notes: Optional[MeetingNotes], total_processing_time, total_token_usage, success, errors }`

- Outputs
  - `MeetingNotes { metadata, attendees, summary, analyses, action_items, key_decisions, first_principles, determining_factors, patentable_ideas, linked_concepts, issue_solution_pairs }`

- Config
  - `AppConfig { llm: LLMConfig, processing: ProcessingConfig, output: OutputConfig, obsidian: ObsidianConfig, analysis: Dict[str, AnalysisConfig] }`

## 4) Analyzers Specification

### 4.1 Stage A — Transcript Analyses (prompt source: prompts/stage a transcript analyses/*)
- `say_means` → 1 say-means.md
  - Input: Transcript ONLY
  - Output: say_mean_pairs, hidden_agendas, etc.
- `perspective_perception` → 2 perspective-perception.md
  - Input: Transcript ONLY
  - Output: explicit/implicit perceptions, perspectives, biases, gaps
- `premises_assertions` → 3 premsises-assertions.md
  - Input: Transcript ONLY
  - Output: explicit/implicit premises, assertions, dependencies
- `postulate_theorem` → 4 postulate-theorem-proper.md
  - Input: Transcript ONLY
  - Output: postulates, theorems, logical chains

### 4.2 Stage B — Results Analyses (prompt source: prompts/stage b results analyses/*)
Stage B analyzers OVERRIDE `format_prompt` to use ONLY the combined results context by default (no raw transcript). When “Include Transcript” is enabled in the UI, `{{ transcript }}` is also provided (trimmed), while fairness budgeting still applies to `{{ context }}`.

- `competing_hypotheses` (ACH) → 5 analysis of competing hyptheses.md
  - Input: Combined Stage A results ONLY (override implemented)
  - Output: hypotheses, evidence, ACH matrix, rankings, most_likely
- `first_principles` → 6 first principles.md
  - Input: Combined results ONLY (override implemented)
  - Output: first_principles, core_truths, assumptions_removed
- `determining_factors` → 7 determining factors.md
  - Input: Combined results ONLY (override implemented)
  - Output: determining_factors, contributing_factors, impact_assessment
- `patentability` → 8 patentability.md
  - Input: Combined results ONLY (override implemented)
  - Output: patentable_ideas, categorization, likelihood_assessment

### 4.3 Final Synthesis
- `meeting_notes` → prompts/final output stage/9 meeting notes.md
  - Input: Transcript + Combined (A+B) results
  - Output: Obsidian-friendly meeting notes (dated title)

## 5) LLM Integration (src/transcript_analyzer/llm_client.py)

- Clients:
  - OpenAI (Async/Synchronous): Uses GPT‑5 Responses API automatically if model starts with `gpt-5` (reasoning.effort, text.verbosity). Falls back to Chat Completions for non-GPT‑5 models.
  - Anthropic (Claude) — optional
  - Ollama (local) — optional
- Features:
  - Token counting for prompts and responses
  - Retries with exponential backoff (`tenacity`)
  - Caching wrapper (`CachedLLMClient`) for deterministic runs (temperature == 0)

## 6) Configuration

### 6.1 Environment Variables (.env)
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-5`
- `TRANSCRIPT_ANALYZER_REASONING_EFFORT=medium` (minimal/low/medium/high)
- `TRANSCRIPT_ANALYZER_TEXT_VERBOSITY=medium` (low/medium/high)
- `TRANSCRIPT_ANALYZER_MAX_TOKENS=8000`
- `TRANSCRIPT_ANALYZER_OUTPUT_DIR=./output`
- `TRANSCRIPT_ANALYZER_FORMAT=obsidian`
- `TRANSCRIPT_ANALYZER_PARALLEL=true|false`

### 6.2 AppConfig Loading
- `AppConfig.from_env()` reads from `.env` (via python-dotenv)
- `AppConfig.from_yaml(path)` reads from a YAML config if preferred

## 7) CLI and Test Runner

### 7.1 Quick Test Runner (recommended during development)
From the project root:
```
# With a specific transcript (quote paths with spaces)
python3 test_pipeline.py "example transcripts/example transcript - with names.md"
python3 test_pipeline.py "example transcripts/example transcript - without names.md"

# Default (uses example transcripts/test_short.md)
python3 test_pipeline.py
```
Outputs saved to `output/` with date‑prefixed filenames:
- `YYYY-MM-DD_{base}_pipeline_result.json`
- `YYYY-MM-DD_{base}_meeting_notes.md`
- `YYYY-MM-DD_{base}_composite_report.md`

### 7.2 CLI (Click-based)
```
# Process a single transcript
python -m src.transcript_analyzer.cli process "path/to/transcript.md" -o output -f obsidian -v

# Batch process a directory
python -m src.transcript_analyzer.cli batch "example transcripts" -p "*.md" -o output

# Interactive mode
python -m src.transcript_analyzer.cli interactive "path/to/transcript.md"

# List available analyzers
python -m src.transcript_analyzer.cli list_analyzers
```

## 8) Outputs

- Meeting Notes: Dated H1 title (`# YYYY-MM-DD - {Title or Meeting Notes}`), Obsidian-friendly formatting.
- Composite Report: Dated top-level title, Meeting Notes first, optional Challenge.gov aggregation, then per-analysis sections (structured summary, top insights, concepts, raw output).
- Pipeline JSON: Token counts, timings, counts of insights/concepts per analyzer.

### 8.1 Insights (Actions, Decisions, Risks)
- Final analyzers emit sections (Decisions, Action Items, Risks) and an `INSIGHTS_JSON` fenced block.
- The backend aggregator resolves items in this order: JSON block → section text (merging Owner/Due fragments) → heuristic scan.
- Evidence anchors like `#seg-123` (if present) become `links.transcript_anchor` in items.
- Artifacts: `output/jobs/{jobId}/final/insight_dashboard.json|md|csv`.
- API: `/api/insights/<jobId>` returns `{ ok, jobId, counts, items }` for the UI.

## 9) Error Handling & Resilience

- Analyzer-level try/except with logging and continuation (unless `stop_on_error` configured).
- LLM retries with exponential backoff.
- Defensive parsing in `BaseAnalyzer` to handle None/empty responses gracefully.

## 10) Performance & Cost Considerations

- Parallelism: Stage A and Stage B run in bounded parallel (semaphores).
- Stage B Results-Only: Prompts omit raw transcript to reduce tokens and cost.
- Prompt Efficiency: Keep templates concise; include only necessary fields.
- Planned Enhancements:
  - Chunked Stage A (map‑reduce) with a merge step
  - Token budget guardrails (auto-switch to chunked mode)
  - Disk caching for repeatability across runs

## 11) Testing Strategy

- Integration Test: `test_pipeline.py` exercises the full phased pipeline and writes all outputs.
- Analyzer Tests: (recommended) Mock LLM responses to validate `parse_response` and insight/concept extraction.
- Performance Tests: Validate token usage and timings on short and long transcripts.

## 12) Security & Privacy

- API keys loaded from environment; not committed.
- Transcript data is processed locally; outputs written to `output/`.
- No uploads or persistent external storage beyond LLM requests.

## 13) Extensibility

- Add a transcript analyzer:
  1) Implement `BaseAnalyzer` subclass and `parse_response`
  2) Add prompt to `prompts/stage a transcript analyses/`
  3) Register in `ANALYZER_REGISTRY` and `STAGE_A_ANALYZERS`
- Add a results analyzer:
  1) Implement subclass and OVERRIDE `format_prompt` to use only context
  2) Add prompt to `prompts/stage b results analyses/`
  3) Register in `ANALYZER_REGISTRY` and `STAGE_B_ANALYZERS`

## 14) Roadmap (next)
- Challenge.gov Evaluation: Post-processing hook to set `analysis.structured_data["challenge_results"]` consistently across analyzers for composite aggregation.
- Chunked Stage A + Merge: Token-efficient pipeline for long transcripts.
- CLI verb to generate composite directly (packaged command alias).
