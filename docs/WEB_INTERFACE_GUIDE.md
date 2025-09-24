# Web Interface User Guide
Transcript Analysis Tool – Browser Interface

Version: 1.3  
Last Updated: 2025-09-10

Overview
This guide explains how to use the web UI, how progress is reported in real time, and how final results are displayed and exported. It reflects the current Docker-based setup, Celery-backed orchestration, and recent fixes to progress consistency and Final tab rendering.

Quick Start (Docker)
Prerequisites
- Docker (Compose v2) installed
- .env file with a valid OPENAI_API_KEY (see .env.template)

Run
- First time:
  cp .env.template .env
  docker compose up -d --build
- Subsequent restarts:
  docker compose restart worker
  docker compose restart app
- Web UI: http://localhost:5001
- Health: http://localhost:5001/api/health

Hard Refresh Note
- After UI/JS changes, force a hard refresh in your browser to load the latest static assets:
  - macOS: Cmd+Shift+R
  - Windows/Linux: Ctrl+F5

Submitting an Analysis
1) Provide Transcript
- Paste your transcript into the text area, or
- Use “Choose File” to upload .txt/.md/.markdown (max 10MB, enforced server-side)

2) Select Analyzers and Prompts
- Stage A, Stage B, and Final analyzers appear in three columns
 - Use the All/None buttons in each column to quickly select or deselect every analyzer in that stage.
 - By default, prompt dropdowns are hidden. Enable the “Advanced” toggle to reveal them.
 - Dropdowns only appear for analyzers that have more than one prompt option (populated via /api/prompt-options).
 - Selecting a different prompt updates the analyzer label to the chosen prompt’s name and applies only to the current run.
 - “Edit” opens the prompt editor modal to view/update template content under the prompts/ directory (server-side validation enforces required variables per stage)
 - “Delete” removes the currently selected prompt file for that analyzer
  - “Delete All Prompts” is available inside the editor modal and removes all prompt files under prompts/ (dangerous)
  - Final includes an optional “Insightful Article” generator (~1000 words, privacy‑safe) in addition to Meeting Notes, Composite Note, Executive Summary, and What Should I Ask?

API Key in Header
- At the top of the page, enter “Your OpenAI API Key” to use a session-scoped key.
- If the server already has a valid key in .env, the field shows dots (masked) and the status indicates the server key is in use. Delete the dots and paste your key to override for your session.

3) Stage B Options
- Include Original Transcript: toggle
- Inclusion Mode: full or summary (Summary generates a real condensed summary; Full injects the raw transcript)
- Max Characters: upper bound on injected text (applies to raw transcript or summary)

Final Options
- Include Original Transcript: toggle (controls whether Final prompts inject transcript content)
- Inclusion Mode: full or summary (Summary generates a real condensed summary; Full injects the raw transcript)
- Max Characters: upper bound on injected text (applies to raw transcript or summary)

4) Start Analysis
- Click Start Analysis
- UI immediately seeds Pending tiles for the selected analyzers
- A jobId is issued by POST /api/analyze and status polling begins

Real-time Progress and Status
Event Sources
- WebSocket (Socket.IO namespace /progress) events:
  - job.queued
  - analyzer.started
  - analyzer.completed
  - stage.completed
  - job.completed
  - job.error
- Status Polling (fallback and augmentation):
  - GET /api/status/<jobId> returns the latest Redis status doc

Tile States
- Pending (gray): seeded at submission time
- In Process (yellow, pulsing): set immediately on analyzer.started
- Completed (green): set on analyzer.completed

Stage Key Normalization (UI fix)
- The backend emits stage values like "stage_a", "stage_b", and "final"
- The UI normalizes these to "stageA", "stageB", and "final" to target the correct tiles
- This ensures analyzer.started flips Pending → In Process immediately

Final Tab Rendering (robust loading)
- On pipeline completion (either job.completed or stage.completed(final)):
  1) The UI attempts to fetch final artifacts from:
     - /api/job-file?jobId=<id>&path=final/meeting_notes.md
     - /api/job-file?jobId=<id>&path=final/composite_note.md
  2) Fallback: If files are not yet readable, the UI uses inline raw_output fields from /api/status/<jobId> at:
     - doc.final.meeting_notes.raw_output
     - doc.final.composite_note.raw_output
  3) Retry: The UI retries a few times briefly to handle any short write-after-complete delay
- The Final tab automatically activates once any Final content is available

Inter-Stage Context Panel (new)
- The Debug Log panel has been removed and replaced by an Inter-Stage Context panel at the bottom of the UI.
- It displays the exact combined context passed between stages:
  - Stage A → Stage B: fair-share combined Stage A results
  - Stage B → Final: combined A+B context used by Final analyzers
- Population sources:
  1) WebSocket log.info events (preferred):
     - "Stage B context assembled" (payload includes `contextText`, `included`, `finalTokens`)
     - "Final context assembled" (payload includes `contextText`, `included`, `totalTokens`)
  2) Files-first fallback via /api/job-file:
     - `intermediate/stage_b_context.txt`
     - `final/context_combined.txt`
- The panel supports Copy and Download. It auto-opens when context first arrives, and you can toggle between A→B and B→Final. When Summary is used, the transcript section is labeled as a summary preview.

What You Should See
- Analyzer tiles flip to “In Process” quickly after submission
- Tiles flip to “Completed” with time and tokens on finish
- Once Final is done, the Final tab shows Meeting Notes and Composite Note (combined or individually if only one is selected). Additional Final analyzers (e.g., Executive Summary) are selectable and their outputs are saved under `final/<slug>.md` in job artifacts and available via the status document.
 - The results pane renders Markdown (headings, lists, tables, code) with a light background for readability. Tables are normalized server‑side even when returned inside code fences.

API Reference (Web UI)
- POST /api/analyze
  - Body:
    {
      "transcriptText": "string",
      "fileId": "string or empty",
      "selected": {
        "stageA": [ "say_means", "perspective_perception", "premises_assertions", "postulate_theorem" ],
        "stageB": [ "competing_hypotheses", "first_principles", "determining_factors", "patentability" ],
        "final": [ "meeting_notes", "composite_note" ]
      },
      "options": {
        "stageBOptions": {
          "includeTranscript": boolean,
          "mode": "full" | "summary",
          "maxChars": number
        },
        "finalOptions": {
          "includeTranscript": boolean,
          "mode": "full" | "summary",
          "maxChars": number
        },
        "models": { "stageA"?: string, "stageB"?: string, "final"?: string }
      },
      "promptSelection": {
        "stageA": { "say_means": "prompts/.../file.md", ... },
        "stageB": { "competing_hypotheses": "prompts/.../file.md", ... },
        "final": { "meeting_notes": "prompts/.../file.md", "composite_note": "prompts/.../file.md", "executive_summary": "prompts/.../file.md" }
      }
    }
  - Returns: { ok: true, jobId: "uuid", queuedAt: number }

- GET /api/status/<jobId>
  - Returns: { ok: true, jobId, status, doc }
  - doc contains:
    - stageA, stageB: per-analyzer objects including:
      status ("processing"/"completed"), processing_time, token_usage, raw_output, structured_data
    - final: for "meeting_notes" and/or "composite_note", includes raw_output
    - tokenUsageTotal
    - startedAt, completedAt

- GET /api/job-file?jobId=<id>&path=<relative path under output/jobs/id>
  - Returns: { ok: true, content }
  - Useful paths for inter-stage context:
    - `intermediate/stage_b_context.txt`
    - `final/context_combined.txt`

Insights Dashboard
- Location: Below Progress, titled “Insights” with a Type selector and export buttons.
- Source of truth: File-based after Final completion. UI fetches `/api/insights/<jobId>` and renders `final/insight_dashboard.json`.
- No WebSocket dependency: The UI does not rely on a WS event; it polls on completion with brief retries.
- Type selector: All, Actions, Decisions, Risks (enabled even during runs). Option labels display counts.
- Clear behavior: Panel clears on app start, reset, and new job start.
- Export: Buttons fetch the corresponding file via `/api/job-file` and trigger a download.

Prompt Requirements for Insights
- Final prompts (meeting_notes, composite_note) include explicit “Decisions”, “Action Items”, and “Risks” sections, plus an `INSIGHTS_JSON` fenced block (JSON schema: `{ actions:[], decisions:[], risks:[] }`, dates in `YYYY-MM-DD`, optional `anchor` like `#seg-123`).

- GET /api/prompt-options
  - Returns per-analyzer prompt options and default paths

- GET /api/prompts?path=... OR ?analyzer=...
  - Returns { ok: true, path, stage, content }

- POST /api/prompts
  - Body: { path, content }
  - Saves template content with validation of required variables per stage

Progress Consistency (Backend)
- The Celery pipeline runs Stage A and Stage B in parallel using groups/chords
- The chord callbacks now assemble authoritative per-stage results from their chord results list (ordered by the analyzer lists), persist to Redis, then emit stage completion
- This eliminates races where the UI might see “Pending” after a stage has truly finished

Troubleshooting
- UI not updating or Final tab blank:
  - Hard refresh the browser (Cmd+Shift+R / Ctrl+F5)
  - Ensure both worker and app are running:
    docker compose ps
  - Verify health:
    curl http://localhost:5001/api/health
  - Check logs: docker compose logs -f worker app

- Status stuck at "processing":
  - Ensure no errors in worker logs (look for analyzer exceptions)
  - Re-submit with fewer analyzers to isolate issues
  - Verify OPENAI_API_KEY is present and valid in .env

- File uploads failing:
  - Confirm within 10MB limit
  - Allowed file types: .txt, .md, .markdown
  - Try pasting transcript text as a workaround

Security and Limits
- Rate limiting: 10 analyses/hour per session (roadmap; check server config)
- Inputs sanitized server-side
- No permanent storage of transcript data unless exported
- Production deployments should enforce HTTPS and secure cookies

Changelog (UI-specific)
 - 1.3 (2025-09-10)
  - Insights panel loads from `/api/insights` (file-based), independent of WebSocket
  - Type selector stays enabled; counts shown in options; Clear on start/reset
  - Prompt and aggregator changes to ensure complete Actions/Decisions/Risks
 - 1.1 (2025-09-07)
  - Stage key normalization in WS client to ensure immediate “In Process”
  - Final tab robust loader with file-first + status fallback + retries
  - Updated endpoint references and Docker usage
- 1.0 (2025-01-05)
  - Initial web interface release with real-time progress and exports

Contact/Support
- Refer to docs/ARCHITECTURE.md for backend orchestration and data flow
- See docs/PRD_ALIGNED_DEVELOPMENT_AND_TEST_PLAN.md for acceptance criteria and tests
