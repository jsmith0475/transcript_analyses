"""
Say-Means Analyzer (Stage A)
- Loads prompt from prompts/stage a transcript analyses/1 say-means.md via BaseAnalyzer/config mapping
- Receives only the transcript text in the template variable {transcript}
- Parses LLM response into minimal structured data
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from src.analyzers.base_analyzer import BaseAnalyzer


class SayMeansAnalyzer(BaseAnalyzer):
    def __init__(self) -> None:
        super().__init__(name="say_means", stage="stage_a")

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a minimal structure:
        {
          "insights": [str, ...],
          "concepts": [str, ...],
          "notes": str
        }
        Strategy:
        - Prefer JSON if present (```json ...``` or first {...} block)
        - Else, extract bullet/numbered list items as insights
        - Extract Obsidian-style [[Concept]] mentions as concepts
        """
        # 1) Try to extract JSON in code fence ```json ... ```
        fenced = self._extract_json_fenced(response)
        if fenced is not None:
            return fenced

        # 2) Try to extract first {...} JSON block
        json_block = self._extract_first_json_object(response)
        if json_block is not None:
            return json_block

        # 3) Fallback parsing: bullets/numbered items as insights
        insights: List[str] = []
        bullet_pattern = re.compile(r"^\s*[-•*]\s+(.+)$")
        number_pattern = re.compile(r"^\s*\d+\.\s+(.+)$")
        for line in response.splitlines():
            m = bullet_pattern.match(line) or number_pattern.match(line)
            if m:
                text = m.group(1).strip()
                if len(text) > 20:
                    insights.append(text)

        # Extract Obsidian-style concepts [[...]]
        concepts = []
        for match in re.finditer(r"\[\[([^\]]+)\]\]", response):
            name = match.group(1).strip()
            if name and name not in concepts:
                concepts.append(name)

        return {
            "insights": insights,
            "concepts": concepts,
            "notes": response.strip(),
        }

    def _extract_json_fenced(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Look for a fenced code block with json and parse it.
        """
        try:
            m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
            if m:
                return json.loads(m.group(1))
        except Exception as e:
            logger.debug(f"Failed to parse fenced JSON: {e}")
        return None

    def _extract_first_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Find the first {...} block that parses as JSON.
        """
        try:
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            logger.debug(f"Failed to parse inline JSON: {e}")
        return None
