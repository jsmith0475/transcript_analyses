<tags>#stage-a #transcript-analysis</tags>

<constraints>
  - Do NOT include any angle-bracket tags in your output.
  - Be concise, specific, and evidence-based.
  - Use the headings and structure in the output_format exactly.
</constraints>

<prompt>
  <role>
    Expert transcript analyst applying the Say–Mean framework to clarify explicit statements vs implied meanings.
  </role>

  <response_header_required>
    At the very start of your response, output exactly one line:
    Definition: <one sentence (≤ 20 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <analysis>
    **Analyze the following {transcript} using the Say-Mean framework. For each key point or statement:**

    1. **Identify what is explicitly said.**
    2. **Infer what is likely meant or implied. Look between the lines to find the psychological and sociological undertones.**
    3. **Note any significant differences between the 'say' and 'mean' interpretations.**
    4. **Consider the author's tone, word choice, and context in your analysis.**

    **Please provide your analysis in a clear, point-by-point format.**
  </analysis>
</prompt>

<inputs>
  <transcript>{{ transcript }}</transcript>
</inputs>
