<prompt>
  <tags>#final #synthesis #insights</tags>

  <role>
    Produce a composite detailed note synthesizing Final outputs for readability and action.
  </role>

  <response_header_required>
    At the very start of your response, output exactly three line:
    Definition: <three sentence (≤ 100 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Use clear Markdown headings; be concise and scannable.
  </constraints>

  <output_format>
    <section name="Composite Note">
      - Synthesize the key content from Final stage into a coherent narrative.
    </section>
    <section name="Decisions">
      - One decision per bullet line.
    </section>
    <section name="Action Items">
      - One action per bullet; include Owner and Due when available.
    </section>
    <section name="Risks">
      - One risk/concern per bullet line.
    </section>
  </output_format>
  <!-- Note: Do not include a visible INSIGHTS_JSON block in the output. The Insights dashboard is derived from the human sections above. -->
</prompt>
