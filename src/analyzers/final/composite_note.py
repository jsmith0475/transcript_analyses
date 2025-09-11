#!/usr/bin/env python3
"""
Final stage generator: Composite Note
Synthesizes Stage A + Stage B results (and optionally the transcript)
into a single Obsidian-friendly composite document.
"""
from __future__ import annotations

from typing import Dict, Any
from src.analyzers.base_analyzer import BaseAnalyzer


class CompositeNoteAnalyzer(BaseAnalyzer):
    def __init__(self) -> None:
        super().__init__(name="composite_note", stage="final")

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Composite note is primarily markdown. Provide a light structure that higher
        layers can reason about if needed.
        """
        # Basic section extraction (optional)
        sections: Dict[str, Any] = {}
        current = None
        for line in response.splitlines():
            if line.strip().startswith("#"):
                current = line.strip().lstrip("#").strip().lower()
                sections[current] = []
            else:
                if current:
                    sections[current].append(line)
        if sections:
            sections = {k: "\n".join(v).strip() for k, v in sections.items()}

        return {
            "format": "markdown",
            "sections": sections,
            "length_chars": len(response),
        }
