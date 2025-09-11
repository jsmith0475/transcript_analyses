from __future__ import annotations

import csv
import io
import json
import re
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.models import AnalysisResult, ProcessedTranscript, TranscriptSegment


@dataclass
class Evidence:
    segment_id: Optional[int] = None
    speaker: Optional[str] = None
    timestamp: Optional[str] = None
    quote: Optional[str] = None


@dataclass
class InsightItem:
    insight_id: str
    type: str  # action | decision | risk
    title: str
    description: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[float] = None
    source_analyzer: Optional[str] = None
    evidence: Evidence = field(default_factory=Evidence)
    links: Optional[Dict[str, Any]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.setdefault("links", {})
        # flatten evidence dataclass
        d["evidence"] = asdict(self.evidence)
        return d


ACTION_PAT = re.compile(
    r"^\s*(?:-\s*\[\s*\]|\*|-)?\s*(?:Action(?:\s*#?\d+)?|Action Items?)\s*[:\-]\s*(.+)$",
    re.IGNORECASE,
)
DECISION_PAT = re.compile(
    r"^\s*(?:\*|-)?\s*(?:Decision(?:\s*#?\d+)?|Key Decisions?)\s*[:\-]\s*(.+)$",
    re.IGNORECASE,
)
RISK_PAT = re.compile(r"^\s*(?:\*|-)?\s*(?:Risk|Issue)\s*[:\-]\s*(.+)$", re.IGNORECASE)
OWNER_PAT = re.compile(r"\b(?:Assigned|Owner)\s*[:\-]\s*([^;,.\n]+)", re.IGNORECASE)
DUE_PAT = re.compile(r"\b(?:Due|Due Date|by)\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", re.IGNORECASE)
QUOTE_HINT = re.compile(r"\“([^\”]+)\”|\"([^\"]+)\"|([^\u001d]+)")


def _mk_id() -> str:
    return str(uuid.uuid4())

ANCHOR_PAT = re.compile(r"\[#?seg-(\d+)\]", re.IGNORECASE)

def _strip_and_capture_anchor(text: str) -> Tuple[str, Optional[str]]:
    """Remove [#seg-123] tokens from text and return (clean_text, anchor)."""
    if not text:
        return "", None
    m = ANCHOR_PAT.search(text)
    anchor = None
    if m:
        seg = m.group(1)
        anchor = f"#seg-{seg}"
        text = ANCHOR_PAT.sub("", text).strip()
    return text.strip(), anchor

def _apply_anchor(it: InsightItem, anchor: Optional[str]) -> None:
    if not anchor:
        return
    it.links = it.links or {}
    it.links["transcript_anchor"] = anchor

def _from_json_block(an_name: str, raw_text: str) -> List[InsightItem]:
    """Extract items from a fenced JSON block, preferably labeled INSIGHTS_JSON."""
    items: List[InsightItem] = []
    if not raw_text:
        return items
    try:
        pat1 = re.compile(r"INSIGHTS_JSON.*?```json\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)
        m = pat1.search(raw_text)
        if not m:
            pat2 = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
            m = pat2.search(raw_text)
        if not m:
            return items
        obj = json.loads(m.group(1))
        for itype, label in (("actions", "action"), ("decisions", "decision"), ("risks", "risk")):
            arr = obj.get(itype) or []
            for entry in arr:
                if isinstance(entry, str):
                    title, anchor = _strip_and_capture_anchor(entry)
                    it = InsightItem(insight_id=_mk_id(), type=label, title=title, source_analyzer=an_name)
                    _apply_anchor(it, anchor)
                    items.append(it)
                elif isinstance(entry, dict):
                    title = (entry.get("title") or entry.get("text") or "").strip()
                    title, anchor = _strip_and_capture_anchor(title)
                    if not title:
                        continue
                    it = InsightItem(
                        insight_id=_mk_id(),
                        type=label,
                        title=title,
                        description=entry.get("description"),
                        owner=entry.get("owner"),
                        due_date=entry.get("due_date") or entry.get("due"),
                        priority=entry.get("priority"),
                        confidence=entry.get("confidence"),
                        source_analyzer=an_name,
                    )
                    # explicit anchor field or captured from title
                    _apply_anchor(it, entry.get("anchor") or anchor)
                    items.append(it)
    except Exception as e:
        logger.debug(f"INSIGHTS_JSON parse skipped: {e}")
    return items


def _from_structured(an_name: str, sd: Dict[str, Any]) -> List[InsightItem]:
    items: List[InsightItem] = []
    # 1) Canonical keys used by some analyzers
    for key, itype in (("action_items", "action"), ("key_decisions", "decision"), ("risks", "risk")):
        data = sd.get(key) or []
        for entry in data:
            if isinstance(entry, str):
                title = entry.strip()
                if title:
                    items.append(InsightItem(insight_id=_mk_id(), type=itype, title=title, source_analyzer=an_name))
            elif isinstance(entry, dict):
                title = (entry.get("title") or entry.get("text") or "").strip()
                if not title:
                    continue
                items.append(
                    InsightItem(
                        insight_id=_mk_id(),
                        type=itype,
                        title=title,
                        description=entry.get("description"),
                        owner=entry.get("owner"),
                        due_date=entry.get("due_date"),
                        priority=entry.get("priority"),
                        confidence=entry.get("confidence"),
                        source_analyzer=an_name,
                    )
                )

    # 2) Lightweight extraction from sectioned markdown structures (Final analyzers)
    try:
        sections = sd.get("sections") or {}
        if isinstance(sections, dict) and sections:
            # Normalize: map section title -> text
            norm = {str(k).strip().lower(): (v or "") for k, v in sections.items()}

            def _lines(txt: str) -> List[str]:
                return [l.strip(" -\t") for l in (txt or "").splitlines() if l.strip()]

            # helper: push or merge owner/due fragments
            def _append_or_merge(container: List[InsightItem], label: str, line: str):
                ll = line.strip()
                if not ll:
                    return
                # Owner/Due fragments update last actionable item
                if OWNER_PAT.search(ll):
                    owner = _extract_owner(ll)
                    if container and container[-1].type in ("action", "decision"):
                        if owner and not container[-1].owner:
                            container[-1].owner = owner
                    return
                if DUE_PAT.search(ll):
                    due = _extract_due(ll)
                    if container and container[-1].type in ("action", "decision"):
                        if due and not container[-1].due_date:
                            container[-1].due_date = due
                    return
                # Strip leading prefixes like "Action:" or bullets
                ll = re.sub(r"^(action|decision|risk)\s*[:\-]\s*", "", ll, flags=re.IGNORECASE).strip()
                title, anchor = _strip_and_capture_anchor(ll)
                container.append(InsightItem(insight_id=_mk_id(), type=label, title=title, source_analyzer=an_name))
                _apply_anchor(container[-1], anchor)

            # Exact-key pulls (common)
            exact_decision_keys = ("decision", "decisions", "key decisions", "key_decisions")
            exact_action_keys = (
                "actions",
                "action items",
                "action_items",
                "next steps",
                "next_steps",
                "immediate next steps",
                "immediate next steps (1–2 weeks)",
            )
            exact_risk_keys = ("risks", "risk", "issues", "open questions", "concerns")

            for key in exact_decision_keys:
                if key in norm:
                    for l in _lines(norm[key]):
                        if l.lower().startswith("decisions"):
                            continue
                        _append_or_merge(items, "decision", l)

            for key in exact_action_keys:
                if key in norm:
                    for l in _lines(norm[key]):
                        if l.lower().startswith("actions"):
                            continue
                        _append_or_merge(items, "action", l)

            for key in exact_risk_keys:
                if key in norm:
                    for l in _lines(norm[key]):
                        if l.lower().startswith("risks") or l.lower().startswith("open questions"):
                            continue
                        _append_or_merge(items, "risk", l)

            # Fuzzy-key pulls to catch headings like "Action items (explicit...)" or "Key decisions and positions"
            for k, v in norm.items():
                lk = k.lower()
                if any(token in lk for token in ("decision", "key decision")):
                    for l in _lines(v):
                        _append_or_merge(items, "decision", l)
                if any(token in lk for token in ("action", "next step", "todo", "task")):
                    for l in _lines(v):
                        _append_or_merge(items, "action", l)
                if any(token in lk for token in ("risk", "concern", "issue", "open question")):
                    for l in _lines(v):
                        _append_or_merge(items, "risk", l)
    except Exception as e:
        logger.debug(f"Section-based structured extraction skipped: {e}")

    return items


def _heuristics_from_text(an_name: str, text: str) -> List[InsightItem]:
    items: List[InsightItem] = []
    last: Optional[InsightItem] = None
    for raw in (text or "").splitlines():
        l = raw.strip()
        if not l:
            continue
        # Primary detections
        m = ACTION_PAT.match(l)
        if m:
            title = m.group(1).strip()
            owner = _extract_owner(l)
            due = _extract_due(l)
            it = InsightItem(
                insight_id=_mk_id(), type="action", title=title, owner=owner, due_date=due, source_analyzer=an_name
            )
            items.append(it)
            last = it
            continue
        m = DECISION_PAT.match(l)
        if m:
            title = m.group(1).strip()
            it = InsightItem(insight_id=_mk_id(), type="decision", title=title, source_analyzer=an_name)
            items.append(it)
            last = it
            continue
        m = RISK_PAT.match(l)
        if m:
            title = m.group(1).strip()
            it = InsightItem(insight_id=_mk_id(), type="risk", title=title, source_analyzer=an_name)
            items.append(it)
            last = it
            continue
        # Secondary attachments: Owner/Due lines that follow an Action/Decision
        if last and last.type in ("action", "decision"):
            owner = _extract_owner(l)
            due = _extract_due(l)
            if owner and not last.owner:
                last.owner = owner
            if due and not last.due_date:
                last.due_date = due
    return items


def _extract_owner(text: str) -> Optional[str]:
    m = OWNER_PAT.search(text or "")
    if m:
        return m.group(1).strip()
    # simple @owner hint
    m2 = re.search(r"@([A-Za-z0-9_\-\.]+)", text or "")
    return m2.group(1) if m2 else None


def _extract_due(text: str) -> Optional[str]:
    m = DUE_PAT.search(text or "")
    if m:
        return m.group(1).strip()
    return None


def _attach_evidence(items: List[InsightItem], segments: List[TranscriptSegment]) -> None:
    if not items or not segments:
        return
    # Build quick search index by lower text
    lower_segments = [(seg.segment_id, (seg.speaker or ""), (seg.timestamp or ""), (seg.text or "")) for seg in segments]
    for it in items:
        # Try to find a quoted snippet in title/description to anchor
        quote = None
        for src in (it.title, it.description):
            if not src:
                continue
            mq = QUOTE_HINT.search(src)
            if mq:
                quote = next((g for g in mq.groups() if g), None)
                if quote:
                    break
        # naive matching: first segment that contains a significant piece of title or quote
        needle = (quote or it.title or "").lower()[:120]
        chosen = None
        for seg_id, spk, ts, txt in lower_segments:
            if not txt:
                continue
            if _similar_substring(needle, txt):
                chosen = (seg_id, spk, ts, txt)
                break
        if chosen:
            it.evidence.segment_id = chosen[0]
            it.evidence.speaker = chosen[1]
            it.evidence.timestamp = chosen[2]
            # short quote preview
            it.evidence.quote = (chosen[3][:200]).strip()
            it.links = it.links or {}
            it.links["transcript_anchor"] = f"#seg-{chosen[0]}"


def _similar_substring(needle: str, hay: str) -> bool:
    if not needle or not hay:
        return False
    # simple containment with loosened spaces
    n = re.sub(r"\s+", " ", needle)
    h = re.sub(r"\s+", " ", hay)
    return n[:40] in h


def aggregate_insights(
    results: Dict[str, AnalysisResult],
    transcript: Optional[ProcessedTranscript] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Aggregate Actions/Decisions/Risks from structured_data first, then heuristics."""
    items: List[InsightItem] = []
    # 0) JSON-first extraction from raw output blocks
    for an, res in (results or {}).items():
        text = (res.raw_output or "")
        if text:
            items.extend(_from_json_block(an, text))
    # 1) Structured sections (from parse_response)
    for an, res in (results or {}).items():
        try:
            sd = res.structured_data or {}
        except Exception:
            sd = {}
        if sd:
            items.extend(_from_structured(an, sd))
    # 2) Heuristic fallback from raw_output
    for an, res in (results or {}).items():
        text = (res.raw_output or "")
        if not text:
            continue
        items.extend(_heuristics_from_text(an, text))
    # Evidence linking
    try:
        segs = list((transcript.segments or [])) if transcript else []
        _attach_evidence(items, segs)
    except Exception as e:
        logger.debug(f"Evidence linking skipped: {e}")
    # Dedupe naive by (type,title,owner,due)
    unique: Dict[Tuple[str, str, Optional[str], Optional[str]], InsightItem] = {}
    for it in items:
        key = (it.type, (it.title or "").lower().strip(), (it.owner or None), (it.due_date or None))
        if key not in unique:
            unique[key] = it
    final_items = list(unique.values())
    counts = {
        "total": len(final_items),
        "actions": sum(1 for i in final_items if i.type == "action"),
        "decisions": sum(1 for i in final_items if i.type == "decision"),
        "risks": sum(1 for i in final_items if i.type == "risk"),
    }
    return [it.to_dict() for it in final_items], counts


def dedupe_items_dict(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique: Dict[Tuple[str, str, Optional[str], Optional[str]], Dict[str, Any]] = {}
    for it in items or []:
        key = (
            str(it.get("type", "")).lower().strip(),
            str(it.get("title") or it.get("summary") or "").lower().strip(),
            it.get("owner"),
            it.get("due_date") or it.get("due"),
        )
        if key not in unique:
            unique[key] = it
    return list(unique.values())


def count_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "total": len(items or []),
        "actions": sum(1 for i in (items or []) if (i.get("type") == "action")),
        "decisions": sum(1 for i in (items or []) if (i.get("type") == "decision")),
        "risks": sum(1 for i in (items or []) if (i.get("type") == "risk")),
    }


def to_json(items: List[Dict[str, Any]]) -> str:
    return json.dumps({"items": items, "generated_at": datetime.utcnow().isoformat() + "Z"}, indent=2)


def to_markdown(items: List[Dict[str, Any]], counts: Dict[str, int]) -> str:
    lines = ["# Insight Dashboard", ""]
    lines.append(f"Total: {counts.get('total', 0)} | Actions: {counts.get('actions', 0)} | Decisions: {counts.get('decisions', 0)} | Risks: {counts.get('risks', 0)}\n")
    lines.append("| Type | Title | Owner | Due | Source | Evidence |")
    lines.append("|---|---|---|---|---|---|")
    for it in items:
        ev = it.get("evidence") or {}
        src = it.get("source_analyzer") or ""
        owner = it.get("owner") or ""
        due = it.get("due_date") or ""
        title = (it.get("title") or "").replace("|", "\\|")
        etext = (ev.get("quote") or "").replace("|", "\\|")[:80]
        lines.append(f"| {it.get('type')} | {title} | {owner} | {due} | {src} | {etext} |")
    return "\n".join(lines) + "\n"


def to_csv(items: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    fieldnames = [
        "type",
        "title",
        "description",
        "owner",
        "due_date",
        "priority",
        "confidence",
        "source_analyzer",
        "evidence.segment_id",
        "evidence.speaker",
        "evidence.timestamp",
        "evidence.quote",
        "links.transcript_anchor",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for it in items:
        row = {
            "type": it.get("type"),
            "title": it.get("title"),
            "description": it.get("description"),
            "owner": it.get("owner"),
            "due_date": it.get("due_date"),
            "priority": it.get("priority"),
            "confidence": it.get("confidence"),
            "source_analyzer": it.get("source_analyzer"),
            "evidence.segment_id": (it.get("evidence") or {}).get("segment_id"),
            "evidence.speaker": (it.get("evidence") or {}).get("speaker"),
            "evidence.timestamp": (it.get("evidence") or {}).get("timestamp"),
            "evidence.quote": (it.get("evidence") or {}).get("quote"),
            "links.transcript_anchor": (it.get("links") or {}).get("transcript_anchor"),
        }
        writer.writerow(row)
    return output.getvalue()
