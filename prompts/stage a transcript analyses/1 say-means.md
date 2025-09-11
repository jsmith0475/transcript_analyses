<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>
    Expert transcript analyst applying the Say–Mean framework to clarify explicit statements vs implied meanings.
  </role>

  <response_header_required>
    At the very start of your response, output exactly one line:
    Definition: <one sentence (≤ 20 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <transcript>{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Be concise, specific, and evidence-based.
    - Use the headings and structure in the output_format exactly.
  </constraints>

  <output_format>
    <section name="Say–Mean Analysis">
      - For each key point, structure as:
        • Said: <quote or paraphrase>
        • Meant: <likely intent/implication>
        • Notes: <tone, context, caveats>
    </section>
  </output_format>
</prompt>
