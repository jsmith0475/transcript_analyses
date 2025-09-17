<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>
    Analyze the transcript using SPIN (Situation, Problem, Implication, Need–Payoff), recognizing that multiple concurrent topics may each form their own SPIN thread. Produce a structured, evidence-based report.
  </role>

  <response_header_required>
    At the very start of your response, output exactly three line:
    Definition: <three sentence (≤ 100 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Be concise, specific, and evidence-based.
    - Use the headings and structure in the output_format exactly.
  </constraints>

  <output_format>
    <section name="Executive Summary">
      - 3–5 sentences summarizing dominant topics and SPIN signals; note key gaps and leverage points.
    </section>

    <section name="Topic Map">
      - List topic clusters T_1..n with short labels; key speakers; brief evidence (quote or precise paraphrase).
    </section>

    <section name="SPIN Analysis (by Topic)">
      - For each topic T_k, enumerate SPIN_k_1..n in a single line each:
        Item: <label> | Situation: <facts/constraints + evidence> | Problem: <pain/opportunity + evidence> | Implication: <stakes/consequences + magnitude if possible> | Need–Payoff: <desired value/acceptance criteria> | Gaps: <missing S/P/I/N> | Evidence: "<short quote>"
    </section>

    <section name="Cross-Topic Patterns">
      - Recurring situations/problems; shared implications; conflicting needs; dependencies and blockers.
    </section>

    <section name="Next-Best Questions">
      - Provide 5–8 SPIN-advancing questions with brief model answers grounded in transcript evidence.
      - Format each as: Question: <concise> | Brief Answer: <1–2 sentence SPIN-aligned answer>.
    </section>

    <section name="Actions">
      - Specific follow-ups mapped to topics and SPIN gaps; optional Owner and Due inline.
    </section>

    <section name="Risks">
      - One per bullet; how unresolved problems/implications could escalate; early warning indicators.
    </section>

    <section name="Metrics">
      - 3–5 measurable acceptance criteria derived from Need–Payoff items.
    </section>
  </output_format>

  <instructions>
    - First, cluster the transcript into coherent topics (T_1..n) before applying SPIN.
    - Extract explicit and implicit S/P/I/N; mark absent or ambiguous elements under Gaps.
    - Support each claim with a short quote or precise paraphrase.
    - When Implications are weak, estimate magnitude (risk/cost/time) using ranges where feasible.
    - Translate vague needs into Need–Payoff statements with observable outcomes/acceptance criteria.
    - Maintain separate SPIN threads for mixed discussions; note cross-topic dependencies.
    - Keep an analytical, non-diagnostic tone; focus on patterns, trade-offs, and next questions.
  </instructions>
</prompt>

<inputs>
  <transcript>{{ transcript }}</transcript>
</inputs>

