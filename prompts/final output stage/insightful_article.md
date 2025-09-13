<prompt>
  <tags>#final #synthesis #article #insight #publish</tags>

  <role>
    Write a deeply insightful, publication-quality article (~1000 words) that synthesizes the principal subject of the conversation into a coherent narrative. 
    Go beyond summarizing: extract underlying themes, reveal tensions, highlight implications, and generate forward-looking insight. 
    Aim for intellectual depth and clarity that would engage an intelligent, non-expert reader in a respected magazine or ideas journal.
  </role>

  <response_header_required>
    At the very start of your response, output exactly one line:
    Definition: <one sentence (≤ 20 words) crisply stating the article’s central argument or insight>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Length: ~1000 words (≈ 900–1100).
    - Tone: authoritative yet accessible; avoid jargon but don’t oversimplify.
    - Evidence: ground every claim in the provided material; never fabricate.
    - Formatting: Markdown headings; short, readable paragraphs; bullets only when they clarify.
    - Must include:
      * A compelling Introduction with a clear hook.
      * A set of body sections (3–6), each with a sharp claim, supporting evidence, and why it matters.
      * At least one section exploring Implications (risks, opportunities, ripple effects).
      * At least one section suggesting Recommendations or forward steps (if relevant).
      * A strong Conclusion tying back to the hook with lasting takeaways.
    - Section names are flexible: adapt, merge, or rename them to best fit the subject matter. 
    - Privacy: anonymize all PII and proper nouns (e.g., use “PM,” “research lead,” “the organization”).
    - Do not include angle-bracket tags in the output.
  </constraints>

  <output_format>
    <section name="Title">Concise, compelling, publication-ready title (no leading #)</section>
    <section name="Introduction">Hook + urgency/context + preview of themes</section>
    <section name="Body">3–6 subsections, structured logically; can include themes, analysis, implications, or recommendations as relevant</section>
    <section name="Conclusion">Tie back to the hook; memorable close with takeaways and a call to action</section>
  </output_format>

  <instructions>
    - Explicitly identify the principal subject and frame it in the Title and opening.
    - Weave in perspectives from Stage A (say/mean gaps, frames, power dynamics) where they sharpen analysis.
    - Use quotations sparingly, inline, and anonymized (e.g., “PM: …”).
    - Ensure smooth transitions; let sections build momentum toward the conclusion.
  </instructions>
</prompt>
