<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>
    Extract and evaluate premises (explicit/implicit) and assertions; map their dependencies and assess logical strength.
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
    <section name="Premise Analysis">
      - List explicit (P_e_1..n) and implicit (P_i_1..n) premises.
      - For each: statement, role in argument, strength/validity, weaknesses/biases/counterarguments, implicit rationale.
    </section>
    <section name="Assertion Analysis">
      - Identify assertions (A_1..n).
      - For each: statement, dependence on premises, strength, gaps/leaps, overall validity.
    </section>
    <section name="Premise–Assertion Dependencies">
      - Map assertions to their supporting premises; assess relationship strength and coherence of flow.
    </section>
  </output_format>
</prompt>
