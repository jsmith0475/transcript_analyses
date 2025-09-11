<prompt>
  <tags>#stage-b #results-analysis</tags>

  <role>
    Identify potentially patentable ideas; classify across strategic dimensions; assess patentability likelihood.
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
    - Prefer specific mechanisms and system interactions; cite evidence.
  </constraints>

  <output_format>
    <section name="Idea Identification">
      - Concrete ideas/mechanisms/workflows/architectures extracted from inputs.
    </section>
    <section name="Categorization">
      - Assign each idea to one of 8: Capable/Differentiable × Short/Long-Term × Fragile/Antifragile; justify.
    </section>
    <section name="Patentability Assessment">
      - Likely / Uncertain / Unlikely with reasons (novelty, non-obviousness, utility, specificity, claim strategy).
    </section>
    <section name="Summary Table">
      - Compact table of ideas, categories, and assessments.
    </section>
  </output_format>
</prompt>
