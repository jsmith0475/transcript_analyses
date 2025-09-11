from __future__ import annotations

from typing import Dict, Tuple, Any, List

from src.models import AnalysisResult


def _count_tokens(llm_client, text: str) -> int:
    """
    Safe token counter with heuristic fallback.
    """
    try:
        return llm_client.count_tokens(text or "")
    except Exception:
        # Fallback heuristic ~4 chars per token
        return max(1, len(text or "") // 4)


def _limit_by_tokens(llm_client, text: str, max_tokens: int) -> str:
    """
    Trim text to approximately fit within max_tokens using llm_client counter
    with a proportional-length fallback.
    """
    if max_tokens is None or max_tokens <= 0:
        return text or ""
    try:
        tokens = llm_client.count_tokens(text or "")
        if tokens <= max_tokens:
            return text or ""
        ratio = max(0.05, float(max_tokens) / float(max(tokens, 1)))
        est_len = max(1, int(len(text or "") * ratio))
        return (text or "")[:est_len]
    except Exception:
        # Fallback ~4 chars per token
        return (text or "")[: max(1, max_tokens * 4)]


def build_fair_combined_context(
    previous_analyses: Dict[str, AnalysisResult],
    llm_client,
    total_budget_tokens: int,
    min_per_analyzer: int = 500,
    include_sections_order: List[str] | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Build a combined Stage B context that guarantees representation from each Stage A analyzer
    under a total token budget using a fair-share allocation.

    Strategy:
      1) Compute per-section token counts.
      2) If sum fits in budget - concatenate as-is.
      3) Else allocate:
         - Base minimum per analyzer (min_per_analyzer), adjusted down if N*min > budget.
         - Distribute remaining tokens proportionally to each section's excess (size - min).
      4) Independently trim each section to its allocation, then concatenate with separators.

    Returns:
      (combined_context, debug_info)
      debug_info includes per_section_tokens, allocations, after_tokens, final_tokens, min_per_analyzer, budget
    """
    # Materialize sections preserving order
    sections: List[Tuple[str, str]] = []
    for slug, res in previous_analyses.items():
        sections.append((slug, res.to_context_string()))

    # Optional reordering to a caller-specified order (if provided)
    if include_sections_order:
        index = {slug: i for i, slug in enumerate(include_sections_order)}
        sections.sort(key=lambda x: index.get(x[0], 10**9))

    # Token counts per section
    per_counts: Dict[str, int] = {}
    total_tokens = 0
    for slug, text in sections:
        c = _count_tokens(llm_client, text)
        per_counts[slug] = c
        total_tokens += c

    # No budget or everything fits: return as-is
    if total_budget_tokens is None or total_budget_tokens <= 0 or total_tokens <= total_budget_tokens:
        combined_list: List[str] = []
        for _, text in sections:
            combined_list.append(text)
            combined_list.append("\n---\n")
        combined_text = "\n".join(combined_list)
        return combined_text, {
            "per_section_tokens": per_counts,
            "allocations": {slug: per_counts[slug] for slug, _ in sections},
            "after_tokens": {slug: per_counts[slug] for slug, _ in sections},
            "final_tokens": _count_tokens(llm_client, combined_text),
            "min_per_analyzer": min_per_analyzer,
            "budget": total_budget_tokens,
        }

    # Budgeted allocation
    n = max(1, len(sections))
    min_per = int(min_per_analyzer or 1)
    if min_per * n > total_budget_tokens:
        min_per = max(1, total_budget_tokens // n)

    remaining = total_budget_tokens - (min_per * n)

    # Weights based on excess beyond min_per
    weights: Dict[str, float] = {}
    weight_sum = 0.0
    for slug, _ in sections:
        excess = max(0, per_counts.get(slug, 0) - min_per)
        w = float(excess) + 1.0  # avoid zero weights
        weights[slug] = w
        weight_sum += w

    # Initial allocations
    allocations: Dict[str, int] = {}
    for slug, _ in sections:
        alloc = min_per
        if remaining > 0 and weight_sum > 0:
            alloc += int(round(remaining * (weights[slug] / weight_sum)))
        allocations[slug] = max(1, alloc)

    # Fix rounding so sum equals budget
    diff = total_budget_tokens - sum(allocations.values())
    if diff != 0:
        last_slug = sections[-1][0]
        allocations[last_slug] = max(1, allocations[last_slug] + diff)

    # Trim each section independently and build combined text
    after_counts: Dict[str, int] = {}
    combined_parts: List[str] = []
    for slug, text in sections:
        trimmed = _limit_by_tokens(llm_client, text, allocations[slug])
        after_counts[slug] = _count_tokens(llm_client, trimmed)
        combined_parts.append(trimmed)
        combined_parts.append("\n---\n")

    combined_text = "\n".join(combined_parts)
    final_tokens = _count_tokens(llm_client, combined_text)

    debug = {
        "per_section_tokens": per_counts,
        "allocations": allocations,
        "after_tokens": after_counts,
        "final_tokens": final_tokens,
        "min_per_analyzer": min_per,
        "budget": total_budget_tokens,
    }
    return combined_text, debug
