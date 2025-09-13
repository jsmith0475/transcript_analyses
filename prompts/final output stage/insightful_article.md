<prompt>
  <tags>#final #synthesis #article #insight</tags>

  <role>
    Write a deeply insightful ~1000‑word article on the principal subject of the conversation, synthesizing key themes, evidence, implications, and recommended next steps.
  </role>

  <response_header_required>
    At the very start of your response, output exactly one line:
    Definition: <one sentence (≤ 20 words) describing the article’s focus>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <!-- Stage B + Final combined results and, optionally, transcript excerpt/summary -->
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Length target: ~1000 words (≈ 900–1100). Favor clarity over verbosity.
    - Audience: intelligent, non‑expert reader; explain terms briefly and avoid heavy jargon.
    - Ground every claim in the provided material; do not fabricate sources or details.
    - Use Markdown with scannable headings and short paragraphs; bullets only when they aid clarity.
    - Include an engaging Introduction (hook) and a strong Conclusion (memorable close + takeaways).
    - Do NOT include any angle‑bracket tags in your output.
  </constraints>

  <output_format>
    <section name="Title">A concise, compelling title (no leading #)</section>
    <section name="Introduction">Hook + why it matters now; what the article covers</section>
    <section name="Core Themes">
      3–5 subsections, each with: the claim, brief evidence from context/transcript, and why it matters
    </section>
    <section name="Implications">So what? risks, opportunities, second‑order effects</section>
    <section name="Recommendations">Actionable next steps and decision criteria</section>
    <section name="Conclusion">Tie back to the hook; crisp takeaways + call to action</section>
  </output_format>

  <instructions>
    - Identify the principal subject by inspecting the Stage A+B combined context; state it explicitly in the Title and opening.
    - Weave in perspectives revealed by Stage A (e.g., say/means gaps, premises, frames, power dynamics) where they sharpen the argument.
    - When quoting, use short inline quotes and attribute minimally (e.g., “PM: …”). Avoid footnotes/endnotes.
    - Keep transitions smooth; end each section with a forward‑looking line that sets up the next section.
  </instructions>
</prompt>

