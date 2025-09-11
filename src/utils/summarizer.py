from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from loguru import logger


def _count_tokens(llm_client, text: str) -> int:
    try:
        return llm_client.count_tokens(text or "")
    except Exception:
        return max(1, len(text or "") // 4)


def _approx_slice_by_tokens(text: str, start_tok: int, end_tok: int) -> str:
    # Approximate 4 chars per token if tokenizer not accessible
    start_idx = max(0, start_tok * 4)
    end_idx = max(start_idx, end_tok * 4)
    return (text or "")[start_idx:end_idx]


def chunk_text_by_tokens(llm_client, text: str, chunk_tokens: int, overlap_tokens: int) -> List[str]:
    """Split text into approx token-sized chunks with overlap."""
    if not text:
        return []
    total_tokens = _count_tokens(llm_client, text)
    if total_tokens <= chunk_tokens:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < total_tokens:
        end = min(total_tokens, start + chunk_tokens)
        chunk = _approx_slice_by_tokens(text, start, end)
        if chunk:
            chunks.append(chunk)
        if end >= total_tokens:
            break
        # advance with overlap
        start = max(0, end - overlap_tokens)
        if start >= total_tokens:
            break
    return chunks


def _map_prompt(chunk: str, target_tokens: int) -> str:
    return (
        "You are summarizing a transcript chunk for downstream analysis.\n"
        "Write a concise, faithful summary with clear headings and bullets.\n"
        "Focus on: key points, decisions, action items, issues/risks, perspectives, and notable facts.\n"
        f"Aim for <= {max(200, target_tokens)} tokens. Avoid speculation or repetition.\n\n"
        "# Chunk\n" + chunk
    )


def _reduce_prompt(chunk_summaries: List[str], target_tokens: int) -> str:
    merged = "\n\n---\n".join(chunk_summaries)
    return (
        "You are consolidating multiple transcript chunk summaries into a single, non-redundant global summary.\n"
        "Keep it faithful, compact, and organized with headings and bullets.\n"
        "Prioritize unique insights, decisions, and actionables; include brief risks/gaps/assumptions.\n"
        f"Fit within ~{max(400, target_tokens)} tokens.\n\n"
        "# Chunk Summaries\n" + merged
    )


def _hash_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
    return h.hexdigest()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def summarize_text(
    llm_client,
    text: str,
    stage: str,
    target_tokens: int,
    job_id: Optional[str] = None,
    map_chunk_tokens: int = 2000,
    map_overlap_tokens: int = 200,
    single_pass_max_tokens: int = 6000,
    map_model: Optional[str] = None,
    reduce_model: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Summarize input text using single-pass or map-reduce, returning (summary, debug)."""
    # Cache key (in-memory per run; callers can add their own disk cache if needed)
    cache: Dict[str, str] = {}
    key = _hash_key(text[:1000], str(target_tokens), str(map_chunk_tokens), str(map_overlap_tokens))
    if key in cache:
        return cache[key], {"cached": True}

    total_tokens = _count_tokens(llm_client, text)
    artifacts_dir = None
    if job_id:
        base = Path(f"output/jobs/{job_id}/intermediate/summaries")
        _ensure_dir(base)
        artifacts_dir = base

    debug: Dict[str, Any] = {"total_tokens": total_tokens, "mode": None, "chunks": 0}

    try:
        if total_tokens <= max(1, single_pass_max_tokens):
            debug["mode"] = "single_pass"
            prompt = _map_prompt(text, target_tokens)
            # favor deterministic small output
            response, _ = llm_client.complete_sync(
                prompt=prompt,
                temperature=0,
                max_tokens=max(512, target_tokens + 200),
                model=map_model or None,
            )
            summary = response.strip()
            if artifacts_dir:
                (artifacts_dir / f"summary.{stage}.single.md").write_text(summary, encoding="utf-8")
            cache[key] = summary
            return summary, debug

        # Map-Reduce path
        debug["mode"] = "map_reduce"
        chunks = chunk_text_by_tokens(llm_client, text, map_chunk_tokens, map_overlap_tokens)
        debug["chunks"] = len(chunks)
        chunk_summaries: List[str] = []
        for idx, ch in enumerate(chunks, 1):
            mprompt = _map_prompt(ch, max(200, target_tokens // 2))
            resp, _ = llm_client.complete_sync(
                prompt=mprompt, temperature=0, max_tokens=512, model=map_model or None
            )
            cs = resp.strip()
            chunk_summaries.append(cs)
            if artifacts_dir:
                (artifacts_dir / f"chunk_{idx:03d}.md").write_text(cs, encoding="utf-8")

        # If the combined map summaries are too large, trim before reduce
        combined = "\n\n".join(chunk_summaries)
        # keep reduce input reasonable (~3x target)
        max_reduce_input_tokens = max(target_tokens * 3, 1200)
        cur_tokens = _count_tokens(llm_client, combined)
        if cur_tokens > max_reduce_input_tokens:
            # trim by slicing text
            keep_ratio = max(0.2, float(max_reduce_input_tokens) / float(cur_tokens))
            approx_chars = int(len(combined) * keep_ratio)
            combined = combined[:approx_chars]

        rprompt = _reduce_prompt(chunk_summaries if combined == "\n\n".join(chunk_summaries) else [combined], target_tokens)
        final, _ = llm_client.complete_sync(
            prompt=rprompt, temperature=0, max_tokens=max(768, target_tokens + 300), model=reduce_model or None
        )
        summary = final.strip()
        if artifacts_dir:
            (artifacts_dir / f"summary.{stage}.reduce.md").write_text(summary, encoding="utf-8")
        cache[key] = summary
        return summary, debug
    except Exception as e:
        logger.warning(f"Summarization failed, falling back to slice: {e}")
        # Fallback: return head slice as last resort
        approx_chars = max(500, target_tokens * 4)
        summary = (text or "")[:approx_chars]
        if artifacts_dir:
            (artifacts_dir / f"summary.{stage}.fallback.md").write_text(summary, encoding="utf-8")
        debug["mode"] = "fallback"
        return summary, debug

