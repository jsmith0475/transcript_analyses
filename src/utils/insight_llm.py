from __future__ import annotations

import json
from typing import Dict, Any, List, Optional

from loguru import logger

from src.models import ProcessedTranscript, AnalysisResult


def build_segmented_transcript(pt: ProcessedTranscript, max_segments: Optional[int] = None) -> str:
    lines: List[str] = []
    segments = pt.segments or []
    if max_segments is not None:
        segments = segments[: max(1, max_segments)]
    for seg in segments:
        prefix = f"SEG {seg.segment_id}"
        if seg.timestamp:
            prefix += f" [{seg.timestamp}]"
        speaker = seg.speaker or "Unknown"
        lines.append(f"{prefix} {speaker}: {seg.text}")
    return "\n\n".join(lines)


def build_combined_context(results: Dict[str, AnalysisResult]) -> str:
    lines: List[str] = []
    for name, res in (results or {}).items():
        try:
            lines.append(res.to_context_string())
            lines.append("\n---\n")
        except Exception:
            continue
    return "\n".join(lines)


def _schema_text() -> str:
    # A simple, robust schema description the model can follow deterministically.
    return (
        "Return a single JSON object with this shape:\n"
        "{\n"
        "  \"items\": [\n"
        "    {\n"
        "      \"type\": \"action|decision|risk\",\n"
        "      \"summary\": \"short one-line summary\",\n"
        "      \"owner\": \"name or team or null\",\n"
        "      \"due\": \"YYYY-MM-DD or freeform or null\",\n"
        "      \"source\": \"meeting_notes|analyzer|transcript\",\n"
        "      \"evidence\": {\n"
        "         \"segment_ids\": [int],\n"
        "         \"speakers\": [\"...\"],\n"
        "         \"timestamps\": [\"...\"],\n"
        "         \"quotes\": [\"short quotes\"],\n"
        "         \"confidence\": 0.0\n"
        "      }\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Ensure valid JSON. Do not include any text outside the JSON. Limit items to the requested maximum."
    )


def extract_insights_llm(
    llm_client,
    segmented_transcript: str,
    combined_context: str,
    max_items: int = 50,
    model: Optional[str] = None,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """Call LLM to extract structured insights. Returns parsed JSON {items:[...]}."""
    system = (
        "You extract Actions, Decisions, and Risks from the provided context and segmented transcript.\n"
        "Use only the provided content. Ground evidence with SEGMENT IDs."
    )
    prompt = []
    prompt.append("## Context (A+B)\n")
    prompt.append(combined_context or "(none)")
    prompt.append("\n\n## Segmented Transcript\n")
    prompt.append(segmented_transcript or "(none)")
    prompt.append("\n\n## Instructions\n")
    prompt.append(f"Extract up to {max_items} items. Use the schema below.\n")
    prompt.append(_schema_text())
    full = "".join(prompt)
    try:
        response_text, _ = llm_client.complete_sync(
            prompt=full,
            system_prompt=system,
            temperature=0,
            max_tokens=max_tokens,
            model=model or None,
        )
        # Parse JSON: accept object with items or bare array
        try:
            text = response_text.strip()
            if text.startswith("["):
                obj = {"items": json.loads(text)}
            else:
                obj = json.loads(text)
            if not isinstance(obj, dict):
                raise ValueError("LLM did not return a JSON object")
            obj.setdefault("items", [])
            # Simple post-filter: enforce max_items
            if isinstance(obj["items"], list) and len(obj["items"]) > max_items:
                obj["items"] = obj["items"][:max_items]
            return obj
        except Exception as pe:
            logger.warning(f"Failed to parse LLM insights JSON: {pe}")
            return {"items": []}
    except Exception as e:
        logger.error(f"LLM insights extraction failed: {e}")
        return {"items": []}

