#!/usr/bin/env python3
"""
Final stage generator: Meeting Notes
Consumes Stage A + Stage B combined context (and optionally the transcript)
and produces Obsidian-friendly meeting notes markdown.
"""
from __future__ import annotations

from typing import Dict, Any
from src.analyzers.base_analyzer import BaseAnalyzer


class MeetingNotesAnalyzer(BaseAnalyzer):
    def __init__(self) -> None:
        super().__init__(name="meeting_notes", stage="final")

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Meeting notes are primarily free-form markdown. We return a minimal
        structured payload for potential downstream aggregation without enforcing
        a rigid schema (avoids brittleness).
        """
        # Lightweight section sniffing (optional)
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
            # Join lines within sections
            sections = {k: "\n".join(v).strip() for k, v in sections.items()}

        return {
            "format": "markdown",
            "sections": sections,
            "length_chars": len(response),
        }
