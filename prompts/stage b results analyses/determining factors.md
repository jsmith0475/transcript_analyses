<prompt>
  <tags>#stage-b #results-analysis</tags>

  <role>
    Distinguish determining (internal/controllable) vs contributing (external/uncontrollable) factors and assess their impact.
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
    - Provide clear reasoning and evidence for classifications.
  </constraints>

  <output_format>
    <section name="Determining Factors">
      - Identify and justify; describe impact on outcomes.
    </section>
    <section name="Contributing Factors">
      - Identify and justify; describe influence and limitations.
    </section>
    <section name="Misinterpretations">
      - Cases where factors were misclassified; consequences.
    </section>
    <section name="Recommendations">
      - Strategies to focus on determining factors to improve outcomes.
    </section>
  </output_format>
</prompt>
