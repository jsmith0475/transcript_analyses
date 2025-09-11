"""
Base analyzer class for all transcript analyzers.
"""

import time
import re
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
import jinja2
from loguru import logger

from src.models import (
    AnalysisResult,
    AnalysisContext,
    AnalyzerStatus,
    TokenUsage,
    Insight,
    Concept,
    ProcessedTranscript
)
from src.llm_client import get_llm_client
from src.utils.markdown_normalizer import normalize_markdown_tables
from src.config import get_config
from src.utils.context_builder import build_fair_combined_context
from src.app.sockets import log_info
from src.utils.summarizer import summarize_text


class BaseAnalyzer(ABC):
    """Abstract base class for all analyzers."""
    
    def __init__(self, name: str, stage: str = "stage_a", prompt_path: Optional[Path] = None):
        """
        Initialize the base analyzer.
        
        Args:
            name: Name of the analyzer
            stage: Stage of analysis (stage_a, stage_b, or final)
            prompt_path: Optional explicit prompt file path override
        """
        self.name = name
        self.stage = stage
        self.config = get_config()
        self.llm_client = get_llm_client()
        self.prompt_template = None
        self.prompt_path_override: Optional[Path] = prompt_path
        self._load_prompt_template()
    
    def _load_prompt_template(self):
        """Load the prompt template for this analyzer."""
        try:
            prompt_path = self.prompt_path_override or self.config.get_prompt_path(self.name)
            if prompt_path and prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Create Jinja2 template
                self.prompt_template = jinja2.Template(template_content)
                logger.debug(f"Loaded prompt template for {self.name} from {prompt_path}")
            else:
                logger.warning(f"No prompt template found for {self.name}")
        except Exception as e:
            logger.error(f"Failed to load prompt template for {self.name}: {e}")
    
    def set_prompt_override(self, prompt_path: Path) -> None:
        """
        Override the prompt file path at runtime and reload the template.
        """
        try:
            self.prompt_path_override = Path(prompt_path)
            self._load_prompt_template()
        except Exception as e:
            logger.error(f"Failed to set prompt override for {self.name}: {e}")
            raise

    def format_prompt(self, context: AnalysisContext) -> str:
        """
        Format the prompt for the LLM.
        
        Args:
            context: Analysis context containing transcript and previous results
            
        Returns:
            Formatted prompt string
        """
        if not self.prompt_template:
            raise ValueError(f"No prompt template loaded for {self.name}")
        
        # Prepare template variables based on stage
        template_vars = {}
        
        if self.stage == "stage_a":
            # Stage A analyzers only get the transcript
            if context.transcript:
                # Enforce a token budget for Stage A to avoid overruns
                budget_tokens = getattr(self.config.processing, "chunk_size", 4000)
                template_vars['transcript'] = self._limit_text_by_tokens(
                    context.transcript.text_for_analysis, budget_tokens
                )
            else:
                raise ValueError("No transcript provided for Stage A analysis")
        
        elif self.stage == "stage_b":
            # Stage B analyzers use combined Stage A results with fair-share token budgeting
            budget_tokens = getattr(self.config.processing, "stage_b_context_token_budget", 8000)
            min_per = getattr(self.config.processing, "stage_b_min_tokens_per_analyzer", 500)

            # Preserve authoritative order of Stage A analyzers
            sections_order = list(context.previous_analyses.keys()) if context.previous_analyses else []

            # Build fair-share combined context and capture debug info for instrumentation
            fair_context, debug = build_fair_combined_context(
                context.previous_analyses,
                self.llm_client,
                total_budget_tokens=budget_tokens,
                min_per_analyzer=min_per,
                include_sections_order=sections_order
            )
            template_vars['context'] = fair_context

            # Optionally include transcript for Stage B if requested via metadata
            inc_tx = False
            tx_preview = None
            try:
                stage_b_opts = (context.metadata or {}).get("stage_b_options") or {}
                inc_tx = bool(stage_b_opts.get("includeTranscript"))
                if inc_tx and context.transcript:
                    mode = (stage_b_opts.get("mode") or "full").lower()
                    if mode == "summary" and getattr(self.config.processing, "summary_enabled", True):
                        # Build summary via summarizer
                        proc = self.config.processing
                        tgt = int(getattr(proc, "summary_stage_b_target_tokens", 1000) or 1000)
                        summary, _dbg = summarize_text(
                            self.llm_client,
                            context.transcript.text_for_analysis or "",
                            stage="stage_b",
                            target_tokens=tgt,
                            job_id=(context.metadata or {}).get("job_id"),
                            map_chunk_tokens=int(getattr(proc, "summary_map_chunk_tokens", 2000) or 2000),
                            map_overlap_tokens=int(getattr(proc, "summary_map_overlap_tokens", 200) or 200),
                            single_pass_max_tokens=int(getattr(proc, "summary_single_pass_max_tokens", 6000) or 6000),
                            map_model=getattr(proc, "summary_map_model", None),
                            reduce_model=getattr(proc, "summary_reduce_model", None),
                        )
                        template_vars['transcript'] = summary
                        tx_preview = summary[:800] + ("\n... (truncated)" if len(summary) > 800 else "")
                    else:
                        max_chars = int(stage_b_opts.get("maxChars") or 20000)
                        tx = context.transcript.text_for_analysis or ""
                        if max_chars > 0 and len(tx) > max_chars:
                            tx = tx[:max_chars]
                        template_vars['transcript'] = tx
                        tx_preview = tx[:800]
                        if len(tx) > 800:
                            tx_preview += "\n... (truncated)"
            except Exception:
                pass

            # Persist context to job artifacts for UI fallback
            try:
                job_id = (context.metadata or {}).get("job_id")
                if job_id:
                    out_dir = Path(f"output/jobs/{job_id}/intermediate")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / "stage_b_context.txt").write_text(fair_context or "", encoding="utf-8")
            except Exception:
                pass

            # Instrumentation log (non-fatal)
            try:
                job_id = (context.metadata or {}).get("job_id")
                logger.info({
                    "evt": "stage_b_context_summary",
                    "analyzer": self.name,
                    "job_id": job_id,
                    "stage": "stage_b",
                    "stage_a_keys": sections_order,
                    "per_section_tokens": debug.get("per_section_tokens"),
                    "allocations": debug.get("allocations"),
                    "after_tokens": debug.get("after_tokens"),
                    "final_tokens": debug.get("final_tokens"),
                    "budget": budget_tokens,
                    "min_per_analyzer": min_per
                })
                # Emit concise preview to Debug Log (WS)
                preview = fair_context[:800]
                if len(fair_context) > 800:
                    preview += "\n... (truncated)"
                # Emit full context for UI panel along with preview
                log_info(
                    message="Stage B context assembled",
                    jobId=job_id,
                    analyzer=self.name,
                    included=sections_order,
                    finalTokens=debug.get("final_tokens"),
                    preview=preview,
                    contextText=fair_context,
                    allocations=debug.get("allocations"),
                    transcriptIncluded=inc_tx,
                    transcriptPreview=tx_preview,
                )
            except Exception:
                pass

            if not template_vars['context']:
                raise ValueError("No Stage A results provided for Stage B analysis")
        
        elif self.stage == "final":
            # Final stage: configurable transcript inclusion + combined results context
            proc = self.config.processing
            include_transcript = bool(getattr(proc, "final_include_transcript", True))
            # Allow UI override via metadata
            final_opts = (context.metadata or {}).get("final_options") or {}
            if 'includeTranscript' in final_opts:
                try:
                    include_transcript = bool(final_opts.get('includeTranscript'))
                except Exception:
                    pass
            transcript_text_for_final = None
            if include_transcript and context.transcript:
                mode = getattr(proc, "final_transcript_mode", "full")
                char_limit = int(getattr(proc, "final_transcript_char_limit", 20000) or 20000)
                try:
                    if final_opts:
                        mode = (final_opts.get('mode') or mode) or mode
                        fl = final_opts.get('maxChars')
                        if fl is not None:
                            char_limit = int(fl)
                except Exception:
                    pass
                if (mode == "summary") and getattr(self.config.processing, "summary_enabled", True):
                    tgt = int(getattr(self.config.processing, "summary_final_target_tokens", 2000) or 2000)
                    summary, _dbg = summarize_text(
                        self.llm_client,
                        context.transcript.text_for_analysis or "",
                        stage="final",
                        target_tokens=tgt,
                        job_id=(context.metadata or {}).get("job_id"),
                        map_chunk_tokens=int(getattr(self.config.processing, "summary_map_chunk_tokens", 2000) or 2000),
                        map_overlap_tokens=int(getattr(self.config.processing, "summary_map_overlap_tokens", 200) or 200),
                        single_pass_max_tokens=int(getattr(self.config.processing, "summary_single_pass_max_tokens", 6000) or 6000),
                        map_model=getattr(self.config.processing, "summary_map_model", None),
                        reduce_model=getattr(self.config.processing, "summary_reduce_model", None),
                    )
                    template_vars['transcript'] = summary
                    transcript_text_for_final = summary
                else:
                    transcript_text = context.transcript.text_for_analysis or ""
                    if len(transcript_text) > char_limit:
                        transcript_text = transcript_text[:char_limit]
                    template_vars['transcript'] = transcript_text
                    transcript_text_for_final = transcript_text
            # Build context from prior analyses (Stage A + Stage B as provided by the orchestrator)
            combined_context = context.get_combined_context(include_transcript=False)
            # Optionally trim Final stage context if a budget is configured (>0)
            final_budget = int(getattr(self.config.processing, "final_context_token_budget", 0) or 0)
            if final_budget > 0:
                template_vars['context'] = self._limit_text_by_tokens(combined_context, final_budget)
            else:
                template_vars['context'] = combined_context

            # Persist combined context to job artifacts for UI fallback
            try:
                job_id = (context.metadata or {}).get("job_id")
                if job_id:
                    out_dir = Path(f"output/jobs/{job_id}/final")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / "context_combined.txt").write_text(template_vars.get('context') or "", encoding="utf-8")
            except Exception:
                pass

            # Emit concise preview of Final combined context
            try:
                job_id = (context.metadata or {}).get("job_id")
                included = list((context.previous_analyses or {}).keys())
                try:
                    total_toks = self.llm_client.count_tokens(template_vars['context'] or "")
                except Exception:
                    total_toks = None
                preview = (template_vars['context'] or "")[:800]
                if len(template_vars['context'] or "") > 800:
                    preview += "\n... (truncated)"
                # Emit full context for UI panel along with preview
                log_info(
                    message="Final context assembled",
                    jobId=job_id,
                    analyzer=self.name,
                    included=included,
                    totalTokens=total_toks,
                    preview=preview,
                    contextText=(template_vars.get('context') or ""),
                    transcriptIncluded=bool(transcript_text_for_final),
                    transcriptPreview=(transcript_text_for_final[:800] if transcript_text_for_final else None),
                )
            except Exception:
                pass
        
        # Add any metadata
        template_vars['metadata'] = context.metadata
        
        # Render the template
        try:
            prompt = self.prompt_template.render(**template_vars)
            return prompt
        except Exception as e:
            logger.error(f"Failed to format prompt for {self.name}: {e}")
            raise
    
    async def analyze(self, context: AnalysisContext, extra_llm_kwargs: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Perform the analysis.
        
        Args:
            context: Analysis context
            
        Returns:
            AnalysisResult object
        """
        start_time = time.time()
        result = AnalysisResult(
            analyzer_name=self.name,
            raw_output="",
            status=AnalyzerStatus.PROCESSING
        )
        
        try:
            # Format the prompt
            prompt = self.format_prompt(context)
            
            # Get analyzer-specific config
            analyzer_config = self.config.get_analyzer_config(self.name)
            llm_params = analyzer_config.merge_with_llm_config(self.config.llm)
            
            # Make LLM call
            logger.info(f"Running {self.name} analyzer...")
            response_text, token_usage = await self.llm_client.complete_async(
                prompt=prompt,
                temperature=llm_params.get('temperature', 0.7),
                max_tokens=llm_params.get('max_tokens', 8000),
                **(extra_llm_kwargs or {})
            )
            
            # Normalize markdown (e.g., unwrap code-fenced tables) and parse the response
            try:
                response_text = normalize_markdown_tables(response_text)
            except Exception:
                pass
            result.raw_output = response_text
            result.token_usage = token_usage
            # Record model actually used
            try:
                result.model_used = (extra_llm_kwargs or {}).get('model', self.config.llm.model)
            except Exception:
                result.model_used = self.config.llm.model
            
            # Extract structured data
            structured_data = self.parse_response(response_text)
            result.structured_data = structured_data
            
            # Extract insights and concepts
            result.insights = self.extract_insights(response_text, structured_data)
            result.concepts = self.extract_concepts(response_text, structured_data)
            
            # Mark as completed
            result.status = AnalyzerStatus.COMPLETED

        except Exception as e:
            logger.error(f"Error in {self.name} analyzer: {e}")
            result.status = AnalyzerStatus.ERROR
            result.error_message = str(e)

        # Record processing time
        result.processing_time = time.time() - start_time
        logger.info(f"{self.name} analyzer completed in {result.processing_time:.2f}s")

        # Emit a concise preview of the analyzer output to the Debug Log
        try:
            job_id = (context.metadata or {}).get("job_id")
            preview = (result.raw_output or "")[:800]
            if result.raw_output and len(result.raw_output) > 800:
                preview += "\n... (truncated)"
            tu = result.token_usage.dict() if result.token_usage else {}
            log_info(
                message="Analyzer output",
                jobId=job_id,
                analyzer=self.name,
                stage=self.stage,
                status=result.status.value,
                tokenUsage=tu,
                preview=preview,
            )
        except Exception:
            pass

        return result
    
    def analyze_sync(self, context: AnalysisContext, save_intermediate: bool = True, 
                     output_dir: Optional[Path] = None, extra_llm_kwargs: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Perform the analysis synchronously.
        
        Args:
            context: Analysis context
            save_intermediate: Whether to save intermediate results
            output_dir: Directory to save intermediate results (defaults to output/intermediate)
            
        Returns:
            AnalysisResult object
        """
        start_time = time.time()
        result = AnalysisResult(
            analyzer_name=self.name,
            raw_output="",
            status=AnalyzerStatus.PROCESSING
        )
        
        try:
            # Format the prompt
            prompt = self.format_prompt(context)
            
            # Get analyzer-specific config
            analyzer_config = self.config.get_analyzer_config(self.name)
            llm_params = analyzer_config.merge_with_llm_config(self.config.llm)
            
            # Make LLM call
            logger.info(f"Running {self.name} analyzer...")
            response_text, token_usage = self.llm_client.complete_sync(
                prompt=prompt,
                temperature=llm_params.get('temperature', 0.7),
                max_tokens=llm_params.get('max_tokens', 8000),
                **(extra_llm_kwargs or {})
            )
            
            # Normalize markdown (e.g., unwrap code-fenced tables) and parse the response
            try:
                response_text = normalize_markdown_tables(response_text)
            except Exception:
                pass
            result.raw_output = response_text
            result.token_usage = token_usage
            # Record model actually used
            try:
                result.model_used = (extra_llm_kwargs or {}).get('model', self.config.llm.model)
            except Exception:
                result.model_used = self.config.llm.model
            
            # Extract structured data
            structured_data = self.parse_response(response_text)
            result.structured_data = structured_data
            
            # Extract insights and concepts
            result.insights = self.extract_insights(response_text, structured_data)
            result.concepts = self.extract_concepts(response_text, structured_data)
            
            # Mark as completed
            result.status = AnalyzerStatus.COMPLETED
            
            # Save intermediate results if requested
            if save_intermediate:
                self.save_intermediate_result(result, output_dir)

        except Exception as e:
            logger.error(f"Error in {self.name} analyzer: {e}")
            result.status = AnalyzerStatus.ERROR
            result.error_message = str(e)

        # Record processing time
        result.processing_time = time.time() - start_time
        logger.info(f"{self.name} analyzer completed in {result.processing_time:.2f}s")

        # Emit a concise preview of the analyzer output to the Debug Log
        try:
            job_id = (context.metadata or {}).get("job_id")
            preview = (result.raw_output or "")[:800]
            if result.raw_output and len(result.raw_output) > 800:
                preview += "\n... (truncated)"
            tu = result.token_usage.dict() if result.token_usage else {}
            log_info(
                message="Analyzer output",
                jobId=job_id,
                analyzer=self.name,
                stage=self.stage,
                status=result.status.value,
                tokenUsage=tu,
                preview=preview,
            )
        except Exception:
            pass

        return result
    
    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into structured data.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Dictionary of structured data
        """
        pass
    
    def extract_insights(self, response: str, structured_data: Dict[str, Any]) -> List[Insight]:
        """
        Extract insights from the response.
        
        Args:
            response: Raw response from LLM
            structured_data: Parsed structured data
            
        Returns:
            List of Insight objects
        """
        insights = []
        
        # Try to extract from structured data first
        if 'insights' in structured_data:
            for insight_text in structured_data['insights']:
                if isinstance(insight_text, str):
                    insights.append(Insight(
                        text=insight_text,
                        source_analyzer=self.name
                    ))
                elif isinstance(insight_text, dict):
                    insights.append(Insight(
                        text=insight_text.get('text', ''),
                        confidence=insight_text.get('confidence'),
                        source_analyzer=self.name,
                        category=insight_text.get('category')
                    ))
        
        # Fallback: Extract from response text using patterns
        if not insights:
            # Look for bullet points
            bullet_pattern = r'^\s*[-•*]\s+(.+)$'
            for line in response.split('\n'):
                match = re.match(bullet_pattern, line)
                if match:
                    text = match.group(1).strip()
                    if len(text) > 20:  # Filter out very short items
                        insights.append(Insight(
                            text=text,
                            source_analyzer=self.name
                        ))
            
            # Look for numbered lists
            if not insights:
                number_pattern = r'^\s*\d+\.\s+(.+)$'
                for line in response.split('\n'):
                    match = re.match(number_pattern, line)
                    if match:
                        text = match.group(1).strip()
                        if len(text) > 20:
                            insights.append(Insight(
                                text=text,
                                source_analyzer=self.name
                            ))
        
        # Limit number of insights
        max_insights = self.config.output.max_insights_per_analyzer
        if len(insights) > max_insights:
            insights = insights[:max_insights]
        
        return insights
    
    def extract_concepts(self, response: str, structured_data: Dict[str, Any]) -> List[Concept]:
        """
        Extract concepts from the response.
        
        Args:
            response: Raw response from LLM
            structured_data: Parsed structured data
            
        Returns:
            List of Concept objects
        """
        concepts = []
        concepts_dict = {}
        
        # Try to extract from structured data first
        if 'concepts' in structured_data:
            for concept_item in structured_data['concepts']:
                if isinstance(concept_item, str):
                    if concept_item not in concepts_dict:
                        concepts_dict[concept_item] = Concept(name=concept_item)
                elif isinstance(concept_item, dict):
                    name = concept_item.get('name', '')
                    if name and name not in concepts_dict:
                        concepts_dict[name] = Concept(
                            name=name,
                            description=concept_item.get('description'),
                            related_concepts=concept_item.get('related', [])
                        )
        
        # Fallback: Extract concepts in [[brackets]] (Obsidian-style)
        bracket_pattern = r'\[\[([^\]]+)\]\]'
        for match in re.finditer(bracket_pattern, response):
            concept_name = match.group(1).strip()
            # Guard against empty or whitespace-only names to avoid validation errors
            if not concept_name:
                continue
            if concept_name not in concepts_dict:
                concepts_dict[concept_name] = Concept(name=concept_name)
            else:
                concepts_dict[concept_name].occurrences += 1
        
        # Convert to list
        concepts = list(concepts_dict.values())
        
        # Limit number of concepts
        max_concepts = self.config.output.max_concepts_per_analyzer
        if len(concepts) > max_concepts:
            # Sort by occurrences and take top N
            concepts.sort(key=lambda c: c.occurrences, reverse=True)
            concepts = concepts[:max_concepts]
        
        return concepts
    
    def _limit_text_by_tokens(self, text: str, max_tokens: int) -> str:
        """
        Trim text to approximately fit within max_tokens using the client's token counter,
        falling back to a 4 chars/token heuristic if needed.
        """
        try:
            tokens = self.llm_client.count_tokens(text)
            if tokens <= max_tokens:
                return text
            # Estimate proportional length to trim
            ratio = max(0.1, float(max_tokens) / float(max(tokens, 1)))
            est_len = max(1, int(len(text) * ratio))
            return text[:est_len]
        except Exception:
            # Fallback: 4 chars per token heuristic
            return text[: max(1, max_tokens * 4)]

    def validate_response(self, response: str) -> bool:
        """
        Validate that the response is valid and contains expected content.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            True if valid, False otherwise
        """
        if not response or len(response.strip()) < 50:
            logger.warning(f"Response from {self.name} is too short")
            return False
        
        # Check for error indicators
        error_patterns = [
            r'error:',
            r'failed to',
            r'unable to',
            r'cannot process'
        ]
        
        response_lower = response.lower()
        for pattern in error_patterns:
            if re.search(pattern, response_lower):
                logger.warning(f"Response from {self.name} contains error indicator: {pattern}")
                return False
        
        return True
    
    def save_intermediate_result(self, result: AnalysisResult, output_dir: Optional[Path] = None):
        """
        Save intermediate analysis results to files.
        
        Args:
            result: The analysis result to save
            output_dir: Directory to save results (should be run-specific directory)
        """
        try:
            # Determine output directory
            if output_dir is None:
                # Create a default run directory if none provided
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = Path(f"output/runs/run_{timestamp}")
            
            # Create intermediate subdirectory structure
            intermediate_dir = output_dir / "intermediate" / self.stage
            intermediate_dir.mkdir(parents=True, exist_ok=True)
            
            # Use simple filenames without timestamps (directory is already timestamped)
            base_filename = self.name
            
            # Save JSON file
            json_path = intermediate_dir / f"{base_filename}.json"
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_data = {
                "analyzer_name": result.analyzer_name,
                "status": result.status.value,
                "timestamp": timestamp_str,
                "processing_time": result.processing_time,
                "token_usage": {
                    "prompt_tokens": result.token_usage.prompt_tokens if result.token_usage else 0,
                    "completion_tokens": result.token_usage.completion_tokens if result.token_usage else 0,
                    "total_tokens": result.token_usage.total_tokens if result.token_usage else 0
                },
                "raw_output": result.raw_output,
                "structured_data": result.structured_data,
                "insights": [
                    {
                        "text": insight.text,
                        "confidence": insight.confidence,
                        "category": insight.category,
                        "source_analyzer": insight.source_analyzer
                    }
                    for insight in result.insights
                ],
                "concepts": [
                    {
                        "name": concept.name,
                        "description": concept.description,
                        "occurrences": concept.occurrences,
                        "related_concepts": concept.related_concepts
                    }
                    for concept in result.concepts
                ],
                "error_message": result.error_message
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            # Save Markdown file
            md_path = intermediate_dir / f"{base_filename}.md"
            md_content = self.format_result_as_markdown(result, timestamp_str)
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)

            # Optionally write a non-truncated "full" raw output companion file for easier review
            try:
                write_full = bool(getattr(self.config.output, "write_full_raw_output", False))
                truncate = bool(getattr(self.config.output, "truncate_raw_output", True))
                if write_full and truncate and result.raw_output:
                    full_md_path = intermediate_dir / f"{base_filename}.full.md"
                    full_lines = []
                    full_lines.append(f"# {self.name.replace('_', ' ').title()} Analysis (Full Raw Output)")
                    full_lines.append(f"\n**Date:** {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")
                    full_lines.append(f"**Stage:** {self.stage.replace('_', ' ').title()}")
                    full_lines.append(f"**Status:** {result.status.value}")
                    full_lines.append("\n## Raw Output (Full)")
                    full_lines.append("```")
                    full_lines.append(result.raw_output)
                    full_lines.append("```")
                    with open(full_md_path, 'w', encoding='utf-8') as ff:
                        ff.write("\n".join(full_lines))
            except Exception as _:
                # Non-fatal
                pass

            logger.info(f"Saved intermediate results for {self.name} to {intermediate_dir}")
            
        except Exception as e:
            logger.error(f"Failed to save intermediate results for {self.name}: {e}")
    
    def format_result_as_markdown(self, result: AnalysisResult, timestamp: str) -> str:
        """
        Format analysis result as a markdown document.
        
        Args:
            result: The analysis result to format
            timestamp: Timestamp string for the document
            
        Returns:
            Formatted markdown string
        """
        lines = []
        
        # Header
        lines.append(f"# {self.name.replace('_', ' ').title()} Analysis")
        lines.append(f"\n**Date:** {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")
        lines.append(f"**Stage:** {self.stage.replace('_', ' ').title()}")
        lines.append(f"**Status:** {result.status.value}")
        
        # Processing metrics
        lines.append("\n## Processing Metrics")
        lines.append(f"- **Processing Time:** {result.processing_time:.2f} seconds")
        if result.token_usage:
            lines.append(f"- **Tokens Used:** {result.token_usage.total_tokens:,}")
            lines.append(f"  - Prompt: {result.token_usage.prompt_tokens:,}")
            lines.append(f"  - Completion: {result.token_usage.completion_tokens:,}")
        
        # Insights
        if result.insights:
            lines.append("\n## Key Insights")
            for i, insight in enumerate(result.insights, 1):
                lines.append(f"\n### Insight {i}")
                lines.append(f"{insight.text}")
                if insight.confidence:
                    lines.append(f"- **Confidence:** {insight.confidence}")
                if insight.category:
                    lines.append(f"- **Category:** {insight.category}")
        
        # Concepts
        if result.concepts:
            lines.append("\n## Identified Concepts")
            for concept in result.concepts:
                lines.append(f"\n### {concept.name}")
                if concept.description:
                    lines.append(f"{concept.description}")
                if concept.occurrences > 1:
                    lines.append(f"- **Occurrences:** {concept.occurrences}")
                if concept.related_concepts:
                    lines.append(f"- **Related:** {', '.join(concept.related_concepts)}")
        
        # Structured Data
        if result.structured_data:
            lines.append("\n## Structured Analysis")
            lines.append("```json")
            lines.append(json.dumps(result.structured_data, indent=2, ensure_ascii=False))
            lines.append("```")
        
        # Raw Output (configurable truncation; never truncate Final stage intermediates)
        if result.raw_output:
            lines.append("\n## Raw Output")
            lines.append("```")
            truncate = bool(getattr(self.config.output, "truncate_raw_output", True))
            max_chars = int(getattr(self.config.output, "raw_output_max_chars", 5000) or 5000)
            # Special-case: do not truncate for final stage intermediates to aid review
            if self.stage == "final" or not truncate:
                lines.append(result.raw_output)
            else:
                if len(result.raw_output) > max_chars:
                    lines.append(result.raw_output[:max_chars])
                    lines.append("\n... (truncated)")
                else:
                    lines.append(result.raw_output)
            lines.append("```")
        
        # Error information if present
        if result.error_message:
            lines.append("\n## Error Information")
            lines.append(f"**Error:** {result.error_message}")
        
        # Footer
        lines.append("\n---")
        lines.append(f"*Generated by {self.name} analyzer at {timestamp}*")
        
        return "\n".join(lines)
