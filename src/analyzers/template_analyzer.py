"""
Generic TemplateAnalyzer to run arbitrary analyzer slugs backed by prompt files.
Falls back to simple parsing when no structured schema is defined.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from src.analyzers.base_analyzer import BaseAnalyzer


class TemplateAnalyzer(BaseAnalyzer):
    """
    A generic analyzer that renders a Jinja2 prompt template and sends it to the LLM.
    It relies on BaseAnalyzer for prompt loading, formatting by stage, and LLM calls.
    """

    def __init__(self, name: str, stage: str = "stage_a", prompt_path: Optional[str] = None):
        super().__init__(name=name, stage=stage, prompt_path=None)
        if prompt_path:
            # Allow string paths here for convenience
            from pathlib import Path
            self.set_prompt_override(Path(prompt_path))

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Best-effort parse:
        - Try to parse the first JSON object in the response (common pattern)
        - If parsing fails, return an empty dict so downstream still works
        """
        if not response:
            return {}

        # Attempt to detect a fenced JSON code block first
        try:
            import re
            m = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```", response, re.IGNORECASE)
            if m:
                obj = json.loads(m.group(1))
                if isinstance(obj, dict):
                    return obj
        except Exception:
            pass

        # Fallback: find first {...} that parses as JSON
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = response[start : end + 1]
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
        except Exception:
            pass

        return {}
