<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>
    Identify foundational postulates and derived theorems; map dependencies and assess logical validity/robustness.
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
    - Use the headings below exactly and label items as requested.
  </constraints>

  <output_format>
    <section name="Postulate Analysis">
      - Label postulates Post_1..n; include: statement, type (definitional/empirical/normative/theoretical), validity, hidden assumptions, scope/limits.
      - Evaluate foundation: consistency, sufficiency, missing postulates.
    </section>
    <section name="Theorem Analysis">
      - Label theorems Thm_1..n; include: statement, supporting postulates (Post_x), reasoning chain, validity, gaps/leaps, added assumptions.
      - Classify: direct, compound, conditional, corollary.
    </section>
    <section name="Postulate–Theorem Dependencies">
      - Dependency map; critical postulates; circular dependencies; completeness, robustness, vulnerabilities.
      - Meta: alternative postulate sets; minimal set considerations.
    </section>
    <section name="Key Insights">
      - Summarize logical structure, strongest/weakest links, and recommendations.
    </section>
  </output_format>
</prompt>
