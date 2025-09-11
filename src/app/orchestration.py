"""
Celery orchestration tasks for the Transcript Analysis Tool.

- run_pipeline: orchestrates Stage A (initially say_means) on a transcript
- Persists status/result in Redis under key: job:{job_id}
- Emits Socket.IO progress events

Note: This is an initial implementation focused on Say-Means to validate Celery wiring.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

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
from src.app.sockets import (
    job_queued,
    analyzer_started,
    analyzer_completed,
    stage_completed,
    job_completed,
    job_error,
)
from src.app.notify import get_notification_manager


def _get_redis():
    cfg = get_config()
    # Ensure db is appended if not present
    url = cfg.web.redis_url
    if url.rstrip("/").count("/") == 2:
        url = f"{url}/{cfg.web.redis_db}"
    return redis_from_url(url)


def _redis_key(job_id: str) -> str:
    return f"job:{job_id}"

# Prompt override helpers
def _prompts_root() -> Path:
    try:
        return (Path.cwd() / "prompts").resolve()
    except Exception:
        return Path("prompts").resolve()

def _is_within_prompts(p: Path) -> bool:
    try:
        return str(p.resolve()).startswith(str(_prompts_root()))
    except Exception:
        return False

def _safe_prompt_path(file_path: str | None) -> Optional[Path]:
    if not file_path:
        return None
    try:
        p = Path(file_path)
        if p.suffix.lower() != ".md":
            return None
        if not p.exists():
            return None
        if not _is_within_prompts(p):
            return None
        return p
    except Exception:
        return None


def _save_status(job_id: str, data: Dict[str, Any]) -> None:
    """Persist job status/result to Redis."""
    r = _get_redis()
    key = _redis_key(job_id)
    r.set(key, json.dumps(data))
    # Optional TTL: 24h
    r.expire(key, 60 * 60 * 24)

def _job_dir(job_id: str) -> Path:
    """
    Filesystem location to drop job artifacts for Celery/web runs.
    Not strictly required for web flow, but enables sentinel + machine-readable status.
    """
    d = Path(f"output/jobs/{job_id}")
    d.mkdir(parents=True, exist_ok=True)
    return d


# Import the parallel pipeline implementation
from src.app.parallel_orchestration import run_parallel_pipeline

@celery.task(name="run_pipeline")
def run_pipeline(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Main entry point that delegates to parallel implementation.
    This maintains backward compatibility while using parallel execution.
    """
    # Use parallel execution for better performance
    return run_parallel_pipeline(job_id, payload)


@celery.task(name="run_pipeline_sequential")
def run_pipeline_sequential(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Orchestration entrypoint.
    payload: {
      "transcriptText": str,
      "fileId": str | None,
      "selected": { "stageA": [..], "stageB": [..], "final": [..] },
      "options": {...}
    }
    """
    start = time.time()
    status_doc: Dict[str, Any] = {
        "jobId": job_id,
        "status": "processing",
        "stageA": {},
        "stageB": {},
        "final": {},
        "tokenUsageTotal": {"prompt": 0, "completion": 0, "total": 0},
        "errors": [],
        "startedAt": time.time(),
    }

    try:
        job_queued(job_id)  # Emit queued event (already emitted by API, but safe)
        _save_status(job_id, status_doc)
        # Proactive notification: pipeline started
        try:
            get_notification_manager().pipeline_started(job_id, {"mechanism": "celery", "output_dir": None})
        except Exception:
            pass

        transcript_text: str = (payload.get("transcriptText") or "").strip()
        if not transcript_text:
            raise ValueError("transcriptText required for run_pipeline")

        # Process transcript
        processor = get_transcript_processor()
        processed = processor.process(transcript_text, filename=None)

        # Build analysis context
        ctx = AnalysisContext(transcript=processed, metadata={"source": "celery.run_pipeline"})

        # Stage A selection (now supports all 4 Stage A analyzers)
        selected = payload.get("selected") or {}
        stage_a_list = selected.get("stageA") or [
            "say_means", 
            "perspective_perception",
            "premises_assertions",
            "postulate_theorem"
        ]
        # Optional prompt overrides mapping (validated in API layer)
        prompt_selection = payload.get("promptSelection") or {}

        # Map analyzer names to classes
        analyzer_map = {
            "say_means": SayMeansAnalyzer,
            "perspective_perception": PerspectivePerceptionAnalyzer,
            "premises_assertions": PremisesAssertionsAnalyzer,
            "postulate_theorem": PostulateTheoremAnalyzer,
        }

        # Run analyzers in sequence (can parallelize later)
        for analyzer_name in stage_a_list:
            if analyzer_name not in analyzer_map:
                logger.warning(f"Analyzer {analyzer_name} not implemented yet; skipping")
                continue

            # Set processing status for this analyzer
            status_doc["stageA"][analyzer_name] = {"status": "processing"}
            _save_status(job_id, status_doc)
            
            analyzer_started(job_id, "stage_a", analyzer_name)
            a_start = time.time()
            # Optional stage_start notification (best-effort)
            try:
                get_notification_manager().stage_started(job_id, "stage_a", analyzer_name)
            except Exception:
                pass

            analyzer_class = analyzer_map[analyzer_name]
            analyzer = analyzer_class()
            # Apply prompt override if provided
            try:
                override_path_str = (prompt_selection.get("stageA") or {}).get(analyzer_name)
                p = _safe_prompt_path(override_path_str) if override_path_str else None
                if p:
                    analyzer.set_prompt_override(p)
            except Exception:
                p = None
            result = analyzer.analyze_sync(ctx)

            # Accumulate token usage
            if result.token_usage:
                status_doc["tokenUsageTotal"]["prompt"] += result.token_usage.prompt_tokens
                status_doc["tokenUsageTotal"]["completion"] += result.token_usage.completion_tokens
                status_doc["tokenUsageTotal"]["total"] += result.token_usage.total_tokens

            # Determine used prompt path for traceability
            try:
                used_prompt_path = str(p) if p else str(get_config().get_prompt_path(analyzer_name))
            except Exception:
                used_prompt_path = None

            # Save result in status_doc
            status_doc["stageA"][analyzer_name] = {
                "status": result.status.value,
                "processing_time": result.processing_time,
                "token_usage": result.token_usage.dict() if result.token_usage else None,
                "raw_output": result.raw_output,
                "structured_data": result.structured_data,
                "insights": [i.dict() for i in result.insights],
                "concepts": [c.dict() for c in result.concepts],
                "error_message": result.error_message,
                "prompt_path": used_prompt_path,
            }
            _save_status(job_id, status_doc)

            analyzer_completed(
                job_id,
                "stage_a",
                analyzer_name,
                int((time.time() - a_start) * 1000),
                token_usage=result.token_usage.dict() if result.token_usage else None,
                cost_usd=None,  # cost tracking can be added later
            )
            # Optional stage_completed notification (best-effort)
            try:
                stats = {
                    "processing_time": result.processing_time,
                    "token_usage": result.token_usage.dict() if result.token_usage else None,
                }
                get_notification_manager().stage_completed(job_id, "stage_a", analyzer_name, stats)
            except Exception:
                pass

        stage_completed(job_id, "stage_a")

        # Stage B: Meta-Analysis of Stage A Results
        stage_b_list = selected.get("stageB") or [
            "competing_hypotheses",
            "first_principles",
            "determining_factors",
            "patentability"
        ]
        
        logger.info(f"Stage A completed. Starting Stage B with {len(stage_b_list)} analyzers: {stage_b_list}")
        logger.info(f"Selected stages from payload: {selected}")

        # Create context from Stage A results for Stage B
        # Stage B analyzers need the original transcript plus Stage A results as previous analyses
        stage_a_analyses = {}
        for name, result_data in status_doc["stageA"].items():
            stage_a_analyses[name] = AnalysisResult(
                analyzer_name=name,
                raw_output=result_data.get("raw_output", ""),
                structured_data=result_data.get("structured_data", {}),
                insights=[],  # We could reconstruct these if needed
                concepts=[],  # We could reconstruct these if needed
                processing_time=result_data.get("processing_time", 0),
                token_usage=None,
                status=AnalyzerStatus.COMPLETED
            )
        
        # Create new AnalysisContext with original transcript and Stage A results
        stage_b_ctx = AnalysisContext(
            transcript=processed,  # Use original transcript
            previous_analyses=stage_a_analyses,  # Pass Stage A results as previous analyses
            metadata={"source": "stage_a_aggregation", "stage": "stage_b"}
        )

        # Map Stage B analyzer names to classes
        stage_b_analyzer_map = {
            "competing_hypotheses": CompetingHypothesesAnalyzer,
            "first_principles": FirstPrinciplesAnalyzer,
            "determining_factors": DeterminingFactorsAnalyzer,
            "patentability": PatentabilityAnalyzer,
        }

        # Run Stage B analyzers
        for analyzer_name in stage_b_list:
            if analyzer_name not in stage_b_analyzer_map:
                logger.warning(f"Stage B Analyzer {analyzer_name} not implemented yet; skipping")
                continue

            # Set processing status for this analyzer
            status_doc["stageB"][analyzer_name] = {"status": "processing"}
            _save_status(job_id, status_doc)
            
            analyzer_started(job_id, "stage_b", analyzer_name)
            b_start = time.time()
            # Optional stage_start notification
            try:
                get_notification_manager().stage_started(job_id, "stage_b", analyzer_name)
            except Exception:
                pass

            analyzer_class = stage_b_analyzer_map[analyzer_name]
            analyzer = analyzer_class()
            # Apply prompt override if provided
            try:
                override_path_str = (prompt_selection.get("stageB") or {}).get(analyzer_name)
                p = _safe_prompt_path(override_path_str) if override_path_str else None
                if p:
                    analyzer.set_prompt_override(p)
            except Exception:
                p = None
            result = analyzer.analyze_sync(stage_b_ctx)

            # Accumulate token usage
            if result.token_usage:
                status_doc["tokenUsageTotal"]["prompt"] += result.token_usage.prompt_tokens
                status_doc["tokenUsageTotal"]["completion"] += result.token_usage.completion_tokens
                status_doc["tokenUsageTotal"]["total"] += result.token_usage.total_tokens

            # Determine used prompt path for traceability
            try:
                used_prompt_path = str(p) if p else str(get_config().get_prompt_path(analyzer_name))
            except Exception:
                used_prompt_path = None

            # Save result in status_doc
            status_doc["stageB"][analyzer_name] = {
                "status": result.status.value,
                "processing_time": result.processing_time,
                "token_usage": result.token_usage.dict() if result.token_usage else None,
                "raw_output": result.raw_output,
                "structured_data": result.structured_data,
                "insights": [i.dict() for i in result.insights],
                "concepts": [c.dict() for c in result.concepts],
                "error_message": result.error_message,
                "prompt_path": used_prompt_path,
            }
            _save_status(job_id, status_doc)

            analyzer_completed(
                job_id,
                "stage_b",
                analyzer_name,
                int((time.time() - b_start) * 1000),
                token_usage=result.token_usage.dict() if result.token_usage else None,
                cost_usd=None,
            )
            # Optional stage_completed notification
            try:
                stats = {
                    "processing_time": result.processing_time,
                    "token_usage": result.token_usage.dict() if result.token_usage else None,
                }
                get_notification_manager().stage_completed(job_id, "stage_b", analyzer_name, stats)
            except Exception:
                pass

        stage_completed(job_id, "stage_b")

        # Final Stage (Synthesis): Meeting Notes and Composite Note
        # Always run final stage if we have Stage A and B results
        final_list = selected.get("final") or ["meeting_notes", "composite_note"]
        
        logger.info(f"Stage B completed. Starting Final stage with {len(final_list)} analyzers: {final_list}")
        
        try:
            # Build combined results as AnalysisResult objects for final context
            combined: Dict[str, AnalysisResult] = {}
            for name, r in (status_doc.get("stageA") or {}).items():
                combined[name] = AnalysisResult(
                    analyzer_name=name,
                    raw_output=(r or {}).get("raw_output", "") or "",
                    structured_data=(r or {}).get("structured_data", {}) or {},
                    insights=[],
                    concepts=[],
                    processing_time=float((r or {}).get("processing_time", 0) or 0),
                    token_usage=None,
                    status=AnalyzerStatus.COMPLETED,
                )
            for name, r in (status_doc.get("stageB") or {}).items():
                combined[name] = AnalysisResult(
                    analyzer_name=name,
                    raw_output=(r or {}).get("raw_output", "") or "",
                    structured_data=(r or {}).get("structured_data", {}) or {},
                    insights=[],
                    concepts=[],
                    processing_time=float((r or {}).get("processing_time", 0) or 0),
                    token_usage=None,
                    status=AnalyzerStatus.COMPLETED,
                )

            # Create final analysis context (transcript + combined Stage A/B)
            final_ctx = AnalysisContext(
                transcript=processed,
                previous_analyses=combined,
                metadata={"source": "stage_a_b", "stage": "final"},
            )

            # Run final generators synchronously (apply prompt overrides if provided)
            # Meeting Notes
            if "meeting_notes" in final_list:
                # Set processing status for meeting_notes
                if "final" not in status_doc:
                    status_doc["final"] = {}
                status_doc["final"]["meeting_notes"] = {"status": "processing"}
                _save_status(job_id, status_doc)
                
                analyzer_started(job_id, "final", "meeting_notes")
                mn_start = time.time()
                try:
                    get_notification_manager().stage_started(job_id, "final", "meeting_notes")
                except Exception:
                    pass
            
            meeting_notes_an = MeetingNotesAnalyzer()
            composite_note_an = CompositeNoteAnalyzer()
            try:
                ov_mn = (prompt_selection.get("final") or {}).get("meeting_notes")
                p_mn = _safe_prompt_path(ov_mn) if ov_mn else None
                if p_mn:
                    meeting_notes_an.set_prompt_override(p_mn)
            except Exception:
                p_mn = None
            try:
                ov_cn = (prompt_selection.get("final") or {}).get("composite_note")
                p_cn = _safe_prompt_path(ov_cn) if ov_cn else None
                if p_cn:
                    composite_note_an.set_prompt_override(p_cn)
            except Exception:
                p_cn = None

            # Run Meeting Notes
            if "meeting_notes" in final_list:
                mn_res = meeting_notes_an.analyze_sync(final_ctx, save_intermediate=False)
                
                # Emit completion event for meeting_notes
                analyzer_completed(
                    job_id,
                    "final",
                    "meeting_notes",
                    int((time.time() - mn_start) * 1000) if 'mn_start' in locals() else 0,
                    token_usage=mn_res.token_usage.dict() if mn_res.token_usage else None,
                    cost_usd=None,
                )
                
                # Update token usage
                if mn_res.token_usage:
                    status_doc["tokenUsageTotal"]["prompt"] += mn_res.token_usage.prompt_tokens
                    status_doc["tokenUsageTotal"]["completion"] += mn_res.token_usage.completion_tokens
                    status_doc["tokenUsageTotal"]["total"] += mn_res.token_usage.total_tokens
            else:
                mn_res = None
            
            # Run Composite Note
            if "composite_note" in final_list:
                # Set processing status for composite_note
                if "final" not in status_doc:
                    status_doc["final"] = {}
                status_doc["final"]["composite_note"] = {"status": "processing"}
                _save_status(job_id, status_doc)
                
                analyzer_started(job_id, "final", "composite_note")
                cn_start = time.time()
                try:
                    get_notification_manager().stage_started(job_id, "final", "composite_note")
                except Exception:
                    pass
                
                cn_res = composite_note_an.analyze_sync(final_ctx, save_intermediate=False)
                
                # Emit completion event for composite_note
                analyzer_completed(
                    job_id,
                    "final",
                    "composite_note",
                    int((time.time() - cn_start) * 1000),
                    token_usage=cn_res.token_usage.dict() if cn_res.token_usage else None,
                    cost_usd=None,
                )
                
                # Update token usage
                if cn_res.token_usage:
                    status_doc["tokenUsageTotal"]["prompt"] += cn_res.token_usage.prompt_tokens
                    status_doc["tokenUsageTotal"]["completion"] += cn_res.token_usage.completion_tokens
                    status_doc["tokenUsageTotal"]["total"] += cn_res.token_usage.total_tokens
            else:
                cn_res = None

            # Persist final outputs under job artifacts directory
            job_dir = _job_dir(job_id)
            final_dir = job_dir / "final"
            final_dir.mkdir(parents=True, exist_ok=True)
            
            if mn_res:
                (final_dir / "meeting_notes.md").write_text(mn_res.raw_output or "", encoding="utf-8")
            if cn_res:
                (final_dir / "composite_note.md").write_text(cn_res.raw_output or "", encoding="utf-8")
            
            # Emit stage completed for final
            stage_completed(job_id, "final")

            # Update status_doc and persist
            try:
                used_mn = str(p_mn) if p_mn else str(get_config().get_prompt_path("meeting_notes"))
            except Exception:
                used_mn = None
            try:
                used_cn = str(p_cn) if p_cn else str(get_config().get_prompt_path("composite_note"))
            except Exception:
                used_cn = None

            status_doc["final"] = {
                "status": "completed",
                "outputs": {
                    "meeting_notes": str(final_dir / "meeting_notes.md"),
                    "composite_note": str(final_dir / "composite_note.md"),
                },
                "prompts": {
                    "meeting_notes": used_mn,
                    "composite_note": used_cn,
                },
            }
            _save_status(job_id, status_doc)
        except Exception as fe:
            logger.warning(f"Final stage generation failed: {fe}")

        # Finish
        total_ms = int((time.time() - start) * 1000)
        status_doc["status"] = "completed"
        status_doc["completedAt"] = time.time()
        status_doc["totalProcessingTimeMs"] = total_ms
        _save_status(job_id, status_doc)

        # Write job directory sentinel and final status (machine-readable)
        try:
            job_dir = _job_dir(job_id)
            final_status = {
                "run_id": job_id,
                "status": status_doc.get("status", "completed"),
                "output_dir": str(job_dir),
                "stage_a": {
                    "analyzers": list(status_doc.get("stageA", {}).keys()),
                    "tokens": sum((r.get("token_usage", {}) or {}).get("total_tokens", 0) for r in status_doc.get("stageA", {}).values()),
                },
                "stage_b": {
                    "analyzers": list(status_doc.get("stageB", {}).keys()),
                    "tokens": sum((r.get("token_usage", {}) or {}).get("total_tokens", 0) for r in status_doc.get("stageB", {}).values()),
                },
                "total_tokens": status_doc.get("tokenUsageTotal", {}).get("total", 0),
                "wall_clock_seconds": total_ms / 1000.0,
                "timestamps": {
                    "start_time": datetime.fromtimestamp(status_doc.get("startedAt")).isoformat() if status_doc.get("startedAt") else None,
                    "end_time": datetime.fromtimestamp(status_doc.get("completedAt")).isoformat() if status_doc.get("completedAt") else None,
                },
            }
            (job_dir / "final_status.json").write_text(json.dumps(final_status, indent=2), encoding="utf-8")
            (job_dir / "COMPLETED").write_text("ok\n", encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to write job final status artifacts: {e}")

        job_completed(
            job_id,
            total_ms,
            total_token_usage=status_doc["tokenUsageTotal"],
            total_cost_usd=None,
        )
        # Proactive notification: pipeline completed
        try:
            summary = {
                "status": status_doc.get("status", "completed"),
                "output_dir": str(_job_dir(job_id)),
                "total_tokens": status_doc.get("tokenUsageTotal", {}).get("total", 0),
                "stage_a": {
                    "analyzers": list(status_doc.get("stageA", {}).keys()),
                    "tokens": sum((r.get("token_usage", {}) or {}).get("total_tokens", 0) for r in status_doc.get("stageA", {}).values()),
                },
                "stage_b": {
                    "analyzers": list(status_doc.get("stageB", {}).keys()),
                    "tokens": sum((r.get("token_usage", {}) or {}).get("total_tokens", 0) for r in status_doc.get("stageB", {}).values()),
                },
                "wall_clock_seconds": total_ms / 1000.0,
            }
            get_notification_manager().pipeline_completed(job_id, summary)
        except Exception:
            pass

    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}: {e}")
        status_doc["status"] = "error"
        status_doc["errors"].append(str(e))
        _save_status(job_id, status_doc)

        # Write error final_status.json (no COMPLETED sentinel on error)
        try:
            job_dir = _job_dir(job_id)
            final_status = {
                "run_id": job_id,
                "status": "error",
                "output_dir": str(job_dir),
                "stage_a": {"analyzers": list(status_doc.get("stageA", {}).keys())},
                "stage_b": {"analyzers": list(status_doc.get("stageB", {}).keys())},
                "total_tokens": status_doc.get("tokenUsageTotal", {}).get("total", 0),
                "wall_clock_seconds": int((time.time() - start) * 1000) / 1000.0,
                "error": str(e),
                "timestamps": {
                    "start_time": datetime.fromtimestamp(status_doc.get("startedAt")).isoformat() if status_doc.get("startedAt") else None,
                    "end_time": datetime.now().isoformat(),
                },
            }
            (job_dir / "final_status.json").write_text(json.dumps(final_status, indent=2), encoding="utf-8")
        except Exception as werr:
            logger.warning(f"Failed to write job error final status: {werr}")

        job_error(job_id, "PIPELINE_ERROR", str(e))
        # Proactive notification: pipeline error
        try:
            get_notification_manager().pipeline_error(job_id, {"message": str(e)}, meta={"output_dir": str(_job_dir(job_id))})
        except Exception:
            pass
