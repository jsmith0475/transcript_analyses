Prompts Guide — How Staged Prompts Work
=======================================

Overview
--------
The Transcript Analysis Tool uses a staged prompt workflow to turn raw meeting transcripts into structured, useful outputs:

- Stage A (Transcript Analysis): transforms raw transcript text into focused analyses (e.g., Say/Means, Perspective/Perception, Premises/Assertions, Postulate/Theorem). Each Stage A analyzer reads the transcript directly and produces a specialized view.
- Stage B (Results Analysis): transforms the set of Stage A analyses (combined context) into higher‑order insights (e.g., Competing Hypotheses, First Principles, Determining Factors, Patentability). Stage B may optionally include a transcript preview or summary alongside Stage A results.
- Final (Synthesis): accumulates Stage A + Stage B results (and optionally a transcript excerpt/summary) to produce final deliverables (e.g., Meeting Notes, Composite Note, Executive Summary, What Should I Ask?).

Why staging is beneficial
-------------------------
Real transcripts often contain specialized knowledge, domain jargon, and multiple, shifting threads. Asking a single prompt to do everything tends to produce shallow or inconsistent results. The staged approach:

- Separates concerns: Each Stage A analyzer focuses on one aspect of the transcript (rhetoric, logic, positions, etc.), reducing prompt complexity and improving fidelity.
- Provides breadth then depth: Stage A covers multiple complementary lenses; Stage B compares, challenges, or consolidates those lenses; Final synthesizes into actionable outputs.
- Improves grounding: Stage B and Final operate on explicit, named artifacts (previous analyses), which are easier for models to reference than unconstrained raw text.
- Controls cost and context: The system allocates a fair token budget when combining Stage A results for Stage B, and can inject either a short transcript preview or a summary when needed.

Where prompts live and how they’re discovered
--------------------------------------------
Prompts are normal Markdown files in the `prompts/` folder:

- Stage A: `prompts/stage a transcript analyses/`
- Stage B: `prompts/stage b results analyses/`
- Final:   `prompts/final output stage/`

At startup and when you click “Rescan” in the UI, the app discovers all `.md` files in these folders and updates the analyzer lists dynamically. You can edit prompts in‑app, add new ones, remove them, or select different prompts per analyzer at run time (Advanced toggle).

Prompt structure (recommended schema)
------------------------------------
Prompts are ordinary Markdown with an optional structured header the tool understands. When you use the in‑app editor or the Normalize feature (now removed from UI by request), prompts generally follow this pattern:

```
<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>Describe the model’s role and objective.</role>

  <response_header_required>
    At the very start of your response, output exactly one line:
    Definition: <one sentence (≤ 20 words) describing this analysis>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <!-- Stage A -->
    <transcript>{{ transcript }}</transcript>
    <!-- Stage B / Final -->
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Be faithful to the provided content; avoid speculation.
    - Use clear, scannable Markdown headings and bullets.
  </constraints>

  <output_format>
    <!-- Optional: hint exact sections or JSON/HTML blocks you want -->
  </output_format>

  <instructions>
    Free‑form instructions specific to the analyzer.
  </instructions>
</prompt>
```

Template variables
------------------
Prompts render using Jinja‑style variables:

- `{{ transcript }}` — the transcript text prepared for analysis. Available to Stage A (required) and optionally to Stage B/Final when configured.
- `{{ context }}` — the combined context of previous analyses. Available to Stage B and Final.

Stage‑specific guidance
-----------------------

Stage A (Transcript Analysis)
- Reads only `{{ transcript }}`.
- Keep the prompt narrowly targeted (one lens per analyzer).
- Prefer concise headings and bullets so Stage B can use the results effectively.

Stage B (Results Analysis)
- Reads `{{ context }}` (the fair‑budget combined Stage A outputs). You can optionally include a transcript excerpt or summary when beneficial.
- Good patterns: compare/contrast Stage A outputs, check for contradictions, propose hypotheses, and identify determining factors.
- When you need tabular summaries here, consider returning HTML `<table>` for display fidelity (the app sanitizes and renders HTML safely).

Final (Synthesis)
- Reads both Stage A and Stage B via `{{ context }}` and may also include a transcript excerpt/summary if configured.
- Outputs end‑user facing documents (e.g., Meeting Notes, Composite Note, What Should I Ask?, and Insightful Article).
- Privacy: Final prompts should avoid PII and identifying references; replace names with roles and organizations with generic descriptors.

Using tags
----------
The `<tags>` element is free‑form. We recommend at least one stage tag (e.g., `#stage-a`, `#stage-b`, or `#final`) plus functional tags (e.g., `#rhetoric`, `#hypotheses`, `#synthesis`). Tags are helpful for organization and optional future filtering; they do not change app behavior by themselves.

Tables, JSON, and other formats
-------------------------------

- Markdown tables: Supported across the app. If a model wraps them in code fences, the UI tries to unwrap/repair. For critical tabular displays (like Patentability summaries), prefer HTML tables.
- HTML tables: Rendered safely (sanitized) with borders and consistent styling. Use when you need precise layout.
- JSON blocks: For machine‑readable sections (e.g., Insights), you can include a fenced `json` block or an `INSIGHTS_JSON` block the app can parse. Keep the JSON small and valid.

Best practices for writing prompts
---------------------------------

1) Be explicit about the lens (Stage A), the analysis task (Stage B), and the deliverable (Final). Avoid mixing responsibilities in a single prompt.
2) Give a short list of constraints (“be faithful”, “use headings”, “avoid speculation”). Models respond better to crisp rules.
3) When you need structured output, show the target structure (Markdown section list, HTML table, or a short JSON schema).
4) Avoid code fences around tables you want rendered as tables. If you must fence a table, label it clearly (e.g., ```table) or prefer HTML.
5) Keep the prompt files short and readable. Use the in‑app editor or your IDE; changes are picked up immediately after “Rescan”.

Editing and selecting prompts
-----------------------------

- Edit in‑app (Edit button) or in your editor; rescan to refresh.
- Use the Advanced toggle to pick different prompt files per analyzer for the current run (does not change defaults).
- You can add new prompt files into the appropriate stage folder; the app will discover them on “Rescan”.

FAQ
---

Q: Can Stage B include the transcript?
A: Yes. The app can inject a transcript excerpt or summary alongside `{{ context }}` when configured in the UI options.

Q: What if my Stage A results are very long?
A: Stage B uses a fair token budget to ensure each Stage A analyzer is represented. The app trims or summarizes content as needed to stay within limits.

Q: Do I need to include the XML‑like wrapper (`<prompt>`, `<inputs>`, etc.)?
A: It’s recommended because it documents intent for future maintainers and matches in‑app expectations, but the core requirement is to include the correct variables for your stage (`{{ transcript }}` or `{{ context }}`) and write clear instructions.
