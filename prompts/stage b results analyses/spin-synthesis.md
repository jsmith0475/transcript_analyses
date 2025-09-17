<prompt>
  <tags>#stage-b #results-analysis</tags>

  <role>
    Synthesize Stage A SPIN findings into ranked needs, impact/ROI estimates, risks, and a decision-ready action plan.
  </role>

  <response_header_required>
    At the very start of your response, output exactly three line:
    Definition: <three sentence (≤ 100 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <spin_output>{{ spin_output }}</spin_output>
    <context optional="true">{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Base all items on the SPIN output (quotes or precise paraphrases); cite brief evidence for each key claim.
    - Use single-line, pipe-delimited fields for lists. If rich tables are supported, you may render HTML tables; otherwise keep the single-line format.
  </constraints>

  <output_format>
    <section name="Ranked Needs (from SPIN)">
      - List N_1..n sorted by priority. For each: Topic: <T_k> | Need: <statement> | Payoff: <value expected> | Evidence: "<short quote/paraphrase>" | Status: <new/ongoing/dependent>.
    </section>

    <section name="Impact/Effort/Confidence Scoring">
      - For each N_k: Impact: <1–5> | Effort: <1–5> | Confidence: <0–100%> | Value Score: <(Impact × Confidence) ÷ Effort rounded> | Rationale: <one sentence>.
      - Note: Derive Impact from SPIN Implications; Effort from scope/dependencies; Confidence from evidence quality.
    </section>

    <section name="ROI & Timeline Summary">
      - Aggregate view: top 3 expected payoffs, rough time-to-value, and break-even assumptions. Use ranges if numbers are not explicit.
    </section>

    <section name="Decision-Ready Action Plan">
      - 3–7 prioritized actions mapping to top needs. For each:
        Action: <what> | Owner: <who> | Start: <date/relative> | End: <date/relative> | Dependencies: <key blockers> | Success Criteria: <observable acceptance criteria>.
    </section>

    <section name="Risks & Mitigations">
      - One risk per bullet with Mitigation and Early Signal. Tie each risk to a specific Need/Action when possible.
    </section>

    <section name="Assumptions & Data Gaps">
      - Critical assumptions behind scoring/ROI and what evidence would change the priority.
    </section>
  </output_format>

  <instructions>
    - Parse the Stage A SPIN output to extract Need–Payoff items per topic; consolidate duplicates.
    - Score each need using Impact/Effort/Confidence; compute Value Score and sort.
    - Where numeric data is missing, provide qualitative ranges and state assumptions explicitly.
    - Build the action plan only from the highest-value needs (top 3–7), ensuring clear success criteria.
    - Keep reasoning tight and cite brief evidence from the SPIN output for each key item.
  </instructions>
</prompt>
