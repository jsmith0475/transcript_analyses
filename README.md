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

Quick Links
- End‑user install (Docker): END_USER_DOCKER_INSTALL.md
- User guide (running the app): HOW_TO_USE.md
- Prompts overview (staging and authoring): PROMPTS_USER_GUIDE.md
- Prompts catalog (per‑prompt details): PROMPTS_CATALOG.md
- Web interface details: docs/WEB_INTERFACE_GUIDE.md
- Docker details for developers: docs/DOCKER_GUIDE.md

Requirements
- Docker and Docker Compose (recommended)
- Or for local development: Python 3.11+ and Redis 7+

Environment and API Key
- Create `.env` (required): `cp .env.template .env`
- Provide your OpenAI API key either:
  1) In `.env`: set `OPENAI_API_KEY=sk-...`
  2) In the app header (per user): paste your key in “Your OpenAI API Key” and Save/Test
- Optional: `OPENAI_MODEL` (default `gpt-5-nano`), `REDIS_URL` (default `redis://localhost:6379`)

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
- Common commands:
  - Restart: `docker compose restart app` (and `worker` if needed)
  - Logs: `docker compose logs -f app worker`
  - Stop: `docker compose down`

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

Prompts (Authoring & Selection)
- Locations:
  - Stage A: `prompts/stage a transcript analyses/`
  - Stage B: `prompts/stage b results analyses/`
  - Final: `prompts/final output stage/`
- Discovery: the app scans these folders at startup and on “Rescan”.
- In the UI (Advanced): pick alternate prompt files per analyzer for a single run; use the editor to view/edit/delete prompt files.
- Learn more: PROMPTS_USER_GUIDE.md (how staging works) and PROMPTS_CATALOG.md (what each prompt does).

Running an Analysis
1) Paste transcript text or choose a file.
2) Select analyzers per stage and, optionally, choose prompt variants.
3) Click Start. Watch live progress and results populate.
  - Results render as Markdown with code highlighting and readable typography (no raw `#` headers).
  - The results pane uses a light card (black text on white) regardless of OS/browser dark mode.
  - Tables render reliably (Markdown tables supported; for critical summaries, prompts may return sanitized HTML tables).

Developer note: API endpoints are documented in docs/WEB_INTERFACE_GUIDE.md.

Troubleshooting
- App won’t start (Docker): ensure ports 5001 (host) and 5000 (container) aren’t in use.
- LLM calls fail: verify `OPENAI_API_KEY` and network egress. The app boots without a key, but any LLM action requires one.
- Redis errors: with Docker Compose, Redis is included. For local dev, start Redis on `localhost:6379` or set `REDIS_URL` accordingly.

Notes
- Prompts are git‑tracked; the UI can edit/delete them.
- `.env` is ignored by git. Never commit your API key.

License & Rights
- Proprietary by default. If you intend to share or open‑source, add a LICENSE file and update this section accordingly.
