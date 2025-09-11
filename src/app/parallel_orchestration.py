"""
Parallel Celery orchestration for the Transcript Analysis Tool.
Uses Celery group/chord to run analyzers in parallel within each stage.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List

from celery import group, chord
from loguru import logger
from redis import from_url as redis_from_url

from src.app.celery_app import celery
from src.config import get_config
from src.transcript_processor import get_transcript_processor
from src.models import AnalysisContext, AnalysisResult, AnalyzerStatus
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
from src.analyzers.stage_a.premises_assertions import PremisesAssertionsAnalyzer
from src.analyzers.stage_a.postulate_theorem import PostulateTheoremAnalyzer
from src.analyzers.stage_b.competing_hypotheses import CompetingHypothesesAnalyzer
from src.analyzers.stage_b.first_principles import FirstPrinciplesAnalyzer
from src.analyzers.stage_b.determining_factors import DeterminingFactorsAnalyzer
from src.analyzers.stage_b.patentability import PatentabilityAnalyzer
from src.analyzers.final.meeting_notes import MeetingNotesAnalyzer
from src.analyzers.final.composite_note import CompositeNoteAnalyzer
from src.analyzers.template_analyzer import TemplateAnalyzer
from src.app.sockets import (
    job_queued,
    analyzer_started,
    analyzer_completed,
    analyzer_error,
    stage_completed,
    job_completed,
    job_error,
)
from src.app.notify import get_notification_manager
from src.utils.insight_aggregator import (
    aggregate_insights,
    to_json as insights_to_json,
    to_markdown as insights_to_md,
    to_csv as insights_to_csv,
    dedupe_items_dict,
    count_items as count_items_dict,
)
from src.utils.insight_llm import build_segmented_transcript, build_combined_context, extract_insights_llm
from src.llm_client import get_llm_client
from src.app.sockets import emit_progress


def _get_redis():
    cfg = get_config()
    url = cfg.web.redis_url
    if url.rstrip("/").count("/") == 2:
        url = f"{url}/{cfg.web.redis_db}"
    return redis_from_url(url)


def _redis_key(job_id: str) -> str:
    return f"job:{job_id}"


def _save_status(job_id: str, data: Dict[str, Any]) -> None:
    """Persist job status/result to Redis."""
    r = _get_redis()
    key = _redis_key(job_id)
    r.set(key, json.dumps(data))
    r.expire(key, 60 * 60 * 24)  # 24h TTL


def _load_status(job_id: str) -> Dict[str, Any]:
    """Load job status from Redis."""
    r = _get_redis()
    key = _redis_key(job_id)
    data = r.get(key)
    if data:
        return json.loads(data)
    return {}


def _job_dir(job_id: str) -> Path:
    """Filesystem location for job artifacts."""
    d = Path(f"output/jobs/{job_id}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_prompt_path(file_path: str | None) -> Optional[Path]:
    """Validate and return safe prompt path."""
    if not file_path:
        return None
    try:
        p = Path(file_path)
        if p.suffix.lower() != ".md":
            return None
        if not p.exists():
            return None
        prompts_root = (Path.cwd() / "prompts").resolve()
        if not str(p.resolve()).startswith(str(prompts_root)):
            return None
        return p
    except Exception:
        return None


@celery.task(name="run_stage_a_analyzer")
def run_stage_a_analyzer(
    job_id: str,
    analyzer_name: str,
    transcript_data: Dict[str, Any],
    prompt_override: Optional[str] = None,
    model_override: Optional[str] = None,
    stage_b_options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Run a single Stage A analyzer."""
    logger.info(f"Running Stage A analyzer: {analyzer_name} for job {job_id}")
    
    # Map analyzer names to classes
    analyzer_map = {
        "say_means": SayMeansAnalyzer,
        "perspective_perception": PerspectivePerceptionAnalyzer,
        "premises_assertions": PremisesAssertionsAnalyzer,
        "postulate_theorem": PostulateTheoremAnalyzer,
    }
    
    try:
        # Update status to processing
        status_doc = _load_status(job_id)
        if "stageA" not in status_doc:
            status_doc["stageA"] = {}
        status_doc["stageA"][analyzer_name] = {"status": "processing"}
        _save_status(job_id, status_doc)
        
        # Emit started event
        analyzer_started(job_id, "stage_a", analyzer_name)
        start_time = time.time()
        
        # Create analyzer and context (fallback to TemplateAnalyzer for custom slugs)
        if analyzer_name in analyzer_map:
            analyzer = analyzer_map[analyzer_name]()
        else:
            analyzer = TemplateAnalyzer(analyzer_name, stage="stage_a")
        
        # Apply prompt override if provided
        if prompt_override:
            p = _safe_prompt_path(prompt_override)
            if p:
                analyzer.set_prompt_override(p)
        
        # Reconstruct transcript from data
        from src.models import ProcessedTranscript
        processed = ProcessedTranscript(**transcript_data)
        ctx = AnalysisContext(
            transcript=processed,
            metadata={"source": "parallel_orchestration", "stage": "stage_a", "job_id": job_id}
        )
        
        # Run analysis
        result = analyzer.analyze_sync(ctx, extra_llm_kwargs={"model": model_override} if model_override else None)
        
        # Prepare result data
        result_data = {
            "status": result.status.value,
            "processing_time": result.processing_time,
            "token_usage": result.token_usage.dict() if result.token_usage else None,
            "raw_output": result.raw_output,
            "structured_data": result.structured_data,
            "insights": [i.dict() for i in result.insights],
            "concepts": [c.dict() for c in result.concepts],
            "model_used": getattr(result, "model_used", None),
            "error_message": result.error_message,
        }
        
        # Update status
        status_doc = _load_status(job_id)
        status_doc["stageA"][analyzer_name] = result_data
        
        # Update token usage totals
        if result.token_usage:
            if "tokenUsageTotal" not in status_doc:
                status_doc["tokenUsageTotal"] = {"prompt": 0, "completion": 0, "total": 0}
            status_doc["tokenUsageTotal"]["prompt"] += result.token_usage.prompt_tokens
            status_doc["tokenUsageTotal"]["completion"] += result.token_usage.completion_tokens
            status_doc["tokenUsageTotal"]["total"] += result.token_usage.total_tokens
        
        _save_status(job_id, status_doc)
        
        # Emit completed event
        analyzer_completed(
            job_id,
            "stage_a",
            analyzer_name,
            int((time.time() - start_time) * 1000),
            token_usage=result.token_usage.dict() if result.token_usage else None,
            cost_usd=None,
        )
        
        logger.info(f"Completed Stage A analyzer: {analyzer_name}")
        return result_data
        
    except Exception as e:
        logger.exception(f"Error in Stage A analyzer {analyzer_name}: {e}")
        
        # Persist error state to Redis so UI reflects failure
        try:
            status_doc = _load_status(job_id)
            if "stageA" not in status_doc:
                status_doc["stageA"] = {}
            status_doc["stageA"][analyzer_name] = {
                "status": "error",
                "error_message": str(e),
            }
            _save_status(job_id, status_doc)
        except Exception:
            pass
        
        # Emit analyzer.error so UI can render red tile
        try:
            analyzer_error(job_id, "stage_a", analyzer_name, str(e))
        except Exception:
            pass
        
        return {"status": "error", "error_message": str(e)}


@celery.task(name="run_stage_b_analyzer")
def run_stage_b_analyzer(
    job_id: str,
    analyzer_name: str,
    transcript_data: Dict[str, Any],
    stage_a_results: Dict[str, Any],
    prompt_override: Optional[str] = None,
    model_override: Optional[str] = None,
    stage_b_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a single Stage B analyzer."""
    logger.info(f"Running Stage B analyzer: {analyzer_name} for job {job_id}")
    
    # Map analyzer names to classes
    analyzer_map = {
        "competing_hypotheses": CompetingHypothesesAnalyzer,
        "first_principles": FirstPrinciplesAnalyzer,
        "determining_factors": DeterminingFactorsAnalyzer,
        "patentability": PatentabilityAnalyzer,
    }
    
    try:
        # Update status to processing
        status_doc = _load_status(job_id)
        if "stageB" not in status_doc:
            status_doc["stageB"] = {}
        status_doc["stageB"][analyzer_name] = {"status": "processing"}
        _save_status(job_id, status_doc)
        
        # Emit started event
        analyzer_started(job_id, "stage_b", analyzer_name)
        start_time = time.time()
        
        # Create analyzer (fallback to TemplateAnalyzer for custom slugs)
        if analyzer_name in analyzer_map:
            analyzer = analyzer_map[analyzer_name]()
        else:
            analyzer = TemplateAnalyzer(analyzer_name, stage="stage_b")
        
        # Apply prompt override if provided
        if prompt_override:
            p = _safe_prompt_path(prompt_override)
            if p:
                analyzer.set_prompt_override(p)
        
        # Reconstruct transcript and Stage A results
        from src.models import ProcessedTranscript
        processed = ProcessedTranscript(**transcript_data)
        
        # Convert Stage A results to AnalysisResult objects
        stage_a_analyses = {}
        for name, result_data in stage_a_results.items():
            stage_a_analyses[name] = AnalysisResult(
                analyzer_name=name,
                raw_output=result_data.get("raw_output", ""),
                structured_data=result_data.get("structured_data", {}),
                insights=[],
                concepts=[],
                processing_time=result_data.get("processing_time", 0),
                token_usage=None,
                status=AnalyzerStatus.COMPLETED
            )
        
        # Create context with Stage A results
        ctx = AnalysisContext(
            transcript=processed,
            previous_analyses=stage_a_analyses,
            metadata={
                "source": "parallel_orchestration",
                "stage": "stage_b",
                "job_id": job_id,
                "stage_b_options": stage_b_options or {},
            }
        )
        
        # Run analysis
        result = analyzer.analyze_sync(ctx, extra_llm_kwargs={"model": model_override} if model_override else None)
        
        # Prepare result data
        result_data = {
            "status": result.status.value,
            "processing_time": result.processing_time,
            "token_usage": result.token_usage.dict() if result.token_usage else None,
            "raw_output": result.raw_output,
            "structured_data": result.structured_data,
            "insights": [i.dict() for i in result.insights],
            "concepts": [c.dict() for c in result.concepts],
            "model_used": getattr(result, "model_used", None),
            "error_message": result.error_message,
        }
        
        # Update status
        status_doc = _load_status(job_id)
        status_doc["stageB"][analyzer_name] = result_data
        
        # Update token usage totals
        if result.token_usage:
            if "tokenUsageTotal" not in status_doc:
                status_doc["tokenUsageTotal"] = {"prompt": 0, "completion": 0, "total": 0}
            status_doc["tokenUsageTotal"]["prompt"] += result.token_usage.prompt_tokens
            status_doc["tokenUsageTotal"]["completion"] += result.token_usage.completion_tokens
            status_doc["tokenUsageTotal"]["total"] += result.token_usage.total_tokens
        
        _save_status(job_id, status_doc)
        
        # Emit completed event
        analyzer_completed(
            job_id,
            "stage_b",
            analyzer_name,
            int((time.time() - start_time) * 1000),
            token_usage=result.token_usage.dict() if result.token_usage else None,
            cost_usd=None,
        )
        
        logger.info(f"Completed Stage B analyzer: {analyzer_name}")
        return result_data
        
    except Exception as e:
        logger.exception(f"Error in Stage B analyzer {analyzer_name}: {e}")
        
        # Persist error state to Redis so UI reflects failure
        try:
            status_doc = _load_status(job_id)
            if "stageB" not in status_doc:
                status_doc["stageB"] = {}
            status_doc["stageB"][analyzer_name] = {
                "status": "error",
                "error_message": str(e),
            }
            _save_status(job_id, status_doc)
        except Exception:
            pass
        
        # Emit analyzer.error so UI can render red tile
        try:
            analyzer_error(job_id, "stage_b", analyzer_name, str(e))
        except Exception:
            pass
        
        return {"status": "error", "error_message": str(e)}


@celery.task(name="run_final_stage")
def run_final_stage(
    all_results: Dict[str, Any],  # Made required - must receive from Stage B
    job_id: str,
    transcript_data: Dict[str, Any],
    selected_final: List[str],
    prompt_selection: Dict[str, Any],
    model_override: Optional[str] = None,
    final_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run Final stage analyzers (Meeting Notes and Composite Note)."""
    logger.info(f"Running Final stage for job {job_id}")
    
    try:
        # all_results must be provided by Stage B completion
        if all_results is None:
            logger.error(f"Final stage called without Stage B results for job {job_id}")
            raise ValueError("Final stage requires completed Stage B results")
        
        # Reconstruct transcript
        from src.models import ProcessedTranscript
        processed = ProcessedTranscript(**transcript_data)
        
        # Build combined results from Stage A and B
        combined: Dict[str, AnalysisResult] = {}
        
        # Add Stage A results
        for name, result_data in all_results.get("stageA", {}).items():
            combined[name] = AnalysisResult(
                analyzer_name=name,
                raw_output=result_data.get("raw_output", ""),
                structured_data=result_data.get("structured_data", {}),
                insights=[],
                concepts=[],
                processing_time=result_data.get("processing_time", 0),
                token_usage=None,
                status=AnalyzerStatus.COMPLETED
            )
        
        # Add Stage B results
        for name, result_data in all_results.get("stageB", {}).items():
            combined[name] = AnalysisResult(
                analyzer_name=name,
                raw_output=result_data.get("raw_output", ""),
                structured_data=result_data.get("structured_data", {}),
                insights=[],
                concepts=[],
                processing_time=result_data.get("processing_time", 0),
                token_usage=None,
                status=AnalyzerStatus.COMPLETED
            )
        
        # Create final context
        final_ctx = AnalysisContext(
            transcript=processed,
            previous_analyses=combined,
            metadata={
                "source": "parallel_orchestration",
                "stage": "final",
                "job_id": job_id,
                "final_options": final_options or {},
            }
        )
        
        # Initialize status
        status_doc = _load_status(job_id)
        if "final" not in status_doc:
            status_doc["final"] = {}
        
        # Collect Final stage results locally so downstream aggregation does not
        # depend on Redis (avoids races or missing data in worker context)
        final_results_local: Dict[str, AnalysisResult] = {}
        
        # Run Meeting Notes
        if "meeting_notes" in selected_final:
            status_doc["final"]["meeting_notes"] = {"status": "processing"}
            _save_status(job_id, status_doc)
            
            analyzer_started(job_id, "final", "meeting_notes")
            mn_start = time.time()
            
            meeting_notes_an = MeetingNotesAnalyzer()
            
            # Apply prompt override if provided
            override = (prompt_selection.get("final") or {}).get("meeting_notes")
            if override:
                p = _safe_prompt_path(override)
                if p:
                    meeting_notes_an.set_prompt_override(p)
            
            mn_res = meeting_notes_an.analyze_sync(final_ctx, save_intermediate=False, extra_llm_kwargs={"model": model_override} if model_override else None)
            
            # Save result
            status_doc = _load_status(job_id)
            status_doc["final"]["meeting_notes"] = {
                "status": getattr(mn_res.status, "value", str(mn_res.status)) if mn_res else "error",
                "raw_output": mn_res.raw_output,
                "processing_time": mn_res.processing_time,
                "token_usage": mn_res.token_usage.dict() if mn_res.token_usage else None,
                "model_used": getattr(mn_res, "model_used", None),
                "structured_data": mn_res.structured_data,
            }
            
            # Update token usage
            if mn_res.token_usage:
                if "tokenUsageTotal" not in status_doc:
                    status_doc["tokenUsageTotal"] = {"prompt": 0, "completion": 0, "total": 0}
                status_doc["tokenUsageTotal"]["prompt"] += mn_res.token_usage.prompt_tokens
                status_doc["tokenUsageTotal"]["completion"] += mn_res.token_usage.completion_tokens
                status_doc["tokenUsageTotal"]["total"] += mn_res.token_usage.total_tokens
            
            _save_status(job_id, status_doc)
            
            # Save to file
            job_dir = _job_dir(job_id)
            final_dir = job_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            (final_dir / "meeting_notes.md").write_text(mn_res.raw_output or "", encoding="utf-8")
            # Track locally for insights aggregation
            try:
                final_results_local["meeting_notes"] = AnalysisResult(
                    analyzer_name="meeting_notes",
                    raw_output=mn_res.raw_output,
                    structured_data=mn_res.structured_data,
                    insights=[],
                    concepts=[],
                )
            except Exception:
                pass
            
            # Emit appropriate event
            if getattr(mn_res.status, "value", str(mn_res.status)) == "completed":
                analyzer_completed(
                    job_id,
                    "final",
                    "meeting_notes",
                    int((time.time() - mn_start) * 1000),
                    token_usage=mn_res.token_usage.dict() if mn_res.token_usage else None,
                    cost_usd=None,
                )
            else:
                analyzer_error(
                    job_id,
                    "final",
                    "meeting_notes",
                    mn_res.error_message or "Analyzer error",
                    processing_time_ms=int((time.time() - mn_start) * 1000),
                )
        
        # Run Composite Note
        if "composite_note" in selected_final:
            status_doc = _load_status(job_id)
            status_doc["final"]["composite_note"] = {"status": "processing"}
            _save_status(job_id, status_doc)
            
            analyzer_started(job_id, "final", "composite_note")
            cn_start = time.time()
            
            composite_note_an = CompositeNoteAnalyzer()
            
            # Apply prompt override if provided
            override = (prompt_selection.get("final") or {}).get("composite_note")
            if override:
                p = _safe_prompt_path(override)
                if p:
                    composite_note_an.set_prompt_override(p)
            
            cn_res = composite_note_an.analyze_sync(final_ctx, save_intermediate=False, extra_llm_kwargs={"model": model_override} if model_override else None)
            
            # Save result
            status_doc = _load_status(job_id)
            status_doc["final"]["composite_note"] = {
                "status": getattr(cn_res.status, "value", str(cn_res.status)) if cn_res else "error",
                "raw_output": cn_res.raw_output,
                "processing_time": cn_res.processing_time,
                "token_usage": cn_res.token_usage.dict() if cn_res.token_usage else None,
                "model_used": getattr(cn_res, "model_used", None),
                "structured_data": cn_res.structured_data,
            }
            
            # Update token usage
            if cn_res.token_usage:
                if "tokenUsageTotal" not in status_doc:
                    status_doc["tokenUsageTotal"] = {"prompt": 0, "completion": 0, "total": 0}
                status_doc["tokenUsageTotal"]["prompt"] += cn_res.token_usage.prompt_tokens
                status_doc["tokenUsageTotal"]["completion"] += cn_res.token_usage.completion_tokens
                status_doc["tokenUsageTotal"]["total"] += cn_res.token_usage.total_tokens
            
            _save_status(job_id, status_doc)
            
            # Save to file
            job_dir = _job_dir(job_id)
            final_dir = job_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            (final_dir / "composite_note.md").write_text(cn_res.raw_output or "", encoding="utf-8")
            # Track locally for insights aggregation
            try:
                final_results_local["composite_note"] = AnalysisResult(
                    analyzer_name="composite_note",
                    raw_output=cn_res.raw_output,
                    structured_data=cn_res.structured_data,
                    insights=[],
                    concepts=[],
                )
            except Exception:
                pass
            
            if getattr(cn_res.status, "value", str(cn_res.status)) == "completed":
                analyzer_completed(
                    job_id,
                    "final",
                    "composite_note",
                    int((time.time() - cn_start) * 1000),
                    token_usage=cn_res.token_usage.dict() if cn_res.token_usage else None,
                    cost_usd=None,
                )
            else:
                analyzer_error(
                    job_id,
                    "final",
                    "composite_note",
                    cn_res.error_message or "Analyzer error",
                    processing_time_ms=int((time.time() - cn_start) * 1000),
                )
        
        # Run any additional custom Final analyzers via TemplateAnalyzer
        try:
            for name in selected_final:
                if name in ("meeting_notes", "composite_note"):
                    continue
                # Initialize status
                status_doc = _load_status(job_id)
                status_doc.setdefault("final", {})
                status_doc["final"][name] = {"status": "processing"}
                _save_status(job_id, status_doc)

                analyzer_started(job_id, "final", name)
                f_start = time.time()

                tmpl = TemplateAnalyzer(name, stage="final")
                # Apply prompt override if provided
                override = (prompt_selection.get("final") or {}).get(name)
                if override:
                    p = _safe_prompt_path(override)
                    if p:
                        tmpl.set_prompt_override(p)

                fres = tmpl.analyze_sync(final_ctx, save_intermediate=False, extra_llm_kwargs={"model": model_override} if model_override else None)

                # Save result
                status_doc = _load_status(job_id)
                status_doc["final"][name] = {
                    "status": getattr(fres.status, "value", str(fres.status)) if fres else "error",
                    "raw_output": fres.raw_output,
                    "processing_time": fres.processing_time,
                    "token_usage": fres.token_usage.dict() if fres.token_usage else None,
                    "model_used": getattr(fres, "model_used", None),
                    "structured_data": fres.structured_data,
                }

                # Update token usage totals
                if fres.token_usage:
                    if "tokenUsageTotal" not in status_doc:
                        status_doc["tokenUsageTotal"] = {"prompt": 0, "completion": 0, "total": 0}
                    status_doc["tokenUsageTotal"]["prompt"] += fres.token_usage.prompt_tokens
                    status_doc["tokenUsageTotal"]["completion"] += fres.token_usage.completion_tokens
                    status_doc["tokenUsageTotal"]["total"] += fres.token_usage.total_tokens

                _save_status(job_id, status_doc)

                # Save to file
                job_dir = _job_dir(job_id)
                final_dir = job_dir / "final"
                final_dir.mkdir(parents=True, exist_ok=True)
                (final_dir / f"{name}.md").write_text(fres.raw_output or "", encoding="utf-8")
                # Track locally for insights aggregation
                try:
                    final_results_local[name] = AnalysisResult(
                        analyzer_name=name,
                        raw_output=fres.raw_output,
                        structured_data=fres.structured_data,
                        insights=[],
                        concepts=[],
                    )
                except Exception:
                    pass

                if getattr(fres.status, "value", str(fres.status)) == "completed":
                    analyzer_completed(
                        job_id,
                        "final",
                        name,
                        int((time.time() - f_start) * 1000),
                        token_usage=fres.token_usage.dict() if fres.token_usage else None,
                        cost_usd=None,
                    )
                else:
                    analyzer_error(
                        job_id,
                        "final",
                        name,
                        fres.error_message or "Analyzer error",
                        processing_time_ms=int((time.time() - f_start) * 1000),
                    )
        except Exception as e:
            logger.warning(f"Custom final analyzers encountered an issue: {e}")
        
        # Emit stage completed
        # Aggregate Insights Dashboard after final results available
        try:
            # Build combined results for aggregator from in-memory data prepared above.
            # This avoids dependency on Redis visibility in the worker and ensures
            # insights are generated deterministically right after files are written.
            all_results_map: Dict[str, AnalysisResult] = {}
            # Stage A + Stage B combined (prepared earlier in this function)
            for k, v in (combined or {}).items():
                all_results_map[k] = v
            # Final stage results captured locally
            for k, v in (final_results_local or {}).items():
                all_results_map[k] = v
            insights, counts = aggregate_insights(all_results_map, processed)

            # Optional: LLM-based insights extraction
            try:
                cfg = get_config()
                proc = cfg.processing
                if getattr(proc, "insights_llm_enabled", True):
                    segtxt = build_segmented_transcript(processed)
                    combo = build_combined_context(all_results_map)
                    llm_items_obj = extract_insights_llm(
                        get_llm_client(),
                        segmented_transcript=segtxt,
                        combined_context=combo,
                        max_items=int(getattr(proc, "insights_llm_max_items", 50) or 50),
                        model=getattr(proc, "insights_llm_model", None),
                        max_tokens=int(getattr(proc, "insights_llm_max_tokens", 2000) or 2000),
                    )
                    # Persist raw LLM results
                    (final_dir / "insight_llm.json").write_text(json.dumps(llm_items_obj, indent=2), encoding="utf-8")
                    # Merge with aggregator results (canonical dicts already)
                    merged = (insights or []) + (llm_items_obj.get("items") or [])
                    merged = dedupe_items_dict(merged)
                    insights = merged
                    counts = count_items_dict(merged)
            except Exception as e:
                logger.warning(f"LLM insights merge failed: {e}")
            job_dir = _job_dir(job_id)
            final_dir = job_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            # Write artifacts
            (final_dir / "insight_dashboard.json").write_text(insights_to_json(insights), encoding="utf-8")
            (final_dir / "insight_dashboard.md").write_text(insights_to_md(insights, counts), encoding="utf-8")
            (final_dir / "insight_dashboard.csv").write_text(insights_to_csv(insights), encoding="utf-8")
            # WS event with counts and items (so UI can populate without fetching)
            try:
                emit_progress("insights.updated", {"jobId": job_id, "counts": counts, "items": insights})
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Insight aggregation failed: {e}")

        stage_completed(job_id, "final")
        
        # Update final status reflecting analyzer outcomes
        status_doc = _load_status(job_id)
        try:
            entries = [v for k, v in (status_doc.get("final") or {}).items() if isinstance(v, dict) and k != "status"]
            any_error = any((e.get("status") == "error") for e in entries)
            status_doc["final"]["status"] = "error" if any_error else "completed"
        except Exception:
            status_doc["final"]["status"] = "completed"
        _save_status(job_id, status_doc)
        
        logger.info("Completed Final stage")
        return {"status": "completed"}
        
    except Exception as e:
        logger.exception(f"Error in Final stage: {e}")
        return {"error": str(e), "status": "error"}


@celery.task(name="complete_stage_a")
def complete_stage_a(results: List[Dict[str, Any]], job_id: str, stage_a_list: List[str], **kwargs) -> Dict[str, Any]:
    """Callback when all Stage A analyzers complete."""
    logger.info(f"Stage A completed for job {job_id}")
    # Build authoritative mapping from the chord's results (order aligns with stage_a_list)
    stage_a_results = {name: res for name, res in zip(stage_a_list, results or [])}
    # Persist to Redis so polling/UI see final state consistently
    status_doc = _load_status(job_id)
    status_doc["stageA"] = stage_a_results
    _save_status(job_id, status_doc)
    # Emit stage completion after persisting
    stage_completed(job_id, "stage_a")
    # Return results for next stage
    return {"stageA": stage_a_results}


@celery.task(name="run_stage_b_after_a", bind=True)
def run_stage_b_after_a(
    self,
    stage_a_results: Dict[str, Any],
    job_id: str,
    transcript_data: Dict[str, Any],
    stage_b_list: List[str],
    prompt_selection: Dict[str, Any],
    model_override: Optional[str] = None,
    stage_b_options: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Run Stage B analyzers in parallel after Stage A completes.
    IMPORTANT: Do NOT block inside a task. Instead, replace this task with a chord
    so the chain waits for the Stage B chord callback (complete_stage_b) and passes
    its result to the next link (run_final_stage).
    """
    logger.info(f"Starting Stage B parallel execution for job {job_id}")
    
    # Build Stage B tasks using Stage A results
    stage_b_tasks = group(
        run_stage_b_analyzer.s(
            job_id,
            analyzer_name,
            transcript_data,
            stage_a_results.get("stageA", {}),
            (prompt_selection.get("stageB") or {}).get(analyzer_name),
            model_override,
            stage_b_options or {},
        )
        for analyzer_name in stage_b_list
    )
    
    # Replace current task with a chord whose callback returns all_results.
    # This ensures the downstream chain receives complete_stage_b's return value.
    return self.replace(
        chord(stage_b_tasks, complete_stage_b.s(job_id=job_id, stage_a_results=stage_a_results, stage_b_list=stage_b_list))
    )


@celery.task(name="complete_stage_b")
def complete_stage_b(results: List[Dict[str, Any]], job_id: str, stage_a_results: Dict[str, Any], stage_b_list: List[str], **kwargs) -> Dict[str, Any]:
    """Callback when all Stage B analyzers complete."""
    logger.info(f"Stage B completed for job {job_id}")
    # Build authoritative mapping from the chord's results (order aligns with stage_b_list)
    stage_b_results = {name: res for name, res in zip(stage_b_list, results or [])}
    # Persist to Redis so polling/UI see final state consistently
    status_doc = _load_status(job_id)
    status_doc["stageB"] = stage_b_results
    _save_status(job_id, status_doc)
    # Emit stage completion after persisting
    stage_completed(job_id, "stage_b")
    # Collect all results (use authoritative Stage A passed in and Stage B we just persisted)
    all_results = {
        "stageA": stage_a_results.get("stageA", {}),
        "stageB": stage_b_results,
    }
    return all_results


@celery.task(name="finalize_pipeline")
def finalize_pipeline(final_result: Dict[str, Any], job_id: str, start_time: float) -> None:
    """Final callback when entire pipeline completes."""
    logger.info(f"Pipeline completed for job {job_id}")
    
    # Calculate total time
    total_ms = int((time.time() - start_time) * 1000)
    
    # Update final status
    status_doc = _load_status(job_id)
    status_doc["status"] = "completed"
    status_doc["completedAt"] = time.time()
    status_doc["totalProcessingTimeMs"] = total_ms
    _save_status(job_id, status_doc)
    
    # Write final status file
    try:
        job_dir = _job_dir(job_id)
        final_status = {
            "run_id": job_id,
            "status": "completed",
            "output_dir": str(job_dir),
            "stage_a": {
                "analyzers": list(status_doc.get("stageA", {}).keys()),
                "tokens": sum((r.get("token_usage", {}) or {}).get("total_tokens", 0) 
                            for r in status_doc.get("stageA", {}).values()),
            },
            "stage_b": {
                "analyzers": list(status_doc.get("stageB", {}).keys()),
                "tokens": sum((r.get("token_usage", {}) or {}).get("total_tokens", 0) 
                            for r in status_doc.get("stageB", {}).values()),
            },
            "total_tokens": status_doc.get("tokenUsageTotal", {}).get("total", 0),
            "wall_clock_seconds": total_ms / 1000.0,
            "timestamps": {
                "start_time": datetime.fromtimestamp(status_doc.get("startedAt")).isoformat() 
                            if status_doc.get("startedAt") else None,
                "end_time": datetime.fromtimestamp(status_doc.get("completedAt")).isoformat() 
                          if status_doc.get("completedAt") else None,
            },
        }
        (job_dir / "final_status.json").write_text(json.dumps(final_status, indent=2), encoding="utf-8")
        (job_dir / "COMPLETED").write_text("ok\n", encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to write final status: {e}")
    
    # Emit completion event
    job_completed(
        job_id,
        total_ms,
        total_token_usage=status_doc.get("tokenUsageTotal", {}),
        total_cost_usd=None,
    )
    
    # Send notification
    try:
        get_notification_manager().pipeline_completed(job_id, {
            "status": "completed",
            "output_dir": str(_job_dir(job_id)),
            "total_tokens": status_doc.get("tokenUsageTotal", {}).get("total", 0),
            "wall_clock_seconds": total_ms / 1000.0,
        })
    except Exception:
        pass


@celery.task(name="run_parallel_pipeline")
def run_parallel_pipeline(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Main orchestration task using parallel execution.
    Runs analyzers in parallel within each stage.
    """
    start_time = time.time()
    
    # Initialize status document
    status_doc = {
        "jobId": job_id,
        "status": "processing",
        "stageA": {},
        "stageB": {},
        "final": {},
        "tokenUsageTotal": {"prompt": 0, "completion": 0, "total": 0},
        "errors": [],
        "startedAt": start_time,
    }
    
    try:
        job_queued(job_id)
        _save_status(job_id, status_doc)
        
        # Send start notification
        try:
            get_notification_manager().pipeline_started(job_id, {
                "mechanism": "parallel_celery",
                "output_dir": None
            })
        except Exception:
            pass
        
        # Process transcript
        transcript_text = (payload.get("transcriptText") or "").strip()
        if not transcript_text:
            raise ValueError("transcriptText required")
        
        processor = get_transcript_processor()
        processed = processor.process(transcript_text, filename=None)
        transcript_data = processed.dict()  # Serialize for passing between tasks
        
        # Get selected analyzers
        selected = payload.get("selected") or {}
        options = payload.get("options") or {}
        models = (options.get("models") or {})
        stage_a_model = models.get("stageA")
        stage_b_model = models.get("stageB")
        final_model = models.get("final")
        stage_a_list = selected.get("stageA") or [
            "say_means",
            "perspective_perception",
            "premises_assertions",
            "postulate_theorem"
        ]
        stage_b_list = selected.get("stageB") or [
            "competing_hypotheses",
            "first_principles",
            "determining_factors",
            "patentability"
        ]
        final_list = selected.get("final") or ["meeting_notes", "composite_note"]
        
        prompt_selection = payload.get("promptSelection") or {}
        
        logger.info(f"Starting parallel pipeline with stages: A={stage_a_list}, B={stage_b_list}, Final={final_list}")
        
        # Create Stage A parallel tasks
        stage_a_tasks = group(
            run_stage_a_analyzer.s(
                job_id,
                analyzer_name,
                transcript_data,
                (prompt_selection.get("stageA") or {}).get(analyzer_name),
                stage_a_model
            )
            for analyzer_name in stage_a_list
        )
        
        # Compose the pipeline with signatures (do not execute yet)
        stage_a_chord_sig = chord(stage_a_tasks, complete_stage_a.s(job_id=job_id, stage_a_list=stage_a_list))
        
        from celery import chain
        
        pipeline = chain(
            stage_a_chord_sig,
            run_stage_b_after_a.s(
                job_id=job_id,
                transcript_data=transcript_data,
                stage_b_list=stage_b_list,
                prompt_selection=prompt_selection,
                model_override=stage_b_model,
                stage_b_options=(options.get("stageBOptions") or {}),
            ),
            run_final_stage.s(
                job_id=job_id,
                transcript_data=transcript_data,
                selected_final=final_list,
                prompt_selection=prompt_selection,
                model_override=final_model,
                final_options=(options.get("finalOptions") or {}),
            ),
            finalize_pipeline.s(job_id=job_id, start_time=start_time)
        )
        
        # Execute the pipeline asynchronously
        pipeline.apply_async()
        
        logger.info(f"Parallel pipeline started for job {job_id}")
        
    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}: {e}")
        status_doc["status"] = "error"
        status_doc["errors"].append(str(e))
        _save_status(job_id, status_doc)
        
        job_error(job_id, "PIPELINE_ERROR", str(e))
        
        try:
            get_notification_manager().pipeline_error(job_id, {"message": str(e)})
        except Exception:
            pass
@celery.task(name="reload_registry")
def reload_registry_task() -> Dict[str, Any]:
    """
    Rebuild the analyzers registry from the filesystem and refresh worker config.
    Useful after UI-triggered rescans so the worker sees new/updated prompts
    without requiring a manual restart.
    """
    try:
        from src.analyzers.registry import rebuild_registry_from_prompts
        from src.config import reset_config, get_config
        summary = rebuild_registry_from_prompts()
        reset_config(); _ = get_config()
        return {"ok": True, "summary": summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}
