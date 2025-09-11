"""
Analyzer registry utilities for adding, deleting, and modifying custom analyzers at runtime.

Registry file (JSON):
  cache/analyzers_registry.json

Schema:
{
  "stageA": {
    "my_new_analyzer": {
      "displayName": "My New Analyzer",
      "defaultPromptPath": "prompts/stage a transcript analyses/my_new_analyzer.md"
    }
  },
  "stageB": { ... },
  "final":  { ... }
}
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

REGISTRY_PATH = Path("cache/analyzers_registry.json")

PROMPTS_DIRS = {
    "stageA": Path("prompts") / "stage a transcript analyses",
    "stageB": Path("prompts") / "stage b results analyses",
    "final": Path("prompts") / "final output stage",
}

# Known built-in filenames per stage (lowercased) to avoid registering them as customs
BUILTIN_FILES = {
    "stageA": {
        "1 say-means.md",
        "2 perspective-perception.md",
        "3 premsises-assertions.md",
        "4 postulate-theorem.md",
    },
    "stageB": {
        "1 analysis of competing hyptheses.md",
        "2 first principles.md",
        "3 determining factors.md",
        "4 patentability.md",
    },
    "final": {
        "1 composite note.md",
        "2 meeting notes.md",
    },
}

# Variable requirements per stage (basic guards)
REQUIRED_VARS = {
    "stageA": re.compile(r"{{\s*transcript\b", re.IGNORECASE),
    "stageB": re.compile(r"{{\s*context\b", re.IGNORECASE),
    "final": re.compile(r"{{\s*context\b", re.IGNORECASE),  # Final may also use {{transcript}}, but must include context
}

SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def _ensure_registry_dir() -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_registry() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Load registry; return empty structure if missing/corrupt."""
    try:
        if REGISTRY_PATH.exists():
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    "stageA": data.get("stageA", {}) or {},
                    "stageB": data.get("stageB", {}) or {},
                    "final": data.get("final", {}) or {},
                }
    except Exception:
        pass
    return {"stageA": {}, "stageB": {}, "final": {}}


def save_registry(reg: Dict[str, Any]) -> None:
    _ensure_registry_dir()
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def is_within_prompts(p: Path) -> bool:
    try:
        root = (Path.cwd() / "prompts").resolve()
        return str(p.resolve()).startswith(str(root))
    except Exception:
        return False


def validate_prompt_file_for_stage(path: Path, stage_key: str) -> Tuple[bool, Optional[str]]:
    if not path.exists() or path.suffix.lower() != ".md":
        return False, "Prompt file must exist and be a .md file"
    if not is_within_prompts(path):
        return False, "Prompt path must be under prompts/"
    pat = REQUIRED_VARS.get(stage_key)
    if pat:
        try:
            txt = path.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Failed to read prompt: {e}"
        if not pat.search(txt or ""):
            return False, f"Prompt missing required variables for stage {stage_key}"
    return True, None


def _slug_from_filename(name: str) -> str:
    base = name.rsplit('.', 1)[0]
    # drop leading numeric ordering like "12 My File"
    import re
    base = re.sub(r"^\s*\d+\s+", "", base)
    base = base.lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = re.sub(r"^_+|_+$", "", base)
    return base or "analyzer"


def discover_prompts_to_registry(stage_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Scan stage directories for *.md files and register them as custom analyzers
    if they are not built-ins or already present. Returns a summary dict.

    stage_filter: one of None, 'stageA', 'stageB', 'final' to limit discovery.
    """
    reg = load_registry()
    added: Dict[str, Any] = {"stageA": [], "stageB": [], "final": []}
    skipped: Dict[str, Any] = {"stageA": [], "stageB": [], "final": []}
    errors: Dict[str, Any] = {"stageA": [], "stageB": [], "final": []}

    stages = ["stageA", "stageB", "final"]
    if stage_filter in stages:
        stages = [stage_filter]

    for sk in stages:
        dir_path = PROMPTS_DIRS[sk]
        try:
            for p in sorted(dir_path.glob("*.md")):
                slug = _slug_from_filename(p.name)
                # Skip built-in default files by filename match
                try:
                    if p.name.lower() in BUILTIN_FILES.get(sk, set()):
                        skipped[sk].append({"slug": slug, "reason": "builtin_file"})
                        continue
                except Exception:
                    pass
                # Skip built-ins
                if is_builtin_slug(slug):
                    skipped[sk].append({"slug": slug, "reason": "built_in"})
                    continue
                # Validate required variables
                ok, err = validate_prompt_file_for_stage(p, sk)
                if not ok:
                    errors[sk].append({"path": str(p), "error": err})
                    continue
                # If slug exists already in registry, skip
                if slug in (reg.get(sk) or {}):
                    skipped[sk].append({"slug": slug, "reason": "exists"})
                    continue
                # If slug collides with another analyzer list in config, skip; handled at merge time too
                # Register new analyzer
                reg.setdefault(sk, {})
                reg[sk][slug] = {
                    "displayName": slug.replace("_", " ").title(),
                    "defaultPromptPath": str(p),
                }
                added[sk].append({"slug": slug, "path": str(p)})
        except Exception as e:
            errors[sk].append({"path": str(dir_path), "error": f"scan_failed: {e}"})

    if any(added.values()):
        save_registry(reg)

    return {"added": added, "skipped": skipped, "errors": errors}


def cleanup_registry() -> Dict[str, Any]:
    """
    Remove problematic or duplicate custom analyzer entries from the registry:
    - Entries whose defaultPromptPath is a known built-in file (by filename)
    - Duplicate entries pointing to the same file path: keep the slug equal to
      the canonical slug derived from the filename, remove others
    - Entries whose slug matches a built-in slug (safety)

    Returns a summary dict of removed entries per stage.
    """
    reg = load_registry()
    removed: Dict[str, list] = {"stageA": [], "stageB": [], "final": []}

    for sk in ("stageA", "stageB", "final"):
        stage_map = reg.get(sk) or {}
        if not stage_map:
            continue
        to_delete = set()
        # 1) Remove entries whose slug is built-in
        for slug in list(stage_map.keys()):
            if is_builtin_slug(slug):
                to_delete.add(slug)
        # 2) Remove entries pointing to built-in files
        for slug, meta in list(stage_map.items()):
            try:
                path = str(meta.get("defaultPromptPath", ""))
                name = Path(path).name.lower()
                if name in BUILTIN_FILES.get(sk, set()):
                    to_delete.add(slug)
            except Exception:
                continue
        # 3) De-duplicate by file path: keep canonical slug from filename
        path_to_slugs: Dict[str, list] = {}
        for slug, meta in stage_map.items():
            if slug in to_delete:
                continue
            p = str(meta.get("defaultPromptPath", ""))
            if not p:
                continue
            path_to_slugs.setdefault(p, []).append(slug)
        for p, slugs in path_to_slugs.items():
            if len(slugs) <= 1:
                continue
            # canonical slug from filename
            canonical = _slug_from_filename(Path(p).name)
            # If canonical present in list, keep it; otherwise keep first
            keep = canonical if canonical in slugs else slugs[0]
            for s in slugs:
                if s != keep:
                    to_delete.add(s)
        # Apply deletions
        for slug in to_delete:
            if slug in stage_map:
                removed[sk].append(slug)
                stage_map.pop(slug, None)
        reg[sk] = stage_map

    save_registry(reg)
    return {"removed": removed}


def rebuild_registry_from_prompts() -> Dict[str, Any]:
    """
    Rebuild the custom analyzer registry from the prompts/ filesystem.
    This treats the filesystem as source of truth:
      - Clears all custom entries in the registry
      - Scans stage directories for *.md files
      - Skips built-in slugs and known built-in filenames
      - Validates required variables by stage
      - Derives canonical slug from filename; resolves collisions with numeric suffix
      - Persists the rebuilt registry

    Returns a summary dict with added/skipped/errors per stage.
    """
    # Start from a clean structure; do not keep prior customs to avoid drift
    new_reg: Dict[str, Dict[str, Dict[str, Any]]] = {"stageA": {}, "stageB": {}, "final": {}}

    added: Dict[str, List[Dict[str, Any]]] = {"stageA": [], "stageB": [], "final": []}
    skipped: Dict[str, List[Dict[str, Any]]] = {"stageA": [], "stageB": [], "final": []}
    errors: Dict[str, List[Dict[str, Any]]] = {"stageA": [], "stageB": [], "final": []}

    for sk in ("stageA", "stageB", "final"):
        dir_path = PROMPTS_DIRS[sk]
        # Map to detect file-path collisions and enforce one-to-one
        path_used: Dict[str, str] = {}
        try:
            for p in sorted(dir_path.glob("*.md")):
                name_l = p.name.lower()
                # Skip built-in prompt files by filename
                if name_l in BUILTIN_FILES.get(sk, set()):
                    skipped[sk].append({"path": str(p), "reason": "builtin_file"})
                    continue
                # Derive slug from filename
                slug = _slug_from_filename(p.name)
                # Skip built-in slugs outright
                if is_builtin_slug(slug):
                    skipped[sk].append({"slug": slug, "reason": "builtin_slug"})
                    continue
                # Validate variables
                ok, err = validate_prompt_file_for_stage(p, sk)
                if not ok:
                    errors[sk].append({"path": str(p), "error": err})
                    continue
                # Unique by file path
                rp = str(p.resolve())
                if rp in path_used:
                    # Already registered this file with another slug; skip
                    skipped[sk].append({"path": str(p), "reason": "duplicate_path"})
                    continue
                # Resolve slug collisions within stage by suffixing
                final_slug = slug
                i = 2
                while final_slug in new_reg[sk]:
                    final_slug = f"{slug}_{i}"
                    i += 1
                # Register
                new_reg[sk][final_slug] = {
                    "displayName": final_slug.replace("_", " ").title(),
                    "defaultPromptPath": str(p),
                }
                path_used[rp] = final_slug
                added[sk].append({"slug": final_slug, "path": str(p)})
        except Exception as e:
            errors[sk].append({"path": str(dir_path), "error": f"scan_failed: {e}"})

    # Persist
    save_registry(new_reg)
    return {"added": added, "skipped": skipped, "errors": errors}


def create_prompt_file_from_content(stage_key: str, slug: str, content: str) -> Path:
    """Create a new prompt file under the correct stage directory using the slug."""
    stage_dir = PROMPTS_DIRS[stage_key]
    stage_dir.mkdir(parents=True, exist_ok=True)
    # Use slug as filename for predictability
    file_path = stage_dir / f"{slug}.md"
    file_path.write_text(content or "", encoding="utf-8")
    return file_path


def merge_registry_into_config(cfg: Any) -> None:
    """
    Merge custom analyzers from registry into the live AppConfig:
    - Append custom slugs into stage lists if not present
    - Set cfg.analyzers[slug].prompt_file so cfg.get_prompt_path resolves
    """
    from src.config import AnalyzerConfig  # Lazy import to avoid circular at module import time

    reg = load_registry()

    def _ensure(cfg_list, slug):
        if slug not in cfg_list:
            cfg_list.append(slug)

    # Stage A
    for slug, meta in (reg.get("stageA") or {}).items():
        _ensure(cfg.stage_a_analyzers, slug)
        try:
            p = Path(meta.get("defaultPromptPath", ""))
            if p:
                cfg.analyzers[slug] = AnalyzerConfig(prompt_file=p)
        except Exception:
            # If invalid path, skip; will be validated on use
            pass

    # Stage B
    for slug, meta in (reg.get("stageB") or {}).items():
        _ensure(cfg.stage_b_analyzers, slug)
        try:
            p = Path(meta.get("defaultPromptPath", ""))
            if p:
                cfg.analyzers[slug] = AnalyzerConfig(prompt_file=p)
        except Exception:
            pass

    # Final
    for slug, meta in (reg.get("final") or {}).items():
        _ensure(cfg.final_stage_analyzers, slug)
        try:
            p = Path(meta.get("defaultPromptPath", ""))
            if p:
                cfg.analyzers[slug] = AnalyzerConfig(prompt_file=p)
        except Exception:
            pass


def find_slug_stage(reg: Dict[str, Any], slug: str) -> Optional[str]:
    for stage_key in ("stageA", "stageB", "final"):
        if slug in (reg.get(stage_key) or {}):
            return stage_key
    return None


def is_valid_slug(slug: str) -> bool:
    return bool(SLUG_RE.match(slug or ""))


def is_builtin_slug(slug: str) -> bool:
    """Protect built-in analyzers from deletion/override by default."""
    BUILT_INS = {
        "say_means",
        "perspective_perception",
        "premises_assertions",
        "postulate_theorem",
        "competing_hypotheses",
        "first_principles",
        "determining_factors",
        "patentability",
        "meeting_notes",
        "composite_note",
    }
    return slug in BUILT_INS
