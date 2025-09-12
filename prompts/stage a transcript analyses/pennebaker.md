<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>
    Analyze linguistic and psychological patterns per speaker (Pennebaker/LIWC style) with cautious interpretation.
  </role>

  <response_header_required>
    At the very start of your response, output exactly three line:
    Definition: <three sentence (≤ 100 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Keep assessments careful and non-diagnostic; cite textual cues.
  </constraints>

  <output_format>
    <section name="[Speaker] — Linguistic Profile">
      - Pronouns; Function words; Emotional tone; Temporal orientation; Cognitive markers; Social terms.
    </section>
    <section name="[Speaker] — Psychological Interpretation">
      - Self/outward focus; Confidence/doubt; Affect; Status signals; Social connection; Cognitive complexity.
    </section>
    <section name="[Speaker] — Deception Indicators (Caution)">
      - Self-distancing; Emotional leakage; Cognitive load; Overcompensation; Lack of nuance.
    </section>
    <section name="[Speaker] — Deception Interpretation (Probabilistic)">
      - Cautious assessment; note limitations.
    </section>
    <section name="[Speaker] — Overall Summary">
      - Narrative synthesis.
    </section>
    <section name="Comparisons (if multiple speakers)">
      - Compare styles, focus, affect, status cues, and deception indicators.
    </section>
  </output_format>
</prompt>

<inputs>
  <transcript>{{ transcript }}</transcript>
</inputs>