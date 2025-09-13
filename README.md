Transcript Analysis Tool
========================

![Transcript Analysis Tool — Screenshot](docs/images/transcript%20analyzer.png)

An interactive Flask web app for multi‑stage transcript analysis with LLMs. It ingests a transcript, runs Stage A analyzers, rolls them up into Stage B, and then generates Final outputs (e.g., meeting notes, composite notes). Prompts are managed as Markdown files under `prompts/` and can be edited in‑app.

Features
- Multi‑stage pipeline: Stage A → Stage B → Final
- Prompt management UI (edit, select, reset, delete files)
- Map‑reduce summarization for long transcripts
- Redis‑backed job status and Socket.IO live updates
- REST API for UI and automation

How To Use (User‑Focused)
- Prefer a simple, non‑technical install? See END_USER_DOCKER_INSTALL.md for a step‑by‑step Docker guide (install Docker Desktop, get the app, start it, and run analyses).
- See HOW_TO_USE.md for a step‑by‑step user guide (API key in‑app, choosing analyzers/prompts, running, and exporting results).

Requirements
- Docker and Docker Compose (recommended), or
- Python 3.11+, Redis 7+ (for local dev without Docker)

Environment and API Key
- Create .env (required): copy the template because other runtime variables live there, even if you plan to set your key in‑app.

     cp .env.template .env

- The app uses OpenAI by default. You have two ways to provide the API key:
  1) Server-wide: set `OPENAI_API_KEY` in `.env` (or export in your shell). Example (`.env.template`):

     OPENAI_API_KEY=sk-...your-key...

  2) Per-user in the app: at the top of the UI there’s “Your OpenAI API Key”. Paste your key and click Save (optionally Test). This stores a session-scoped key so the server can run without a global key.

  Notes:
  - The app can start without any key; LLM features won’t work until a key is provided (either method above).
  - You can Clear your per-user key in the UI to fall back to the server default.
  - If a server default key is configured, the input box is prefilled with dots (masked) to indicate it’s in use. Delete the dots and paste your own key to override.

- Optional environment variables:
  - `OPENAI_MODEL` (default: `gpt-5-nano`)
  - `REDIS_URL` (default: `redis://localhost:6379`)

Quick Start (Docker)
1) Copy the template and set your API key:
   cp .env.template .env
   # edit .env and set OPENAI_API_KEY

2) Start services (app, worker, redis):
   docker compose up -d --build

3) Open the UI:
   http://localhost:5001

4) Health checks:
   - App: http://localhost:5001/health
   - Internal API health: http://localhost:5001/api/health

Docker Notes
- The app service binds container port 5000 to host port 5001 (see `docker-compose.yml`).
- The default command runs Gunicorn with the Eventlet worker to support Socket.IO.
- The worker service runs Celery for the analysis pipeline.

Common Docker Commands
- Restart app/worker after code changes:
  docker compose restart app
  docker compose restart worker
- View logs:
  docker compose logs -f app worker
- Stop services:
  docker compose down

Local Development (without Docker)
1) Create a virtualenv and install deps:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt

2) Ensure Redis is running locally (or via Docker):
   docker run --rm -p 6379:6379 redis:7-alpine

3) Set environment and/or use the in‑app key, then run the app:
   export OPENAI_API_KEY=sk-...  # or use .env
   export REDIS_URL=redis://localhost:6379
   export FLASK_APP=src.app
   flask run --host 0.0.0.0 --port 5000
   # or, for full Socket.IO support like prod:
   gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 "src.app:create_app()"

4) Open and (optionally) set your key in the UI header:
   http://localhost:5000

Prompts
- All prompts live under `prompts/` in these subfolders:
  - `prompts/stage a transcript analyses/`
  - `prompts/stage b results analyses/`
  - `prompts/final output stage/`
- For an end‑user overview of how staged prompts work (Stage A → Stage B → Final), see PROMPTS_USER_GUIDE.md.
- For detailed, per‑prompt descriptions and interpretation guidance, see PROMPTS_CATALOG.md.
- At startup, the app scans these directories and loads available `.md` files. Built‑in analyzer prompts are included in this scan as well, so all analyzers (built‑in and custom) resolve their prompt paths dynamically from the filesystem.
- From the UI you can:
  - Edit a prompt file (Edit)
  - Delete a selected prompt file (Delete)
  - Reset the editor to a stage‑appropriate template
  - Delete all prompt files (in the editor modal)
  - Advanced prompt selection per analyzer (per‑run only): enable the “Advanced” toggle to reveal a prompt dropdown. Dropdowns only appear when an analyzer has more than one prompt option. Selecting a different prompt updates the label next to the analyzer, and that prompt path is used for this run only.
  - Rescan analyzers (per stage): rebuilds the analyzer registry from the `prompts/` folders and refreshes both the web app and Celery worker so new/updated prompt files are immediately available without restarting processes.

Running an Analysis
1) Paste transcript text or choose a file.
2) Select analyzers per stage and, optionally, choose prompt variants.
3) Click Start. Watch live progress and results populate.
  - Results render as Markdown with code highlighting and readable typography (no raw `#` headers).
  - The results pane uses a light card (black text on white) regardless of OS/browser dark mode.
  - Tables are server‑normalized (even if the model returns them inside code blocks) to display as real Markdown tables.

Key Endpoints
- UI: `/`
- Health: `/health`
- API base: `/api`
  - Prompt options: `GET /api/prompt-options`
  - Rescan analyzers: `POST /api/analyzers/rescan`
  - Get/Save prompt: `GET/POST /api/prompts`
  - Delete prompt file: `DELETE /api/prompts?path=...`
  - Delete all prompts: `DELETE /api/prompts/all`
  - Analyze: `POST /api/analyze`
  - Status: `GET /api/status/<jobId>`
  - Insights: `GET /api/insights/<jobId>`

Troubleshooting
- App won’t start (Docker): ensure ports 5001 (host) and 5000 (container) aren’t in use.
- LLM calls fail: verify `OPENAI_API_KEY` and network egress. The app boots without a key, but any LLM action requires one.
- Redis errors: with Docker Compose, Redis is included. For local dev, start Redis on `localhost:6379` or set `REDIS_URL` accordingly.

Development Notes
- Prompts are git‑tracked by default. The UI can delete them; you can restore from git.
- Analyzer prompts are dynamically discovered at startup and on “Rescan”. The worker is also refreshed during rescan so you don’t need to restart it to pick up new prompts.
- `.env` is ignored by git. Never commit your API key.

What’s New (2025‑09‑11)
- Filesystem‑driven analyzers: At startup and on “Rescan”, the app scans `prompts/` and replaces stage analyzer lists from the filesystem. Filenames determine slugs; numeric prefixes are no longer required.
- Rescan refreshes the worker: The Celery worker reloads the registry/config during Rescan, so new/renamed prompt files are available immediately.

License
- Proprietary to your project unless you add a license.
