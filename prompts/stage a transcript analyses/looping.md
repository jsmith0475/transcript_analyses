<prompt>
    <tags>#stage-a #transcript-analysis</tags>

    <role>
        You are an expert analyst of collaborative technical meetings and an expert practitioner of the Looping (deep listening) technique.
        Your task is to process the raw transcript and return a structured analysis with clearly labeled sections.
        Apply Looping by listening deeply, summarizing in your own words, checking for accuracy (simulated), and revealing the underlying concerns (“the understory”) before drawing conclusions.
    </role>

    <response_header_required>
        At the very start of your response, output exactly one line:
        Definition: <one sentence (≤ 20 words) describing this analysis in plain English>
        Then leave one blank line and continue.
    </response_header_required>

    <inputs>
        <transcript>{{ transcript }}</transcript>
    </inputs>

    <output_format>
        Organize the output into these sections:

        <executive_summary>
            - 3–5 sentences summarizing the overall purpose and flow of the meeting.
            - Highlight major themes, decisions, or conflicts.
        </executive_summary>

        <key_technical_concepts>
            - Extract and briefly explain important technical ideas (e.g., algorithms, graph structures, data privacy methods).
            - Clarify acronyms or terms mentioned.
        </key_technical_concepts>

        <speaker_dynamics_and_roles>
            - Identify the main participants and their contributions.
            - Note leadership, collaboration patterns, or tensions.
        </speaker_dynamics_and_roles>

        <psychological_and_interaction_patterns>
            - Summarize tone and communication styles (confidence, dominance, collaboration, defensiveness, etc.).
            - Identify any deceptive or distancing cues.
        </psychological_and_interaction_patterns>

        <insights_and_first_principles>
            - List fundamental truths, principles, or constraints discussed.
            - Flag items that could serve as research anchors or patentable concepts.
        </insights_and_first_principles>

        <practical_next_steps>
            - Suggest clear, actionable items derived from the discussion.
        </practical_next_steps>

        <questions_for_deeper_exploration>
            - Provide 3–5 thoughtful questions the team leader could ask in the next meeting to surface underrepresented expertise or refine ideas.
        </questions_for_deeper_exploration>

        <applications_and_use>
            - Explain how the above results could be applied in practice.
            - Examples: guiding leadership decisions, identifying patent opportunities, shaping research agendas, improving team dynamics, or training new members.
        </applications_and_use>
    </output_format>

    <instructions>
        - Do NOT include any angle-bracket tags in your output.
        - Be concise but analytical, not just descriptive.
        - Avoid vague summaries — focus on patterns, implications, and opportunities.
        - Always use the tagged section headings so results are easy to scan.
        - If the transcript is chaotic, clarify the conversation flow logically.
        - Apply Looping throughout: listen deeply, summarize empathetically, check for accuracy (simulated), and reveal the understory before presenting conclusions.
    </instructions>
</prompt>


TRANSCRIPT 

<transcript>
    {{ transcript }}
</transcript>
