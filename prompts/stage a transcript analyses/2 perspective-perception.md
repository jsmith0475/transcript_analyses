<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>
    Analyze perception (subjective interpretation) and perspective (broader viewpoint) with explicit contrasts and dependencies.
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
    <section name="Perception Analysis">
      1) Identify explicit (P_e_1..n) and implicit (P_i_1..n) perceptions.
      2) For each: statement, influence on understanding/actions, strengths/limitations, biases/assumptions, implicit rationale.
      3) Role of perception in shaping viewpoint; potential constraints on understanding/decisions.
    </section>
    <section name="Perspective Analysis">
      1) Identify perspective instances (S_1..n): objective/empathetic viewpoints.
      2) Contrast/complement with perceptions; evaluate breadth/balance; gaps/limitations.
      3) Analyze transition from perception→perspective and its effects.
    </section>
    <section name="Perception–Perspective Dependencies">
      1) Map perceptions to supporting/challenging perspectives; required shifts.
      2) Assess logical connection, coherence, and overall balance.
    </section>
  </output_format>
</prompt>
