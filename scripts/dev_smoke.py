"""
Dev smoke script:
- Calls Flask app using test_client (no external server needed)
- GET /api/health and POST /api/smoke-openai
- Writes responses to dev_health.json and dev_smoke.json (in repo root)
Note: /api/smoke-openai performs a REAL OpenAI API call using your .env OPENAI_API_KEY.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.abspath("."))

from src.app import create_app


def main() -> int:
    app = create_app()

    root = Path(".")
    health_path = root / "dev_health.json"
    smoke_path = root / "dev_smoke.json"

    with app.test_client() as c:
        # Health
        h = c.get("/api/health")
        health_path.write_text(h.get_data(as_text=True), encoding="utf-8")

        # Smoke (real OpenAI)
        s = c.post("/api/smoke-openai", json={})
        smoke_path.write_text(s.get_data(as_text=True), encoding="utf-8")

        # Analyze-now with sample transcript if available
        sample_path = root / "input sample transcripts" / "sample1.md"
        analyze_path = root / "dev_analyze_now.json"
        if sample_path.exists():
            sample_text = sample_path.read_text(encoding="utf-8")
            a = c.post("/api/analyze-now", json={"transcriptText": sample_text})
            analyze_path.write_text(a.get_data(as_text=True), encoding="utf-8")
            analyze_status = a.status_code
        else:
            analyze_status = None

        print(f"Health status: {h.status_code} -> {health_path}")
        print(f"Smoke status: {s.status_code} -> {smoke_path}")
        print(f"Analyze-now status: {analyze_status} -> {analyze_path if sample_path.exists() else 'sample not found'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
