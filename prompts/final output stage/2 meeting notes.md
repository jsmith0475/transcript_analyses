<prompt>
  <response_header_required>
        At the very start of your response, output exactly one line:
        Definition: <one sentence (≤ 20 words) describing this analysis in plain English>
        Then leave one blank line and continue.
  </response_header_required>

This is the {context} and {transcript} from a meeting. Please perform the following tasks:

Attendee List: Confirm and provide a list of attendees from the transcript and attendance list.

Meeting Details: Provide details about the meeting from the {transcript}, capturing the main discussions, decisions, and any major insights shared.

Core Subject Areas Analysis: Identify core subject areas discussed in the meeting. Provide a very detailed breakdown for each area, including its significance, associated risks, and any concerns raised. Structure this analysis so someone who did not attend would gain a solid understanding of the main topics covered.

Determining and Contributing (please give a single line description for reference): List of the most significant Determining and contributing factors, why they are significant.

First Principles Analysis: Identify first principles discussed in the meeting. For each first principle, provide a very detailed title of the first principle, a breakdown of the principle, including its significance, associated risks, and any concerns raised.

Issue-Solution Pairs: Extract all explicitly mentioned issues or problems from the transcript, along with any identified or implied solutions. Each issue-solution pair should be detailed, comprehensive, and clear.

Action Items: List all explicit and implicit action items from the transcript, with enough context to understand Determine's purpose.
Determine
Patentable Ideas: Summary of Patentable Ideas, listing those that are more Differentiable, Long-Term, Antifragile. Include any summary table on patentable ideas, if created.

Since these notes will be used in my Obsidian system as my "second brain," link the first mention of major concepts in [[ ]] brackets to support "Linking is Thinking." This should include items likely to be referenced across related topics, such as [[Retrieval-Augmented Generation (RAG)]], [[Neo4j]], [[vector embeddings]], [[first principles]], and other relevant concepts that arise in the context of this discussion.

</prompt>

 <inputs>
    <context>{{ context }}</context>
    <transcript optional="true">{{ transcript }}</transcript>
</inputs>