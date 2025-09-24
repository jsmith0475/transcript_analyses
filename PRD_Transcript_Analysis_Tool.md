# Product Requirements Document (PRD)
## Transcript Analysis Tool

**Version:** 1.0  
**Date:** September 6, 2025  
**Author:** Product Team  
**Status:** Draft

---

## 1. Executive Summary

The Transcript Analysis Tool is an AI-powered web application that transforms meeting transcripts into actionable insights through multi-stage analysis. It employs a sophisticated pipeline of specialized analyzers to extract meaning, identify patterns, and generate comprehensive reports suitable for knowledge management systems like Obsidian.

### Key Value Proposition
- Automated extraction of insights from unstructured conversation data
- Multi-perspective analysis using different analytical frameworks
- Obsidian-compatible output with knowledge graph integration
- Patent opportunity identification
- Actionable meeting notes generation

---

## 2. Problem Statement

### Current Challenges
1. **Information Loss**: Critical insights from meetings are often lost or buried in lengthy transcripts
2. **Manual Analysis Burden**: Extracting actionable items from conversations is time-consuming
3. **Lack of Structure**: Raw transcripts lack the structure needed for knowledge management systems
4. **Missed Opportunities**: Innovative ideas and patentable concepts go unrecognized
5. **Context Fragmentation**: Related concepts across meetings remain disconnected

### Target Users
- **Primary**: Knowledge workers, researchers, and innovation teams
- **Secondary**: Product managers, consultants, and strategic planners
- **Tertiary**: Patent attorneys and intellectual property professionals

---

## 3. Product Overview

### Core Concept
A three-stage analysis pipeline that progressively refines transcript data:

1. **Stage A - Transcript Analysis**: Direct analysis of conversation content
   - **Input**: Raw transcript only
   - **Output**: Individual intermediate results from each analyzer
   
2. **Stage B - Meta-Analysis**: Analysis of Stage A results to identify patterns
   - **Input**: Combined Stage A intermediate results (context)
   - **Output**: Higher-level insights and patterns
   
3. **Final Stage - Synthesis**: Generation of actionable outputs
   - **Input**: Stage A results + Stage B results + Original transcript
   - **Output**: Comprehensive meeting notes and composite documentation

### Key Differentiators
- Multi-stage analytical approach with different perspectives
- Customizable prompt templates for each analyzer
- Real-time progress tracking via WebSocket
- Obsidian-optimized output with automatic concept linking
- Flexible analyzer selection per stage

---

## 4. Functional Requirements

### 4.1 Core Features

#### 4.1.1 Transcript Processing
- **Input Methods**:
  - Direct text input via web interface
  - File upload (supported formats: .txt, .md, .markdown)
  - Maximum file size: 10MB
- **Speaker Identification**: Automatic detection and labeling of speakers
- **Segmentation**: Breaking transcript into analyzable segments

#### 4.1.2 Stage A Analyzers (Transcript Analysis)

1. **Say-Means Analyzer**
   - Identifies what was explicitly said vs. implied meanings
   - Extracts subtext and underlying messages
   - Output: Structured mapping of literal vs. interpretive content

2. **Perspective-Perception Analyzer**
   - Maps different viewpoints expressed in the conversation
   - Identifies perception gaps between participants
   - Output: Multi-perspective analysis matrix

3. **Premises-Assertions Analyzer**
   - Extracts foundational assumptions and claims
   - Validates logical consistency
   - Output: Argument structure diagram

4. **Postulate-Theorem Analyzer**
   - Identifies hypotheses and their supporting evidence
   - Maps theoretical frameworks discussed
   - Output: Theory-evidence relationships

#### 4.1.3 Stage B Analyzers (Results Analysis)

1. **Competing Hypotheses Analyzer**
   - Applies Analysis of Competing Hypotheses (ACH) methodology
   - Evaluates multiple explanations against evidence
   - Output: Hypothesis ranking with evidence matrix

2. **First Principles Analyzer**
   - Breaks down complex problems to fundamental truths
   - Identifies core assumptions
   - Output: First principles breakdown

3. **Determining Factors Analyzer**
   - Distinguishes causal factors from correlations
   - Identifies critical decision points
   - Output: Causal factor hierarchy

4. **Patentability Analyzer**
   - Identifies potentially patentable innovations
   - Assesses novelty and non-obviousness
   - Output: Patent opportunity assessment

#### 4.1.4 Final Stage Outputs

1. **Meeting Notes**
   - Executive summary
   - Action items with assignees
   - Key decisions made
   - Follow-up requirements

2. **Composite Note**
   - Comprehensive Obsidian-formatted document
   - Automatic concept linking with [[brackets]]
   - Hierarchical organization of insights
   - Cross-references between all analyses

### 4.2 User Interface Requirements

#### 4.2.1 Main Interface
- **Transcript Input Area**: Large text field with syntax highlighting
- **File Upload Zone**: Drag-and-drop support
- **Analyzer Selection Panel**: 
  - Three columns for Stage A, B, and Final
  - Checkboxes for individual analyzer selection
  - Select/Deselect all options per stage

#### 4.2.2 Analysis Configuration
- **Stage B Options**:
  - Include transcript toggle
  - Transcript inclusion mode (full/summary)
  - Maximum character limit for transcript inclusion

#### 4.2.3 Progress Tracking
- **Real-time Updates**: WebSocket-based progress notifications
- **Visual Indicators**:
  - Pending (gray)
  - Processing (animated spinner)
  - Completed (green checkmark)
  - Error (red X)
- **Time and Token Tracking**: Display processing time and token usage

#### 4.2.4 Results Interface
- **Tabbed Navigation**:
  - Stage A Results
  - Stage B Results
  - Final Outputs
- **Result Viewer**: Markdown-rendered content with syntax highlighting
- **Export Options**: 
  - Markdown (.md)
  - JSON (.json)
  - Copy to clipboard

#### 4.2.5 Insights Dashboard
- **Location**: Below Progress, titled “Insights” with a Type selector and export buttons.
- **Types**: All, Actions, Decisions, Risks (selector is always enabled, even during runs).
- **Source of Truth**: File-based (`final/insight_dashboard.json`) loaded via `/api/insights/<jobId>` after Final completion.
- **Behavior**: Panel clears on app start, reset, and new run start to avoid stale data.
- **Export**: Buttons export JSON/CSV/Markdown via `/api/job-file`.

### 4.3 Prompt Management

#### 4.3.1 Prompt Input Requirements
Each prompt template has specific input requirements based on its stage:

**Stage A Prompts**:
- **Input**: `{transcript}` - The raw transcript text
- **Processing**: Each analyzer runs independently with only the transcript
- **Output**: Individual intermediate results

**Stage B Prompts**:
- **Input**: `{context}` - Combined results from all Stage A analyzers
- **Processing**: Analyzes patterns across Stage A outputs
- **Output**: Meta-analysis results

**Final Stage Prompts**:
- **Inputs**: 
  - `{context}` - Combined Stage A + Stage B results
  - `{transcript}` - Original transcript (optional, based on settings)
- **Processing**: Synthesizes all previous analyses
- **Output**: Final deliverables (Meeting Notes, Composite Note, Executive Summary, What Should I Ask?, Insightful Article)

Insights Output Structure (Final)
- Final prompts must include explicit sections: “Decisions”, “Action Items”, and “Risks” with single-line bullets.
- Additionally, prompts must append a fenced `INSIGHTS_JSON` block mapping those bullets to a strict schema:
  - `{ actions: [{ title, owner?, due_date?, anchor? }], decisions: [{ title }], risks: [{ title }] }`
  - Dates use `YYYY-MM-DD`; `anchor` is optional and refers to a transcript segment (e.g., `#seg-123`).

#### 4.3.2 Prompt Editor
- **In-browser Editing**: Direct modification of analyzer prompts
- **Template Variables**: Stage-specific as defined above
- **Save Functionality**: Persist changes to filesystem
- **Reset to Default**: Restore original prompts

#### 4.3.3 Prompt Organization
- **Directory Structure**:
  ```
  prompts/
  ├── stage a transcript analyses/
  │   ├── 1 say-means.md
  │   ├── 2 perspective-perception.md
  │   ├── 3 premises-assertions.md
  │   └── 4 postulate-theorem.md
  ├── stage b results analyses/
  │   ├── 5 analysis of competing hypotheses.md
  │   ├── 6 first principles.md
  │   ├── 7 determining factors.md
  │   └── 8 patentability.md
  └── final output stage/
      ├── 9 meeting notes.md
      ├── 9 composite note.md
      └── executive_summary.md
  ```

---

## 5. Technical Requirements

### 5.1 Architecture

#### 5.1.1 Backend Stack
- **Framework**: Flask (Python)
- **Async Processing**: Celery with Redis broker
- **WebSocket**: Flask-SocketIO for real-time updates
- **Session Management**: Redis-backed sessions
- **LLM Integration**: OpenAI API (GPT-4/GPT-5)

#### 5.1.2 Frontend Stack
- **Framework**: Vanilla JavaScript with modern ES6+
- **UI Components**: Custom components with Tailwind CSS
- **Markdown Rendering**: Marked.js library
- **Syntax Highlighting**: Highlight.js
- **Real-time Communication**: Socket.IO client

#### 5.1.3 Data Flow

**Detailed Pipeline Execution**:

1. **Input Phase**:
   - User submits transcript
   - WebSocket connection established
   - Background task initiated

2. **Stage A Processing**:
   - Each Stage A analyzer receives: `{transcript}`
   - Analyzers run sequentially or in parallel
   - Produces 4 intermediate result sets
   - Results stored individually

3. **Context Aggregation**:
   - All Stage A results combined into context object
   - Context formatted for Stage B consumption

4. **Stage B Processing**:
   - Each Stage B analyzer receives: `{context}` (combined Stage A results)
   - Analyzes patterns across Stage A outputs
   - Produces meta-analysis results

5. **Final Stage Processing**:
   - Meeting Notes analyzer receives:
     - `{context}` - All Stage A + Stage B results
     - `{transcript}` - Original transcript (if enabled)
   - Composite Note analyzer receives:
     - `{context}` - All Stage A + Stage B results  
     - `{transcript}` - Original transcript (if enabled)
   - Executive Summary analyzer receives:
     - `{context}` - All Stage A + Stage B results  
     - `{transcript}` - Original transcript (if enabled)
   - Generates final deliverables

6. **Output Phase**:
   - All results stored in session
   - Client notified via WebSocket
> "As a researcher, I want to analyze interview transcripts to identify recurring themes and extract key insights, so I can build a comprehensive understanding of my research domain."

**Acceptance Criteria:**
- Can upload interview transcripts
- Can select specific analyzers for theme extraction
- Can export results to Obsidian-compatible format

### 7.2 Product Manager
> "As a product manager, I want to extract action items and decisions from meeting transcripts, so I can ensure nothing falls through the cracks."

**Acceptance Criteria:**
- Meeting notes clearly list action items
- Decisions are highlighted with context
- Can export to project management tools

### 7.3 Innovation Team Lead
> "As an innovation team lead, I want to identify patentable ideas from brainstorming sessions, so we can protect our intellectual property."

**Acceptance Criteria:**
- Patentability analyzer identifies novel concepts
- Ideas are assessed for patent potential
- Can generate patent disclosure drafts

### 7.4 Knowledge Manager
> "As a knowledge manager, I want to build a connected knowledge graph from meeting transcripts, so organizational knowledge is preserved and discoverable."

**Acceptance Criteria:**
- Automatic concept linking in outputs
- Obsidian-compatible formatting
- Cross-reference between related concepts

---

## 8. Success Metrics

### 8.1 Adoption Metrics
- **Daily Active Users**: Target 100 within 3 months
- **Analyses per User**: Average 5 per week
- **Retention Rate**: 60% monthly retention

### 8.2 Performance Metrics
- **Analysis Completion Rate**: > 95%
- **Average Processing Time**: < 45 seconds
- **Error Rate**: < 1% of analyses

### 8.3 Quality Metrics
- **User Satisfaction**: NPS score > 40
- **Insight Accuracy**: 85% relevance rating
- **Export Success Rate**: > 99%

---

## 9. Roadmap

### Phase 1: MVP (Current)
- ✅ Core analysis pipeline
- ✅ Web interface
- ✅ Basic analyzer set
- ✅ Export functionality

### Phase 2: Enhancement (Q1 2026)
- [ ] Additional analyzers
- [ ] Batch processing
- [ ] API access
- [ ] Custom prompt libraries

### Phase 3: Intelligence (Q2 2026)
- [ ] ML-based analyzer selection
- [ ] Cross-transcript analysis
- [ ] Trend identification
- [ ] Automated report generation

### Phase 4: Enterprise (Q3 2026)
- [ ] Multi-tenant architecture
- [ ] SSO integration
- [ ] Advanced permissions
- [ ] Audit logging

---

## 10. Dependencies

### 10.1 External Services
- **OpenAI API**: GPT-4/GPT-5 access
- **Redis Server**: For session and queue management
- **Python 3.8+**: Runtime environment

### 10.2 Libraries
- Flask ecosystem (Flask, Flask-SocketIO, Flask-Session)
- Celery for task queue
- OpenAI Python SDK
- Jinja2 for templating
- Pydantic for data validation

---

## 11. Risks and Mitigations

### 11.1 Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM API Downtime | High | Medium | Implement retry logic and fallback models |
| Token Limit Exceeded | Medium | High | Implement chunking and summarization |
| Redis Failure | High | Low | Implement in-memory fallback |

### 11.2 Business Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Low Adoption | High | Medium | User training and onboarding |
| Data Privacy Concerns | High | Medium | Clear data retention policies |
| Competitive Products | Medium | High | Continuous innovation and differentiation |

---

## 12. Appendices

### Appendix A: Glossary
- **ACH**: Analysis of Competing Hypotheses
- **LLM**: Large Language Model
- **WebSocket**: Protocol for real-time bidirectional communication
- **Obsidian**: Knowledge management application
- **Token**: Unit of text processed by LLM

### Appendix B: References
- OpenAI API Documentation
- Flask Documentation
- Obsidian Markdown Specification
- WebSocket Protocol RFC 6455

### Appendix C: Change Log
| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-09-06 | Initial PRD creation | Product Team |

---

**Document Status**: This PRD is a living document and will be updated as the product evolves.
