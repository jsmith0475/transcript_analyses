<prompt>
  <tags>#final #synthesis #insights</tags>

  <role>
    Propose high-leverage, insightful questions to ask next, grounded in the prior analyses and transcript.
  </role>

  <response_header_required>
    At the very start of your response, output exactly one line:
    Definition: <one sentence (≤ 20 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <inputs>
    <bio>
      Dr. Jerry A. Smith is a frontier AI lead researcher and consultant specializing in brain‑inspired, agentic intelligence and hierarchical reasoning. He architects autonomous AI systems that think, decide, and act like the human brain—translating hippocampal memory models and prefrontal decision frameworks into enterprise-grade agents that deliver measurable business impact. He currently serves as Managing Director of AI and Agentics R&D at Ailevate and sits on the board of Waggle.org, with prior leadership roles at Ankura, AgileThought, and Cognizant. A prolific author and creator, he has published 50+ insights reaching 100K+ views, hosts the Deep Dive – Frontier AI podcast, and wrote the science‑fiction novel “The Last Theorem.” Dr. Smith holds a PhD in Computer Science from Nova Southeastern University and is recognized for advancing neuro-cognitive architectures, multi‑agent systems, and advanced memory models for LLMs.
    </bio>
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
  </inputs>

  <constraints>
    - Do NOT include any angle-bracket tags in your output.
    - Questions must be actionable, specific, and tailored to the context.
  </constraints>

  <output_format>
    <section name="Questions">
      - 10–20 questions grouped by theme (if helpful); each is concise and high‑leverage.
    </section>
  </output_format>
</prompt>
