# Transcript Analysis Tool — Implementation Roadmap

Status: Active (Phased pipeline complete; Stage B results-only enforced; dated outputs shipped)

This roadmap outlines near-term and mid-term work to harden the system, reduce cost/latency on long transcripts, and improve UX.

## 1) Recently Completed

- Phased pipeline (Stage A → Stage B) with bounded parallelism
- Analyzer taxonomy and registry with phase groupings
- Meeting Notes synthesis + Composite Report generator
- Dated titles and filenames for all saved artifacts
- Stage B results-only prompts enforced (including ACH override in competing_hypotheses)
- Test runner (test_pipeline.py) supporting transcript path arguments

## 2) High-Priority Next Steps (Q1)

1. Chunked Stage A (Map–Reduce)
   - Map: Split transcript into chunks (configurable chunk_size/overlap); run Stage A analyzers per chunk in parallel.
   - Reduce: Merge chunk-level results deterministically (e.g., dedupe insights, union concepts, merge structured_data with defined rules).
   - Output: A single “StageACombined” context for Stage B.
   - Acceptance:
     - Functional on long transcripts; stable token usage
     - Deterministic merge rules documented; unit tests for merging

2. Challenge.gov Evaluation (Post-Processing Hook)
   - Implement ChallengeGovEvaluator applied to each AnalysisResult after parse_response.
   - Populate: analysis.structured_data["challenge_results"] = {
       "criteria_scores": {...}, "overall_rating": "...", "rationale": "..."
     }
   - Composite report auto-aggregates this section across analyses.
   - Acceptance:
     - Present for all analyses; composite shows aggregated view
     - Unit test: evaluator behavior on sample outputs

3. CLI “run” Command (One-shot Composite Generation)
   - Add a CLI verb (e.g., `run`) producing meeting notes and composite report from a given transcript (mirrors test runner behavior).
   - Flags: --output, --config, --parallel (N), --format (obsidian|markdown|json)
   - Acceptance:
     - End-to-end success with date-prefixed outputs; parity with test runner

4. Token Budget Guardrails
   - Estimate prompt sizes pre-call; warn/switch to chunked mode if threshold exceeded.
   - Configurable max prompt tokens per request.
   - Acceptance:
     - Guard triggers on long transcripts; runs without failure

## 3) Medium Priority

5. Disk Cache (Optional, Opt-In)
   - Persistent cache keyed by model+system+prompt+inputs (hash)
   - TTL configurable; disabled by default
   - Acceptance:
     - Cache hits reduce API calls in repeated dev runs; resilience when temperature=0

6. Structured Data Contracts
   - Stabilize structured_data schemas per analyzer (document keys/types)
   - Add schema validation and minimal normalizers (e.g., list/dict coercion)
   - Acceptance:
     - Documentation updated; validation without excessive runtime cost

7. Prompt Compaction & Retrieval
   - Trim transcript formatting when not needed (speaker/timestamps toggles)
   - Optional lightweight retrieval (top-K relevant segments) for analyzers that don’t require full context
   - Acceptance:
     - Lower token usage; metrics show improvements

## 4) Documentation & Examples

8. Documentation Refresh
   - Architecture, Technical Spec updated (done)
   - Analysis Workflow (update for staged prompts, dated outputs, run commands)
   - User Guide (quick start, CLI/test runner examples, outputs)
   - README/Quickstart (install, .env, quick commands)
   - Acceptance:
     - Docs reflect Stage B results-only; show dated filenames/titles

9. Example Transcripts & Golden Outputs
   - Provide a set of short/medium examples and expected outputs for regression
   - Acceptance:
     - Deterministic runs with cached/dry-run modes for docs and CI

## 5) Delivery Plan & Milestones

- M1: ChallengeGovEvaluator + CLI run command
  - Duration: ~2–3 days
  - Deliverables: evaluator, wiring, unit tests; CLI verb with flags; docs updated

- M2: Chunked Stage A + Merge with Guardrails
  - Duration: ~4–5 days
  - Deliverables: chunking, merge rules, tests; budget guardrail; doc updates

- M3: Disk Cache + Structured Data Contracts
  - Duration: ~3–4 days
  - Deliverables: optional disk cache, schemas/validators; docs; examples

## 6) Risks & Mitigations

- LLM Output Variability
  - Mitigation: robust parse_response; schema normalization; evaluator fallbacks

- Token Overruns on Long Transcripts
  - Mitigation: Stage B results-only (done); chunked Stage A; budget guardrails

- Cost/Latency
  - Mitigation: prompt compaction; selective context; caching

## 7) Testing Strategy

- Unit: BaseAnalyzer parsing, ChallengeGovEvaluator, merge reducers
- Integration: Phased pipeline on short/long inputs; verify outputs and dated filenames
- Performance: Token/millisecond budgets tracked across runs; guardrails triggering validated

## 8) Configuration Defaults (Recommended)

- LLM: gpt-5, reasoning.effort=low|minimal, text.verbosity=low
- Processing: parallel=true, max_concurrent=3, chunk_size ~4k tokens, overlap ~400
- Output: format=obsidian, directory=./output, date-prefixed filenames (enabled)
