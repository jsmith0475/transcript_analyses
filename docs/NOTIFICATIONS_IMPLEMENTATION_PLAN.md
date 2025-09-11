# Notifications Implementation Plan

Goal: Provide proactive, “push” notifications when a run completes (or errors), regardless of which mechanism initiated the run (CLI scripts, async orchestrator, Celery/web). A single NotificationManager abstraction will unify behavior and fan out to configured channels (Slack, webhook, desktop notification, etc.).

Status (Sept 7, 2025): Implemented across async and Celery runners with a unified NotificationManager. Channels supported: Slack webhook, generic Webhook, Desktop (macOS say/terminal-notifier/log), and FileChannel (JSONL). FileChannel is used for autonomous verification: scripts/verify_notifications.py runs the async pipeline, reads the JSONL, asserts pipeline_completed, and validates artifacts in the run directory (COMPLETED sentinel + final_status.json).

## 1) Design Overview

- One abstraction: `NotificationManager`
  - Invoked by any runner (CLI scripts, async orchestrator, Celery task)
  - Decouples “who did the work” from “how to notify”
- Channel plugins:
  - Slack (incoming webhook)
  - Webhook (generic HTTP POST)
  - Desktop (macOS say/terminal-notifier or cross-platform plyer)
  - (Optional later) Email via SMTP
- Events to emit:
  - `pipeline_started(run_id, meta)`
  - `stage_started(run_id, stage, analyzer)`
  - `stage_completed(run_id, stage, analyzer, stats)`
  - `pipeline_completed(run_id, summary)` ← primary success signal
  - `pipeline_error(run_id, error, meta)` ← failure signal

## 2) Public Interface (used by runners)

```python
# src/app/notify.py
class NotificationManager:
    def __init__(self, config: AppConfig):
        ...

    def pipeline_started(self, run_id: str, meta: dict) -> None: ...
    def stage_started(self, run_id: str, stage: str, analyzer: str) -> None: ...
    def stage_completed(self, run_id: str, stage: str, analyzer: str, stats: dict) -> None: ...
    def pipeline_completed(self, run_id: str, summary: dict) -> None: ...
    def pipeline_error(self, run_id: str, error: dict, meta: dict | None = None) -> None: ...
```

- All methods are no-throw (catch/log internally). Notifications must never fail the pipeline.
- Debounce/throttle duplicates within N seconds (configurable).

## 3) Channel Plugin Model

```python
class BaseChannel:
    def send(self, event: str, payload: dict) -> None: ...
```

Implementations:
- `SlackChannel(webhook_url: str)`
  - POST JSON with a simple text block summarizing status, run_id, tokens, and a link to results.
- `WebhookChannel(url: str, headers: dict | None = None, secret: str | None = None)`
  - Generic POST of the full payload envelope (see #4).
- `DesktopChannel(strategy: Literal["plyer","macos_say","terminal_notifier"], speak: bool = False)`
  - plyer: cross-platform notify if available
  - macOS: `say "Pipeline complete"` and/or `terminal-notifier` if installed
  - Fallback to printing a loud bell/line if desktop unsupported

(Phase 2) Optional:
- `EmailChannel(smtp_cfg: dict)` – send a minimal email summary
- `SocketIOChannel()` – only if ever needed server-side; the Web app already receives Socket.IO events.

## 4) Payload Contract (consistent across channels)

Envelope example (for pipeline completion):
```json
{
  "event": "pipeline_completed",
  "run_id": "run_20250907_074030",
  "status": "completed",
  "started_at": "2025-09-07T07:40:30Z",
  "ended_at": "2025-09-07T07:46:20Z",
  "wall_clock_seconds": 349.28,
  "stage_a": { "analyzers": ["say_means","perspective_perception","premises_assertions","postulate_theorem"], "tokens": 39241 },
  "stage_b": { "analyzers": ["competing_hypotheses","first_principles","determining_factors","patentability"], "tokens": 51040 },
  "total_tokens": 90281,
  "output_dir": "output/runs/run_20250907_074030",
  "link": "file:///absolute/path/output/runs/run_20250907_074030",
  "error": null
}
```

For errors:
- `event: "pipeline_error"`, `status: "error"`, include `error: {"message": "...", "trace_id": "..."}`
- Channels may render a more concise text, but must include core fields.

## 5) Configuration Additions (AppConfig.notifications)

Extend `src/config.py` with:
```python
class NotificationsConfig(BaseModel):
    enabled: bool = False
    channels: List[str] = Field(default_factory=list)  # e.g., ["desktop","slack","webhook"]
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = Field(default_factory=dict)
    secret_token: Optional[str] = None
    desktop_enabled: bool = False
    desktop_strategy: str = "plyer"  # or "macos_say" | "terminal_notifier"
    desktop_speak_on_complete: bool = False
    throttle_seconds: int = 5
    include_links: bool = True
```

- Wire into `AppConfig` as `notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)`
- .env support:
  - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED=true`
  - `TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS=desktop,slack,webhook`
  - `TRANSCRIPT_ANALYZER_SLACK_WEBHOOK_URL=...`
  - `TRANSCRIPT_ANALYZER_WEBHOOK_URL=...`
  - `TRANSCRIPT_ANALYZER_DESKTOP_ENABLED=true`
  - `TRANSCRIPT_ANALYZER_DESKTOP_STRATEGY=plyer`
  - etc.

## 6) Integration Points

Wire `NotificationManager` into:

A) CLI scripts
- `scripts/test_parallel_pipeline.py` and `scripts/test_full_pipeline_fixed.py`
  - On success: `manager.pipeline_completed(run_id, summary)`
  - On error/exception: `manager.pipeline_error(run_id, {"message": str(e)}, meta)`

B) Async orchestrator
- `src/app/async_orchestrator.run_pipeline_async`
  - After metadata finalize: call `pipeline_completed(run_id, summary)`
  - Wrap top-level try/except to call `pipeline_error` in failure

C) Celery task
- `src/app/orchestration.py` (run_pipeline)
  - After `job_completed(...)`: call `pipeline_completed(job_id, summary)` – use what’s already compiled for `metadata.json`
  - In `except:` branch: call `pipeline_error(job_id, {"message": str(e)})`

## 7) CLI Overrides (Optional)

Augment scripts with flags to override config at runtime:
- `--notify desktop,slack`
- `--slack-webhook https://hooks.slack.com/services/...`
- `--webhook-url https://example.com/notify`
- `--desktop-speak`
- `--no-notify` (forces notifications off)

## 8) Error Handling & Resilience

- All senders catch exceptions and log at WARN/ERROR.
- Add basic retry (1–2 attempts) for transient Slack/webhook failures with short delay; do not block entire pipeline completion.
- Throttle duplicate events within `throttle_seconds`.

## 9) Implementation Steps

1) Add `NotificationsConfig` to config; read from ENV (follow existing pattern)
2) Create `src/app/notify.py`:
   - `NotificationManager` and channels (`SlackChannel`, `WebhookChannel`, `DesktopChannel`)
   - Helper to build payload from run_dir/metadata or provided summary
3) Wire manager into:
   - `src/app/async_orchestrator.run_pipeline_async` (success + error)
   - `src/app/orchestration.run_pipeline` (success + error)
   - `scripts/test_parallel_pipeline.py` and `scripts/test_full_pipeline_fixed.py` (success + error)
4) Test matrix:
   - Desktop-only (no Slack/webhook)
   - Slack-only (requires a test webhook URL)
   - Webhook-only (test URL like webhook.site)
   - Combination of channels
5) Documentation:
   - Update README/docs (usage, ENV vars, sample payloads)
   - Example: `.env.template` with commented notification keys

## 10) Acceptance Criteria

- On success, at least one channel proactively notifies without user polling; for autonomous tests, FileChannel (JSONL) must be enabled.
- pipeline_completed event is recorded in the JSONL with: run_id, status="completed", output_dir, total tokens, wall_clock_seconds, and a file:// link to the run directory.
- Async path: output/runs/run_YYYYMMDD_HHMMSS/ contains COMPLETED sentinel and final_status.json. Web/Celery path: output/jobs/{jobId}/ contains the same on success (no COMPLETED on error, but final_status.json written with status="error").
- Failures to notify do not affect pipeline result; errors logged, retries attempted.
- Configurable via ENV and override in CLI scripts (e.g., --notify, --file-path, --slack-webhook, --webhook-url, --desktop).

## 11) Time & Sequencing

- Implementation: ~60–90 minutes for Slack, Webhook, Desktop (plyer or macOS say).
- Additional 30–45 minutes to update docs and run tests across channels.

## 12) Future Enhancements

- Email integration via SMTP with templated content
- Rich Slack formatting (blocks) with top insights
- Link to a Web UI results page when available instead of file://
- Notification aggregation for multi-run batches
