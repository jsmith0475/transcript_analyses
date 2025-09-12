Transcript Analysis Tool — End‑User Docker Install Guide
=======================================================

Who this is for
- Non‑technical users who want the simplest, most reliable way to run the app on their own computer using Docker.

What you will do (high level)
1) Install Docker Desktop (one‑time) and verify it runs
2) Get the app files (download as ZIP or use Git)
3) Tell the app your OpenAI API key (in a file or in the app header)
4) Start the app with a single command and open it in your browser

What you need
- A computer with recent macOS, Windows 10/11, or Ubuntu 22.04+
- Internet access (for Docker and model calls)
- An OpenAI API key (you can add this after the app starts)

Step 1 — Install Docker Desktop
-------------------------------

Mac (Apple Silicon or Intel)
- Download: https://www.docker.com/products/docker-desktop/
- Open the .dmg and drag “Docker.app” to Applications
- Launch Docker (first start can take up to a minute)
- You should see the whale icon in the menu bar when Docker is running

Windows 10/11
- Download: https://www.docker.com/products/docker-desktop/
- Run the installer. If prompted, enable “Use WSL 2” and reboot.
- Start “Docker Desktop” from the Start menu and wait for it to say “Running”.

Ubuntu (or other Linux)
- Follow: https://docs.docker.com/engine/install/ubuntu/ and install the Compose plugin
- Ensure your user is in the `docker` group or run commands with `sudo`

Verify Docker
- Open a Terminal (Mac) or PowerShell (Windows) and run:

  docker --version
  docker compose version

Both commands should print versions (no errors).

Step 2 — Get the App Files
--------------------------

Option A: Download as ZIP (simplest)
1) Go to your repository page on GitHub
2) Click “Code” → “Download ZIP”
3) Unzip it to a folder you can find (e.g., Desktop/transcript-analysis)

Option B: Use Git (if you prefer)
1) Install Git (https://git-scm.com/downloads)
2) In a terminal, choose a folder and run:

   git clone https://github.com/your-org-or-user/transcript_analyses.git
   cd transcript_analyses

Throughout this guide, “project folder” means the top‑level folder that contains files like `docker-compose.yml`, `README.md`, and the `src/` directory.

Step 3 — Provide Your OpenAI API Key
------------------------------------

You can provide your key in either place. Pick just one.

Method A (recommended): in the app header (per user)
- Start the app first (next step), then paste your key into “Your OpenAI API Key” at the top of the page and click Save (or Test). This does not require editing files.

Method B: in a settings file (server‑wide)
1) In the project folder, copy the template to create a `.env` file:

   cp .env.template .env

2) Open `.env` in a text editor and set your key:

   OPENAI_API_KEY=sk-...your-key...

3) Save the file.

Notes
- You can run the app without a key, but model features will not work until you add one (either method).
- Never share your API key publicly.

Step 4 — Start the App
-----------------------

1) Make sure Docker Desktop is running.
2) In a terminal, switch to the project folder (where `docker-compose.yml` lives).
3) First start (or after updating the app), run:

   docker compose up -d --build

4) Wait for Docker to finish. Then open your browser to:

   http://localhost:5001

5) Optional health checks:

   http://localhost:5001/health
   http://localhost:5001/api/health

You should see the web page titled “Transcript Analysis Tool”.

Step 5 — Use the App
---------------------

Basic run
1) If you didn’t set a key in `.env`, paste your OpenAI API key into the header field and click Save/Test.
2) Paste your transcript into the big text box or click “Choose File” to upload a .txt/.md file (up to 10 MB).
3) Choose which analyzers you want to run (Stage A, Stage B, Final). Click “Advanced” if you want to pick different prompt files.
4) Click “Start Analysis”. You’ll see live progress tiles. Results appear in tabs and are downloadable.
5) The Insights panel (below the progress section) can export JSON / CSV / Markdown after the run completes.

Where files go
- Job outputs: `output/jobs/<jobId>/...`
- Final documents: `output/jobs/<jobId>/final/`
- Prompt files (editable): `prompts/` (three stage folders)

Step 6 — Stop, Restart, Update
-------------------------------

Stop the app

  docker compose down

Restart after changing code or prompts

  docker compose restart app
  docker compose restart worker

See logs (helpful for troubleshooting)

  docker compose logs -f app worker

Update the app
- If you used ZIP: download a fresh ZIP, replace the folder, and re-run `docker compose up -d --build`.
- If you used Git:

  git pull
  docker compose up -d --build

Troubleshooting
---------------

Docker isn’t running
- Start Docker Desktop first; wait until it says “Running”.

Browser can’t connect to http://localhost:5001
- Make sure containers are up: `docker compose ps`
- Rebuild and start: `docker compose up -d --build`
- Another app may be using that port. Close it or edit the port mapping in `docker-compose.yml` (the line like `"5001:5000"`).

“Model/key” errors or empty outputs
- Add your OpenAI key in the app header or in `.env` and restart containers.
- Make sure your computer can access the internet (firewalls/proxies can block API calls).

Redis connection error
- With Docker Compose, Redis is included automatically. If you changed `REDIS_URL` in `.env`, restore it to `redis://redis:6379` or remove the override.

Seeing old files
- Your browser may be caching old scripts. Do a hard refresh (Mac: Cmd+Shift+R, Windows: Ctrl+F5).

Uninstall / clean up
- Stop containers: `docker compose down`
- You can delete the project folder to remove code and outputs.
- To free Docker space, you can run: `docker system prune` (this deletes unused containers/images; read the prompt carefully).

Frequently Asked Questions (FAQ)
--------------------------------

Where are my results?
- In the `output/jobs/<jobId>/` folder inside the project directory. Final documents are in `output/jobs/<jobId>/final/`.

Can I run without a global API key?
- Yes. Leave `.env` as is, start the app, and paste your key in the header field per run/user.

Is this safe to run on my computer?
- The app and Redis run locally in Docker containers. Your transcripts and results stay on your machine unless you choose to share them.

Can multiple people use this on one machine?
- Yes. Each browser session can set its own API key in the header. All users share the same Docker app and outputs folder.

How do I change which analyzers or prompts are available?
- Prompts are regular Markdown files in the `prompts/` folders. The app lets you edit or delete them. Click “Rescan” in the UI to pick up new files immediately.

Need help?
- See `README.md` for an overview and `docs/WEB_INTERFACE_GUIDE.md` for UI details. If you run into issues, capture screenshots or the output of `docker compose logs -f app worker` and share them with whoever supports your deployment.

