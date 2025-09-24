<prompt>
  <tags>#final #executive #so-what #decisions #synthesis</tags>

  <role>
    Produce an executive-level summary of the meeting focused on the "so what" and "what now" for leadership: outcomes, decisions/asks, business impact, risks, and fast next steps.
  </role>

  <response_header_required>
    At the very start of your response, output exactly three line:
    Definition: <three sentence (≤ 100 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
    <spin_output optional="true">{{ spin_output }}</spin_output>
    <stage_a_outputs optional="true">{{ stage_a_outputs }}</stage_a_outputs>
    <stage_b_outputs optional="true">{{ stage_b_outputs }}</stage_b_outputs>
  </inputs>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Keep it one-page, scannable, and decision-oriented; use concise headings and bullets.
    - Replace personal names with roles/titles; avoid PII and proprietary identifiers.
    - Prefer single-line, pipe-delimited summaries when listing items with multiple fields.
    - Ground key claims with brief quotes or precise paraphrases when available.
    - Tone: Plain, direct leadership voice. Active verbs, concrete specifics; quantify where possible.
    - Avoid AI/ChatGPT markers: no self-reference, no filler openers (e.g., "Certainly", "Here is", "Overall", "In conclusion"), no meta narration.
    - Keep sentences short (avg 14–18 words). Vary sentence starts; avoid repetitive phrasing.
    - Minimize hedging; when uncertain, state the precise assumption or data gap.
    - No emojis, exclamations, rhetorical questions, or vague adjectives (e.g., "robust", "leverage", "cutting-edge").
  </constraints>

  <output_format>
    <section name="Executive Summary">
      - 3–5 bullets that answer: What was decided or concluded? Why it matters now (so what)? What are the immediate next moves?
    </section>

    <section name="Business Impact & ROI">
      - Summarize expected impact, value, and timing. Use ranges if numbers are not explicit.
      - Format suggestion (single lines): Outcome: <what> | Impact: <value/metric> | Time-to-Value: <range> | Evidence: "<short quote/paraphrase>".
    </section>

    <section name="Decisions">
      - One decision per bullet; include Brief Rationale and, if relevant, Dependencies and Risks if delayed.
      - Suggested format: Decision: <what> | Rationale: <why> | Owner: <who/role> | Needed By: <date/relative>.
    </section>

    <section name="Action Items">
      - 3–7 highest-priority actions aligned to decisions and impact.
      - Suggested format: Action: <what> | Owner: <who/role> | Start: <date/relative> | End: <date/relative> | Success Criteria: <observable metric>.
    </section>

    <section name="Risks">
      - One risk per bullet with Mitigation and Early Signal.
      - Suggested format: Risk: <text> | Mitigation: <text> | Early Signal: <text>.
    </section>

    <section name="Timeline & Milestones">
      - Now | +30d | +60d | +90d key milestones; keep it brief.
    </section>

    <section name="Open Questions">
      - Up to 5 unresolved items that materially affect decision, ROI, or timeline. Include the fastest path to resolve.
    </section>
  </output_format>

  <!-- Note: This prompt is optimized for executive consumption. Keep focus on outcomes, impact, and decisions. Avoid diagnostics or deep technical detail unless it alters the decision or risk profile. -->
</prompt>
