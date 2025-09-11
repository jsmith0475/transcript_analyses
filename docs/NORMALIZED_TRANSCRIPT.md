# Normalized Transcript (text_for_analysis)

This document explains what the “normalized transcript” is, how we build it, where it is used, and why it’s important for high‑quality, predictable analysis.

## What It Is
- The normalized transcript is a clean, analysis‑ready rendering of your source transcript (not the raw file blob).
- It is exposed as `ProcessedTranscript.text_for_analysis` and looks like speaker‑labeled lines separated by blank lines, for example:
  
  ```text
  Moderator: Welcome everyone. Today we’re discussing the Q4 strategy…
  
  PM (Alex): The biggest issue customers report is that insights are buried…
  
  Research Lead (Priya): In recent interviews, users emphasized…
  ```

## Why It Matters
- Clarity for the LLM: Reduces noise, boilerplate, and formatting artifacts; preserves speaker attributions and conversational flow.
- Better attribution: Keeps explicit `Speaker: utterance` formatting, which leads to fewer hallucinations about who said what and better downstream reasoning.
- Deterministic formatting: All Stage A analyzers receive a consistent view of the conversation, regardless of the original file’s styles/quirks.
- Token efficiency: Removes non‑informative decoration and normalizes spacing, lowering prompt tokens for the same content.
- Stronger building block: Reliable input for summarization, Stage B context budgeting, and Final synthesis.

## How We Build It
1. Load raw text and extract optional metadata (title, date, duration) if present.
2. Detect speakers using robust patterns:
   - `Name: text` (e.g., `Alex: We should…`)
   - `[Name] text` (e.g., `[Priya] We observed…`)
   - Bulleted variants: `- Name: text`, `• Name: text`
3. Segment the transcript:
   - With speakers: each contiguous set of lines by the same speaker becomes a segment.
   - Without speakers: split on blank lines into paragraph segments.
4. Compose `text_for_analysis`:
   - For each segment, render `Speaker: text` (or just `text` when the speaker is unknown), separating segments with blank lines.

Code references:
- Processor & patterns: `src/transcript_processor.py`
  - `_process_with_speakers()`, `_process_without_speakers()`
  - `speaker_patterns` (covers `Name:`, `[Name]`, `- Name:`, `• Name:`)
- Structured model: `src/models.py` → `ProcessedTranscript.text_for_analysis`

## Where It’s Used
- Stage A prompts: Always inject `{{ transcript }}` = `text_for_analysis` (with a protective token cap for very long inputs).
- Summary mode: When Summary is selected, we summarize `text_for_analysis` (not the raw blob) for injection into Stage B / Final.
- Final synthesis: Optionally include the transcript (raw or summary) along with combined A+B context.

## Guardrails & Limits
- Stage A protective cap: To avoid overruns on very long inputs, a token limit (configurable) is applied when injecting into Stage A.
- Stage B / Final: Transcript injection respects your UI “Include Transcript” toggle and mode (Full vs Summary) with a configurable cap.
- No semantic changes: Normalization preserves the original wording; it does not paraphrase or delete content—only formats it consistently.

## Tips for Better Results
- Prefer explicit speaker labels: `Name: text` improves attribution and downstream analysis.
- Keep headings/metadata separate: Leading lines like `Title:` or `Date:` are fine; they’re captured as metadata when possible.
- Avoid mixing list bullets with `Name:` unless they truly denote speakers (we support them, but plain `Name:` is clearer).

## Quick Ways to Inspect
- In code: `ProcessedTranscript.text_for_analysis` after `TranscriptProcessor.process()`.
- For display: `TranscriptProcessor.format_for_display(processed, include_speakers=True)` gives a human‑readable preview similar to what the LLM sees.

## Summary
- The normalized transcript is a faithful, speaker‑aware rendering of your conversation shown to analyzers.
- It improves clarity, attribution, and token efficiency while remaining deterministic.
- Stage A always uses it; Stage B/Final may include it (as raw or summary) according to your UI toggles and caps.

