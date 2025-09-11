# Execution Plan — Transcript Analysis Tool
Version: 1.0  
Date: 2025-09-07  
Owner: Engineering

This plan is derived directly from PRD_Transcript_Analysis_Tool.md (v1.0) and the current codebase. It specifies scope, architecture, milestones, acceptance criteria, and test procedures. All development, validation, and benchmarks will use real GPT calls via the OpenAI API key configured in .env unless a specific test calls for mocks.

---

## 1) Scope and Objectives

- Build and ship a multi-stage transcript analysis pipeline (Stage A ➜ Stage B ➜ Final) with:
  - Parallelized execution for Stage A and Stage B with bounded concurrency
  - Prompt templates per analyzer with strict input variable contracts
  - Organized per-run output directory with intermediate, final, logs, and run metadata
  - Web interface with real-time progress (WebSocket/Socket.IO) and export
  - Proactive notifications (Slack/Webhook/Desktop/File) across all orchestrators
  - Autonomous notification test harness that validates “pipeline_completed” without external services
- Performance target (per PRD): average end-to-end analysis under 60 seconds for a 10,000-word transcript with 10 concurrent users (with tuning and caching strategies).

---

## 2) Architecture Mapping to Requirements

- Backend: Flask API + Celery workers (Redis broker), Flask-SocketIO for realtime updates.
- Async CLI path: asyncio-based orchestrator (bounded concurrency per stage).
- LLM: OpenAI API via `src/llm_client.py` with configurable model, temperature, retry/backoff, and token accounting.
- Analyzers:
  - Stage A (transcript-only): say-means, perspective-perception, premises-assertions, postulate-theorem
  - Stage B (meta-analysis): competing-hypotheses (ACH), first-principles, determining-factors, patentability
  - Final (synthesis): meeting notes, composite note
- Prompt system: Jinja2 templates with strict input variables by stage (runtime toggles supported):
  - Stage A: {transcript}
  - Stage B: {context} (+ {transcript} as a synthesized summary or raw text when enabled)
  - Final: {context} (+ {transcript} as a synthesized summary or raw text when enabled)
- Notification system: `NotificationManager` (Slack/Webhook/Desktop/File) with a unified event schema and lifecycle hooks (start/stage started/stage completed/completed/error).
- Output/runs: run_id directory containing metadata.json, intermediate/stage outputs, final deliverables, logs, and executive_summary.md.

---

## 3) Data and Output Organization

- Input:
  - Web: POST transcript text or uploaded file (.txt, .md, .markdown up to 10MB).
  - CLI: sample transcripts in `input sample transcripts/`.
- Run directory: `output/runs/run_{YYYYMMDD_HHMMSS}/`
  - intermediate/
    - stage_a/[analyzer].(json|md) and `stage_a_context.json`
    - stage_b/[analyzer].(json|md) and optional `stage_b_context_debug.txt`
  - final/
    - `executive_summary.md`
    - `meeting_notes.md`, `composite_note.md` (when final stage implemented)
  - intermediate/summaries/
    - `chunk_###.md` (map summaries for long transcripts)
    - `summary.stage_b.single.md|reduce.md` (used for Stage B injection)
    - `summary.final.single.md|reduce.md` (used for Final injection)
  - logs/ (raw logs, timings, token counts)
  - `metadata.json` (run config, analyzers used, timing, token usage summary)
  - Optional sentinel `COMPLETED` file on success (see Milestone M7)
- Notifications FileChannel (for autonomous test):
  - Configured to write JSONL lines to path set by `TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH`, e.g. `output/notifications.jsonl`
  - Must include at least events: `pipeline_started`, `stage_started`, `stage_completed`, `pipeline_completed`, `pipeline_error`.

---

## 4) LLM Strategy

- Models: Start with `gpt-4o` or the project’s configured GPT-4/GPT-5 model in `.env` (see `src/llm_client.py`).
- Token policy:
  - Enforce `stage_b_context_token_budget` (config-driven, default 8000 tokens) when assembling `{context}` for Stage B to reduce latency and errors.
  - Consider an optional structured reducer (future optimization) to include top-N insights from Stage A by salience.
- Calls:
  - Real API calls by default. Retries with exponential backoff on rate limits/transient errors.
  - Capture token usage and wall-clock timing per analyzer for performance metrics.
- Prompt hygiene:
  - Each analyzer template must ONLY reference allowed variables per stage.
  - Strict Jinja validation; fail fast if a template references an invalid variable.

---

## 5) Orchestration and Concurrency

- CLI Orchestrator (`src/app/async_orchestrator.py`)
  - Run Stage A analyzers concurrently with `asyncio.Semaphore(config.processing.max_concurrent)`.
  - Aggregate `stage_a_context.json`.
  - Run Stage B analyzers concurrently after Stage A completes.
  - Generate `executive_summary.md` and metadata; emit all notifications.
- Web/Celery Orchestrator (`src/app/orchestration.py` + `src/app/celery_app.py`)
  - Celery task per pipeline run; emit Socket.IO events to front-end for progress UI.
  - Same lifecycle events as CLI, reusing NotificationManager.
- Error handling:
  - Any analyzer error is captured, logged, and surfaced via notifications and API response.
  - Pipeline error triggers `pipeline_error` event; partial results preserved.

---

## 6) Web Interface Plan (High-Level)

- Frontend: Vanilla JS + Tailwind CSS, Marked.js for markdown, Highlight.js for code blocks.
- Main views:
  - Input screen: transcript text area and drag/drop upload
  - Analyzer selection per stage (checkboxes), select/deselect all
  - Options toggles for Stage B context/transcript inclusion in Final
  - Progress screen: per-analyzer cards with states (Pending/Processing/Completed/Error), token/time stats
  - Results tabs: Stage A, Stage B, Final; markdown viewer; export buttons (md/json/clipboard)
- WebSocket/Socket.IO:
  - Receive progress events with timing/token counts and statuses
  - Display live logs and enable “View result” when each analyzer completes

---

## 7) Notifications and Proactive Callbacks

- NotificationManager API:
  - `pipeline_started(run_id, meta)`
  - `stage_started(run_id, stage, analyzer)`
  - `stage_completed(run_id, stage, analyzer, stats)`
  - `pipeline_completed(run_id, summary)`
  - `pipeline_error(run_id, error, meta=None)`
- Channels:
  - SlackChannel (webhook)
  - WebhookChannel (generic POST for custom integrations)
  - DesktopChannel (macOS say/terminal-notifier or console fallback)
  - FileChannel (JSONL writer) — primary for autonomous verification
- Event Schema (minimum fields):
  - event, run_id, timestamp, status, output_dir, stage name/analyzer (where applicable), token/timing stats, link to local run folder (file://)
- Autonomy requirement:
  - The FileChannel-based test must verify completion without internet or external services.

---

## 8) Performance Targets and Strategy

- Targets (PRD):
  - Initial API response (ack): < 2s
  - Full analysis: < 60s for a 10,000-word transcript
  - 10 concurrent users
- Strategy:
  - Parallelize Stage A and Stage B with bounded concurrency
  - Enforce Stage B context token budget
  - Cache analyzer results for 24h (TODO in Phase 2)
  - Collect timing/token stats per analyzer and entire run; report in metadata and executive summary

---

## 9) Security, Privacy, Reliability

- Security:
  - API key in `.env`; never logged
  - Input sanitization and file-type checks on upload
  - Rate limit: 10 analyses/hour/session (web)
- Privacy:
  - No permanent storage of raw transcripts (default); only per-run ephemeral files
  - Optional export only on user request
- Reliability:
  - Retries on LLM calls; graceful error notifications
  - Redis required for Celery/SocketIO; fallback for CLI path is in-process

---

## 10) Testing Strategy (Real GPT, plus autonomous where required)

- Unit Tests (selective, with mocks):
  - Prompt assembly and Jinja validation
  - Token budgeting/trimming logic
  - Config/env parsing (pydantic)
- Integration Tests (real GPT calls):
  - Stage A-only smoke on sample transcript
  - Stage B uses aggregated context from Stage A (validate ACH matrix shape, etc.)
  - Final stage: meeting notes and composite note presence and formatting
- End-to-End (CLI pipeline with notifications):
  - Run full pipeline with FileChannel enabled
  - Validate run directory structure, metadata.json, and executive_summary.md
- Web E2E (Celery + Socket.IO):
  - Launch stack via docker-compose; run a real analysis from the UI
  - Observe live progress and export outputs
- Performance Benchmarks:
  - Measure wall-clock and tokens across analyzers; tune `max_concurrent` and Stage B budget
- Autonomous Proactive Callback Test (FileChannel):
  1) Set environment:
     - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED=true`
     - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS=file`
     - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH=output/notifications.jsonl`
  2) Execute: `python scripts/test_parallel_pipeline.py --notify file --file-path output/notifications.jsonl`
  3) Verify:
     - Parse `output/notifications.jsonl` to find a line where `event=="pipeline_completed"`, `status=="completed"`
     - Assert `run_id` matches the created run directory in `output/runs/`
     - Assert `output_dir` exists and contains `metadata.json` and `final/executive_summary.md`
  4) Pass/Fail: Test passes if such a line is found and assertions hold; otherwise fail with diagnostic log dump.
- Optional: Add `scripts/verify_notifications.py` to perform step (3) automatically (see Milestone M6).

---

## 11) Milestones, Deliverables, Acceptance Criteria

- M1: Stage A/B Parallelization Hardening (Complete if already present, validate with benchmark)
  - Deliverables: updated orchestrator docs, timing charts, `metadata.json` includes tokens/time
  - Acceptance: Stage A and Stage B run concurrently post-A completion with bounded concurrency; stable on 3x runs
- M2: Stage B Context Budget Enforcement (Complete)
  - Deliverables: enforcement in `base_analyzer.py`, config default, docs
  - Acceptance: Prompt size trims to configured `stage_b_context_token_budget` without template errors
- M3: NotificationManager Integrated Everywhere (Complete)
  - Deliverables: Notifier channels, unified event schema, CLI/Celery wired
  - Acceptance: All runners emit start/stage/complete/error events; Slack/Webhook tested via dry run; Desktop prints/logs locally
- M4: Final Stage Outputs (Meeting Notes, Composite Note)
  - Deliverables: Implement final stage analyzers and templates
  - Acceptance: Both files generated in `final/`, include context links and Obsidian-friendly formatting
- M5: Web UI Progress and Exports
  - Deliverables: Live per-analyzer status, token/time stats; export md/json/clipboard
  - Acceptance: Socket.IO events accurately drive UI state; export buttons work and produce correct files
- M6: Autonomous Proactive Notification Test (Complete)
  - Deliverables: `scripts/verify_notifications.py` that:
    - Runs pipeline with FileChannel configured
    - Parses `output/notifications_*.jsonl`
    - Asserts `pipeline_completed` with valid run link and artifacts
  - Acceptance: Single command exits 0 on success; validated with real GPT calls and JSONL verification
- M7: Run Completion Sentinel and Machine-Readable Summary (Complete)
  - Deliverables: `COMPLETED` sentinel file and `final_status.json` in run root (async: `output/runs/run_*`, web/Celery: `output/jobs/{jobId}/`)
  - Acceptance: Summary includes counts, analyzers, timings (cpu_time_seconds + wall_clock_seconds), tokens, and status; sentinel exists only on success
- M8: Performance Target Check
  - Deliverables: Benchmark report on 10,000-word transcript with concurrency tuning
  - Acceptance: Median end-to-end <= 60s; document settings used (model, budgets, concurrency)
- M9: Documentation and Ops
  - Deliverables: Updated `docs/USER_GUIDE.md`, `docs/WEB_INTERFACE_GUIDE.md`, `docs/DOCKER_GUIDE.md`
  - Acceptance: New developer can run stack and complete an analysis in < 10 minutes following docs

---

## 12) Risks and Mitigations

- LLM Variability: Use deterministic temperature for analyzers demanding structure; validate JSON outputs.
- Token Overruns: Hard budget Stage B; consider chunking/summarization fallback for extremely large Stage A contexts.
- Redis/Celery Failures: Provide CLI path as fallback; include health checks in docker-compose.
- Cost Controls: Log token usage per run; optional environment caps to abort if expected cost exceeded.

---

## 13) Configuration Reference (ENV via Pydantic)

- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`
- Processing: `MAX_CONCURRENT`, `STAGE_B_CONTEXT_TOKEN_BUDGET`
- Notifications:
  - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED` (bool)
  - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS` (csv: slack,webhook,desktop,file)
  - `TRANSCRIPT_ANALYZER_SLACK_WEBHOOK_URL`
  - `TRANSCRIPT_ANALYZER_WEBHOOK_URL`
  - `TRANSCRIPT_ANALYZER_DESKTOP_ENABLED` (bool)
  - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH`
- Web/Celery:
  - `REDIS_URL`, `FLASK_SECRET_KEY`, session settings
  - Guards for `src/app/__init__.py` to avoid side-effects in CLI runs

---

## 14) Concrete Next Actions (Engineering)

1) Validate current orchestrators produce full lifecycle notifications for CLI and Celery paths.  
2) Implement Final Stage analyzers and templates; write outputs to `final/`.  
3) Add `COMPLETED` sentinel + `final_status.json` with machine-readable summary.  
4) Implement autonomous notification verification script (`scripts/verify_notifications.py`) per Section 10.  
5) Run performance benchmarks on 10k-word transcript; tune `MAX_CONCURRENT` and `STAGE_B_CONTEXT_TOKEN_BUDGET`.  
6) Update docs and add a “one command” smoke for web via docker-compose.  

---

## 15) Acceptance Checklist (per-run)

- [ ] Stage A results present (all selected analyzers)  
- [ ] `stage_a_context.json` created and valid  
- [ ] Stage B results present (all selected analyzers)  
- [ ] Final outputs exist (meeting_notes.md, composite_note.md)  
- [ ] `metadata.json` contains tokens and timings  
- [ ] Notifications emitted (at least `pipeline_started` and `pipeline_completed`)  
- [ ] COMPLETED sentinel present in run/job directory  
- [ ] `final_status.json` present and valid (run_id, status, tokens, cpu_time_seconds, wall_clock_seconds, timestamps)  
- [ ] Autonomous test finds `pipeline_completed` in JSONL file with valid run link  
- [ ] Performance within target budget or report filed with tuning recommendations  

---

End of plan.
