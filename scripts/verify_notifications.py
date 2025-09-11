#!/usr/bin/env python3
"""
Autonomous verification of proactive callbacks via FileChannel.

This script:
  1) Runs the async parallel pipeline test with FileChannel notifications enabled
  2) Writes notifications to a unique JSONL file under output/
  3) Parses the JSONL to find a `pipeline_completed` event with status "completed"
  4) Verifies the referenced run directory exists with required artifacts:
       - metadata.json
       - final/executive_summary.md
  5) Exits 0 on success, non-zero on failure WITH diagnostics

Usage:
  python3 scripts/verify_notifications.py

Notes:
  - Uses real GPT calls (ensure .env is configured and OpenAI API key present)
  - No external services required (Slack/Webhook are not used)
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime


def run_pipeline_with_file_channel(notifications_path: Path) -> int:
    """
    Invoke the async pipeline test script with FileChannel enabled and JSONL path set.
    Returns the subprocess return code.
    """
    notifications_path.parent.mkdir(parents=True, exist_ok=True)
    if notifications_path.exists():
        # ensure clean slate
        notifications_path.unlink()

    cmd = [
        sys.executable,
        "scripts/test_parallel_pipeline.py",
        "--notify", "file",
        "--file-path", str(notifications_path),
    ]

    # Set env explicitly (script also sets them from CLI flags)
    env = os.environ.copy()
    env["TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED"] = "true"
    env["TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS"] = "file"
    env["TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH"] = str(notifications_path)

    print(f"[verify] Running pipeline: {' '.join(cmd)}")
    start = time.time()
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    elapsed = time.time() - start
    print(f"[verify] Pipeline return code: {proc.returncode}, elapsed: {elapsed:.2f}s")

    # Always show a compact tail of stdout/stderr for diagnostics
    def tail(s: str, n: int = 40):
        lines = s.strip().splitlines()
        return "\n".join(lines[-n:]) if lines else ""

    print("\n[verify] --- pipeline stdout (tail) ---")
    print(tail(proc.stdout))
    print("\n[verify] --- pipeline stderr (tail) ---")
    print(tail(proc.stderr))

    return proc.returncode


def parse_notifications(notifications_path: Path):
    """
    Parse JSONL file and return the last pipeline_completed event with status 'completed', if any.
    """
    if not notifications_path.exists():
        return None, []

    events = []
    with notifications_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                events.append(evt)
            except Exception:
                # capture undecodable lines for diagnostics
                events.append({"_raw": line, "event": "_decode_error"})

    pipeline_completed = [
        e for e in events
        if isinstance(e, dict)
        and e.get("event") == "pipeline_completed"
        and e.get("status") == "completed"
    ]
    last_completed = pipeline_completed[-1] if pipeline_completed else None
    return last_completed, events


def validate_artifacts(event: dict) -> (bool, str):
    """
    Validate that output_dir exists and contains required files.
    Returns (ok, message).
    """
    run_id = event.get("run_id")
    output_dir = event.get("output_dir")
    if not output_dir:
        # Fallback if not present
        output_dir = str(Path("output/runs") / (run_id or ""))

    out_path = Path(output_dir)
    if not out_path.exists():
        return False, f"Output directory does not exist: {out_path}"

    metadata = out_path / "metadata.json"
    if not metadata.exists():
        return False, f"Missing metadata.json in {out_path}"

    executive = out_path / "final" / "executive_summary.md"
    if not executive.exists():
        return False, f"Missing final/executive_summary.md in {out_path}"

    # Final stage outputs
    mn = out_path / "final" / "meeting_notes.md"
    if not mn.exists():
        return False, f"Missing final/meeting_notes.md in {out_path}"
    cn = out_path / "final" / "composite_note.md"
    if not cn.exists():
        return False, f"Missing final/composite_note.md in {out_path}"

    completed = out_path / "COMPLETED"
    if not completed.exists():
        return False, f"Missing COMPLETED sentinel in {out_path}"

    final_status = out_path / "final_status.json"
    if not final_status.exists():
        return False, f"Missing final_status.json in {out_path}"

    # Optional: sanity-check contents of final_status.json
    try:
        data = json.loads(final_status.read_text(encoding="utf-8"))
        if data.get("run_id") != run_id:
            return False, f"final_status.json run_id mismatch: expected {run_id}, got {data.get('run_id')}"
        if data.get("status") != "completed":
            return False, f"final_status.json status not 'completed': {data.get('status')}"
    except Exception as e:
        return False, f"Unable to parse final_status.json: {e}"

    return True, f"Artifacts validated for run_id={run_id}, output_dir={out_path} (COMPLETED + final_status.json + final stage outputs present)"


def main() -> int:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    notifications_path = Path(f"output/notifications_{ts}.jsonl")
    print(f"[verify] Notifications file: {notifications_path}")

    rc = run_pipeline_with_file_channel(notifications_path)
    # Even if rc != 0, attempt to parse notifications (best-effort)
    event, all_events = parse_notifications(notifications_path)

    if event is None:
        print("[verify] ERROR: No pipeline_completed event with status 'completed' found in notifications.")
        print("[verify] Diagnostics: Events recorded (up to last 50):")
        for e in all_events[-50:]:
            print("  ", json.dumps(e, ensure_ascii=False) if isinstance(e, dict) else str(e))
        return 2

    ok, msg = validate_artifacts(event)
    if not ok:
        print(f"[verify] ERROR: {msg}")
        print("[verify] Diagnostics: pipeline_completed event payload:")
        print(json.dumps(event, indent=2, ensure_ascii=False))
        return 3

    print(f"[verify] SUCCESS: {msg}")
    print("[verify] pipeline_completed payload:")
    print(json.dumps(event, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
