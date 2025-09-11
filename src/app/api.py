"""
API blueprint for the Transcript Analysis Tool.

Endpoints:
- GET /api/health
- GET /api/config
- POST /api/smoke-openai  (real OpenAI call using .env key)
- POST /api/analyze       (stub orchestration; enqueues jobId and emits job.queued)
- GET /api/results/<job_id> (stub results store)
"""

from __future__ import annotations

import time
import uuid
import json
from typing import Any, Dict, List, Tuple, Optional

from flask import Blueprint, jsonify, request
from pathlib import Path
import os
import re

from src.config import get_config, reset_config
from src.llm_client import get_llm_client
from .sockets import job_queued
from src.transcript_processor import get_transcript_processor
from src.models import AnalysisContext
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from redis import from_url as redis_from_url
from src.app.orchestration import run_pipeline

api_bp = Blueprint("api", __name__)

# In-memory job store for dev (non-persistent; placeholder until Redis/Celery wired)
_job_store: Dict[str, Dict[str, Any]] = {}

def _get_redis():
    cfg = get_config()
    url = cfg.web.redis_url
    if url.rstrip("/").count("/") == 2:
        url = f"{url}/{cfg.web.redis_db}"
    return redis_from_url(url)

def _redis_key(job_id: str) -> str:
    return f"job:{job_id}"

# Prompt discovery and validation helpers
PROMPTS_DIRS = {
    "stage_a": Path("prompts") / "stage a transcript analyses",
    "stage_b": Path("prompts") / "stage b results analyses",
    "final": Path("prompts") / "final output stage",
}

def _analyzer_stage_map() -> Dict[str, str]:
    cfg = get_config()
    mapping: Dict[str, str] = {}
    for name in cfg.stage_a_analyzers:
        mapping[name] = "stage_a"
    for name in cfg.stage_b_analyzers:
        mapping[name] = "stage_b"
    for name in cfg.final_stage_analyzers:
        mapping[name] = "final"
    return mapping

def _list_prompt_files(dir_path: Path) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    try:
        if dir_path.exists():
            for p in sorted(dir_path.glob("*.md")):
                files.append({"name": p.name, "path": str(p)})
    except Exception:
        pass
    return files

_VAR_PATTERNS = {
    "stage_a": re.compile(r"{{\s*transcript\b"),
    "stage_b": re.compile(r"{{\s*context\b"),
    "final": re.compile(r"{{\s*context\b"),
}

def _validate_prompt_vars_for_stage(file_path: Path, stage: str) -> bool:
    try:
        txt = file_path.read_text(encoding="utf-8")
    except Exception:
        return False
    pat = _VAR_PATTERNS.get(stage)
    if not pat:
        return False
    return bool(pat.search(txt))

def _is_within_prompts(path_obj: Path) -> bool:
    try:
        root = (Path.cwd() / "prompts").resolve()
        return str(path_obj.resolve()).startswith(str(root))
    except Exception:
        return False

def _clean_prompt_selection(selection: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate and sanitize promptSelection mapping.
    Returns (cleaned_selection, errors)
    """
    errors: List[str] = []
    cleaned: Dict[str, Any] = {"stageA": {}, "stageB": {}, "final": {}}
    amap = _analyzer_stage_map()
    # Normalize keys
    stage_map_keys = {
        "stageA": "stage_a",
        "stageB": "stage_b",
        "final": "final",
    }
    for stage_key_ui, analyzers in (selection or {}).items():
        analyzers = analyzers or {}
        norm_stage = stage_map_keys.get(stage_key_ui)
        if not norm_stage:
            continue
        for analyzer, file_path in analyzers.items():
            if analyzer not in amap:
                errors.append(f"Unknown analyzer: {analyzer}")
                continue
            stage_for_analyzer = amap[analyzer]
            if stage_for_analyzer != norm_stage:
                errors.append(f"Analyzer {analyzer} not in stage {norm_stage}")
                continue
            p = Path(file_path)
            if not _is_within_prompts(p) or not p.exists() or p.suffix.lower() != ".md":
                errors.append(f"Invalid prompt path for {analyzer}: {file_path}")
                continue
            if not _validate_prompt_vars_for_stage(p, norm_stage):
                errors.append(f"Prompt missing required variables for {analyzer}: {file_path}")
                continue
            cleaned[stage_key_ui][analyzer] = str(p)
    return cleaned, errors

@api_bp.get("/prompt-options")
def api_prompt_options():
    """
    List available prompt templates per stage and per analyzer, and identify defaults.
    """
    # Proactively discover prompt files so newly-added *.md appear without manual rescan
    try:
        _ = discover_prompts_to_registry()
        _ = cleanup_registry()
        reset_config()
    except Exception:
        pass
    cfg = get_config()
    options: Dict[str, Any] = {
        "stageA": {},
        "stageB": {},
        "final": {},
    }
    # Stage directories
    dirs = {
        "stageA": PROMPTS_DIRS["stage_a"],
        "stageB": PROMPTS_DIRS["stage_b"],
        "final": PROMPTS_DIRS["final"],
    }
    # Build per-analyzer options using directory listing; mark defaults
    for name in cfg.stage_a_analyzers:
        default_path = str(cfg.get_prompt_path(name))
        files = _list_prompt_files(dirs["stageA"])
        for f in files:
            try:
                f["isDefault"] = (str(Path(f["path"]).resolve()) == str(Path(default_path).resolve()))
            except Exception:
                f["isDefault"] = False
        options["stageA"][name] = {"default": default_path, "options": files}
    for name in cfg.stage_b_analyzers:
        default_path = str(cfg.get_prompt_path(name))
        files = _list_prompt_files(dirs["stageB"])
        for f in files:
            try:
                f["isDefault"] = (str(Path(f["path"]).resolve()) == str(Path(default_path).resolve()))
            except Exception:
                f["isDefault"] = False
        options["stageB"][name] = {"default": default_path, "options": files}
    for name in cfg.final_stage_analyzers:
        default_path = str(cfg.get_prompt_path(name))
        files = _list_prompt_files(dirs["final"])
        for f in files:
            try:
                f["isDefault"] = (str(Path(f["path"]).resolve()) == str(Path(default_path).resolve()))
            except Exception:
                f["isDefault"] = False
        options["final"][name] = {"default": default_path, "options": files}
    return jsonify({"ok": True, "options": options})

def _infer_stage_from_path(p: Path) -> Optional[str]:
    try:
        rp = str(p.resolve()).lower()
    except Exception:
        return None
    if "stage a transcript analyses" in rp:
        return "stage_a"
    if "stage b results analyses" in rp:
        return "stage_b"
    if "final output stage" in rp:
        return "final"
    return None


def _normalize_stage_param(s: str) -> Optional[str]:
    s = (s or "").strip().lower()
    if s in ("a", "stagea", "stage_a"):
        return "stage_a"
    if s in ("b", "stageb", "stage_b"):
        return "stage_b"
    if s in ("f", "final", "final_stage"):
        return "final"
    return None


def _default_template_for_stage(stage: str) -> str:
    """
    Return a minimal, stage-appropriate template that satisfies variable requirements.
    """
    if stage == "stage_a":
        return "## Inputs\n\nTRANSCRIPT (required)\n{{ transcript }}\n"
    if stage == "stage_b":
        return "## Inputs\n\nCONTEXT (Combined Stage A results)\n{{ context }}\n"
    if stage == "final":
        return (
            "## Inputs\n\n"
            "CONTEXT (Combined Stage A and Stage B results)\n"
            "{{ context }}\n\n"
            "TRANSCRIPT (optional)\n"
            "{{ transcript }}\n"
        )
    return "## Inputs\n\n{{ context }}\n"


@api_bp.get("/prompt-template")
def api_prompt_template():
    """
    Return a default blank template for a given stage that includes required variables.
    Query params:
      - stage: stage_a | stage_b | final (also accepts A|B|Final)
    Returns: { ok, stage, template }
    """
    stage_param = (request.args.get("stage") or "").strip()
    norm = _normalize_stage_param(stage_param)
    if not norm:
        return jsonify({"ok": False, "error": "Invalid stage"}), 400
    try:
        tmpl = _default_template_for_stage(norm)
        return jsonify({"ok": True, "stage": norm, "template": tmpl})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to build template: {e}"}), 500

@api_bp.get("/prompts")
def api_get_prompt():
    """
    Fetch prompt file content.
    Query params:
      - path: absolute or relative path under prompts/ (preferred)
      - analyzer: optional analyzer slug to resolve default path (e.g., say_means)
    Returns: { ok, path, stage, analyzer?, content }
    """
    cfg = get_config()
    path_param = (request.args.get("path") or "").strip()
    analyzer = (request.args.get("analyzer") or "").strip()

    prompt_path: Optional[Path] = None
    if path_param:
        p = Path(path_param)
        if not _is_within_prompts(p) or not p.exists() or p.suffix.lower() != ".md":
            return jsonify({"ok": False, "error": "Invalid prompt path"}), 400
        prompt_path = p
    elif analyzer:
        try:
            prompt_path = cfg.get_prompt_path(analyzer)
        except Exception:
            return jsonify({"ok": False, "error": f"Unknown analyzer: {analyzer}"}), 400
    else:
        return jsonify({"ok": False, "error": "Provide 'path' or 'analyzer'"}), 400

    try:
        content = prompt_path.read_text(encoding="utf-8")
        stage = _infer_stage_from_path(prompt_path) or "unknown"
        return jsonify({"ok": True, "path": str(prompt_path), "stage": stage, "analyzer": analyzer or None, "content": content})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to read prompt: {e}"}), 500

@api_bp.post("/prompts")
def api_save_prompt():
    """
    Save prompt file content.
    Body: { path: str, content: str }
    Validates the path is under prompts/, enforces .md, and checks stage variables.
    """
    data = request.get_json(silent=True) or {}
    path_param = (data.get("path") or "").strip()
    content = data.get("content")
    if not path_param or content is None:
        return jsonify({"ok": False, "error": "path and content are required"}), 400

    p = Path(path_param)
    if not _is_within_prompts(p) or p.suffix.lower() != ".md":
        return jsonify({"ok": False, "error": "Invalid prompt path"}), 400

    # Determine stage to validate required variables
    stage = _infer_stage_from_path(p)
    if not stage:
        return jsonify({"ok": False, "error": "Unable to infer stage from path"}), 400

    # Temp file validation using regex patterns
    try:
        pat = _VAR_PATTERNS.get(stage)
        if pat and not pat.search(content):
            return jsonify({"ok": False, "error": f"Prompt missing required variables for stage: {stage}"}), 400
    except Exception:
        pass

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return jsonify({"ok": True, "path": str(p), "stage": stage})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to save prompt: {e}"}), 500

@api_bp.delete("/prompts")
def api_delete_prompt():
    """
    Delete a single prompt file under prompts/.
    Accepts either JSON body or query params:
      - path: absolute or relative path under prompts/ (preferred)
      - analyzer: optional analyzer slug to resolve default path
    Returns: { ok, deleted: true, path }
    """
    data = request.get_json(silent=True) or {}
    path_param = (data.get("path") or request.args.get("path") or "").strip()
    analyzer = (data.get("analyzer") or request.args.get("analyzer") or "").strip()

    cfg = get_config()
    prompt_path: Optional[Path] = None
    if path_param:
        p = Path(path_param)
        if not _is_within_prompts(p) or p.suffix.lower() != ".md" or not p.exists():
            return jsonify({"ok": False, "error": "Invalid prompt path"}), 400
        prompt_path = p
    elif analyzer:
        try:
            p = cfg.get_prompt_path(analyzer)
            if not _is_within_prompts(p) or p.suffix.lower() != ".md" or not p.exists():
                return jsonify({"ok": False, "error": "Resolved prompt path invalid or missing"}), 400
            prompt_path = p
        except Exception:
            return jsonify({"ok": False, "error": f"Unknown analyzer: {analyzer}"}), 400
    else:
        return jsonify({"ok": False, "error": "Provide 'path' or 'analyzer'"}), 400

    try:
        prompt_path.unlink()
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to delete: {e}"}), 500

    # Refresh registry/config so UI reflects removal
    try:
        summary = rebuild_registry_from_prompts()
        reset_config(); _ = get_config()
    except Exception:
        summary = None

    return jsonify({"ok": True, "deleted": True, "path": str(prompt_path), "registry": summary})

@api_bp.post("/prompts/reset")
def api_reset_prompt():
    """
    Reset prompt to default path for an analyzer (path selection reset).
    Note: Content reset to original baseline is not implemented (no defaults snapshot yet).
    Body: { analyzer: str }
    Returns: { ok, defaultPath }
    """
    data = request.get_json(silent=True) or {}
    analyzer = (data.get("analyzer") or "").strip()
    if not analyzer:
        return jsonify({"ok": False, "error": "analyzer is required"}), 400
    try:
        default_path = get_config().get_prompt_path(analyzer)
        # Do not overwrite file content; just report default mapping path.
        return jsonify({"ok": True, "defaultPath": str(default_path)})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Unknown analyzer or default not found: {e}"}), 400


@api_bp.delete("/prompts/all")
def api_delete_all_prompts():
    """
    Danger: Delete all prompt files (*.md) under prompts/ recursively, regardless of origin.
    Body: { confirm: true }
    Returns: { ok, deleted: number, errors: [ { path, error } ] }
    """
    data = request.get_json(silent=True) or {}
    if not bool(data.get("confirm")):
        return jsonify({"ok": False, "error": "Confirmation required: set { confirm: true }"}), 400

    root = Path("prompts")
    if not root.exists():
        return jsonify({"ok": True, "deleted": 0, "errors": []})

    deleted = 0
    errors = []
    try:
        for p in root.rglob("*.md"):
            try:
                # Extra safety: ensure path is within prompts/
                if not _is_within_prompts(p):
                    continue
                if p.exists():
                    p.unlink()
                    deleted += 1
            except Exception as e:
                errors.append({"path": str(p), "error": str(e)})
    except Exception as e:
        return jsonify({"ok": False, "error": f"scan_failed: {e}"}), 500

    # Rebuild registry and reset config to reflect file removal
    try:
        summary = rebuild_registry_from_prompts()
        reset_config(); _ = get_config()
    except Exception:
        summary = None

    return jsonify({"ok": True, "deleted": deleted, "errors": errors, "registry": summary})

# Analyzer Registry CRUD

from src.analyzers.registry import (
    load_registry,
    save_registry,
    validate_prompt_file_for_stage,
    create_prompt_file_from_content,
    is_valid_slug,
    is_builtin_slug,
    find_slug_stage,
    rebuild_registry_from_prompts,
    discover_prompts_to_registry,
    cleanup_registry,
)
from flask import session
from openai import OpenAI

def _stage_label_to_key(label: str) -> Optional[str]:
    s = (label or "").strip().lower()
    if s in ("a", "stagea", "stage_a"): return "stageA"
    if s in ("b", "stageb", "stage_b"): return "stageB"
    if s in ("f", "final", "final_stage"): return "final"
    return None

def _detect_stage_from_text(text: str) -> str:
    """Heuristic stage detection based on presence of Jinja vars and keywords."""
    t = (text or "").lower()
    has_ctx = "{{ context" in t
    has_tx = "{{ transcript" in t
    # If both appear, prefer Final
    if has_ctx and has_tx:
        return "final"
    if has_ctx:
        return "stageB"
    # Default to Stage A when only transcript or neither are present
    return "stageA"

def _normalize_prompt_text(raw: str, stage_key: str) -> str:
    """Wrap user-provided prompt into the standard tagged schema for the chosen stage."""
    raw = (raw or "").strip()
    # Indent original safely inside <instructions>
    def _indent(s: str, n: int = 4) -> str:
        pad = " " * n
        return "\n".join(pad + line if line.strip() else line for line in s.splitlines())

    if stage_key == "final":
        return (
            "<prompt>\n"
            "  <tags>#final #synthesis #insights</tags>\n\n"
            "  <role>Generate clear, scannable, actionable meeting outputs.</role>\n\n"
            "  <response_header_required>\n"
            "    At the very start of your response, output exactly one line:\n"
            "    Definition: <one sentence (≤ 20 words) describing this analysis in plain English>\n"
            "    Then leave one blank line and continue.\n"
            "  </response_header_required>\n\n"
            "  <inputs>\n"
            "    <context>{{ context }}</context>\n"
            "    <transcript optional=\"true\">{{ transcript }}</transcript>\n"
            "  </inputs>\n\n"
            "  <constraints>\n"
            "    - Do NOT include any angle-bracket tags in your output.\n"
            "    - Use Markdown headings exactly as specified.\n"
            "  </constraints>\n\n"
            "  <output_format>\n"
            "    <section name=\"Decisions\">- One decision per bullet line.</section>\n"
            "    <section name=\"Action Items\">- One action per bullet; include Owner and Due inline when available.</section>\n"
            "    <section name=\"Risks\">- One risk/concern per bullet line.</section>\n"
            "  </output_format>\n\n"
            "  <instructions>\n" + _indent(raw, 2) + "\n  </instructions>\n"
            "</prompt>\n"
        )
    elif stage_key == "stageB":
        return (
            "<prompt>\n"
            "  <tags>#stage-b #results-analysis</tags>\n\n"
            "  <role>Analyze combined Stage A results with optional transcript.</role>\n\n"
            "  <response_header_required>\n"
            "    At the very start of your response, output exactly one line:\n"
            "    Definition: <one sentence (≤ 20 words) describing this analysis in plain English>\n"
            "    Then leave one blank line and continue.\n"
            "  </response_header_required>\n\n"
            "  <inputs>\n"
            "    <context>{{ context }}</context>\n"
            "    <transcript optional=\"true\">{{ transcript }}</transcript>\n"
            "  </inputs>\n\n"
            "  <constraints>\n"
            "    - Do NOT include any angle-bracket tags in your output.\n"
            "    - Use clear, scannable headings.\n"
            "  </constraints>\n\n"
            "  <output_format>\n"
            "    <section name=\"Findings\">- Organize results with evidence.</section>\n"
            "  </output_format>\n\n"
            "  <instructions>\n" + _indent(raw, 2) + "\n  </instructions>\n"
            "</prompt>\n"
        )
    else:  # stageA
        return (
            "<prompt>\n"
            "  <tags>#stage-a #transcript-analysis</tags>\n\n"
            "  <role>Analyze the raw transcript and produce a structured, evidence-based report.</role>\n\n"
            "  <response_header_required>\n"
            "    At the very start of your response, output exactly one line:\n"
            "    Definition: <one sentence (≤ 20 words) describing this analysis in plain English>\n"
            "    Then leave one blank line and continue.\n"
            "  </response_header_required>\n\n"
            "  <inputs>\n"
            "    <transcript>{{ transcript }}</transcript>\n"
            "  </inputs>\n\n"
            "  <constraints>\n"
            "    - Do NOT include any angle-bracket tags in your output.\n"
            "    - Use clear headings and bullet points.\n"
            "  </constraints>\n\n"
            "  <output_format>\n"
            "    <section name=\"Analysis\">- Organize findings with clear headings and bullets.</section>\n"
            "  </output_format>\n\n"
            "  <instructions>\n" + _indent(raw, 2) + "\n  </instructions>\n"
            "</prompt>\n"
        )

@api_bp.post("/analyzers/normalize")
def api_normalize_prompt():
    """Normalize a free-form prompt into the standard tagged schema and detect stage."""
    data = request.get_json(silent=True) or {}
    raw = data.get("promptContent") or ""
    stage_param = (data.get("stage") or "").strip()
    if not raw.strip():
        return jsonify({"ok": False, "error": "promptContent required"}), 400
    # Detect stage if not provided/invalid
    stage_key = _stage_label_to_key(stage_param) or stage_param if stage_param in ("stageA", "stageB", "final") else None
    if not stage_key:
        stage_key = _detect_stage_from_text(raw)
    normalized = _normalize_prompt_text(raw, stage_key)
    return jsonify({"ok": True, "stageDetected": stage_key, "normalized": normalized})

@api_bp.get("/analyzers")
def api_list_analyzers():
    """
    Return merged analyzers (built-ins + custom).
    { ok, analyzers: [ { slug, stage, displayName, defaultPromptPath?, isBuiltIn } ] }
    """
    cfg = get_config()
    reg = load_registry()
    out = []

    def push(stage_key: str, slug: str):
        # Determine displayName
        display = (reg.get(stage_key, {}).get(slug, {}) or {}).get("displayName") or slug.replace("_", " ").title()
        # Resolve prompt path if possible
        default_path = None
        try:
            p = cfg.get_prompt_path(slug)
            default_path = str(p)
        except Exception:
            default_path = (reg.get(stage_key, {}).get(slug, {}) or {}).get("defaultPromptPath")
        out.append({
            "slug": slug,
            "stage": stage_key,
            "displayName": display,
            "defaultPromptPath": default_path,
            "isBuiltIn": is_builtin_slug(slug),
        })

    for s in (cfg.stage_a_analyzers or []):
        push("stageA", s)
    for s in (cfg.stage_b_analyzers or []):
        push("stageB", s)
    for s in (cfg.final_stage_analyzers or []):
        push("final", s)

    return jsonify({"ok": True, "analyzers": out})

@api_bp.post("/analyzers")
def api_create_analyzer():
    """
    Create a custom analyzer.
    Body: { stage: "A"|"B"|"Final", slug, displayName, promptContent?, defaultPromptPath? }
    """
    data = request.get_json(silent=True) or {}
    stage_label = (data.get("stage") or "")
    slug = (data.get("slug") or "").strip()
    display_name = (data.get("displayName") or "").strip()
    content = data.get("promptContent")
    default_path_param = (data.get("defaultPromptPath") or "").strip()

    stage_key = _stage_label_to_key(stage_label)
    if not stage_key:
        return jsonify({"ok": False, "error": "Invalid stage"}), 400
    if not is_valid_slug(slug):
        return jsonify({"ok": False, "error": "Invalid slug. Use snake_case alphanumerics."}), 400
    if is_builtin_slug(slug):
        return jsonify({"ok": False, "error": "Cannot override built-in analyzer"}), 400

    reg = load_registry()
    # Reject duplicates in registry
    if slug in (reg.get(stage_key) or {}):
        return jsonify({"ok": False, "error": "Analyzer slug already exists"}), 400
    # Also protect from duplicates present in built-in stage lists via config
    cfg = get_config()
    if stage_key == "stageA" and slug in (cfg.stage_a_analyzers or []):
        return jsonify({"ok": False, "error": "Analyzer slug already exists in Stage A"}), 400
    if stage_key == "stageB" and slug in (cfg.stage_b_analyzers or []):
        return jsonify({"ok": False, "error": "Analyzer slug already exists in Stage B"}), 400
    if stage_key == "final" and slug in (cfg.final_stage_analyzers or []):
        return jsonify({"ok": False, "error": "Analyzer slug already exists in Final"}), 400

    # Determine prompt path
    if content is not None and len((content or "").strip()) > 0:
        try:
            p = create_prompt_file_from_content(stage_key, slug, content or "")
        except Exception as e:
            return jsonify({"ok": False, "error": f"Failed to create prompt file: {e}"}), 500
        default_path = p
    else:
        if not default_path_param:
            return jsonify({"ok": False, "error": "Provide promptContent or defaultPromptPath"}), 400
        default_path = Path(default_path_param)

    ok, err = validate_prompt_file_for_stage(default_path, stage_key)
    if not ok:
        return jsonify({"ok": False, "error": err or "Invalid prompt file"}), 400

    # Persist in registry
    reg.setdefault(stage_key, {})
    reg[stage_key][slug] = {
        "displayName": display_name or slug.replace("_", " ").title(),
        "defaultPromptPath": str(default_path),
    }
    try:
        save_registry(reg)
        # Force config reload to merge registry
        reset_config()
        # Touch get_config() to rebuild
        _ = get_config()
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to persist analyzer: {e}"}), 500

    return jsonify({"ok": True, "slug": slug, "stage": stage_key, "defaultPromptPath": str(default_path)})

@api_bp.post("/analyzers/rescan")
def api_rescan_analyzers():
    """
    Rescan prompt directories and register any new prompt files as analyzers.
    Returns a summary of added/skipped/errors and refreshed analyzer list.
    """
    stage = (request.args.get("stage") or "").strip().lower()
    stage_map = {"a": "stageA", "stagea": "stageA", "stage_a": "stageA",
                 "b": "stageB", "stageb": "stageB", "stage_b": "stageB",
                 "f": "final", "final": "final", "final_stage": "final"}
    stage_key = stage_map.get(stage) if stage else None
    try:
        # Rebuild registry from filesystem (full rescan), limited to stage if provided
        # For simplicity, rebuild full registry always to avoid drift
        summary = rebuild_registry_from_prompts()
        reset_config(); _ = get_config()
        # Return updated analyzers list
        cfg = get_config()
        reg = load_registry()
        out = []
        def push(stage_key_ui: str, slug: str):
            display = (reg.get(stage_key_ui, {}).get(slug, {}) or {}).get("displayName") or slug.replace("_", " ").title()
            default_path = None
            try:
                p = cfg.get_prompt_path(slug)
                default_path = str(p)
            except Exception:
                default_path = (reg.get(stage_key_ui, {}).get(slug, {}) or {}).get("defaultPromptPath")
            out.append({
                "slug": slug,
                "stage": stage_key_ui,
                "displayName": display,
                "defaultPromptPath": default_path,
                "isBuiltIn": is_builtin_slug(slug),
            })
        for s in (cfg.stage_a_analyzers or []):
            push("stageA", s)
        for s in (cfg.stage_b_analyzers or []):
            push("stageB", s)
        for s in (cfg.final_stage_analyzers or []):
            push("final", s)
        return jsonify({"ok": True, "summary": summary, "analyzers": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@api_bp.put("/analyzers/<slug>")
def api_update_analyzer(slug: str):
    """
    Update a custom analyzer's displayName and/or defaultPromptPath.
    Body: { displayName?, defaultPromptPath? }
    """
    if is_builtin_slug(slug):
        return jsonify({"ok": False, "error": "Cannot modify built-in analyzer"}), 400

    data = request.get_json(silent=True) or {}
    display_name = data.get("displayName")
    default_path_param = data.get("defaultPromptPath")

    reg = load_registry()
    stage_key = find_slug_stage(reg, slug)
    if not stage_key:
        return jsonify({"ok": False, "error": "Analyzer not found"}), 404

    if default_path_param:
        p = Path(default_path_param)
        ok, err = validate_prompt_file_for_stage(p, stage_key)
        if not ok:
            return jsonify({"ok": False, "error": err or "Invalid prompt path"}), 400
        reg[stage_key][slug]["defaultPromptPath"] = str(p)

    if isinstance(display_name, str) and display_name.strip():
        reg[stage_key][slug]["displayName"] = display_name.strip()

    try:
        save_registry(reg)
        reset_config()
        _ = get_config()
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to update analyzer: {e}"}), 500

    return jsonify({"ok": True, "slug": slug, "stage": stage_key, "meta": reg[stage_key][slug]})

@api_bp.delete("/analyzers/<slug>")
def api_delete_analyzer(slug: str):
    """
    Delete a custom analyzer from the registry.
    Query: deleteFile=true to remove the prompt file as well (if under prompts/)
    """
    if is_builtin_slug(slug):
        return jsonify({"ok": False, "error": "Cannot delete built-in analyzer"}), 400

    delete_file = (request.args.get("deleteFile") or "").strip().lower() == "true"

    reg = load_registry()
    stage_key = find_slug_stage(reg, slug)
    if not stage_key:
        return jsonify({"ok": False, "error": "Analyzer not found"}), 404

    meta = reg[stage_key].pop(slug, None)

    # Optionally delete the prompt file
    removed_file = None
    if delete_file and meta and meta.get("defaultPromptPath"):
        p = Path(meta["defaultPromptPath"])
        try:
            from src.analyzers.registry import is_within_prompts
            if is_within_prompts(p) and p.exists():
                p.unlink()
                removed_file = str(p)
        except Exception:
            pass

    try:
        save_registry(reg)
        reset_config()
        _ = get_config()
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to delete analyzer: {e}"}), 500

    return jsonify({"ok": True, "slug": slug, "stage": stage_key, "removedFile": removed_file})

@api_bp.get("/health")
def api_health():
    cfg = get_config()
    return jsonify(
        {
            "status": "ok",
            "model": cfg.llm.model,
            "processing": {
                "parallel": cfg.processing.parallel,
                "max_concurrent": cfg.processing.max_concurrent,
            },
            "web": {
                "max_content_length": cfg.web.max_content_length,
                "upload_folder": str(cfg.web.upload_folder),
                "socketio_async_mode": cfg.web.socketio_async_mode,
            },
        }
    )


@api_bp.get("/config")
def api_config():
    cfg = get_config().to_dict()
    # Redact secrets if present
    if "llm" in cfg and "api_key" in cfg["llm"]:
        cfg["llm"]["api_key"] = "****"
    return jsonify(cfg)


# Per-user API key management (session-backed)
@api_bp.get("/user/key")
def api_user_key_status():
    """Return whether a per-user API key is set in the session (masked)."""
    present = bool(session.get('user_api_key'))
    # Also report whether a server-wide default API key is configured (.env)
    server_present = False
    server_masked = None
    server_valid = False
    try:
        cfg = get_config()
        if cfg and cfg.llm and cfg.llm.api_key:
            server_present = True
            k = cfg.llm.api_key or ""
            try:
                server_masked = ("****" + k[-4:]) if len(k) >= 4 else "****"
            except Exception:
                server_masked = "****"
            # Validate server key with a minimal metadata call
            try:
                from openai import OpenAI  # lazy import to avoid import cycles
                _client = OpenAI(api_key=cfg.llm.api_key)
                _ = _client.models.list()
                server_valid = True
            except Exception:
                server_valid = False
    except Exception:
        server_present = False
    masked = None
    if present:
        try:
            k = session.get('user_api_key', '')
            masked = ("****" + k[-4:]) if len(k) >= 4 else "****"
        except Exception:
            masked = "****"
    return jsonify({
        "ok": True,
        "present": present,
        "masked": masked,
        "serverPresent": server_present,
        "serverMasked": server_masked,
        "serverValid": server_valid,
    })


@api_bp.post("/user/key")
def api_user_key_set():
    """Set or update the per-user API key in the session."""
    data = request.get_json(silent=True) or {}
    api_key = (data.get('apiKey') or '').strip()
    if not api_key:
        return jsonify({"ok": False, "error": "apiKey required"}), 400
    # Minimal validation: typical OpenAI keys start with 'sk-' but allow others
    if len(api_key) < 20:
        return jsonify({"ok": False, "error": "apiKey appears invalid (too short)"}), 400
    session['user_api_key'] = api_key
    return jsonify({"ok": True})


@api_bp.delete("/user/key")
def api_user_key_delete():
    """Delete the per-user API key from the session."""
    try:
        session.pop('user_api_key', None)
    except Exception:
        pass
    return jsonify({"ok": True})


@api_bp.post("/user/key/validate")
def api_user_key_validate():
    """Validate a provided API key (or the one in session) by making a lightweight API call."""
    data = request.get_json(silent=True) or {}
    api_key = (data.get('apiKey') or '').strip() or session.get('user_api_key')
    if not api_key:
        return jsonify({"ok": False, "error": "No key provided and no key in session"}), 400
    try:
        client = OpenAI(api_key=api_key)
        # Low-cost/metadata-only call: list one model
        _ = client.models.list()
        return jsonify({"ok": True})
    except Exception as e:
        # Avoid leaking too much detail
        msg = str(e)
        return jsonify({"ok": False, "error": msg[:200]}), 400


@api_bp.post("/smoke-openai")
def api_smoke_openai():
    """
    Make a minimal real OpenAI call via LLMClient using your .env key.
    Keeps token usage very small to minimize cost.
    """
    cfg = get_config()
    payload = request.get_json(silent=True) or {}
    user_prompt = payload.get("prompt") or "Reply with exactly the single word: PONG"
    temperature = float(payload.get("temperature", 0))
    max_tokens = int(payload.get("max_tokens", 16))

    client = get_llm_client(use_cache=False)
    start = time.time()
    try:
        response_text, token_usage = client.complete_sync(
            prompt=user_prompt,
            system_prompt="You are a precise assistant. Follow user instructions exactly.",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed = time.time() - start
        return jsonify(
            {
                "ok": True,
                "model": cfg.llm.model,
                "response": response_text,
                "token_usage": token_usage.dict(),
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": str(e),
                }
            ),
            500,
        )


@api_bp.post("/analyze-now")
def api_analyze_now():
    """
    Synchronous, single-analyzer run for Say-Means (Stage A).
    Uses REAL OpenAI API via LLMClient. Returns AnalysisResult JSON.
    """
    data = request.get_json(silent=True) or {}
    transcript_text = (data.get("transcriptText") or "").strip()
    if not transcript_text:
        return jsonify({"ok": False, "error": "transcriptText is required"}), 400

    try:
        processor = get_transcript_processor()
        processed = processor.process(transcript_text, filename=None)

        ctx = AnalysisContext(
            transcript=processed,
            metadata={"source": "api.analyze-now"}
        )

        analyzer = SayMeansAnalyzer()
        result = analyzer.analyze_sync(ctx)

        payload = {
            "ok": (getattr(result.status, "value", str(result.status)) == "completed"),
            "analyzer": result.analyzer_name,
            "status": getattr(result.status, "value", str(result.status)),
            "processing_time": result.processing_time,
            "token_usage": result.token_usage.dict() if result.token_usage else None,
            "raw_output": result.raw_output,
            "structured_data": result.structured_data,
            "insights": [i.dict() for i in result.insights],
            "concepts": [c.dict() for c in result.concepts],
            "error_message": result.error_message,
        }
        return jsonify(payload)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@api_bp.get("/insights/<job_id>")
def api_insights(job_id: str):
    """
    Return the aggregated Insights Dashboard for a job, if present.
    Reads final/insight_dashboard.json under output/jobs/<jobId>/.
    """
    base = Path(f"output/jobs/{job_id}/final")
    json_path = base / "insight_dashboard.json"
    if not json_path.exists():
        return jsonify({"ok": False, "error": "insight dashboard not found"}), 404
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        counts = {
            "total": len(items),
            "actions": sum(1 for i in items if (i.get("type") == "action")),
            "decisions": sum(1 for i in items if (i.get("type") == "decision")),
            "risks": sum(1 for i in items if (i.get("type") == "risk")),
        }
        return jsonify({"ok": True, "jobId": job_id, "counts": counts, "items": items})
    except Exception as e:
        return jsonify({"ok": False, "error": f"failed to read insights: {e}"}), 500


@api_bp.get("/jobs")
def api_jobs():
    """
    List jobs under output/jobs sorted by most recent modification time.
    Returns: { ok, jobs: [ { jobId, mtime, hasInsights, hasFinal } ] }
    """
    base = Path("output/jobs")
    if not base.exists():
        return jsonify({"ok": True, "jobs": []})
    jobs = []
    try:
        for p in sorted((d for d in base.iterdir() if d.is_dir()), key=lambda x: x.stat().st_mtime, reverse=True):
            job_id = p.name
            mtime = int(p.stat().st_mtime)
            has_insights = (p / "final" / "insight_dashboard.json").exists()
            has_final = (p / "final").exists()
            jobs.append({"jobId": job_id, "mtime": mtime, "hasInsights": has_insights, "hasFinal": has_final})
    except Exception:
        pass
    return jsonify({"ok": True, "jobs": jobs})


@api_bp.get("/jobs/latest")
def api_jobs_latest():
    """
    Return the most recent job (by directory mtime) under output/jobs.
    { ok, jobId, mtime, hasInsights, hasFinal } or { ok: true, jobId: null }
    """
    base = Path("output/jobs")
    if not base.exists():
        return jsonify({"ok": True, "jobId": None})
    try:
        dirs = [d for d in base.iterdir() if d.is_dir()]
        if not dirs:
            return jsonify({"ok": True, "jobId": None})
        latest = max(dirs, key=lambda x: x.stat().st_mtime)
        job_id = latest.name
        mtime = int(latest.stat().st_mtime)
        has_insights = (latest / "final" / "insight_dashboard.json").exists()
        has_final = (latest / "final").exists()
        return jsonify({"ok": True, "jobId": job_id, "mtime": mtime, "hasInsights": has_insights, "hasFinal": has_final})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@api_bp.post("/analyze")
def api_analyze():
    """
    Enqueue Celery pipeline run. Returns jobId immediately.
    """
    data = request.get_json(silent=True) or {}
    transcript_text = (data.get("transcriptText") or "").strip()
    file_id = (data.get("fileId") or "").strip()
    selected = data.get("selected") or {"stageA": ["say_means"], "stageB": [], "final": []}
    options = data.get("options") or {}

    if not transcript_text and not file_id:
        return jsonify({"ok": False, "error": "Provide transcriptText or fileId"}), 400

    job_id = str(uuid.uuid4())
    created_at = time.time()

    # Save initial status in Redis
    r = _get_redis()
    r.set(
        _redis_key(job_id),
        json.dumps(
            {
                "jobId": job_id,
                "status": "queued",
                "createdAt": created_at,
                "stageA": {},
                "stageB": {},
                "final": {},
                "tokenUsageTotal": {"prompt": 0, "completion": 0, "total": 0},
                "errors": [],
            }
        ),
    )
    r.expire(_redis_key(job_id), 60 * 60 * 24)

    # Emit progress and enqueue task
    job_queued(job_id)
    # Optional per-analyzer prompt selection mapping
    prompt_selection = data.get("promptSelection") or {}
    cleaned_prompt_selection, selection_errors = _clean_prompt_selection(prompt_selection)

    payload = {
        "transcriptText": transcript_text,
        "fileId": file_id,
        "selected": selected,
        "options": options,
        "promptSelection": cleaned_prompt_selection,
    }
    run_pipeline.delay(job_id, payload)

    return jsonify({"ok": True, "jobId": job_id, "queuedAt": created_at})


@api_bp.get("/status/<job_id>")
def api_status(job_id: str):
    """
    Return latest status doc from Redis for the given jobId.
    """
    r = _get_redis()
    raw = r.get(_redis_key(job_id))
    if not raw:
        return jsonify({"ok": False, "error": "jobId not found"}), 404
    try:
        doc = json.loads(raw)
    except Exception:
        doc = {"raw": raw.decode("utf-8")}
    return jsonify({"ok": True, "jobId": job_id, "status": doc.get("status"), "doc": doc})


@api_bp.get("/results/<job_id>")
def api_results(job_id: str):
    """
    Return results for a jobId. Stub returns pending unless updated elsewhere.
    """
    record = _job_store.get(job_id)
    if not record:
        return jsonify({"ok": False, "error": "jobId not found"}), 404

    return jsonify(
        {
            "ok": True,
            "jobId": job_id,
            "status": record["status"],
            "result": record["result"],
        }
    )

def _job_dir(job_id: str) -> Path:
    """
    Filesystem location to read job artifacts for Celery/web runs.
    """
    d = Path(f"output/jobs/{job_id}")
    return d

def _safe_join(base: Path, relative: str) -> Optional[Path]:
    """
    Safely resolve a relative path under a base directory. Returns None if traversal detected or file missing.
    """
    try:
        candidate = (base / relative).resolve()
        base_res = base.resolve()
        if not str(candidate).startswith(str(base_res)):
            return None
        if not candidate.exists() or not candidate.is_file():
            return None
        return candidate
    except Exception:
        return None

@api_bp.get("/job-file")
def api_job_file():
    """
    Read a file from a job's artifacts directory (read-only).
    Query params:
      - jobId: the job id
      - path: relative path under output/jobs/<jobId>/ (e.g., 'final/meeting_notes.md')
    Returns: { ok, jobId, path, content }
    """
    job_id = (request.args.get("jobId") or "").strip()
    rel_path = (request.args.get("path") or "").strip()
    if not job_id or not rel_path:
        return jsonify({"ok": False, "error": "jobId and path are required"}), 400
    base = _job_dir(job_id)
    p = _safe_join(base, rel_path)
    if not p:
        return jsonify({"ok": False, "error": "Invalid job file path"}), 400
    try:
        content = p.read_text(encoding="utf-8")
        return jsonify({"ok": True, "jobId": job_id, "path": rel_path, "content": content})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to read file: {e}"}), 500
