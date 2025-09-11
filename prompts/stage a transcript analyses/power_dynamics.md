<prompt>
  <tags>#stage-a #transcript-analysis</tags>

  <role>Analyze the raw transcript and produce a structured, evidence-based report.</role>

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
    - Use clear headings and bullet points.
  </constraints>

  <output_format>
    <section name="Analysis">- Organize findings with clear headings and bullets.</section>
  </output_format>

  <instructions>
  Power Dynamics & Influence Tactics

  Analyze the meeting transcript to surface who holds sway, how they wield it, and the immediate effects on alignment and decisions. Be evidence‑based: include short quotes or concise paraphrases for each claim.

  What to look for

  Turn‑taking asymmetry, interruptions, deference, hedging vs certainty, imperative language
  Cialdini tactics: authority, consensus, reciprocity, scarcity, liking, commitment/consistency
  French–Raven power bases: legitimate, expert, referent, reward, coercive, informational
  Output format (use these exact headings)

  Power Moves (by speaker)

  For each speaker, list moves as:
  Move: <brief label> | Evidence: "<short quote>" | Power base/tactic: <label> | Effect: <immediate impact>
  Influence Episodes

  For each episode:
  Who→Whom: <A→B> | Tactic: <label> | Outcome: <what changed> | Resistance/Counter‑move: <if any> | Evidence: "<short quote>"
  Status Gradient & Participation

  Speaking Time: who dominated vs who was brief/silent (qualitative, with a quote)
  Interruptions & Deference: patterns and by whom
  Participation Equity: balanced vs skewed (with a quote)
  Risks

  One per bullet, concise (e.g., dominance traps, conformity pressure, silenced voices), each with brief evidence
  Actions

  One per bullet, specific guardrails/facilitation moves to balance influence (optional Owner and Due inline)
  </instructions>
</prompt>
