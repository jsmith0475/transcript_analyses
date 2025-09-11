"""
Data models for the Transcript Analysis Tool.
"""

from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class AnalyzerStatus(str, Enum):
    """Status of an analyzer during processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class TokenUsage(BaseModel):
    """Token usage tracking for LLM calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    # Echo the max_tokens limit used for this completion (for display/telemetry)
    max_tokens: Optional[int] = None
    
    def add(self, other: 'TokenUsage') -> 'TokenUsage':
        """Add token usage from another instance."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


class TranscriptSegment(BaseModel):
    """A segment of the transcript with speaker information."""
    segment_id: int
    speaker: Optional[str] = None
    text: str
    timestamp: Optional[str] = None
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Segment text cannot be empty')
        return v.strip()


class Speaker(BaseModel):
    """Speaker information extracted from transcript."""
    id: str
    name: Optional[str] = None
    segments_count: int = 0
    total_words: int = 0


class TranscriptMetadata(BaseModel):
    """Metadata about the transcript."""
    filename: Optional[str] = None
    date: Optional[datetime] = None
    duration: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    word_count: int = 0
    segment_count: int = 0
    speaker_count: int = 0


class ProcessedTranscript(BaseModel):
    """Processed transcript with structured segments and metadata."""
    segments: List[TranscriptSegment]
    speakers: List[Speaker]
    metadata: TranscriptMetadata
    raw_text: str
    has_speaker_names: bool = False
    
    @property
    def text_for_analysis(self) -> str:
        """Get formatted text for analysis."""
        if not self.segments:
            return self.raw_text
        
        lines = []
        for segment in self.segments:
            if segment.speaker:
                lines.append(f"{segment.speaker}: {segment.text}")
            else:
                lines.append(segment.text)
        return "\n\n".join(lines)


class Insight(BaseModel):
    """An insight extracted from analysis."""
    text: str
    confidence: Optional[float] = None
    source_analyzer: Optional[str] = None
    category: Optional[str] = None
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Insight text cannot be empty')
        return v.strip()


class Concept(BaseModel):
    """A concept or entity identified in the analysis."""
    name: str
    description: Optional[str] = None
    related_concepts: List[str] = Field(default_factory=list)
    occurrences: int = 1
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Concept name cannot be empty')
        return v.strip()


class AnalysisResult(BaseModel):
    """Result from a single analyzer."""
    analyzer_name: str
    raw_output: str
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    insights: List[Insight] = Field(default_factory=list)
    concepts: List[Concept] = Field(default_factory=list)
    processing_time: float = 0.0
    token_usage: Optional[TokenUsage] = None
    # Model actually used for this analyzer execution (echo for audit/UI)
    model_used: Optional[str] = None
    status: AnalyzerStatus = AnalyzerStatus.PENDING
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_context_string(self) -> str:
        """Convert result to string for context passing."""
        lines = [f"## {self.analyzer_name} Analysis\n"]
        
        if self.raw_output:
            lines.append(self.raw_output)
        
        if self.insights:
            lines.append("\n### Key Insights:")
            for insight in self.insights[:5]:  # Top 5 insights
                lines.append(f"- {insight.text}")
        
        if self.concepts:
            lines.append("\n### Identified Concepts:")
            concept_names = [c.name for c in self.concepts[:10]]  # Top 10 concepts
            lines.append(", ".join(concept_names))
        
        return "\n".join(lines)


class AnalysisContext(BaseModel):
    """Context passed between analysis stages."""
    transcript: Optional[ProcessedTranscript] = None
    previous_analyses: Dict[str, AnalysisResult] = Field(default_factory=dict)
    accumulated_insights: List[Insight] = Field(default_factory=list)
    identified_concepts: Set[str] = Field(default_factory=set)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_combined_context(self, include_transcript: bool = False) -> str:
        """Get combined context string for Stage B analyzers."""
        lines = []
        
        if include_transcript and self.transcript:
            lines.append("## Original Transcript\n")
            lines.append(self.transcript.text_for_analysis)
            lines.append("\n---\n")
        
        if self.previous_analyses:
            lines.append("## Previous Analysis Results\n")
            for analyzer_name, result in self.previous_analyses.items():
                lines.append(result.to_context_string())
                lines.append("\n---\n")
        
        return "\n".join(lines)


class ActionItem(BaseModel):
    """An action item extracted from the meeting."""
    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    
    @validator('description')
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Action item description cannot be empty')
        return v.strip()


class KeyDecision(BaseModel):
    """A key decision made during the meeting."""
    decision: str
    rationale: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    
    @validator('decision')
    def decision_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Decision text cannot be empty')
        return v.strip()


class PatentableIdea(BaseModel):
    """A potentially patentable idea identified."""
    title: str
    description: str
    novelty_assessment: Optional[str] = None
    potential_claims: List[str] = Field(default_factory=list)
    priority: Optional[str] = None


class MeetingNotes(BaseModel):
    """Structured meeting notes output."""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    attendees: List[str] = Field(default_factory=list)
    summary: str
    analyses: Dict[str, str] = Field(default_factory=dict)
    action_items: List[ActionItem] = Field(default_factory=list)
    key_decisions: List[KeyDecision] = Field(default_factory=list)
    first_principles: List[str] = Field(default_factory=list)
    determining_factors: List[str] = Field(default_factory=list)
    patentable_ideas: List[PatentableIdea] = Field(default_factory=list)
    linked_concepts: List[str] = Field(default_factory=list)
    issue_solution_pairs: Dict[str, str] = Field(default_factory=dict)
    next_steps: List[str] = Field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Convert meeting notes to Obsidian-compatible markdown."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        title = self.metadata.get('title', 'Meeting Notes')
        
        lines = [f"# {date_str} - {title}\n"]
        
        if self.metadata:
            lines.append("## Metadata")
            for key, value in self.metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        if self.attendees:
            lines.append("## Attendees")
            for attendee in self.attendees:
                lines.append(f"- {attendee}")
            lines.append("")
        
        lines.append("## Summary")
        lines.append(self.summary)
        lines.append("")
        
        if self.action_items:
            lines.append("## Action Items")
            for item in self.action_items:
                assignee = f" (@{item.assignee})" if item.assignee else ""
                due = f" - Due: {item.due_date}" if item.due_date else ""
                lines.append(f"- [ ] {item.description}{assignee}{due}")
            lines.append("")
        
        if self.key_decisions:
            lines.append("## Key Decisions")
            for decision in self.key_decisions:
                lines.append(f"- **{decision.decision}**")
                if decision.rationale:
                    lines.append(f"  - Rationale: {decision.rationale}")
            lines.append("")
        
        if self.patentable_ideas:
            lines.append("## Patentable Ideas")
            for idea in self.patentable_ideas:
                lines.append(f"### {idea.title}")
                lines.append(idea.description)
                if idea.novelty_assessment:
                    lines.append(f"\n**Novelty**: {idea.novelty_assessment}")
                lines.append("")
        
        if self.linked_concepts:
            lines.append("## Linked Concepts")
            for concept in self.linked_concepts:
                lines.append(f"- [[{concept}]]")
            lines.append("")
        
        if self.next_steps:
            lines.append("## Next Steps")
            for step in self.next_steps:
                lines.append(f"- {step}")
            lines.append("")
        
        return "\n".join(lines)


class CompositeReport(BaseModel):
    """Complete composite report combining all analyses."""
    title: str
    date: datetime = Field(default_factory=datetime.now)
    meeting_notes: MeetingNotes
    stage_a_results: Dict[str, AnalysisResult] = Field(default_factory=dict)
    stage_b_results: Dict[str, AnalysisResult] = Field(default_factory=dict)
    total_processing_time: float = 0.0
    total_token_usage: TokenUsage = Field(default_factory=TokenUsage)
    
    def to_markdown(self) -> str:
        """Convert composite report to markdown."""
        date_str = self.date.strftime("%Y-%m-%d")
        lines = [f"# {date_str} - {self.title}\n"]
        
        # Meeting Notes Section
        lines.append("## Meeting Notes\n")
        lines.append(self.meeting_notes.to_markdown())
        lines.append("\n---\n")
        
        # Stage A Results
        if self.stage_a_results:
            lines.append("## Stage A - Transcript Analysis\n")
            for analyzer_name, result in self.stage_a_results.items():
                lines.append(f"### {analyzer_name}\n")
                lines.append(result.raw_output)
                
                if result.insights:
                    lines.append("\n**Key Insights:**")
                    for insight in result.insights[:5]:
                        lines.append(f"- {insight.text}")
                
                lines.append("\n---\n")
        
        # Stage B Results
        if self.stage_b_results:
            lines.append("## Stage B - Results Analysis\n")
            for analyzer_name, result in self.stage_b_results.items():
                lines.append(f"### {analyzer_name}\n")
                lines.append(result.raw_output)
                
                if result.insights:
                    lines.append("\n**Key Insights:**")
                    for insight in result.insights[:5]:
                        lines.append(f"- {insight.text}")
                
                lines.append("\n---\n")
        
        # Processing Metrics
        lines.append("## Processing Metrics\n")
        lines.append(f"- **Total Processing Time**: {self.total_processing_time:.2f} seconds")
        lines.append(f"- **Total Tokens Used**: {self.total_token_usage.total_tokens:,}")
        lines.append(f"  - Prompt Tokens: {self.total_token_usage.prompt_tokens:,}")
        lines.append(f"  - Completion Tokens: {self.total_token_usage.completion_tokens:,}")
        
        return "\n".join(lines)


class PipelineResult(BaseModel):
    """Complete pipeline execution result."""
    transcript: ProcessedTranscript
    analyses: Dict[str, AnalysisResult] = Field(default_factory=dict)
    meeting_notes: Optional[MeetingNotes] = None
    composite_report: Optional[CompositeReport] = None
    total_processing_time: float = 0.0
    total_token_usage: TokenUsage = Field(default_factory=TokenUsage)
    success: bool = True
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def get_stage_results(self, stage: str) -> Dict[str, AnalysisResult]:
        """Get results for a specific stage."""
        stage_analyzers = {
            'stage_a': ['say_means', 'perspective_perception', 'premises_assertions', 'postulate_theorem'],
            'stage_b': ['competing_hypotheses', 'first_principles', 'determining_factors', 'patentability'],
            'final': ['meeting_notes']
        }
        
        if stage not in stage_analyzers:
            return {}
        
        return {
            name: result 
            for name, result in self.analyses.items() 
            if name in stage_analyzers[stage]
        }


class AnalysisRequest(BaseModel):
    """Request to analyze a transcript."""
    transcript: str
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    selected_analyzers: Optional[List[str]] = None
    include_transcript_in_stage_b: bool = False
    session_id: Optional[str] = None
    
    @validator('transcript')
    def transcript_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Transcript cannot be empty')
        return v.strip()


class AnalysisProgress(BaseModel):
    """Progress update for analysis."""
    task_id: str
    overall_progress: float = 0.0
    current_stage: str = "initializing"
    analyzers: Dict[str, AnalyzerStatus] = Field(default_factory=dict)
    messages: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
