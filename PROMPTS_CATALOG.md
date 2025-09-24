Prompts Catalog and Cognitive Architecture
=========================================

Purpose of this document
-----------------------
This guide explains the staged prompt design used by the Transcript Analysis Tool and documents each built‑in prompt. It describes how Stage A, Stage B, and Final prompts work together to extract meaning from complex, human conversations and to produce actionable, trustworthy outputs.

How the staged prompts work (cognitive architecture)
----------------------------------------------------
Real transcripts contain multiple, overlapping signals: facts, intentions, attitudes, power dynamics, and implicit assumptions. A single “one‑shot” prompt tends to miss nuance. The app therefore uses three cooperating stages:

- Stage A — Transcript Analysis (specialized lenses)
  - Each analyzer examines the raw transcript through a particular lens (e.g., what was said vs. what was meant; perspectives; premises; postulates). The goal is fidelity and coverage, not final synthesis.
  - Outputs are short, structured, and easy to reuse (headings/bullets/tables), giving later stages high‑quality material.

- Stage B — Results Analysis (meta‑reasoning over Stage A)
  - Takes the combined Stage A outputs (a fair‑budget context) and, optionally, a transcript excerpt or summary.
  - Performs higher‑order reasoning: compare/contrast, reconcile conflicts, identify drivers and hypotheses, assess patentability, etc.

- Final — Synthesis (documents for people)
  - Accumulates Stage A + Stage B and formats end‑user deliverables: Meeting Notes, Composite Notes, Executive Summaries, and focused question sets.
  - Emphasizes clarity, actions, decisions, risks, and clean exports.

Why this matters for human dynamics
-----------------------------------
Human group conversations encode expertise, social positioning, risk management, and tacit knowledge. The staged design:

- Makes implicit knowledge visible: dedicated lenses detect subtle cues (e.g., function words, hedging, stance) known to correlate with psychological states and social dynamics.
- Reduces cognitive load: Stage A decomposes the problem; Stage B recomposes it with explicit cross‑checks; Final speaks in concise human‑friendly language.
- Improves reliability: structured intermediate artifacts are easier to audit and reason about than a single long narrative.

Elements common to prompts
--------------------------
- Variables:
  - `{{ transcript }}`: the transcript text (Stage A required; optional for Stage B/Final).
  - `{{ context }}`: combined Stage A results (Stage B and Final).
- Tags: a free‑form list inside `<tags>` (e.g., `#stage-a #rhetoric`). Helpful for organization.
- Structure: prompts commonly include `<role>`, `<response_header_required>`, `<inputs>`, `<constraints>`, `<output_format>`, and `<instructions>`. The app does not enforce a schema, but this structure documents intent and yields consistent outputs.
- Tables: Markdown tables are supported; for critical summaries (e.g., Patentability) prefer HTML `<table>` for rendering reliability (the app sanitizes HTML before display).

Stage A — Transcript Analysis (built‑in and included prompts)
------------------------------------------------------------

1) Say‑Means (`prompts/stage a transcript analyses/say-means.md`)
- What it does: Distinguishes the literal surface of an utterance (“what was said”) from plausible communicative intent and subtext (“what it means”).
- Why it matters: In natural dialogue, speakers often hedge, understate, or imply. Separating form from intent exposes commitments, constraints, and negotiations.
- How to interpret: Look for systematic gaps between “say” and “means” across roles or topics; recurring gaps frequently mark unspoken constraints or risk.

2) Perspective–Perception (`prompts/stage a transcript analyses/perspective-perception.md`)
- What it does: Identifies stakeholder viewpoints, frames, and attentional focus (what each actor attends to, values, or avoids).
- Why it matters: Conflicts are often frame conflicts; mapping perspectives reveals alignment and misalignment without pathologizing either side.
- How to interpret: Compare perspectives across roles and time; convergence suggests shared mental models, divergence suggests coordination work.

3) Premises–Assertions (`prompts/stage a transcript analyses/premsises-assertions.md`)
- What it does: Extracts explicit claims, hidden premises, and supporting/contradicting evidence.
- Why it matters: Decisions are only as sound as their premises; surfacing them enables challenge, testing, and redesign.
- How to interpret: Look for assertions resting on weak or unshared premises; track which premises reappear across topics.

4) Postulate–Theorem (`prompts/stage a transcript analyses/postulate-theorem.md`)
- What it does: Reformulates discussion into first‑principle postulates and derived theorems (implications if the postulates hold).
- Why it matters: Forces clarity about axioms and causal structure; reduces reliance on analogies or precedent.
- How to interpret: Use derived theorems to test consistency across the conversation; unstable theorems signal shaky assumptions.

5) Power Dynamics (`prompts/stage a transcript analyses/power_dynamics.md`)
- What it does: Observes influence moves, deference, face‑work, and status‑related language (requests vs. directives, mitigation, turn‑taking).
- Why it matters: Power and status shape what becomes sayable; recognizing them improves facilitation and equitable decision‑making.
- How to interpret: Notice who frames problems and who proposes solutions; imbalance can indicate risk for silent objections.

6) Looping (`prompts/stage a transcript analyses/looping.md`)
- What it does: Detects repeated themes, stuck loops, and cyclical reasoning that indicates unresolved tensions.
- Why it matters: Loops often flag the few issues that matter most but are hard to resolve.
- How to interpret: Use loops to prioritize; break cycles by adding missing information, reframing, or choosing an experiment.

7) Pennebaker/LIWC‑style Linguistic Signals (`prompts/stage a transcript analyses/pennebaker.md`)
- What it does: Inspects function words (pronouns, tense, prepositions), affect words, and style markers inspired by LIWC research.
- Why it matters: Function words correlate with attention, status, group identity, and psychological states; small shifts can reveal big changes.
- How to interpret: Track pronoun shifts (I→we), certainty/tense markers, and affect balance across segments and speakers.

8) Sowell Vision & Economic Reasoning (`prompts/stage a transcript analyses/soul.md`)
- What it does: Classifies statements by Sowell’s constrained vs. unconstrained visions; evaluates economic reasoning (trade‑offs, incentives, dispersed knowledge) and cultural explanations.
- Why it matters: Reveals hidden assumptions about human nature, policy design, and market coordination that drive proposals and conflict.
- How to interpret: Contrast trade‑off recognition vs. utopian framing; highlight incentive‑aware arguments and evidence‑based appeals; surface red/green flags.

9) SPIN (Situation–Problem–Implication–Need) Analysis (`prompts/stage a transcript analyses/spin-analysis.md`)
- What it does: Extracts SPIN items per topic thread to show facts/constraints, pains/opportunities, consequences, and desired payoffs.
- Why it matters: Structures discovery; turns diffuse discussion into decision‑relevant needs with evidence and acceptance criteria.
- How to interpret: Map SPIN threads across topics; use gaps (missing S/P/I/N) to guide next questions and actions.

Stage B — Results Analysis (built‑in)
-------------------------------------

1) Analysis of Competing Hypotheses (ACH) (`prompts/stage b results analyses/analysis of competing hyptheses.md`)
- What it does: Compares multiple hypotheses against evidence extracted in Stage A, looking for disconfirming evidence and consistency.
- Why it matters: ACH reduces confirmation bias and encourages structured challenge of the preferred story.
- How to interpret: Prefer hypotheses that best survive disconfirmation; record assumptions that would swing the choice.

2) First Principles (`prompts/stage b results analyses/first principles.md`)
- What it does: Re‑derives options from irreducible facts and constraints (as opposed to analogy or precedent).
- Why it matters: Avoids local maxima and imported constraints; promotes genuinely novel options.
- How to interpret: Use outputs to generate experiments that directly test first‑principle assertions.

3) Determining Factors (`prompts/stage b results analyses/determining factors.md`)
- What it does: Extracts the few drivers, constraints, and enabling conditions that determine outcomes.
- Why it matters: Focus enables leverage; most decisions hinge on a small set of factors.
- How to interpret: Tie actions to factors with highest sensitivity or uncertainty.

4) Patentability (`prompts/stage b results analyses/patentability.md`)
- What it does: Classifies ideas across “Capable/Differentiable × Short/Long‑Term × Fragile/Antifragile” and assesses patentability likelihood.
- Why it matters: Organizes ideation along strategic dimensions and highlights novelty/non‑obviousness factors (not legal advice).
- How to interpret: Use HTML summary tables to scan opportunities; look for clusters in Differentiable + Long‑Term cells.

5) SPIN Synthesis (`prompts/stage b results analyses/spin-synthesis.md`)
- What it does: Ingests Stage A SPIN output to rank needs, score impact/effort/confidence, summarize ROI/timelines, and produce a decision‑ready action plan.
- Why it matters: Converts discovery into prioritized execution with explicit assumptions, risks, and measurable success criteria.
- How to interpret: Sort by value score; tie actions to top needs; revisit assumptions as new evidence emerges.

Final — Synthesis (built‑in)
----------------------------

1) Meeting Notes (`prompts/final output stage/meeting notes.md`)
- What it does: Produces concise, scannable notes: attendees, summary, actions, decisions, risks.
- How to interpret: Copy/paste into your notes system; actions include owner/due when available.

2) Composite Note (`prompts/final output stage/composite note.md`)
- What it does: A single document combining key outputs from Stage A and B with metrics.
- Tone/Format: Plain, direct business language; short sentences; avoid AI‑style phrasing; includes Decisions, Action Items, and Risks.
- How to interpret: Use as a full audit trail or to onboard new stakeholders.

3) What Should I Ask? (`prompts/final output stage/what_should_i_ask.md`)
- What it does: Curates high‑leverage questions for the next conversation based on detected gaps and risks.
- How to interpret: Treat as a checklist; turn questions into short experiments or agenda items.

4) Insightful Article (`prompts/final output stage/insightful_article.md`)
- What it does: Generates a ~1000‑word, privacy‑safe article on the principal subject synthesized from the combined Stage A+B context (and optional transcript excerpt/summary). It requires a strong introduction and conclusion, scannable Markdown headings, short paragraphs, and grounded claims (no fabrication). Strict privacy/anonymization constraints prohibit PII or identifying references to real people, companies, or products.
- How to interpret: Use as a narrative summary for broad stakeholders. Scan the Title/Definition line to confirm the identified subject; in the body, look for core themes supported by explicit evidence from earlier stages. The “Implications” and “Recommendations” sections should translate insights into next steps without leaking identities (roles/organizations remain generic).

Interpreting results wisely
---------------------------
- Triangulate: Prefer patterns that appear across multiple Stage A lenses.
- Follow the evidence: Note where Stage B finds disconfirming evidence; treat those items seriously.
- Human‑in‑the‑loop: These analyses increase signal; final judgments remain with the team.

Selected references and foundations
----------------------------------
- Pennebaker, J. W., Boyd, R. L., Jordan, K., & Blackburn, K. (2015). The Development and Psychometric Properties of LIWC2015. Pennebaker Conglomerates.  
- Pennebaker, J. W. (2011). The Secret Life of Pronouns: What Our Words Say About Us. Bloomsbury.  
- Heuer, R. J. (1999). Psychology of Intelligence Analysis. Center for the Study of Intelligence. (ACH method)  
- Toulmin, S. (2003). The Uses of Argument (Updated ed.). Cambridge University Press. (claims/warrants/backing)  
- Meadows, D. (2008). Thinking in Systems. Chelsea Green. (feedback loops)  
- Senge, P. (2006). The Fifth Discipline. Doubleday. (systems thinking, loops)  
- Cialdini, R. (2006). Influence: The Psychology of Persuasion. Harper Business. (influence/power cues)  
- Kahneman, D. (2011). Thinking, Fast and Slow. Farrar, Straus and Giroux. (cognitive biases that stages help mitigate)  

Notes
-----
This catalog summarizes intent and interpretation. It is not legal advice and does not replace domain‑expert review. When assessing patentability, consult qualified counsel for jurisdiction‑specific standards (e.g., novelty and non‑obviousness).
5) Executive Summary (`prompts/final output stage/executive_summary.md`)
- What it does: Produces a one‑page, leadership‑ready summary that answers “so what?” and “what now?” with decisions, business impact, key risks, and next steps. Uses a plain, direct tone with short sentences and avoids AI‑style phrasing.
- How to interpret: Treat as an executive brief for quick alignment. Scan Executive Summary, then Decisions and Action Items for immediate follow‑through; Business Impact & ROI and Timeline provide magnitude and timing at a glance.
