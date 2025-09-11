#!/usr/bin/env python3
"""
NotificationManager and channel plugins to proactively announce pipeline events.

Channels supported (no external deps required):
- Slack via Incoming Webhook (HTTP POST)
- Generic Webhook (HTTP POST)
- Desktop notifications (macOS say or terminal-notifier if available; cross-platform fallback to stdout)

Notes:
- All send() calls are best-effort and swallow exceptions (logged), so notifications never break the pipeline.
- A simple throttle avoids duplicate events within a short window.
"""

from __future__ import annotations

import json
import os
import time
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from loguru import logger

from src.config import get_config, AppConfig


class BaseChannel:
    def send(self, event: str, payload: Dict[str, Any]) -> None:
        raise NotImplementedError


class SlackChannel(BaseChannel):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            text = self._format_text(event, payload)
            data = {"text": text}
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as _resp:
                pass
        except Exception as e:
            logger.warning(f"[Notify:Slack] failed: {e}")

    def _format_text(self, event: str, p: Dict[str, Any]) -> str:
        run_id = p.get("run_id", "")
        status = p.get("status", "")
        total_tokens = p.get("total_tokens", "")
        secs = p.get("wall_clock_seconds", "")
        link = p.get("link", "")
        output_dir = p.get("output_dir", "")
        if event == "pipeline_completed":
            base = f"✅ Pipeline completed: {run_id} | status={status} | tokens={total_tokens} | time={secs:.2f}s"
        elif event == "pipeline_error":
            err = p.get("error", {})
            msg = err.get("message", "")
            base = f"❌ Pipeline error: {run_id} | {msg}"
        else:
            base = f"ℹ️ Event {event}: {run_id}"
        if link:
            base += f"\n{link}"
        elif output_dir:
            # Provide file path as a hint
            base += f"\nOutput: {output_dir}"
        return base


class WebhookChannel(BaseChannel):
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, secret: Optional[str] = None) -> None:
        self.url = url
        self.headers = headers or {}
        self.secret = secret

    def send(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            body = dict(payload)
            body["event"] = event
            headers = {"Content-Type": "application/json"}
            headers.update(self.headers)
            if self.secret:
                headers["X-Notifier-Token"] = self.secret
            req = urllib.request.Request(
                self.url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as _resp:
                pass
        except Exception as e:
            logger.warning(f"[Notify:Webhook] failed: {e}")


class FileChannel(BaseChannel):
    """Append JSON lines with event + payload to a file (autonomous test-friendly)."""
    def __init__(self, path: str) -> None:
        self.path = path
        try:
            d = os.path.dirname(self.path)
            if d:
                os.makedirs(d, exist_ok=True)
        except Exception:
            pass

    def send(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            rec = dict(payload or {})
            rec["event"] = event
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"[Notify:File] failed: {e}")

class DesktopChannel(BaseChannel):
    """
    macOS strategies:
      - 'macos_say': uses 'say' to speak a message
      - 'terminal_notifier': calls terminal-notifier if installed
    Cross-platform fallback: logger.info line (acts as visible terminal notification)
    """
    def __init__(self, strategy: str = "plyer", speak_on_complete: bool = False) -> None:
        self.strategy = strategy
        self.speak_on_complete = speak_on_complete

    def send(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            title = "Transcript Analysis"
            run_id = payload.get("run_id", "")
            status = payload.get("status", "")
            msg = f"{event}: {run_id} ({status})"
            # Prefer macOS native tools if available
            if self.strategy == "terminal_notifier" and self._has_cmd("terminal-notifier"):
                subprocess.run(["terminal-notifier", "-title", title, "-message", msg], check=False)
            elif self.strategy == "macos_say" and self._has_cmd("say"):
                # speak message
                if self.speak_on_complete or event in ("pipeline_completed", "pipeline_error"):
                    subprocess.run(["say", msg], check=False)
                else:
                    # Use a short beep via osascript
                    subprocess.run(["osascript", "-e", 'beep 1'], check=False)
            else:
                # Fallback to printing a visible line in logs
                logger.info(f"[DesktopNotify] {msg}")
        except Exception as e:
            logger.warning(f"[Notify:Desktop] failed: {e}")

    def _has_cmd(self, cmd: str) -> bool:
        from shutil import which
        return which(cmd) is not None


class NotificationManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.channels: List[BaseChannel] = []
        self._last_event_ts: Dict[str, float] = {}
        self._throttle = max(0, int(getattr(config.notifications, "throttle_seconds", 5)))
        self._include_links = bool(getattr(config.notifications, "include_links", True))

        if not getattr(config.notifications, "enabled", False):
            logger.debug("Notifications disabled by config")
            return

        chans = getattr(config.notifications, "channels", []) or []
        chans = [c.lower() for c in chans]

        # Desktop
        if ("desktop" in chans) or getattr(config.notifications, "desktop_enabled", False):
            strategy = getattr(config.notifications, "desktop_strategy", "plyer")
            speak = bool(getattr(config.notifications, "desktop_speak_on_complete", False))
            self.channels.append(DesktopChannel(strategy=strategy, speak_on_complete=speak))

        # Slack
        slack_url = getattr(config.notifications, "slack_webhook_url", None)
        if "slack" in chans and slack_url:
            self.channels.append(SlackChannel(slack_url))

        # Webhook
        webhook_url = getattr(config.notifications, "webhook_url", None)
        webhook_headers = getattr(config.notifications, "webhook_headers", {}) or {}
        secret = getattr(config.notifications, "secret_token", None)
        if "webhook" in chans and webhook_url:
            self.channels.append(WebhookChannel(webhook_url, headers=webhook_headers, secret=secret))

        # File channel (JSONL writer) for autonomous tests
        file_path = getattr(config.notifications, "file_path", None)
        if "file" in chans and file_path:
            self.channels.append(FileChannel(file_path))

        if not self.channels:
            logger.debug("NotificationManager initialized with no active channels")

    def _should_throttle(self, key: str) -> bool:
        if self._throttle <= 0:
            return False
        now = time.time()
        last = self._last_event_ts.get(key, 0)
        if (now - last) < self._throttle:
            return True
        self._last_event_ts[key] = now
        return False

    def _ensure_link(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._include_links:
            out_dir = payload.get("output_dir")
            if out_dir:
                try:
                    abs_path = os.path.abspath(out_dir)
                    payload["link"] = f"file://{abs_path}"
                except Exception:
                    pass
        return payload

    def pipeline_started(self, run_id: str, meta: Dict[str, Any]) -> None:
        if not self.channels:
            return
        key = f"pipeline_started:{run_id}"
        if self._should_throttle(key):
            return
        payload = {"run_id": run_id, "status": "processing"}
        payload.update(meta or {})
        for ch in self.channels:
            ch.send("pipeline_started", payload)

    def stage_started(self, run_id: str, stage: str, analyzer: str) -> None:
        if not self.channels:
            return
        key = f"stage_started:{run_id}:{stage}:{analyzer}"
        if self._should_throttle(key):
            return
        payload = {"run_id": run_id, "status": "processing", "stage": stage, "analyzer": analyzer}
        for ch in self.channels:
            ch.send("stage_started", payload)

    def stage_completed(self, run_id: str, stage: str, analyzer: str, stats: Dict[str, Any]) -> None:
        if not self.channels:
            return
        key = f"stage_completed:{run_id}:{stage}:{analyzer}"
        if self._should_throttle(key):
            return
        payload = {"run_id": run_id, "status": "completed", "stage": stage, "analyzer": analyzer}
        payload.update(stats or {})
        for ch in self.channels:
            ch.send("stage_completed", payload)

    def pipeline_completed(self, run_id: str, summary: Dict[str, Any]) -> None:
        if not self.channels:
            return
        key = f"pipeline_completed:{run_id}"
        if self._should_throttle(key):
            return
        payload = {"run_id": run_id, "status": "completed"}
        payload.update(summary or {})
        payload = self._ensure_link(payload)
        for ch in self.channels:
            ch.send("pipeline_completed", payload)

    def pipeline_error(self, run_id: str, error: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> None:
        if not self.channels:
            return
        key = f"pipeline_error:{run_id}"
        if self._should_throttle(key):
            return
        payload = {"run_id": run_id, "status": "error", "error": error or {}}
        if meta:
            payload.update(meta)
        payload = self._ensure_link(payload)
        for ch in self.channels:
            ch.send("pipeline_error", payload)


# Singleton accessor
_notify_manager: Optional[NotificationManager] = None

def get_notification_manager() -> NotificationManager:
    global _notify_manager
    if _notify_manager is None:
        _notify_manager = NotificationManager(get_config())
    return _notify_manager
