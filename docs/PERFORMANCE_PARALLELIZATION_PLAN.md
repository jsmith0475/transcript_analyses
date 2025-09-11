# Performance and Parallelization Plan

Goal: Reduce end-to-end wall-clock time for the Transcript Analysis pipeline by introducing safe parallel execution and prompt-size controls, without degrading result quality or breaking the current run directory/output guarantees.

## Summary of Agreed Principles

- Stage A analyzers are independent, all read the same transcript, and can run in parallel.
- Stage B analyzers are independent, all read the same aggregated Stage A context, and can run in parallel once Stage A is complete.

## Success Criteria

1) Wall-clock reduction
   - Stage A total time ≈ max(single Stage A analyzer time) ± overhead
   - Stage B total time ≈ max(single Stage B analyzer time) ± overhead
   - Overall target: 2–3x speed-up versus current synchronous execution (exact factor depends on model latency and concurrency limits)

2) Stability and correctness
   - All analyzers still complete successfully (8/8) on sample runs
   - Intermediate outputs, structured_data, and insights remain populated and grounded
   - Output directory structure and metadata.json integrity preserved

3) Cost and token management
   - No unbounded prompt growth; Stage B prompt length maintained within a configurable target
   - Analyzer-specific max_tokens adhered to, with graceful truncation

---

## Current State Assessment (Relevant)

- BaseAnalyzer supports both sync and async pathways (analyze/analyze_sync); llm_client has async API (complete_async).
- Orchestration currently executes analyzers in sequence for each stage in most scripts.
- Stage B context can exceed typical budgets (observed prompt warnings ~14k tokens pre-fix); we must control payload size.

---

## Architecture Changes

### 1) Async Concurrent Orchestration (Core)

Implement a concurrency-capable orchestrator using asyncio with a Semaphore to throttle concurrent LLM calls, driven by config.

- File: `src/app/orchestration.py` (extend or add functions)
- New helpers:
  - `async run_stage_analyzers_concurrently(stage_name: str, analyzers: list[BaseAnalyzer], context: AnalysisContext, output_dir: Path, max_concurrent: int) -> dict[str, AnalysisResult]`
    - Use `asyncio.Semaphore(max_concurrent)` to guard concurrency
    - For each analyzer:
      - Launch a task that calls `await analyzer.analyze(context)` (async version)
      - On success, optionally save_intermediate_result (same as today)
      - On error, capture error_message and mark status properly
    - Use `asyncio.gather(..., return_exceptions=True)` to avoid failing the entire stage on one exception
  - `async run_pipeline_async(...)`:
    - Stage A: `await run_stage_analyzers_concurrently('stage_a', ...)`
    - Aggregate Stage A results; assemble Stage B context
    - Stage B: `await run_stage_analyzers_concurrently('stage_b', ...)`
    - Final outputs and metadata updates at the end

- Thread-safety and metadata
  - Metadata writes: use a shared `asyncio.Lock()` to guard `metadata.json` open/write, or write once per stage completion to reduce contention
  - Logging remains at INFO level; avoid per-token heavy logs

- Configuration
  - Use: `config.processing.max_concurrent` (default 3)
  - Future extension: separate `max_concurrent_stage_a` and `max_concurrent_stage_b` if needed

### 2) Prompt Payload Control for Stage B (Important)

Introduce a configurable context reducer (non-LLM summarization first; optional LLM summarization later) to ensure prompt length stays within target.

- Add a utility: `src/app/context_utils.py` with:
  - `build_stage_b_context(previous_analyses: dict[str, AnalysisResult], include_transcript: bool, token_target: int, top_insights: int, include_structured_keys: list[str]) -> str`
    - Strategy: extract top-N insights from each Stage A analyzer (respecting `config.output.max_insights_per_analyzer`)
    - Include only selected structured_data keys (e.g., for ACH: hypotheses/evidence if present; for others: domain-specific keys)
    - Optionally include a small transcript slice (disabled by default for Stage B per current design)
    - Use token counter to trim to `token_target` with a back-off: drop low-priority sections until under budget

- Config additions (in AppConfig or ProcessingConfig):
  - `processing.stage_b_context_token_budget: int = 8000` (tokens for context section before completion)
  - `processing.stage_b_context_top_insights: int = 5` (per analyzer)
  - `processing.stage_b_context_include_structured_keys: list[str] = []` (global defaults; analyzers can override)
  - Maintain analyzer-specific overrides via `analyzers[analyzer_name].max_tokens` for completion budget

- Enforcement
  - `BaseAnalyzer.format_prompt` (stage_b branch) can call the new builder instead of `get_combined_context()` when enabled via config
  - Alternatively: keep `get_combined_context()` but add trimming using `BaseAnalyzer._limit_text_by_tokens()` to the configured token budget (quick win; less semantic control)

### 3) Rate Limiting, Retries, and Timeouts (Resilience)

- Ensure `llm_client` async calls respect:
  - `timeout` from `LLMConfig` (already present)
  - `max_retries` and `retry_delay` (already present)
  - Add exponential backoff with jitter on 429s/5xx responses if not present in async path
- Concurrency tuning guidelines:
  - Start with `max_concurrent=3` (observed stable for large prompts)
  - Increase cautiously; measure error rates and latency

### 4) I/O Optimizations (Second-order)

- Save intermediate results after all responses for a stage complete to reduce interleaved writes (optional)
- Avoid frequent metadata writes; do a single update per stage transition (start/end), plus final summary

---

## Implementation Steps & Order

1) Orchestrator skeleton
   - Implement `run_stage_analyzers_concurrently` using async/await and Semaphore
   - Implement/extend `run_pipeline_async` to run Stage A then Stage B
   - Keep current synchronous scripts untouched for fallback

2) Hook into existing scripts
   - Add `scripts/test_parallel_pipeline.py` that invokes the async orchestrator (via `asyncio.run`)
   - Preserve run directory layout, metadata, and output file formats

3) Stage B context control (MVP, low-risk)
   - Add a token target and trimming using `_limit_text_by_tokens()` around `context.get_combined_context()`
   - Config gate: `processing.stage_b_context_token_budget` (e.g., 8000)
   - Validate token usage moves from ~18–19k towards the configured budget while maintaining quality

4) Optional richer context reducer (Phase 2)
   - Implement `context_utils.build_stage_b_context(...)` to extract top insights and selected structured_data portions
   - Analyzer-specific inclusion rules if necessary (ACH might want specific evidentiary bullets)

5) Benchmarks and acceptance
   - Add timing and token logging:
     - Per analyzer: latency and token usage
     - Per stage: wall-clock start/end
     - Per run: overall summary (already in metadata and final report)
   - Compare wall-clock before vs after on the same transcript
   - Confirm intermediate outputs are still grounded and non-template

6) Tuning
   - Adjust `max_concurrent` to balance speed vs. rate limits
   - Tune Stage B token budgets for quality vs. latency/cost
   - If using OpenAI rate-limited org keys, consider short sleeps between batches if 429s observed

---

## Risks & Mitigations

- Rate-limit or timeout errors when increasing concurrency
  - Mitigation: Semaphore, backoff with jitter, max_retries, and sane `max_concurrent`

- Output write races or metadata corruption
  - Mitigation: write metadata on stage boundaries; use `asyncio.Lock()` for concurrent writes if needed

- Quality regression from context trimming
  - Mitigation: start with conservative token targets and incremental trimming; add top-N insights selection later

- Memory/CPU pressure on local environment when running many simultaneous tasks
  - Mitigation: cap concurrency; stagger batch starts if necessary

---

## Configuration Additions (Proposed)

- `processing.max_concurrent: int = 3`
- `processing.stage_b_context_token_budget: int = 8000`
- `processing.stage_b_context_top_insights: int = 5`
- `processing.stage_b_context_include_structured_keys: list[str] = []`
- Optional per-analyzer overrides via `analyzers[<name>].max_tokens`

---

## Deliverables

- Code: Async orchestrator in `src/app/orchestration.py`, optional `src/app/context_utils.py`
- Script: `scripts/test_parallel_pipeline.py` (end-to-end run using async)
- Documentation: This plan; brief README notes in `docs/DEVELOPMENT_STATUS.md` or `docs/EXECUTION_PLAN.md` describing how to run parallel pipeline
- Benchmark report: Before/After wall-clock, token usage, and success counts; saved under `output/runs/…/logs/benchmark.json` (optional)

---

## Milestones and Acceptance Criteria

- M1: Orchestrator runs Stage A concurrently; wall-clock < sum of individual analyzers; outputs identical structure
- M2: Orchestrator runs Stage B concurrently; outputs grounded; no template fallbacks; token usage within configured budgets
- M3: Benchmark comparisons demonstrate ≥2x end-to-end speed-up versus synchronous baseline on sample1.md
- M4: Optional: Stage B context reducer produces comparable quality while reducing prompt size variability

---

## Rollback Plan

- Keep existing synchronous scripts (`scripts/test_full_pipeline.py` and `scripts/test_full_pipeline_fixed.py`) intact
- New orchestrator and script are additive; if issues occur, use the synchronous baseline immediately
