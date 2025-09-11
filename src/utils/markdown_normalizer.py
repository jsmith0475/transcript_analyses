from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```[^\n]*\n([\s\S]*?)\n```", re.MULTILINE)


def _is_pipe_table_header(line: str) -> bool:
    return bool(re.match(r"^\s*\|.*\|\s*$", line or ""))


def _repair_separator(header: str, sep: str) -> str:
    cols = len([c for c in header.split("|") if c.strip()])
    if cols < 2:
        return sep
    canonical = "|" + "|".join(["---"] * cols) + "|"
    looks_ok = ("-" in sep) and ((sep.count("|") >= (cols - 1)))
    return sep if looks_ok else canonical


def normalize_markdown_tables(text: str) -> str:
    """Normalize Markdown to improve table rendering.

    - Unwrap code-fenced pipe tables into real tables
    - Repair/insert separator rows based on header column count
    - Normalize unicode dashes to hyphens
    - Dedent lines that look like pipe-table rows but are indented like code
    """
    if not text:
        return text

    out = text.replace("–", "-").replace("—", "-").replace("−", "-")

    def _unwrap_fence(m: re.Match) -> str:
        body = (m.group(1) or "").strip()
        lines = body.splitlines()
        if len(lines) < 2:
            return m.group(0)
        non_empty = [ln for ln in lines if ln.strip()]
        if len(non_empty) < 2:
            return m.group(0)
        header = non_empty[0]
        if not _is_pipe_table_header(header):
            return m.group(0)
        repaired = []
        seen_header = False
        replaced_sep = False
        for ln in lines:
            if not seen_header and ln.strip():
                repaired.append(ln)
                seen_header = True
                continue
            if seen_header and not replaced_sep:
                canonical = _repair_separator(header, ln)
                repaired.append(canonical)
                replaced_sep = True
                continue
            repaired.append(ln)
        return "\n" + "\n".join(repaired) + "\n"

    out = _FENCE_RE.sub(_unwrap_fence, out)
    out = re.sub(r"^[ \t]{4,}(\|)", r"\1", out, flags=re.MULTILINE)
    return out
