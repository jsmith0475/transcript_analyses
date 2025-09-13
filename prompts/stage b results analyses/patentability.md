<prompt>
  <tags>#stage-b #results-analysis</tags>

  <role>
    Identify potentially patentable ideas; classify across strategic dimensions; assess patentability likelihood.
  </role>

  <response_header_required>
    At the very start of your response, output exactly three line:
    Definition: <three sentence (≤ 100 words) describing this analysis in plain English>
    Then leave one blank line and continue.
  </response_header_required>

  <constraints>
    - For any tabular summary, return tables as HTML, not Markdown. Use valid HTML table structure:
      <table><thead><tr><th>…</th></tr></thead><tbody>…</tbody></table>
    - Do not wrap the HTML table in code fences.
  </constraints>

  <directions>
    You are an expert analyst specializing in product strategy and decision-making frameworks. Given the all the code (python, javascript, yaml, config, markdown, etc.) and discussion, your task is to identify and classify ideas into **8 distinct categories** based on the following dimensions:

  1. **Capable vs Differentiable**:
    - Capable: Focuses on reliability, functionality, and meeting basic needs.
    - Differentiable: Focuses on unique features, innovation, or emotional appeal.

  2. **Short-Term vs Long-Term**:
    - Short-Term: Benefits or impacts that are immediate but may not sustain over time.
    - Long-Term: Benefits or impacts that grow or endure over time.

  3. **Fragile vs Antifragile**:
    - Fragile: Vulnerable to disruption, change, or stress.
    - Antifragile: Gains strength or value from disruption, change, or stress.

  ### Steps:
  1. Identify ideas or themes from the provided text.
  2. Group these ideas into one of the **8 combinations** of the above categories:
    - Capable, Short-Term, Fragile
    - Capable, Short-Term, Antifragile
    - Capable, Long-Term, Fragile
    - Capable, Long-Term, Antifragile
    - Differentiable, Short-Term, Fragile
    - Differentiable, Short-Term, Antifragile
    - Differentiable, Long-Term, Fragile
    - Differentiable, Long-Term, Antifragile
  3. Provide a concise explanation for each categorization.

  ### Patentability Assessment:
  For each identified idea, assess its potential for patentability based on these insights:
  - Categories most likely to lead to patentable ideas:
    - Differentiable, Long-Term, Antifragile
    - Differentiable, Long-Term, Fragile
    - Differentiable, Short-Term, Antifragile
  - Justify whether the idea aligns with these categories and explain why it might (or might not) be patentable.

  ### Output:
  For each identified idea:
  - **Category**: [Specify one of the 8 categories]
  - **Idea**: [State the idea or theme]
  - **Justification**: [Provide reasoning for the categorization]
  - **Patentability**: [Likely Patentable / Unlikely Patentable]
    - **Reason**: [Explain why the idea is or is not patentable based on the category and characteristics.]

  ### Markdown & Tables — How to Format
  - Use clear Markdown headings and bullet lists for explanatory sections.
  - You may show small, inline examples as Markdown tables. For instance, a header row looks like:
    
    My Table Summary: Create a Table that summarizes all stuff. For example:
    
    |**My Category**|**An Idea**|**Etc**|**Etc**|**Etc**|
    |---|---|---|---|---|
    
  - For the primary Patentability Summary table at the end of your response, return a real HTML table (see constraints). Do not wrap the HTML table in code fences.


  Patentability Summary (HTML Table Required): provide a tabular summary of all patentable ideas using an HTML `<table>` with `<thead>` and `<tbody>` as specified in the constraints.

</directions>

<inputs>
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
</inputs>
