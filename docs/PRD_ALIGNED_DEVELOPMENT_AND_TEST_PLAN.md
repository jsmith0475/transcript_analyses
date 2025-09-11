# PRD-Aligned Development, Coding, and Test Plan
Transcript Analysis Tool

Version: 1.0  
Date: 2025-09-07  
Owner: Engineering

This plan operationalizes the PRD into concrete deliverables, milestones, acceptance criteria, and tests. It maps directly to the current codebase and infrastructure, and will be executed with real OpenAI GPT calls via .env configuration.

---

## 1) Goals and Non-Goals

- Goals
  - End-to-end multi-stage (A → B → Final) analysis pipeline with parallelization within stages using Celery chords/groups and chain sequencing across stages.
  - Real-time progress and status reporting over WebSocket/Socket.IO with accurate visual indicators.
  - Robust prompt management (editable, resettable) with clear template-variable semantics for each stage.
  - Obsidian-optimized outputs (Meeting Notes, Composite Note), with export to .md and .json.
  - Secure, resilient, performant baseline meeting PRD SLA targets for typical transcripts.

- Non-Goals (for this phase)
  - Multi-tenant enterprise controls (SSO, audit logs)
  - Cross-transcript analytics and ML-based analyzer selection
  - Persistent database storage (will use filesystem + Redis in this phase)

---

## 2) Architecture and Current Code Mapping

- Backend Stack
  - Flask REST API + Flask-SocketIO for WebSocket updates
  - Celery workers with Redis broker/result backend
  - OpenAI LLM via src/llm_client.py (reads .env OPENAI_API_KEY, model, base_url if configured)

- Frontend Stack
  - Vanilla JS (ES6+) + Tailwind CSS
  - Socket.IO client for real-time updates
  - Marked.js + highlight.js for Markdown rendering and syntax highlighting

- Orchestration (parallel per stage, sequential across stages)
  - src/app/parallel_orchestration.py (canonical)
    - Stage A: chord(group(stage A analyzers), complete_stage_a)
    - Bridge: run_stage_b_after_a uses self.replace(chord(...)) to avoid blocking
    - Stage B: chord(group(stage B analyzers), complete_stage_b)
    - Final: run_final_stage(all_results, job_id, transcript, selections)
    - Finalize: finalize_pipeline → writes final_status.json and emits completion
  - Supporting modules
    - src/app/api.py (REST endpoints)
    - src/app/sockets.py (WebSocket events)
    - src/llm_client.py (OpenAI calls)
    - src/analyzers/* (Stage A, Stage B, Final analyzers)
    - src/config.py (configuration)
  - Docker
    - docker-compose.yml: services app, worker, redis; host port mapping 5001 → app:5000

- Data Flow (aligned with PRD §5.1.3)
  1) Input → transcript text or upload (.txt/.md; up to 10 MB)
  2) Stage A analyzers → produce intermediate outputs (independent, parallel)
  3) Stage A aggregation → context for Stage B
  4) Stage B analyzers → meta-analysis (parallel)
  5) Final stage → meeting_notes + composite_note (uses Stage A context + transcript as configured)
  6) Output → filesystem job directory + WebSocket events + API readable

- Output Organization
  - output/jobs/<jobId>/
    - stageA/<analyzer>.json|.md
    - stageB/<analyzer>.json|.md
    - final/meeting_notes.md, composite_note.md
    - final_status.json
    - timings.json, tokens.json (optional metrics)

---

## 3) Environment and Configuration (.env)

- Required
  - OPENAI_API_KEY=<your key>
- Optional/Recommended
  - OPENAI_MODEL=gpt-4.1 (or gpt-4o, or configured per openai/gpt-5.md)
  - OPENAI_BASE_URL=https://api.openai.com/v1 (override for gateways)
  - REDIS_URL=redis://redis:6379/0
  - FLASK_ENV=production (or development)
  - APP_PORT=5000 (container internal)
  - HOST_PORT=5001 (docker-compose mapped host port)
  - RATE_LIMIT_PER_HOUR=10
  - INCLUDE_TRANSCRIPT_IN_FINAL=true|false (UI overrides at runtime)
  - MAX_UPLOAD_MB=10
  - CACHE_TTL_HOURS=24

- Start/Restart (Runbook)
  - docker-compose up -d (first run)
  - docker-compose restart app (restart web server)
  - docker-compose restart worker (restart Celery workers)
  - Confirm at http://localhost:5001

---

## 4) API and WebSocket Contracts

- REST Endpoints
  - POST /api/analyze
    - body: { transcriptText?: string, fileId?: string, selection: { stageA: string[], stageB: string[], final: string[] }, settings: { includeTranscriptInFinal: boolean, transcriptInclusionMode: "full"|"summary", transcriptCharLimit?: number } }
    - returns: { jobId: string }
  - GET /api/status/<jobId>
    - returns: { jobId, stage: "queued"|"running"|"finalizing"|"done"|"error", progress: { A: { analyzer: "pending|processing|done|error", ... }, B: {...}, Final: {...} }, timings, tokens, error? }
  - GET /api/results/<jobId>
    - returns aggregated results JSON and links to markdown exports
  - Prompt management (to add as needed)
    - GET /api/prompts?stage=A|B|Final
    - GET /api/prompts/<id>
    - PUT /api/prompts/<id> { content }
    - POST /api/prompts/<id>/reset

- WebSocket Events (server → client)
  - job_started { jobId, startTime }
  - stage_a_progress { jobId, analyzer, status: "pending|processing|done|error", startedAt?, finishedAt?, tokens? }
  - stage_b_progress { ... }
  - final_progress { analyzer: "meeting_notes"|"composite_note", ... }
  - job_completed { jobId, finishedAt, summary }
  - job_error { jobId, errorMessage }

- Frontend Visual States
  - Pending (gray), Processing (spinner), Completed (green check), Error (red X)
  - Token/time display per analyzer and cumulative

---

## 5) Prompt Management

- Template Variables
  - Stage A: {transcript}
  - Stage B: {context} (combined Stage A results)
  - Final: {context} + {transcript} (optional per settings)
- Files (current)
  - prompts/stage a transcript analyses/*.md
  - prompts/stage b results analyses/*.md
  - prompts/final output stage/*.md
- Requirements
  - In-browser editing with PUT /api/prompts/<id>
  - Reset to default via POST /api/prompts/<id>/reset
  - Persist to filesystem; validate template variables on save

---

## 6) Performance, Reliability, Security

- Performance Targets (PRD)
  - Initial response < 2s
  - Complete analysis < 60s for 10,000 words (with parallelization)
  - 10 concurrent analyses
- Techniques
  - Celery chord/group fan-out per stage; chain across stages
  - Prompt size optimization; summarized transcript for Final when configured
  - Optional caching of analyzer results for 24h by content hash + prompt version
- Reliability
  - Retries for transient LLM/Redis errors (exponential backoff)
  - No blocking .get() inside tasks; use self.replace and callbacks
  - Graceful error propagation to WebSocket + status API
- Security
  - Sanitize inputs; validate file types and sizes
  - Rate limit per session/IP (10/hour)
  - Do not persist raw transcripts beyond job folder; optional ephemeral cleanup
  - Production HTTPS via reverse proxy (out of scope locally)

---

## 7) Work Breakdown Structure (WBS) and Milestones

- Milestone M0: Baseline Ready (Done)
  - Parallel Stage A and Stage B orchestration working
  - Final stage executed and pipeline finalized
  - API endpoints functional and returning status
  - Proof via scripts/test_celery_parallel.py

- Milestone M1: Web UI Feature-Complete for PRD
  1) Input + Upload
     - Drag-and-drop upload (.txt/.md up to 10 MB)
     - Large text area with basic syntax highlighting
     - Server-side validation and size checks
  2) Analyzer Selection
     - Three columns (Stage A, B, Final) with selectable analyzers
     - Select/Deselect all per column
  3) Progress and Metrics
     - Real-time statuses with correct states
     - Time and token tracking display
     - Error visibility with retry affordance
  4) Results Viewer + Export
     - Tabbed Stage A / Stage B / Final
     - Markdown-rendered content
     - Export .md and .json; copy to clipboard
  5) Prompt Editor (phase-appropriate)
     - List prompts by stage
     - Edit/save; reset to default
     - Validate template variables client-side and server-side

- Milestone M2: Performance and Caching
  - Token-aware prompt compaction (truncate or summarize transcript for Final per settings)
  - Optional content-hash cache (24h) with invalidation on prompt change
  - Concurrency validation for 10 parallel jobs

- Milestone M3: Reliability, Security, and Ops
  - Retry policies for LLM calls and Celery tasks
  - Rate limiting (10/hour/session)
  - Logging with Loguru; structured logs and per-job tracing
  - Runbooks (start/restart, health checks, Redis maintenance)

---

## 8) Detailed Implementation Tasks

- Backend
  - [A] API contract hardening (src/app/api.py)
    - Validate request schema, analyzer selections, size limits
    - Return jobId immediately; early status update event
    - Add /api/results/<jobId> aggregation endpoint
  - [B] WebSockets (src/app/sockets.py)
    - Emit progress events from complete_stage_x and analyzers
    - Ensure idempotent updates and final completion event
  - [C] Prompt Management
    - Add prompt CRUD endpoints
    - Filesystem persistence and default-restore logic
    - Variable validation ({transcript}, {context})
  - [D] LLM Client (src/llm_client.py)
    - Confirm .env usage and model selection override
    - Add retry/backoff; surface token usage when provided
  - [E] Caching (optional in this phase)
    - Content hash (transcript+prompt+analyzer) → cache key
    - TTL of 24 hours; invalidated on prompt change/version bump
  - [F] Rate Limiting
    - Simple Redis-based token bucket per session/IP
  - [G] Export Pipeline
    - Ensure filesystem outputs match UI tabs
    - API to stream/download .md and .json exports
  - [H] Observability
    - Loguru integration across tasks
    - timings.json, tokens.json per job (optional)

- Frontend
  - [I] Upload + Input (src/app/templates/index.html, static/js/*.js)
    - Drag-drop; accept .txt/.md; preview
    - Text input area with syntax highlighting
  - [J] Analyzer Selection UI
    - Three columns; checkbox lists; select/deselect all
    - Persist last selection in session/localStorage
  - [K] Progress Dashboard
    - Subscribe to job events; update indicators
    - Show durations and token counts
  - [L] Results Tabs
    - Stage A/Stage B/Final tabs; Markdown rendering (marked.js) + code highlight
    - Export buttons (.md and .json)
  - [M] Prompt Editor (Phase-appropriate)
    - List prompts; edit with client-side variable validation
    - Save/Reset actions
  - [N] UX Polish
    - Responsive layout; keyboard shortcuts; accessible labels

- Docker/Infra
  - [O] Ensure docker-compose healthchecks for app and worker
  - [P] Host port mapping 5001; document restart commands
  - [Q] Redis config: disable stop-writes-on-bgsave-error in dev if needed (doc-only)

---

## 9) Acceptance Criteria (Traceable to PRD)

- Transcript Processing
  - Accepts text or .txt/.md upload up to 10 MB (blocked otherwise)
  - Speaker ID and segmentation available or stubbed; segments passed to analyzers (optional if LLM prompt handles segmentation internally)
- Stage A/B Analyzers
  - Each analyzer runs independently with correct input per PRD
  - Parallel execution verified via timestamps; total time ~ max(task times)
- Final Stage Outputs
  - meeting_notes.md and composite_note.md generated for selected final analyzers
  - Obsidian [[link]] format preserved
- UI
  - Analyzer selection per stage with select/deselect all
  - Real-time progress with pending/processing/done/error states
  - Time and token metrics visible
  - Results tabs render Markdown; export works
- Prompt Management
  - Edit and save prompt templates; reset restores original
  - Server validates presence of required variables
- Performance
  - 10k words processed <= 60s (baseline target; dependent on LLM/model/latency)
  - 10 concurrent analyses execute without deadlocks or queue starvation
- Security/Rate Limiting
  - Rate limiting enforced (10/hour)
  - Inputs sanitized; invalid files rejected with clear error
- Reliability
  - No blocking get() inside tasks; Celery canvas only
  - Failures are surfaced to UI; partial results are preserved

---

## 10) Testing Strategy

- Unit Tests (pytest)
  - Analyzer input shaping and output schema validation
  - Prompt rendering with variable substitution; invalid variable detection
  - llm_client retry/backoff logic
- Integration Tests
  - scripts/test_minimal_pipeline.py: sanity run with short transcript
  - scripts/test_full_pipeline_fixed.py or scripts/test_full_pipeline.py: full A→B→Final
  - scripts/test_parallel_pipeline.py: verify parallel timings
  - scripts/test_api.py: /api/analyze and /api/status happy/error paths
  - scripts/test_web_ui.py and scripts/test_status_display.py: UI smoke (if headless harness present)
- End-to-End (Manual + Automated)
  - Upload test file; select analyzers; monitor progress; verify outputs saved
  - Edge cases: large transcripts (near token bound), malformed files, partial analyzer failure
- Performance/Load
  - 10 concurrent job submissions; ensure completion < concurrency SLA
  - Measure token usage; confirm summarized transcript mode reduces cost/time
- Observability
  - Validate timings/tokens files exist when enabled
  - Logs include jobId correlation

---

## 11) Risks and Mitigations

- LLM Latency/Quota → Backoff/retry, optional cached results, allow alternative model via .env
- Token Limits → Summarize transcript for Final; character caps in settings; chunk if necessary
- Redis Persistence Errors → Document dev-only toggle; add healthchecks; fail gracefully with user-visible error
- Browser Upload Limits → Enforce server-side 10 MB; chunked upload if needed (future)
- Parallel Overload → Cap Celery concurrency; queue per stage

---

## 12) Timeline (Indicative)

- Week 0: Baseline verification (done); restart and stabilize environment; smoke tests
- Week 1:
  - M1 UI: Analyzer selection, upload/input, progress indicators
  - WebSocket event completeness; status page polish
- Week 2:
  - Results tabs, export, token/time metrics
  - Prompt management endpoints + minimal editor
- Week 3:
  - Performance tuning, summarized transcript mode
  - Caching (optional), rate limiting, log polish
- Week 4:
  - Full test sweep, docs, runbooks, sign-off

---

## 13) Runbooks

- Start/Stop
  - docker-compose up -d
  - docker-compose restart app
  - docker-compose restart worker
- Health Checks
  - curl http://localhost:5001/ (UI)
  - curl http://localhost:5001/api/status/<nonexistent> (404 expected)
- Submitting Jobs
  - POST http://localhost:5001/api/analyze with transcript and selections
  - Monitor via /api/status/<jobId> and UI WebSocket feed
- Redis Maintenance (dev)
  - docker exec -it redis redis-cli info
  - If snapshot warnings: CONFIG SET stop-writes-on-bgsave-error no (dev only)

---

## 14) Definition of Done Checklist

- [ ] API validates inputs; returns jobId; status endpoint reflects progression
- [ ] WebSocket events cover A/B/Final transitions and completion/error
- [ ] Parallel execution verified; no blocking inside Celery tasks
- [ ] UI implements upload/input, analyzer selection, progress, and results tabs
- [ ] Prompt editor supports edit/save/reset with variable validation
- [ ] Exports to .md/.json correct; Obsidian links intact
- [ ] Rate limiting and basic security in place
- [ ] Performance target demonstrated on representative transcript
- [ ] Tests (unit, integration, E2E) written and passing
- [ ] Runbooks and documentation updated

---

## 15) Immediate Next Actions

1) Restart web server for manual testing  
   - Command: docker-compose restart app

2) Verify pipeline via provided scripts  
   - scripts/test_parallel_pipeline.py  
   - scripts/test_full_pipeline.py

3) Execute UI smoke via scripts/test_web_ui.py (if configured) and manual walkthrough

4) Begin M1 UI tasks per WBS (Sections 7–8)
