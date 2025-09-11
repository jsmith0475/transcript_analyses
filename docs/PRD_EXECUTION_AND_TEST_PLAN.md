# PRD-Aligned Execution and Test Plan
Transcript Analysis Tool — Implementation Blueprint
Version: 1.0 (aligned to PRD v1.0, Sept 6, 2025)
Author: Engineering

This document is the engineering source of truth for building, testing, and delivering the Transcript Analysis Tool per the PRD. It converts requirements into concrete architecture, APIs, implementation steps, test plans, and milestones. Real OpenAI GPT calls will be made using the API key set in .env.

References
- PRD: PRD_Transcript_Analysis_Tool.md
- Existing Docs: docs/ARCHITECTURE.md, docs/WEB_INTERFACE_PLAN.md, docs/WEB_INTERFACE_GUIDE.md, docs/FINAL_DEVELOPMENT_PLAN.md, docs/PRD_ALIGNED_DEVELOPMENT_AND_TEST_PLAN.md (superseded by this plan where conflicts exist)

Scope and Goals
- Implement a 3-stage pipeline with analyzers:
  - Stage A (Transcript Analysis) — inputs: {transcript}
  - Stage B (Meta-Analysis) — inputs: {context} = combined Stage A outputs (fair-share + budget)
  - Final (Synthesis) — inputs: {context} = Stage A + Stage B, and optionally {transcript}
- Real-time UI with progress, token/time usage, and selectable analyzers per stage.
- Prompt management: in-browser editing, reset-to-default, save to filesystem.
- Obsidian-optimized outputs (wikilinks, structured hierarchy).
- Security, performance, and reliability per PRD.
- Testing with REAL GPT calls using .env OPENAI_API_KEY; cost guards in place.

Non-Goals (Phase 1)
- Multi-tenant, SSO, advanced permissions (Phase 4).
- PostgreSQL persistent storage (future; use Redis + filesystem for MVP).
- Cross-transcript analytics (Phase 3).

Current State Assessment (Codebase)
- Backend: Flask, Celery, Redis, Flask-SocketIO present.
- Analyzers: Stage A/B/final templates exist; base/template analyzer classes implemented.
- LLM client: src/llm_client.py present with OpenAI chat usage and retry/timeouts.
- Config: src/config.py with AppConfig, env overrides, budgeting knobs.
- Context fairness: src/utils/context_builder.py implements fair-share builder.
- Orchestration: src/app/orchestration.py (+ parallel_orchestration.py, async_orchestrator.py) and sockets.
- Web UI: index.html, js/api.js, js/ws.js, js/ui.js, js/main.js; Tailwind-based.
- Prompt templates located under prompts/ per PRD directory structure.
- Test scripts: scripts/ (various), e2e helpers and smoke tests.

Architecture and Data Flow (Aligned to PRD)
- Backend:
  - Flask app (src/app/__init__.py), REST API (src/app/api.py), Socket.IO (src/app/sockets.py).
  - Async pipeline: Celery tasks (broker/result backend Redis).
  - Sessions: Redis-backed session store (ephemeral per PRD).
  - Filesystem: per-job output dir under ./output/{jobId} for markdown and JSON exports.
- Frontend:
  - Single-page UI (index.html) with three-column analyzer selection + results tabs.
  - Socket.IO client for progress events; live updates; markdown rendering (Marked + Highlight.js).
- LLM:
  - OpenAI models (default gpt-4o-mini; optional GPT-5 if enabled).
  - Token budgeting + chunking for long transcripts; retries; timeout.
- Data Flow:
  1) Client submits transcript (text or upload), config, selected analyzers.
  2) Server creates jobId, enqueues Stage A analyzers (parallel).
  3) Stage A results combined (fair-share) into context for Stage B.
  4) Stage B analyzers run (parallel).
  5) Final analyzers synthesize Stage A + Stage B (+ optional transcript).
  6) Results stored; client receives events; user can view/export.

Data Models and Storage
Pydantic models (conceptual; actual code may exist and should align):
- AnalysisRequest
  - transcript_text: str | None
  - upload_path: str | None
  - selections: { stage_a: [str], stage_b: [str], final: [str] }
  - options: {
      final_include_transcript: bool,
      final_transcript_mode: "full"|"summary",
      final_transcript_char_limit: int
    }
- AnalysisContext
  - job_id: str
  - transcript: str
  - previous_analyses: Dict[str, AnalyzerResult]  # used to build context for Stage B and Final
  - metadata: { timestamps, user_agent, etc. }
- AnalyzerResult
  - name: str
  - stage: "stage_a"|"stage_b"|"final"
  - prompt_used: str
  - raw_output: str
  - tokens_prompt: int
  - tokens_completion: int
  - duration_ms: int
  - status: "pending"|"processing"|"completed"|"error"
  - error: Optional[str]
- JobStatus (cached in Redis + filesystem mirror)
  - job_id: str
  - stage_a: Dict[str, AnalyzerResult|{status}]  # per-analyzer
  - stage_b: Dict[str, AnalyzerResult|{status}]
  - final: Dict[str, AnalyzerResult|{status}]
  - started_at, completed_at
Storage
- Ephemeral: Redis for job status and progress.
- Filesystem: ./output/{jobId}/ for
  - stage_a/{analyzer}.md
  - stage_b/{analyzer}.md
  - final/{analyzer}.md
  - job.json (full structured results)
  - export bundles.

LLM Strategy and Token Budgeting
- Provider: OpenAI; API key from env OPENAI_API_KEY.
- Model: default gpt-4o-mini (configurable OPENAI_MODEL); support GPT-5 using text_verbosity and reasoning_effort.
- Retry/Timeout: max_retries=3, timeout=120s (configurable).
- Stage A: Each analyzer uses only {transcript}. For long inputs:
  - Chunk transcript (config: chunk_size=4000, overlap=400). Run analyzer per chunk and summarize if needed, or pre-summarize transcript into bounded length for analyzers requiring full context.
- Stage B: Uses build_fair_combined_context(previous_analyses, budget=stage_b_context_token_budget, min_per_analyzer). Ensures representation of all selected Stage A outputs.
- Final: context = Stage A + Stage B results; optionally include transcript (full/summary) with final_context_token_budget if enabled.
- Prompt hygiene: deterministic template variables per PRD
  - Stage A: {{transcript}}
  - Stage B: {{context}}
  - Final: {{context}}, optionally {{transcript}}
- Validation: On save/edit of prompts, validate presence of required variables for their stage; backend rejects invalid templates.

Backend Services and APIs (Contracts)
- POST /api/analyze
  - body: AnalysisRequest (JSON; transcript text or upload ref + selections + options)
  - returns: { job_id }
  - side effects: emits "job_started" event
  - options payload example:
    {
      "stageBOptions": { "includeTranscript": true, "mode": "full", "maxChars": 20000 },
      "finalOptions":  { "includeTranscript": false, "mode": "summary", "maxChars": 8000 },
      "models": { "stageA": "gpt-4o-mini", "stageB": "gpt-5-mini", "final": "gpt-5" }
    }
- GET /api/status/<jobId>
  - returns JobStatus snapshot with per-analyzer statuses and minimal metadata
- GET /api/job-file?jobId=...&path=stage_a/xyz.md
  - returns raw file content if exists (for UI to render)
  - Inter‑stage context paths of interest:
    - intermediate/stage_b_context.txt
    - final/context_combined.txt
- GET /api/prompt-template?stage=stage_a|stage_b|final
  - returns default template text
- GET /api/prompt?analyzer=slug
  - returns current prompt file content
- PUT /api/prompt?analyzer=slug
  - body: { content: str }
  - validates stage variables; saves to filesystem
- POST /api/prompt/reset?analyzer=slug
  - restores default
- Rate limit middleware (simple session-based) to 10 analyses/hour/session
- Error handling: JSON { error, details, job_id? }

WebSocket Events (Socket.IO)
- job_started: { job_id, selections }
- analyzer_started: { job_id, stage, analyzer, ts }
- analyzer_progress: { job_id, stage, analyzer, pct?, info? }
- analyzer_completed: { job_id, stage, analyzer, tokens_prompt, tokens_completion, duration_ms }
- analyzer_error: { job_id, stage, analyzer, error }
 - log.info: { message: "Stage B context assembled" | "Final context assembled", contextText, included, finalTokens|totalTokens, transcriptIncluded?, transcriptPreview? }
- job_completed: { job_id, summary: { durations, tokens } }
- job_error: { job_id, error }

Orchestration and Background Processing
- Celery worker pool with concurrency N (config.processing.max_concurrent).
- For each job:
  - Create job context and persist initial status.
  - Stage A: submit tasks per selected analyzer in parallel; chord callback aggregates results.
  - Build Stage B context with fair-share combiner.
  - Stage B: submit tasks per selected analyzer in parallel; chord callback aggregates results.
  - Final: submit tasks per selected final analyzer in parallel or small batch; combine Stage A + Stage B (+ transcript) into final context per prompt.
  - Each task:
    - formats prompt using template + variables
    - calls LLM client (with retries, timeout, max_tokens)
    - writes raw_output to filesystem and status to Redis
    - emits Socket.IO events through a thread-safe notifier.
- Stop-on-error configurable (processing.stop_on_error). Default false; errors do not abort entire job.

Frontend/UI Flows and State
- Analyzer Selection Panel: Three columns (Stage A, B, Final) with checkboxes and Select/Deselect all per stage.
- Transcript Input: Text area + drag-and-drop file upload; show file size limits, allowed extensions.
- Configuration Panel (Stage B):
  - Include transcript toggle (affects Stage B)
  - Mode (full/summary)
  - Max chars for transcript or summary injection
  
  Configuration Panel (Final):
  - Include transcript toggle (affects Final)
  - Mode (full/summary)
  - Max chars for transcript or summary injection
- Progress and Status:
  - Tiles show Pending/Processing/Completed/Error; timers and token usage per analyzer.
  - Global progress bar derived from completed analyzers/total.
- Results:
  - Tabs: Stage A Results | Stage B Results | Final Outputs
  - Each tab lists analyzers as selectable tiles; selecting shows markdown rendered content.
  - Export: Markdown and JSON and Copy. For Markdown export, bundle per-analyzer files and composite note.
- Prompt Editor:
  - Open analyzer config modal; fetch default template for that stage; inline edit; validate; Save and Reset-to-default.
  - Ensure custom analyzers behave like built-ins: tile selection, auto-loading content, and no “Result not available yet.” regressions.

Security and Keys
- API key in .env: OPENAI_API_KEY. Never log the key.
- Environment variables via dotenv; sensitive values not exposed to client.
- Input validation: sanitize markdown, enforce upload size/type (WebConfig.allowed_extensions), limit rate.
- Session security: SECRET_KEY; CORS config for Socket.IO; HTTPS in production via reverse proxy (nginx/traefik).
- Data retention: no permanent transcript storage beyond session/output dir chosen by user; optional TTL cleanup job.

Observability
- Structured logging with JSON context: job_id, stage, analyzer, durations, token usage, retries.
- Context builder instrumentation logs allocations per analyzer.
- Metrics (optional): counters for completed jobs, errors, average durations, token totals (can log to file / JSONL).
- Trace IDs: job_id used across tasks and logs.

Performance and Cost Controls
- Targets: Full analysis < 60s on 10k words; average < 45s (PRD).
- Concurrency: processing.max_concurrent, Celery worker autoscale.
- Token budgets: stage_b_context_token_budget; final_context_token_budget (optional); min_per_analyzer fairness.
- Chunking strategy for large transcripts; summarization fallback.
- Caching (24h): cache analyzer outputs by transcript hash + template hash (config.processing.cache_enabled, ttl). Note: ensure privacy constraints are respected.
- Real-call test mode uses smaller models and lower max_tokens by default to control cost.

Testing Strategy (Real GPT Calls)
Principles
- Use real OpenAI API for integration/e2e with constrained budgets and small inputs.
- Unit tests do not require network (mock completions).
- Provide reproducible smoke tests via scripts/.

Unit Tests
- utils/context_builder: allocation fairness, deterministic concatenation under budgets.
- llm_client: retry policy, timeout behavior (mock transport), parameter mapping (max_tokens).
- analyzers/template formatting: variable presence per stage, validation errors for missing variables.
- config: env overrides behavior.

Integration Tests (Backend)
- /api/analyze with minimal transcript and 1 analyzer per stage using real GPT
  - Asserts job lifecycle, status transitions, artifacts present on disk, Socket.IO events are emitted.
- Prompt editor endpoints: GET/PUT/reset with stage validation.
- Export endpoints: /api/job-file returns file content for completed analyzers.

E2E Tests (Full Pipeline)
- scripts/test_full_pipeline.py (or fixed variant) with sample1.md:
  - Selections: all Stage A, 1-2 Stage B, both Final.
  - Verify:
    - Stage B context includes contributions from all selected Stage A outputs (via debug allocations/logs).
    - Final outputs render in UI (tiles selectable, content loads).
    - Obsidian formatting present ([[wikilinks]]) and hierarchical sections generated.
- scripts/test_web_ui.py (manual/automated):
  - Start Flask + Celery + Redis.
  - Upload transcript; select analyzers; run; observe tiles through to completion.
  - Confirm time/token usage displayed.

Reliability and Error Tests
- Simulate OpenAI timeouts (lower timeout) and ensure retry/backoff occurs.
- Force one analyzer error; ensure others continue (stop_on_error=false) and final job completes with partial results.
- Redis outage simulation (document fallback or graceful failure).

Cost Guardrails
- Test profiles:
  - DEV_REAL_SMALL: OPENAI_MODEL=gpt-4o-mini, llm.max_tokens=800, processing.stage_b_context_token_budget=2000, short transcripts.
  - DEV_FAST_LOCAL: mock completions for unit tests.
- Nightly e2e limited to N jobs, small inputs; dynamic sampling of analyzers.

Runbooks
Local Dev (without Docker)
- Prereqs: Python 3.10+, Redis running locally (brew services start redis).
- Setup:
  - cp .env.template .env
  - set OPENAI_API_KEY=...
  - python -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
- Start services:
  - Terminal 1: python -m src.app
  - Terminal 2: celery -A src.app.celery_app.celery_app worker --loglevel=INFO --concurrency=3
  - Ensure Redis is reachable at REDIS_URL or default.
- Open UI: http://localhost:5000

Docker Compose
- docker compose up -d --build
- Environment passed via .env; services: web, worker, redis.
- Reverse proxy/HTTPS to be configured for production.

Milestones, Deliverables, and Acceptance
M1 — API and Pipeline Backbone (2–3 days)
- Deliverables: /api/analyze, /api/status, Celery tasks for Stage A/B/Final, fair-share Stage B context, job filesystem artifacts, Socket.IO events, basic UI updates.
- Acceptance: End-to-end job runs for sample transcript; statuses and files present; Stage B fairness confirmed in logs.

M2 — Prompt Management and UI Polish (2 days)
- Deliverables: Prompt editor (GET/PUT/reset), default templates per stage, add-analyzer UX parity with built-ins, tiles selection behavior consistent.
- Acceptance: Newly added custom analyzers selectable; content renders; reset-to-default works; validation prevents saving invalid templates.

M3 — Export, Obsidian Formatting, and Token/Time Displays (1–2 days)
- Deliverables: Export markdown and JSON; Obsidian formatting with wikilinks; per-analyzer token/time display; caching TTL.
- Acceptance: Files exported to ./output/{jobId}; Obsidian opens and links resolve; UI displays tokens/time.

M4 — Security, Rate Limits, and Reliability (1 day)
- Deliverables: Rate limit (10/hour/session), upload validation (size/type), improved error messaging, retry/backoff verified.
- Acceptance: Limits enforced; graceful failure with clear UI messages.

M5 — Testing and Performance Validation (2 days)
- Deliverables: Unit tests, integration tests with real GPT on small inputs, e2e script; performance smoke shows <60s for 10k words with constrained selection (documented).
- Acceptance: Test suite green; runbook documented.

Detailed Implementation Checklist (Engineering DoD)
Backend
- Define/confirm Pydantic models for requests and status.
- Harden src/llm_client.py for parameter names, retries, timeout, telemetry.
- Ensure src/utils/context_builder.py logs allocations and returned lengths.
- Validate BaseAnalyzer.format_prompt stage-specific variable inclusion.
- Implement/cross-check Celery chords for Stage A and Stage B; chain into Final.
- Emit Socket.IO events at task boundaries with job_id correlation.
- Implement caching key design (transcript hash + template hash + model + temp).
- Implement rate limiting and input sanitization.
- Persist artifacts in ./output by jobId with predictable naming.

Frontend
- Analyzer selection UI with stage toggles and select/deselect all.
- Transcript input with drag-and-drop; show limits and file type feedback.
- Socket.IO client handlers for all events; maintain per-stage stores.
- Tile selection state with blue outline and default auto-select on first available.
- Prompt editor modal: prefill by stage; validate; save; reset.
- Results tabs with markdown renderer and syntax highlighting.
- Export buttons (MD, JSON, Copy) and download endpoints usage.
- Display tokens/time per analyzer.

Validation and QA
- Verify Stage B context fairness uses all selected Stage A outputs under budget.
- Verify Final stage templates refer to both Stage A + Stage B results (context) and optional transcript.
- Verify custom final analyzers produce rendered content and selectable tiles.
- Verify Obsidian wikilinks and structure.

Acceptance Criteria Mapping (PRD User Stories)
- Researcher: Theme extraction via Stage A; export to Obsidian (.md). Acceptance: stage_a results present with cross-references and exportable.
- Product Manager: Clear action items and decisions in Meeting Notes. Acceptance: final meeting notes include sections and assignments fields.
- Innovation Team Lead: Patentability analyzer flags novelty/non-obviousness. Acceptance: stage_b patentability.md includes assessment with evidence list.
- Knowledge Manager: Knowledge graph linkage. Acceptance: wikilinks in outputs and composite note cross-references.

Risk Register and Mitigations
- LLM Downtime: retry with backoff; allow model override; optional fallback to smaller models.
- Token Overrun: enforce budgets; chunking and summarization; fair-share allocations.
- Redis Failure: startup checks; clear error states; document local fallback (degraded single-process path optional later).
- Cost Spikes: use DEV_REAL_SMALL profile; limit nightly test frequency and token caps.

Environment and Configuration Matrix
- .env keys (examples; see src/config.py):
  - OPENAI_API_KEY=...
  - OPENAI_MODEL=gpt-4o-mini
  - TRANSCRIPT_ANALYZER_STAGE_B_CONTEXT_TOKEN_BUDGET=8000
  - TRANSCRIPT_ANALYZER_STAGE_B_MIN_TOKENS_PER_ANALYZER=500
  - TRANSCRIPT_ANALYZER_FINAL_CONTEXT_TOKEN_BUDGET=0
  - REDIS_URL=redis://localhost:6379
  - SECRET_KEY=change-me-in-prod
- Profiles:
  - DEV_REAL_SMALL: smaller budgets for real calls during dev.
  - PROD_DEFAULT: PRD defaults, scalable workers.

Verification Steps (Go/No-Go)
- Spin up services; run scripts/dev_smoke.py (or scripts/test_full_pipeline_fixed.py).
- Observe UI tiles transition and final outputs rendering.
- Confirm filesystem artifacts and Obsidian-compatible markdown.
- Review logs for fair-share allocations and token usage.
- Run scripts/test_web_ui.py to sanity-check UI endpoints and rendering.

Appendix A: API and Event Schemas (Illustrative)
- POST /api/analyze request:
  {
    "transcript_text": "string | null",
    "upload_path": "string | null",
    "selections": {
      "stage_a": ["say_means","perspective_perception"],
      "stage_b": ["first_principles"],
      "final": ["meeting_notes","composite_note"]
    },
    "options": {
      "final_include_transcript": true,
      "final_transcript_mode": "summary",
      "final_transcript_char_limit": 12000
    }
  }
- Socket.IO analyzer_completed:
  {
    "job_id": "abc",
    "stage": "stage_b",
    "analyzer": "first_principles",
    "tokens_prompt": 1342,
    "tokens_completion": 612,
    "duration_ms": 28950
  }

Appendix B: Directory Conventions
- prompts/ per PRD structure
- output/{jobId}/stage_a|stage_b|final/*.md
- output/{jobId}/job.json

Appendix C: Done Definition (per feature)
- Code complete with tests (unit/integration/e2e as applicable)
- Logging and error handling implemented
- Documentation updated (README + docs/)
- Verified in UI with real GPT calls
- No regressions on analyzer selection/tiles/markdown rendering
