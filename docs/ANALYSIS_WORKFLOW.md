# Transcript Analysis Workflow (Phased, Parallel)

This document describes the end-to-end workflow for running the Transcript Analysis Tool using the phased, parallel pipeline:
- Stage A: Transcript-only analyzers run in parallel.
- Stage B: Results-only analyzers run in parallel using combined Stage A results (no raw transcript).
- Final synthesis: Meeting Notes consume both transcript and combined results. Composite report aggregates everything with dated titles/filenames.

## Visual Process Flow (Phased + Parallel)

```mermaid
flowchart TD
    A[Input Transcript (.md)] --> B[Transcript Processor]
    B --> C[ProcessedTranscript (segments, speakers, metadata)]

    subgraph STAGE_A[Stage A - Transcript Analyses (Parallel)]
      direction LR
      A1[Say-Means]:::a
      A2[Perspective-Perception]:::a
      A3[Premises-Assertions]:::a
      A4[Postulate-Theorem]:::a
    end

    C --> STAGE_A
    STAGE_A --> D[Combined Stage A Results (Context)]

    subgraph STAGE_B[Stage B - Results Analyses (Parallel, Results-Only)]
      direction LR
      B1[Competing Hypotheses (ACH)]:::b
      B2[First Principles]:::b
      B3[Determining Factors]:::b
      B4[Patentability]:::b
    end

    D --> STAGE_B
    STAGE_B --> E[Combined A+B Context]

    E --> F[Meeting Notes Analyzer (Transcript + A+B)]
    F --> G[Meeting Notes (Markdown, Dated Title)]

    G --> H[Composite Report Builder]
    H --> I[Composite Report (Dated Title)]
    classDef a fill:#CDE7FF,stroke:#1C6DD0,color:#0A2A66;
    classDef b fill:#D6F8D6,stroke:#1D823A,color:#0D3D1F;
```

Key points:
- Stage A analyzers read the transcript only.
- Stage B analyzers read the combined results from Stage A by default; transcript can be injected as either a synthesized summary (Summary mode) or raw text (Full mode).
- Meeting Notes consume both transcript (raw or summary) and the combined (A+B) context.

## Detailed Pipeline

### Stage A: Transcript Analyses (Parallel)
- Say-Means (prompts/stage a transcript analyses/1 say-means.md)
- Perspective-Perception (prompts/stage a transcript analyses/2 perspective-perception.md)
- Premises-Assertions (prompts/stage a transcript analyses/3 premsises-assertions.md)
- Postulate-Theorem (prompts/stage a transcript analyses/4 postulate-theorem-proper.md)

Behavior:
- Each analyzer receives the formatted transcript and an isolated context.
- Results are merged into a single Stage A combined context for Stage B.

### Stage B: Results Analyses (Parallel, Results-Only)
- Competing Hypotheses (ACH) (prompts/stage b results analyses/5 analysis of competing hyptheses.md)
- First Principles (prompts/stage b results analyses/6 first principles.md)
- Determining Factors (prompts/stage b results analyses/7 determining factors.md)
- Patentability (prompts/stage b results analyses/8 patentability.md)

Behavior:
- Each analyzer overrides format_prompt to use ONLY the combined Stage A results.
- No raw transcript text is injected in Stage B prompts (token-efficient).

### Final Synthesis
- MeetingNotesAnalyzer (prompts/final output stage/9 meeting notes.md)
  - Consumes the formatted transcript plus the combined A+B results.
  - Produces Obsidian-friendly Meeting Notes with a dated H1 title.
  - Transcript injection can be Summary (synthesized) or Full (raw, capped) based on UI toggle.
  - Includes explicit “Decisions”, “Action Items”, and “Risks” sections, plus a fenced `INSIGHTS_JSON` block to drive the Insights dashboard.

### Composite Report
- Composite builder composes:
  1) Meeting Notes (verbatim)
  2) Challenge.gov Results aggregation (if analyses populate structured_data["challenge_results"])
  3) All analyses (structured summary, top insights, key concepts, raw output)

## Running the Workflow

From the project root:

### Quick Test Runner (Recommended)
```
# With a specific transcript (quote paths with spaces)
python3 test_pipeline.py "example transcripts/example transcript - with names.md"
python3 test_pipeline.py "example transcripts/example transcript - without names.md"

# Default (uses example transcripts/test_short.md)
python3 test_pipeline.py
```

Outputs are written to `output/` with date-prefixed filenames:
- `YYYY-MM-DD_{base}_meeting_notes.md`
- `YYYY-MM-DD_{base}_composite_report.md`
- `YYYY-MM-DD_{base}_pipeline_result.json`

### Full CLI (More Options)
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

## Outputs (Dated)

- Meeting Notes (Obsidian-friendly) with H1: `# YYYY-MM-DD - {Title or Meeting Notes}`
- Composite Report with top-level title: `YYYY-MM-DD - Composite Report`
- Pipeline JSON with token usage and timings
 - Summaries (when Summary mode enabled):
   - `output/jobs/{jobId}/intermediate/summaries/chunk_###.md`
   - `output/jobs/{jobId}/intermediate/summaries/summary.stage_b.single|reduce.md`
   - `output/jobs/{jobId}/intermediate/summaries/summary.final.single|reduce.md`
 - Insights dashboard artifacts:
   - `output/jobs/{jobId}/final/insight_dashboard.json|md|csv`

## Inter‑Stage Context Artifacts

For transparency and debugging, the combined context passed between stages is exposed:
- Stage A → Stage B: `output/jobs/{jobId}/intermediate/stage_b_context.txt`
- Stage B → Final: `output/jobs/{jobId}/final/context_combined.txt`

In the web UI, the bottom Inter‑Stage Context panel displays these in real time (via WebSocket) or reads from the files above as a fallback.

## Performance Notes

- Parallel phases reduce wall time.
- Stage B results-only significantly lowers token usage on long transcripts.
- Use `.env` tuning for model reasoning.effort and text.verbosity to control cost/latency.

## Challenge.gov Aggregation (Optional)

- If analyzers populate `structured_data["challenge_results"]`, the composite report includes an aggregated section: “Challenge.gov Results (All Analyses)”.
