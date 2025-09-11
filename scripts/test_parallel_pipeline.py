#!/usr/bin/env python3
"""
Parallel pipeline test runner using the async orchestrator.

- Runs Stage A analyzers concurrently
- Aggregates Stage A outputs
- Runs Stage B analyzers concurrently
- Prints timing and token usage summary
- Saves outputs in a run_YYYYMMDD_HHMMSS directory under output/runs/

Usage:
  python3 scripts/test_parallel_pipeline.py
"""

import sys
import time
from pathlib import Path
import asyncio
import os
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.app.async_orchestrator import run_pipeline_async
from src.app.notify import get_notification_manager


def load_sample_transcript() -> str:
    sample_path = Path("input sample transcripts/sample1.md")
    if sample_path.exists():
        return sample_path.read_text(encoding="utf-8")
    # Fallback minimal transcript
    return """Speaker 1: We have 20 years of scientific data sitting in our systems that we've never monetized.
Speaker 2: That's interesting. What kind of data are we talking about?
Speaker 1: Lab results, experimental data, all stored in Chromeleon and our LIMS systems.
Speaker 2: Have we considered the privacy and regulatory implications?
Speaker 1: That's the first thing we need to address. But the opportunity is massive."""


def main() -> int:
    # CLI args to enable and test notifications easily
    parser = argparse.ArgumentParser(description="Parallel pipeline test with optional notifications")
    parser.add_argument("--notify", type=str, default="",
                        help="Comma-separated channels e.g. desktop,slack,webhook")
    parser.add_argument("--slack-webhook", type=str, default="", help="Slack incoming webhook URL")
    parser.add_argument("--webhook-url", type=str, default="", help="Generic webhook URL")
    parser.add_argument("--desktop", action="store_true", help="Enable desktop notifications")
    parser.add_argument("--desktop-strategy", type=str, default="macos_say",
                        choices=["macos_say", "terminal_notifier", "plyer"],
                        help="Desktop notification strategy (default: macos_say)")
    parser.add_argument("--desktop-speak", action="store_true", help="Speak on completion")
    parser.add_argument("--file-path", type=str, default="", help="Path to JSONL notifications file for FileChannel")
    parser.add_argument("--no-notify", action="store_true", help="Force notifications off")
    args = parser.parse_args()

    # Apply notification config via environment so orchestrator picks it up
    if args.no_notify:
        os.environ["TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED"] = "false"
    else:
        if args.notify or args.slack_webhook or args.webhook_url or args.desktop or args.file_path:
            os.environ["TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED"] = "true"
            channels = []
            if args.notify:
                channels = [c.strip() for c in args.notify.split(",") if c.strip()]
            if args.desktop and "desktop" not in channels:
                channels.append("desktop")
            if args.slack_webhook and "slack" not in channels:
                channels.append("slack")
            if args.webhook_url and "webhook" not in channels:
                channels.append("webhook")
            if args.file_path and "file" not in channels:
                channels.append("file")
            if channels:
                os.environ["TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS"] = ",".join(channels)
            if args.slack_webhook:
                os.environ["TRANSCRIPT_ANALYZER_SLACK_WEBHOOK_URL"] = args.slack_webhook
            if args.webhook_url:
                os.environ["TRANSCRIPT_ANALYZER_WEBHOOK_URL"] = args.webhook_url
            if args.file_path:
                os.environ["TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH"] = args.file_path
            if args.desktop:
                os.environ["TRANSCRIPT_ANALYZER_DESKTOP_ENABLED"] = "true"
                os.environ["TRANSCRIPT_ANALYZER_DESKTOP_STRATEGY"] = args.desktop_strategy
                if args.desktop_speak:
                    os.environ["TRANSCRIPT_ANALYZER_DESKTOP_SPEAK_ON_COMPLETE"] = "true"

    print("\n" + "=" * 80)
    print("  PARALLEL TRANSCRIPT ANALYSIS PIPELINE (ASYNC)")
    print("=" * 80)
    if os.getenv("TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED", "false").lower() == "true":
        print(f"\n🔔 Notifications enabled via channels: {os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS', '')}")

    transcript_text = load_sample_transcript()
    print(f"\n📄 Loaded transcript: {len(transcript_text)} characters")

    start = time.time()
    result = asyncio.run(run_pipeline_async(transcript_text))
    elapsed = time.time() - start

    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"✅ Successful analyzers: "
          f"{sum(1 for r in result.stage_a_results.values() if r.status.value == 'completed') + sum(1 for r in result.stage_b_results.values() if r.status.value == 'completed')}"
          f"/{len(result.stage_a_results) + len(result.stage_b_results)}")
    print(f"📊 Total tokens used: {result.total_tokens:,}")
    print(f"⏱️  Total time (wall-clock): {elapsed:.2f} seconds")
    print(f"📁 Run directory: {result.run_dir}")

    print("\nStage A analyzers:")
    for name, r in result.stage_a_results.items():
        tokens = r.token_usage.total_tokens if r.token_usage else 0
        print(f"  - {name}: {tokens:,} tokens, {r.processing_time:.2f}s")

    print("\nStage B analyzers:")
    for name, r in result.stage_b_results.items():
        tokens = r.token_usage.total_tokens if r.token_usage else 0
        print(f"  - {name}: {tokens:,} tokens, {r.processing_time:.2f}s")

    print("\n" + "=" * 80)
    print("  PIPELINE COMPLETE (ASYNC)")
    print("=" * 80)

    # Proactive notification (best-effort)
    try:
        nm = get_notification_manager()
        stage_a_tokens = sum(r.token_usage.total_tokens if r.token_usage else 0 for r in result.stage_a_results.values())
        stage_b_tokens = sum(r.token_usage.total_tokens if r.token_usage else 0 for r in result.stage_b_results.values())
        summary_payload = {
            "output_dir": str(result.run_dir),
            "status": "completed",
            "stage_a": {"analyzers": list(result.stage_a_results.keys()), "tokens": stage_a_tokens},
            "stage_b": {"analyzers": list(result.stage_b_results.keys()), "tokens": stage_b_tokens},
            "total_tokens": result.total_tokens,
            "wall_clock_seconds": elapsed,
        }
        nm.pipeline_completed(result.run_dir.name, summary_payload)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
