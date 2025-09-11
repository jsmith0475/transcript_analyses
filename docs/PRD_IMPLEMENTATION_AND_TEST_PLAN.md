# PRD-Aligned Implementation and Test Plan
Transcript Analysis Tool — Execution Blueprint (v1.0)

Status: Active
Date: 2025-09-07
Owner: Engineering

This is the authoritative plan we will work against to develop, code, and test the Transcript Analysis Tool described in PRD_Transcript_Analysis_Tool.md. This plan maps PRD requirements to concrete architecture, tasks, deliverables, and validation steps. The application will run with real OpenAI GPT calls using the key provided in .env.

-------------------------------------------------------------------------------

1. Goals and Non-Goals

1.1 Goals
- Implement a three-stage analysis pipeline (Stage A, Stage B, Final) with parallel execution within each stage and sequential chaining across stages.
- Provide a real-time web UI to submit transcripts (text/upload), track analyzer progress, and view/export results.
- Persist per-job status/results in Redis and export final outputs as Obsidian-friendly Markdown and JSON.
- Execute real OpenAI GPT calls with configured models, track token usage and timing, and enforce PRD performance, reliability, and privacy constraints.
- Deliver a robust, race-free orchestration model using Celery chords/chains with authoritative fan-in callbacks that persist stage results before emitting completion.

1.2 Non-Goals (Phase 1 / MVP)
- Multi-tenant, SSO, advanced permissions, and audit logging (Phase 4).
- Cross-transcript trend analysis and ML-driven analyzer selection (Phase 3).
- Persistent database (PostgreSQL) beyond ephemeral job state in Redis (future).

-------------------------------------------------------------------------------

2. Current State Summary (Repository Snapshot)

- Backend: Flask API with Socket.IO; Celery workers; Redis as broker/result store/session/state.
- Orchestration: Parallel per-stage via Celery chords, chained across stages; final stage synthesizes and writes meeting notes and composite note.
- UI: Vanilla JS + Tailwind; WebSocket progress; Start button/controls disable-while-running implemented.
- Prompts: Organized under prompts/ with Stage A, Stage B, and Final templates.
- LLM Client: src/llm_client.py integrates OpenAI; model selection present; .env template exists.
- Docker: docker-compose.yml for app, worker, redis; port 5001 exposed.
- Scripts: Extensive test and verification scripts for stages, API, and UI.

This plan formalizes deliverables, fills PRD gaps (schemas, contracts, metrics), and defines tests and acceptance criteria.

-------------------------------------------------------------------------------

3. Architecture and Data Flow

3.1 High-Level
- Client submits transcript (text or file).
- API enqueues Stage A chord (parallel analyzers). Fan-in callback persists authoritative Stage A mapping and signals completion.
- Stage B chord runs in parallel using Stage A context. Fan-in callback persists Stage B mapping and signals completion.
- Final stage (chain) runs synthesizers (Meeting Notes, Composite Note) and writes outputs. Completion persists final status, emits job.completed, and saves files for export.

3.2 Backend Components
- Flask app (src/app/__init__.py, api.py, sockets.py): REST + WebSocket.
- Celery app (src/app/celery_app.py), orchestration (src/app/parallel_orchestration.py).
- LLM client (src/llm_client.py) with model config and usage tracking.
- Analyzers (src/analyzers/*) split by stages; each reads prompt, feeds model, returns structured result.
- Status/State in Redis: job document keyed by job_id.

3.3 Frontend Components
- HTML template (src/app/templates/index.html), JS modules (api.js, ws.js, ui.js, main.js).
- Real-time progress tiles, token/time display, results tabs (Stage A, Stage B, Final), exports.

3.4 Data Flow Contracts
- Stage A analyzers input: { transcript }
- Stage B analyzers input: { context: combined_stage_a_results }
- Final analyzers input: { context: combined_stage_a_results, transcript?: optional }
- Results persisted per analyzer with standardized schema.

-------------------------------------------------------------------------------

4. Environment, Configuration, and Secrets

4.1 Environment Variables (.env)
- OPENAI_API_KEY=...
- OPENAI_BASE_URL (optional; defaults to OpenAI)
 - OPENAI_MODEL_STAGE_A=gpt-5-nano
 - OPENAI_MODEL_STAGE_B=gpt-5-nano
 - OPENAI_MODEL_FINAL=gpt-5-nano
- OPENAI_TEMPERATURE=0.2
- APP_HOST=0.0.0.0
- APP_PORT=5001
- REDIS_URL=redis://redis:6379/0
- SESSION_SECRET=change-me
- MAX_UPLOAD_MB=10
- RATE_LIMIT_ANALYSES_PER_HOUR=10
- CACHE_TTL_HOURS=24
- LIVE_MODE=true  (if false, a dry-run stub can be used in certain tests)

4.2 Model Policy
 - Default fast path: gpt-5-nano for all analyzers to meet throughput/cost targets.
- Optional quality path: allow per-stage overrides (Stage B/Final can use gpt-4o).
- Strict token budgeting: prompts trimmed and context summarized when needed.

4.3 Token/Time Tracking
- LLM client must record usage.prompt_tokens, usage.completion_tokens, usage.total_tokens and latency per call.
- Aggregate per analyzer, per stage, per job.

-------------------------------------------------------------------------------

5. API and WebSocket Contracts

5.1 REST Endpoints
- POST /api/analyze
  - Body: { transcript?: string, fileId?: string, options?: { includeTranscriptInFinal: boolean, transcriptInclusionMode: "full"|"summary", transcriptMaxChars?: number, selectedAnalyzers?: { stageA?: string[], stageB?: string[], final?: string[] } } }
  - Returns: { jobId: string, status: "queued" }
- GET /api/status/:jobId
  - Returns:
    {
      jobId,
      status: "queued"|"running"|"completed"|"error",
      startedAt?, completedAt?,
      usage?: { totalTokens, totalCostUsd, perAnalyzer: { [key]: { tokens, costUsd, durationMs } } },
      stageA?: { [analyzerName]: AnalyzerResult },
      stageB?: { [analyzerName]: AnalyzerResult },
      final?: {
        meetingNotes?: { filePath?, raw_output? },
        compositeNote?: { filePath?, raw_output? }
      },
      error?: { message, traceId? }
    }
- GET /api/job-file
  - Query: jobId=...&type=final&name=meeting_notes.md|composite_note.md
  - Returns: text/markdown or 404 if not available.
  - Inter‑stage context files available via `path` parameter:
    - `intermediate/stage_b_context.txt` (Stage A → Stage B)
    - `final/context_combined.txt` (Stage B → Final)

UI Options Coverage (Test)
- Stage B Options: Toggle includeTranscript on/off and verify the Stage A → Stage B panel shows/hides “TRANSCRIPT (included preview)”. Confirm prompt size capped by maxChars.
- Final Options: Toggle includeTranscript on/off and verify the Stage B → Final panel shows/hides the transcript preview. Confirm Final prompt size capped by maxChars.
- POST /api/prompt
  - Body: { stage: "A"|"B"|"Final", analyzer: string, content: string }
  - Persists prompt override; returns { ok: true }.
- GET /api/prompt?stage=...&analyzer=...
  - Returns current prompt content.
- POST /api/prompt/reset
  - Resets prompt to default for analyzer.

5.2 WebSocket Events (namespace: /progress)
- From server:
  - job.started { jobId }
  - analyzer.started { jobId, stage: "stage_a"|"stage_b"|"final", analyzer }
  - analyzer.completed { jobId, stage, analyzer, usage: { tokens, durationMs } }
  - stage.completed { jobId, stage: "stage_a"|"stage_b"|"final" }
  - job.completed { jobId }
  - job.error { jobId, message }
- From client:
  - subscribe { jobId }
  - unsubscribe { jobId }

-------------------------------------------------------------------------------

6. Data Schema and Storage

6.1 Job Document (Redis JSON or hash)
key: job:{jobId}
{
  jobId,
  status,                // queued|running|completed|error
  createdAt, startedAt?, completedAt?,
  options: { includeTranscriptInFinal, transcriptInclusionMode, transcriptMaxChars, selectedAnalyzers },
  usage: {
    totalTokens: number,
    totalCostUsd: number,
    perAnalyzer: {
      [stage.analyzerKey]: { promptTokens, completionTokens, totalTokens, durationMs, model }
    }
  },
  stageA: { [analyzerName]: AnalyzerResult },
  stageB: { [analyzerName]: AnalyzerResult },
  final: {
    meetingNotes?: { filePath?, raw_output? },
    compositeNote?: { filePath?, raw_output? }
  },
  error?: { message, traceId? }
}

6.2 File Layout
- tmp/jobs/{jobId}/final/meeting_notes.md
- tmp/jobs/{jobId}/final/composite_note.md
- tmp/jobs/{jobId}/logs/*.log (optional)
- No permanent transcript storage; transient in memory or ephemeral file during job.

-------------------------------------------------------------------------------

7. Orchestration and Concurrency Model

7.1 Execution Graph
- chain(
    chord(StageA tasks[], complete_stage_a(jobId, stage_a_list))),
    chord(StageB tasks[], complete_stage_b(jobId, stage_b_list, stage_a_results))),
    chain(Final tasks[] in series, finalize_job(jobId))
  )

7.2 Race-Free Fan-in
- Stage fan-in callbacks receive ordered results list. Build authoritative { analyzerName: result } mapping by zipping stage list with results. Persist immediately before emitting stage.completed.
- Do not re-fetch flaky in-progress results from Redis during fan-in.

7.3 Non-Blocking Semantics
- Use self.replace for chords to avoid result.get/join.
- Errors bubble into job.error with persisted error state and WS emit.

7.4 Parallelism Controls
- Set concurrency via Celery worker pools; cap concurrent job count to meet PRD performance and token rate limits.
- Each job’s Stage A/B run in parallel; Final runs in series to ensure proper file writes.

-------------------------------------------------------------------------------

8. Prompt Management and LLM Policy

8.1 Prompt Sources
- Default prompts under prompts/... directory.
- Override flow via /api/prompt endpoints; persist overrides to disk under prompts_overrides/ mirroring structure; at runtime, prefer override if present.

8.2 Template Variables
- Stage A: {transcript}
- Stage B: {context}
- Final: {context}, {transcript? based on options}

8.3 Token Budget and Summarization
- Before Stage B and Final, compute serialized context size. If nearing model limit:
  - Apply schema-aware compaction (e.g., keep top-N items per analyzer).
  - Optionally run a summarizer prompt (fast model) to reduce context.

8.4 Retry and Backoff
- For 429/5xx: exponential backoff with jitter (e.g., 0.5s,1s,2s,4s; max 4 tries).
- Idempotency: analyzer task recomputes from inputs; safe to retry. Persist only once in fan-in.

-------------------------------------------------------------------------------

9. UI/UX Implementation Plan

9.1 Main Interface
- Transcript input, file upload with drag-and-drop (10MB limit; accept .txt/.md/.markdown).
- Analyzer selection per stage, select/deselect all.
- Start button disabled/greyed while running; re-enabled on completion/error/reset.
- Real-time tiles with states: Pending, Processing, Completed, Error.
- Time and token display per analyzer and totals.
- Results tabs: Stage A, Stage B, Final (Meeting Notes, Composite Note) with Markdown rendering and syntax highlighting.
- Export buttons: Markdown and JSON; Copy to clipboard.

9.2 Robust Final Loader (done/verify)
- Files-first fetch via /api/job-file; fallback to inline raw_output in /api/status; retries with backoff; auto-activate Final tab when available.

9.3 Accessibility and Responsiveness
- Tailwind utility classes for focus states and color contrast (WCAG AA).
- Keyboard navigation for Start, tabs, and exports.

-------------------------------------------------------------------------------

10. Security, Privacy, and Rate Limiting

10.1 Input Validation
- Sanitize transcript text; strip invalid UTF-8; enforce size max.
- Validate file type and size server-side.

10.2 Privacy
- Do not store transcripts beyond job lifetime; no durable DB by default.
- Redact secrets in logs; never log transcript content verbatim in production mode.

10.3 Rate Limiting
- Per-session token bucket in Redis: allow RATE_LIMIT_ANALYSES_PER_HOUR per session. Enforce on /api/analyze.

10.4 HTTPS (Production)
- Terminate TLS at reverse proxy; ensure secure cookies and HSTS headers (prod docs/runbook).

-------------------------------------------------------------------------------

11. Observability: Logging, Metrics, Tracing

11.1 Logging
- Loguru for structured logs at app and worker; include jobId, stage, analyzer, durationMs, tokens, model, status transitions.

11.2 Metrics
- Counters: analyses_started, analyses_completed, analyses_failed.
- Histograms: analyzer_duration_ms by stage/analyzer; tokens_per_call; job_total_duration.
- Export simple JSON metrics endpoint or integrate lightweight Prom client (optional).

11.3 Trace IDs
- Generate per job traceId (same as jobId) and include in all logs.

-------------------------------------------------------------------------------

12. Testing Strategy

12.1 Unit Tests (pytest)
- Analyzers: prompt loading, variable substitution, result schema validation.
- LLM client: usage accounting, retry/backoff logic (can mock for unit tests).
- API: input validation, rate limiting, file handling.

12.2 Integration Tests (live GPT enabled with small inputs)
- Stage A chord parallelism: verify all selected analyzers complete; usage recorded.
- Stage B chord with Stage A context: verify meta-analyses produce structured outputs.
- Final stage: verify Markdown files exist and /api/job-file serves content.
- Orchestration race conditions: confirm stage.completed emitted after authoritative persistence.

12.3 End-to-End (Web UI)
- Launch stack; hard-refresh browser; run a sample transcript through full pipeline.
- Validate Start disabled state and re-enable behavior; status tiles transitions; Final tab content availability; exports functioning.

12.4 Performance and Load
- 10,000-word transcript: ensure < 60s average on default model config and worker pool size; document results and tuning knobs.
- 10 concurrent analyses: validate queueing and acceptable degradation; no job starvation.

12.5 Reliability/Recovery
- Induce transient OpenAI 429/5xx via fault injection/mock to validate retry behavior.
- Simulate worker crash mid-stage: ensure job error surfaces and UI recovers.

12.6 Security
- Upload fuzz tests for file validation; transcript sanitizer tests.
- Rate limit tests: exceeding hourly cap returns 429 with retry-after.

-------------------------------------------------------------------------------

13. Performance Plan

- Optimize prompts to minimize tokens while preserving structure.
- Cap included transcript chars per PRD options; enable summary mode for Final.
- Celery pool tuning: default concurrency= (CPU cores) for worker; max_concurrent jobs configurable (e.g., 3) to manage costs and API rate.
- Cache results by hash: key on analyzer+prompt hash+transcript hash for 24h to skip recomputation; invalidate on prompt change.

-------------------------------------------------------------------------------

14. Deployment and Runbook

14.1 Local (Docker)
- docker compose up -d --build
- Visit http://localhost:5001
- Health: GET /api/health (if exposed) or check logs show “status: ok”

14.2 Secrets
- Copy .env.template → .env and fill OPENAI_API_KEY and SESSION_SECRET.

14.3 Restart Procedure
- docker compose restart app worker
- Validate with scripts/test_api.py and scripts/test_web_ui.py

14.4 Production Notes
- Reverse proxy (nginx/Traefik), TLS termination, log shipping, metrics scraping.
- Horizontal scale by increasing worker replicas; sticky sessions not required.

-------------------------------------------------------------------------------

15. Acceptance Criteria (Mapped to PRD)

- Functional
  - Stage A (4 analyzers) run in parallel and persist individual intermediate results.
  - Stage B (4 analyzers) run in parallel on combined Stage A context; results persisted.
  - Final stage produces Meeting Notes and Composite Note; available in UI and via /api/job-file and export.
  - UI supports text input & file upload (.txt/.md/.markdown up to 10MB).
  - Real-time status tiles with correct state transitions; Start disabled while processing.
  - Token and time per analyzer displayed; totals shown at job level.
- Non-Functional
  - Complete analysis < 60s for 10,000-word transcript (baseline target).
  - Support 10 simultaneous analyses with graceful degradation.
  - No long-term transcript storage; clear rate limiting enforced (10/hour/session).
  - Logs include usage and durations; retries on 429/5xx implemented.

-------------------------------------------------------------------------------

16. Work Breakdown Structure (WBS) and Deliverables

A. Environment & Config
- A1 Finalize .env schema and defaults; document in DOCKER_GUIDE.md
- A2 Ensure src/llm_client.py reads env, supports per-stage models, temperature
- A3 Implement usage tracking and per-call timers in LLM client

B. Backend API & Status
- B1 Validate/extend /api/analyze payload options (Final transcript inclusion settings)
- B2 Rate limiting middleware (session-scoped bucket in Redis)
- B3 Define and enforce Job Document schema; add JSON schema validator for internal use
- B4 Implement /api/prompt CRUD (get/update/reset) and disk persistence for overrides

C. Orchestration
- C1 Confirm Stage A/B chords use ordered lists; fan-in persists authoritative mappings
- C2 Ensure self.replace usage and removal of result.get/join
- C3 Final stage serial chain writes meeting_notes.md and composite_note.md; finalize_job updates status

D. Analyzers & Prompts
- D1 Validate each analyzer loads correct prompt and substitutes variables
- D2 Implement schema validators for analyzer outputs (Pydantic models in src/models.py)
- D3 Caching layer: result-by-hash with TTL=24h

E. UI/UX
- E1 Confirm disable/enable controls across job lifecycle; address edge cases (error/reset)
- E2 Implement token/time displays per analyzer and totals
- E3 Final loader (files-first, inline fallback, retries) verified
- E4 Export buttons (MD, JSON, Copy) and download endpoints

F. Observability
- F1 Structured logs with jobId, stage, analyzer, model, tokens, durations
- F2 Minimal metrics endpoint or log-based counters; document collection

G. Security & Privacy
- G1 File upload validation; transcript size enforcement
- G2 PI/secret redaction in logs; production logging policy
- G3 HTTPS guidance and secure headers (docs)

H. Testing
- H1 Unit tests (analyzers, LLM client, API validation, rate limiting)
- H2 Integration tests (Stage A/B chords, Final outputs)
- H3 E2E UI tests (status, disable states, final outputs, exports)
- H4 Performance tests (10k words; 10 concurrent jobs)
- H5 Reliability tests (retries; worker crash simulation)

I. Delivery
- I1 Documentation updates (ARCHITECTURE.md, WEB_INTERFACE_GUIDE.md, RUNBOOK)
- I2 Final acceptance validation run and sign-off packet (evidence, timings, logs)

-------------------------------------------------------------------------------

17. Detailed Test Matrix

Unit
- Prompt Variable Substitution: Stage A/B/Final templates render without missing variables
- Result Schemas: say_means, perspective_perception, premises_assertions, postulate_theorem; competing_hypotheses, first_principles, determining_factors, patentability; final outputs lightweight schema (title/sections/actions)

Integration
- Stage A Parallelism: Start → ensure 4 analyzer completed events and persisted mapping; check no Pending tiles
- Stage B Parallelism: Verify fan-in uses Stage A context; persisted mapping matches analyzers selected
- Final Outputs: Files created and /api/job-file returns 200; /api/status has raw_output fallback

E2E
- Start Button Behavior: Disabled immediately on start, shows “Running…”, re-enabled on job.completed and job.error and on Reset
- Tile States: Pending → Processing → Completed with correct stage normalization keys
- Exports: Download MD and JSON; copy to clipboard success message

Performance
- 10k-word transcript: log total duration, tokens; ensure < 60s average (document CPU/worker config); adjust concurrency and model as needed

Reliability
- Inject 429: verify exponential backoff; eventual success or job.error with clear message
- Worker Crash: kill one worker mid-job; ensure job.error or recovery with clear state

Security
- Upload invalid types/oversized: 400 with friendly error; server stable
- Rate limit exceeded: 429 with Retry-After header and status in UI

-------------------------------------------------------------------------------

18. Implementation Checklist (per PRD)

- Transcript Input (text/upload): implemented and validated
- Analyzer Selection per Stage: UI checkboxes and select/deselect all
- Stage A: parallel execution; structured outputs persisted
- Stage B: parallel execution; meta-analysis persisted
- Final Stage: synthesizers produce Meeting Notes / Composite Note
- Real-time Progress: WebSocket events and UI tiles
- Token/Time Tracking: displayed per analyzer and totals
- Prompt Management: in-browser edit, save, reset; stage-scoped variables enforced
- Exports: Markdown, JSON, copy to clipboard
- Privacy/Rate-Limiting: enforced; no durable storage of transcripts
- Performance: run and document targets; provide tuning guidance

-------------------------------------------------------------------------------

19. Timeline and Milestones (indicative)

- Week 1: Config, API contracts, rate limiting, usage tracking (A,B); validate chords (C1,C2)
- Week 2: Prompt CRUD, analyzers schema validation, caching (D,B4,D3); UI token/time (E2)
- Week 3: Final outputs hardening, export endpoints, Final loader verification (C3,E3,E4)
- Week 4: Observability, security hardening, performance/reliability tests (F,G,Perf/Reliab)
- Week 5: E2E polish, docs, acceptance sign-off (H,I)

-------------------------------------------------------------------------------

20. Run Commands (Live Mode with Real GPT)

- Local stack: docker compose up -d --build
- Smoke test API: python scripts/test_api.py
- Full pipeline test: python scripts/test_full_pipeline.py
- Parallelism test: python scripts/test_parallel_pipeline.py
- Web UI test: python scripts/test_web_ui.py
- Monitor pipeline: python scripts/monitor_pipeline.py

Ensure .env has OPENAI_API_KEY and LIVE_MODE=true. Use gpt-5-nano by default for cost/speed.

-------------------------------------------------------------------------------

21. Risk Register (Implementation-Focused)

- OpenAI Rate Limits: implement backoff and per-session analysis cap; consider queueing jobs when reaching near-global quotas.
- Token Overflows: implement summarization and context compaction before Stage B/Final.
- Race Conditions: authoritative fan-in persistence before emits; avoid re-reading in-flight keys.
- Cost Spikes: Prefer mini models; show usage/cost in status; cap concurrent jobs.

-------------------------------------------------------------------------------

22. Acceptance Validation Script (What we will execute to sign off)

1) Restart stack with fresh .env and clear Redis; docker compose up -d --build
2) Load UI; paste a 10–20 paragraph transcript; select all analyzers; Start
3) Observe:
   - Start disabled; tiles move to Processing; tokens/time accumulate
   - Stage A completes; Stage B completes; Final completes
4) Final Tab shows Meeting Notes and Composite Note; both downloadable; /api/status includes raw_output fallback
5) Repeat with file upload (.md) 8–10MB; verify processing under 60s average (document)
6) Run scripts/test_parallel_pipeline.py to confirm in logs that chords run in parallel and fan-in persists authoritative mappings
7) Trigger rate limit path by 11th run in 1 hour (artificially lower cap for test); expect 429 and UI message
8) Produce acceptance packet: logs, timings, token usage, outputs, screenshots

-------------------------------------------------------------------------------

Appendices

A. Analyzer Naming Keys
- Stage A: say_means, perspective_perception, premises_assertions, postulate_theorem
- Stage B: competing_hypotheses, first_principles, determining_factors, patentability
- Final: meeting_notes, composite_note

B. Cost Estimation
- Log per-call tokens and infer cost using model pricing table; aggregate to per-job cost.

C. JSON Schemas (high-level)
- AnalyzerResult minimal: { title?: string, items?: any[], text?: string, metadata?: object }
- Final outputs minimal: { filePath?: string, raw_output?: string }
