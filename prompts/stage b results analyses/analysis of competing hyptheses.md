<prompt>
  <tags>#stage-b #results-analysis</tags>

  <role>
    Apply the Analysis of Competing Hypotheses (ACH) to generate, assess, and rank hypotheses against evidence.
  </role>

  <response_header_required>
    At the very start of your response, output exactly one line:
    Definition: <one sentence (≤ 20 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Be explicit and cite evidence.
  </constraints>

  <output_format>
    <section name="Hypotheses">
      - Concise list; mutually exclusive where feasible.
    </section>
    <section name="Evidence Matrix">
      - For each hypothesis: supporting, contradictory, ambiguous evidence; reliability/strength.
    </section>
    <section name="Inconsistencies & Diagnosticity">
      - Most diagnostic evidence; gaps.
    </section>
    <section name="Interim Judgments">
      - Likely/Plausible/Unlikely with rationale.
    </section>
    <section name="Conclusion & Ranking">
      - Ranked list with concise explanation.
    </section>
  </output_format>
</prompt>
