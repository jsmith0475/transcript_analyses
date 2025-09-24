<prompt>
  <tags>#final #synthesis #insights #stage-a #stage-b</tags>

  <role>
    Produce a comprehensive, decision-ready note that synthesizes Stage A (transcript analyses) and Stage B (results syntheses) into one coherent, scannable document.
  </role>

  <response_header_required>
    At the very start of your response, output exactly three line:
    Definition: <three sentence (≤ 100 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <context optional="true">{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
    <stage_a_outputs optional="true">{{ stage_a_outputs }}</stage_a_outputs>
    <stage_b_outputs optional="true">{{ stage_b_outputs }}</stage_b_outputs>
  </inputs>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Use clear Markdown headings; be concise and scannable.
    - Prefer single-line, pipe-delimited summaries for lists that crosswalk Stage A → Stage B.
    - When available, ground key claims with short quotes or precise paraphrases.
  </constraints>

  <output_format>
    <section name="Composite Note">
      - Executive narrative weaving together Stage A findings (patterns, gaps, metrics) and Stage B outcomes (ranked needs, ROI, decisions, plan).
      - Call out 3–5 most material insights and what they imply for near-term action.
    </section>

    <section name="Stage A Highlights (Transcript Analyses)">
      - Summarize dominant topics and patterns across Stage A outputs (e.g., SPIN, power dynamics, premises/assertions, perspective-perception).
      - Topic Map Brief: T_k | Speakers: <names> | Signals: <SPIN/problems/needs> | Evidence: "<short quote/paraphrase>".
      - Gaps & Open Questions: one per bullet; note missing S/P/I/N or ambiguity.
      - Metrics Candidates: 3–5 acceptance criteria inferred from needs/payoffs.
    </section>

    <section name="Stage B Highlights (Results Syntheses)">
      - Ranked Needs Summary: Topic: <T_k> | Need: <statement> | Payoff: <value> | Status: <new/ongoing/dependent>.
      - Impact/Effort/Confidence: Impact: <1–5> | Effort: <1–5> | Confidence: <0–100%> | Value Score: <rounded> | Rationale: <one sentence>.
      - ROI & Timeline: top expected payoffs, time-to-value ranges, break-even assumptions.
      - Decision-Ready Actions: Action: <what> | Owner: <who> | Start: <date/relative> | End: <date/relative> | Dependencies | Success Criteria.
      - Risks & Mitigations: Risk: <text> | Mitigation: <text> | Early Signal: <text>.
      - Assumptions & Data Gaps: one per bullet; what evidence would change priorities.
    </section>

    <section name="Crosswalk (Stage A → Stage B)">
      - For each top need/action, map the underpinning Stage A evidence:
        Map: Topic: <T_k> | Stage A Signal: <S/P/I/N or other> | Evidence: "<quote/paraphrase>" | Stage B Need/Action: <summary> | Success Criteria: <metric>.
    </section>
    <section name="Decisions">
      - One decision per bullet line; include Brief Rationale tied to Stage A/B evidence when possible.
    </section>

    <section name="Action Items">
      - One action per bullet; include Owner and Due when available; align each to a top Need and Success Criteria.
    </section>

    <section name="Risks">
      - One risk/concern per bullet; include Mitigation and Early Signal when available.
    </section>

    <section name="Assumptions & Data Gaps">
      - Critical assumptions behind decisions/scoring; evidence that would change priority or approach.
    </section>
  </output_format>
  <!-- Note: Do not include a visible INSIGHTS_JSON block in the output. The Insights dashboard is derived from the human sections above. -->
</prompt>
