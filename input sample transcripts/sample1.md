# Product Strategy Meeting - Transcript

[00:00] Moderator: Welcome everyone. Today we’re discussing the Q4 product strategy for the Transcript Analysis Tool. Let's cover customer pain points, a lightweight roadmap, and potential IP opportunities.

[00:12] PM (Alex): The biggest issue customers report is that insights are buried in long transcripts. They want a way to extract action items and decisions quickly, and to see divergent viewpoints.

[00:25] Research Lead (Priya): In recent interviews, users emphasized knowledge reusability. They want Obsidian-style links and cross-references so insights don’t die after one meeting.

[00:38] Eng Lead (Marco): On the technical side, our current pipeline is solid but we need to ensure Stage B actually integrates all of Stage A. There’s a risk that long outputs from say-means overshadow premises-assertions if we just concatenate and trim at the end.

[00:54] IP Counsel (Dana): Also consider patentable aspects—our fair-share context budgeting in meta-analysis might be novel if we guarantee representation for each analyzer in downstream prompts.

[01:06] PM (Alex): Priorities for Q4: 1) Reliability under load (10 concurrent analyses), 2) Better UI clarity on progress and token usage, 3) Runtime prompt management so teams can tune frameworks without redeploys.

[01:19] Eng Lead (Marco): For reliability, we’ll use Celery chords with a race-free fan-in. For Stage B, I propose we compute per-analyzer token budgets—minimum allocation plus proportional distribution—to avoid starving smaller analyzers.

[01:33] Research Lead (Priya): From a methodology perspective, we should emphasize “Perspective-Perception” to expose differences in how stakeholders interpret the same facts. That’s crucial for identifying misalignment early.

[01:45] Moderator: What are the key assumptions we’re making?

[01:48] PM (Alex): We assume the LLM can produce structured outputs consistently. We also assume that users prefer markdown exports compatible with [[Obsidian]].

[01:57] IP Counsel (Dana): Challenge those assumptions. Consistency can vary with model choice and prompt drift. We need guardrails, validations, and perhaps JSON block extraction where possible.

[02:08] Eng Lead (Marco): We’ll log token usage per analyzer and aggregate per-stage. Also, a debug summary before Stage B LLM calls listing included analyzers and their allocated tokens. That should make the context source-of-truth auditable.

[02:21] PM (Alex): Another theme from customers is “first principles.” They want the system to separate foundational truths from assumptions and derived conclusions.

[02:30] Research Lead (Priya): Yes, and in “Premises-Assertions” we must call out where participants conflate evidence with inference.

[02:38] Moderator: What are the critical decisions we need from this session?

[02:41] PM (Alex): Approve the fair-share context budgeting, commit to runtime prompt CRUD in the web UI, and add a “files-first” loader for final outputs with a retry fallback.

[02:52] Eng Lead (Marco): Also confirm rate limits: 10 analyses/hour per session to prevent unexpected costs. And default to a test-friendly model during development.

[03:02] IP Counsel (Dana): For patentability, look for signals like: novel context allocation strategy, explicit AnalyzerRegistry with UI-driven defaults, and deterministic chord callbacks that persist authoritative mappings prior to meta-analysis.

[03:15] PM (Alex): What about action items?

[03:17] Moderator: Draft them now.

[03:20] Action (Assigned: Marco): Implement per-analyzer fair-share token budgeting for Stage B context with minimum tokens guaranteed and proportional redistribution, plus instrumentation logs.

[03:30] Action (Assigned: Priya): Expand Stage A prompts to elicit explicit claims vs. assumptions, and emphasize opposing viewpoints.

[03:37] Action (Assigned: Dana): Review the fair-share algorithm and runtime prompt editing for potential patent filings; prepare novelty analysis notes.

[03:45] Action (Assigned: Alex): Update the PRD with success metrics, load targets, and export scenarios for Obsidian with [[Concept Links]].

[03:54] Research Lead (Priya): One more risk: if transcripts exceed token budgets, we need summarization and chunking with overlap to preserve continuity.

[04:03] Eng Lead (Marco): Agreed. We’ll cap transcript inclusion in final stage, and use combined Stage A results for meta-analysis. Transcript inclusion in Stage B remains off by default to keep the signal strong.

[04:15] Moderator: Any disagreements?

[04:16] IP Counsel (Dana): None, but we should document the fairness allocator’s math and why it ensures representation without biasing toward the longest section.

[04:25] PM (Alex): Let’s ensure the UI disables “Start” while running and clearly shows “In Process” for Stage B and Final to avoid confusion.

[04:32] Moderator: Summary: We align on fair-share Stage B context budgeting, improved visibility, runtime prompt CRUD, and clear acceptance criteria. Next step is to implement and validate that Stage B actually uses all Stage A outputs via the allocation logs.

[04:45] All: Agreed.
