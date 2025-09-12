<prompt>
  <tags>#stage-b #results-analysis</tags>

  <role>
    Extract irreducible first principles from the context, separating facts from assumptions and conventions.
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
    - Ignore analogies/established conventions; focus on fundamentals.
  </constraints>

  <output_format>
    <section name="First Principles">
      - For each principle: statement, why it is irreducible, evidence.
    </section>
    <section name="Assumptions to Discard">
      - Conventional ideas to drop; rationale.
    </section>
    <section name="Goal/Function Clarification">
      - Ultimate goal(s) or function(s) clarified.
    </section>
  </output_format>
</prompt>
