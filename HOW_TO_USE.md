How To Use — Transcript Analysis Tool
=====================================

This guide walks end‑users through running the web app, setting an API key, choosing analyzers/prompts, and exporting results.

Prerequisites
- Docker Desktop (Compose v2) or Docker Engine + compose plugin
- An OpenAI API key (can be provided in‑app or via `.env`)

1) Start the App
- Create `.env` from the template:
  - `cp .env.template .env`
  - You may leave `OPENAI_API_KEY` empty if you plan to set your key in the app.
- Start services (Redis, app, worker):
  - `docker compose up -d --build`
- Open the UI:
  - http://localhost:5001

2) Provide Your API Key
- In the page header, use “Your OpenAI API Key”:
  - Paste your key → Save (optional: Test)
  - You can Clear it later to fall back to the server default key.
- Alternatively, set `OPENAI_API_KEY` in `.env` before starting the app.

3) Load or Paste a Transcript
- Paste text directly into the Transcript box or click “Choose File” to upload `.txt`/`.md`.
- Large transcripts are supported; Stage B uses a combined results context to keep prompts efficient.

4) Choose Analyzers and Prompts
- Each stage lists available analyzers with a prompt dropdown.
- Prompts are Markdown files under `prompts/` and are auto‑discovered at startup.
- You can change the selected prompt for any analyzer using the dropdown.

Prompt Actions
- Edit: Opens a modal to view and edit the selected file.
- Delete: Removes the selected prompt file from `prompts/`.
- Reset to Default Template: Replaces the editor content with a stage‑appropriate starter template.
- Delete All Prompts: In the editor modal, deletes all `.md` files under `prompts/` (dangerous).

Custom Analyzers (Optional)
- Use the “Add Analyzer” control to create a custom analyzer, either from pasted prompt content (auto‑normalized) or by mapping an existing prompt file to a new slug.

5) Run Analysis
- Click “Start Analysis”. The app enqueues the job and shows live progress tiles.
- Stage A runs first (transcript analyzers), Stage B second (results analyzers), then Final outputs.
- The Inter‑Stage Context panel (bottom) displays the exact context passed between stages.

6) View Results and Exports
- Stage A/B tabs: Select an analyzer tile to view its Markdown output.
- Final tab: View Meeting Notes and other final documents.
- Insights: After Final completes, open the Insights panel to filter Actions, Decisions, and Risks or export JSON/CSV/Markdown.
- Download/Copy: Use the buttons above the results area to download or copy the current tab content.

Where Files Are Written
- Job artifacts: `output/jobs/<jobId>/...`
- Final insights: `output/jobs/<jobId>/final/insight_dashboard.{json,md,csv}`
- Prompts: `prompts/` (three stage subfolders)

Troubleshooting
- Can’t start containers:
  - Ensure Docker is running; try `docker compose version`.
  - First‑time start: use `docker compose up -d --build`.
  - If only `docker-compose` exists, try `docker-compose up -d --build`.
- No LLM output / 401 errors:
  - Set your API key in the UI header or in `.env` and restart.
- UI not updating after changes:
  - Hard refresh the browser (Cmd/Ctrl+Shift+R).
- Redis connection error:
  - With Compose, Redis is bundled. For local Redis, set `REDIS_URL=redis://localhost:6379` in `.env`.

See Also
- README.md (overview, Docker quick start)
- docs/WEB_INTERFACE_GUIDE.md (UI details and API reference)
- docs/USER_GUIDE.md (broader pipeline and CLI usage)
