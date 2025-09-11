#!/usr/bin/env python3
"""
Async concurrent orchestrator for the Transcript Analysis pipeline.

- Runs Stage A analyzers concurrently against the same transcript
- Aggregates Stage A results
- Runs Stage B analyzers concurrently against the same aggregated Stage A context
- Persists intermediate outputs using BaseAnalyzer.save_intermediate_result
- Writes run-level metadata and simple summaries

Usage: see scripts/test_parallel_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.config import get_config
from src.models import AnalysisContext, AnalysisResult, TokenUsage, ProcessedTranscript, TranscriptMetadata
from src.transcript_processor import get_transcript_processor
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
from src.analyzers.stage_a.premises_assertions import PremisesAssertionsAnalyzer
from src.analyzers.stage_a.postulate_theorem import PostulateTheoremAnalyzer
from src.analyzers.stage_b.competing_hypotheses import CompetingHypothesesAnalyzer
from src.analyzers.stage_b.first_principles import FirstPrinciplesAnalyzer
from src.analyzers.stage_b.determining_factors import DeterminingFactorsAnalyzer
from src.analyzers.stage_b.patentability import PatentabilityAnalyzer
from src.app.notify import get_notification_manager
from src.analyzers.final.meeting_notes import MeetingNotesAnalyzer
from src.analyzers.final.composite_note import CompositeNoteAnalyzer


@dataclass
class OrchestratorResult:
    stage_a_results: Dict[str, AnalysisResult]
    stage_b_results: Dict[str, AnalysisResult]
    total_tokens: int
    total_time_seconds: float
    run_dir: Path


def _default_stage_a_analyzers() -> List:
    return [
        ("say_means", SayMeansAnalyzer()),
        ("perspective_perception", PerspectivePerceptionAnalyzer()),
        ("premises_assertions", PremisesAssertionsAnalyzer()),
        ("postulate_theorem", PostulateTheoremAnalyzer()),
    ]


def _default_stage_b_analyzers() -> List:
    return [
        ("competing_hypotheses", CompetingHypothesesAnalyzer()),
        ("first_principles", FirstPrinciplesAnalyzer()),
        ("determining_factors", DeterminingFactorsAnalyzer()),
        ("patentability", PatentabilityAnalyzer()),
    ]

def _default_final_analyzers() -> List:
    return [
        ("meeting_notes", MeetingNotesAnalyzer()),
        ("composite_note", CompositeNoteAnalyzer()),
    ]


async def _run_one_analyzer(
    sem: asyncio.Semaphore,
    analyzer_tuple: Tuple[str, Any],
    context: AnalysisContext,
    output_dir: Path,
    run_id: Optional[str] = None,
) -> Tuple[str, AnalysisResult]:
    """Run a single analyzer under semaphore control, save intermediates, and return result."""
    name, analyzer = analyzer_tuple
    async with sem:
        nm = get_notification_manager()
        logger.info(f"[{analyzer.stage}] Starting analyzer: {name}")
        if run_id:
            try:
                nm.stage_started(run_id, analyzer.stage, name)
            except Exception:
                pass
        result = await analyzer.analyze(context)
        # Save intermediates to run-dir structure
        try:
            analyzer.save_intermediate_result(result, output_dir)
        except Exception as e:
            logger.warning(f"Failed to save intermediate for {name}: {e}")
        logger.info(f"[{analyzer.stage}] Completed analyzer: {name} ({result.processing_time:.2f}s)")
        if run_id:
            try:
                stats = {
                    "processing_time": result.processing_time,
                    "token_usage": result.token_usage.dict() if result.token_usage else None,
                    "analyzer_name": name,
                    "stage": analyzer.stage,
                }
                nm.stage_completed(run_id, analyzer.stage, name, stats)
            except Exception:
                pass
        return name, result


async def run_stage_concurrently(
    stage_name: str,
    analyzers: List[Tuple[str, Any]],
    context: AnalysisContext,
    output_dir: Path,
    max_concurrent: int,
) -> Dict[str, AnalysisResult]:
    """Run a set of analyzers concurrently with concurrency limit."""
    sem = asyncio.Semaphore(max_concurrent)
    # Try to compute run_id from output_dir
    try:
        run_id = output_dir.name
    except Exception:
        run_id = None
    tasks = [
        asyncio.create_task(_run_one_analyzer(sem, analyzer_tuple, context, output_dir, run_id))
        for analyzer_tuple in analyzers
    ]
    results: Dict[str, AnalysisResult] = {}
    for fut in asyncio.as_completed(tasks):
        try:
            name, res = await fut
            results[name] = res
        except Exception as e:
            logger.error(f"Analyzer task failed: {e}")
    return results


def _create_run_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"output/runs/run_{timestamp}")
    (run_dir / "intermediate" / "stage_a").mkdir(parents=True, exist_ok=True)
    (run_dir / "intermediate" / "stage_b").mkdir(parents=True, exist_ok=True)
    (run_dir / "final").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    return run_dir


def _create_metadata(run_dir: Path, config: Dict[str, Any]) -> Path:
    metadata_path = run_dir / "metadata.json"
    metadata = {
        "run_id": run_dir.name,
        "start_time": datetime.now().isoformat(),
        "configuration": config,
        "status": "in_progress",
        "stages": {
            "stage_a": {"status": "pending", "analyzers": []},
            "stage_b": {"status": "pending", "analyzers": []},
            "final": {"status": "pending", "outputs": []},
        },
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    return metadata_path


def _update_metadata_stage(
    metadata_path: Path,
    stage_key: str,
    updates: Dict[str, Any],
) -> None:
    try:
        with open(metadata_path, "r") as f:
            data = json.load(f)
        data["stages"][stage_key].update(updates)
        with open(metadata_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to update metadata for {stage_key}: {e}")


def _finalize_metadata(
    metadata_path: Path,
    totals: Dict[str, Any],
    status: str = "completed",
) -> None:
    try:
        with open(metadata_path, "r") as f:
            data = json.load(f)
        data.update({
            "end_time": datetime.now().isoformat(),
            "status": status,
            "summary": totals,
        })
        with open(metadata_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to finalize metadata: {e}")


def _aggregate_tokens(results: Dict[str, AnalysisResult]) -> int:
    total = 0
    for r in results.values():
        if r.token_usage:
            total += r.token_usage.total_tokens
    return total


async def run_pipeline_async(
    transcript_text: str,
    stage_a: Optional[List[Tuple[str, Any]]] = None,
    stage_b: Optional[List[Tuple[str, Any]]] = None,
    save_stage_b_context_debug: bool = True,
) -> OrchestratorResult:
    """
    Run the pipeline end-to-end with concurrency for Stage A and Stage B.
    """
    cfg = get_config()
    nm = get_notification_manager()
    max_cc = getattr(cfg.processing, "max_concurrent", 3)
    start_ts = datetime.now()

    # Create run dir and metadata
    run_dir = _create_run_dir()
    metadata_path = _create_metadata(
        run_dir,
        {
            "model": cfg.llm.model,
            "temperature": cfg.llm.temperature,
            "parallel": cfg.processing.parallel,
            "max_concurrent": max_cc,
        },
    )

    # Build transcript context
    processor = get_transcript_processor()
    processed: ProcessedTranscript = processor.process(transcript_text, filename="uploaded.md")
    ctx_a = AnalysisContext(transcript=processed, metadata={"run_id": run_dir.name, "stage": "stage_a"})
    # Notify pipeline start
    try:
        nm.pipeline_started(run_dir.name, {"output_dir": str(run_dir)})
    except Exception:
        pass

    # Stage A
    _update_metadata_stage(metadata_path, "stage_a", {"status": "in_progress"})
    analyzers_a = stage_a if stage_a is not None else _default_stage_a_analyzers()
    stage_a_results = await run_stage_concurrently("stage_a", analyzers_a, ctx_a, run_dir, max_cc)
    _update_metadata_stage(
        metadata_path,
        "stage_a",
        {
            "status": "completed",
            "analyzers": list(stage_a_results.keys()),
            "total_tokens": _aggregate_tokens(stage_a_results),
        },
    )

    # Build Stage B AnalysisContext (Stage B does not receive transcript; only combined results)
    ctx_b = AnalysisContext(
        transcript=None,
        previous_analyses=stage_a_results,
        metadata={"run_id": run_dir.name, "stage": "stage_b", "source": "stage_a_aggregation"},
    )

    # Save Stage B context for debugging if requested
    if save_stage_b_context_debug:
        try:
            combined = ctx_b.get_combined_context(include_transcript=False)
            with open(run_dir / "intermediate" / "stage_b_context_debug.txt", "w") as f:
                f.write(combined)
        except Exception as e:
            logger.warning(f"Failed to save stage_b_context_debug: {e}")

    # Stage B
    _update_metadata_stage(metadata_path, "stage_b", {"status": "in_progress"})
    analyzers_b = stage_b if stage_b is not None else _default_stage_b_analyzers()
    stage_b_results = await run_stage_concurrently("stage_b", analyzers_b, ctx_b, run_dir, max_cc)
    _update_metadata_stage(
        metadata_path,
        "stage_b",
        {
            "status": "completed",
            "analyzers": list(stage_b_results.keys()),
            "total_tokens": _aggregate_tokens(stage_b_results),
        },
    )

    # Final Stage (Synthesis)
    _update_metadata_stage(metadata_path, "final", {"status": "in_progress"})
    # Merge Stage A and Stage B results for final context
    merged_results: Dict[str, AnalysisResult] = {}
    merged_results.update(stage_a_results)
    merged_results.update(stage_b_results)

    ctx_final = AnalysisContext(
        transcript=processed,
        previous_analyses=merged_results,
        metadata={"run_id": run_dir.name, "stage": "final", "source": "stage_a_b"},
    )
    final_analyzers = _default_final_analyzers()
    final_results = await run_stage_concurrently("final", final_analyzers, ctx_final, run_dir, max_cc)

    # Write final outputs to final/ directory
    final_dir = run_dir / "final"
    try:
        for name, res in final_results.items():
            out_path = final_dir / f"{name}.md"
            with open(out_path, "w") as f:
                f.write(res.raw_output or "")
    except Exception as e:
        logger.warning(f"Failed to write one or more final outputs: {e}")

    _update_metadata_stage(
        metadata_path,
        "final",
        {
            "status": "completed",
            "outputs": list(final_results.keys()),
        },
    )

    # Final simple executive summary
    exec_summary_path = run_dir / "final" / "executive_summary.md"
    try:
        with open(exec_summary_path, "w") as f:
            f.write(f"# Executive Summary\n\n")
            f.write(f"**Run ID:** {run_dir.name}\n")
            f.write(f"**Date:** {datetime.now().strftime('%B %d, %Y %H:%M')}\n\n")
            f.write("## Stage A\n\n")
            f.write(f"- Analyzers: {', '.join(stage_a_results.keys())}\n")
            f.write(f"- Total Tokens: {_aggregate_tokens(stage_a_results):,}\n\n")
            f.write("## Stage B\n\n")
            f.write(f"- Analyzers: {', '.join(stage_b_results.keys())}\n")
            f.write(f"- Total Tokens: {_aggregate_tokens(stage_b_results):,}\n\n")
    except Exception as e:
        logger.warning(f"Failed to write executive summary: {e}")

    # Totals and final status artifacts
    total_tokens = _aggregate_tokens(stage_a_results) + _aggregate_tokens(stage_b_results)
    cpu_time_seconds = sum([r.processing_time for r in stage_a_results.values()]) + sum(
        [r.processing_time for r in stage_b_results.values()]
    )
    end_ts = datetime.now()
    wall_clock_seconds = (end_ts - start_ts).total_seconds()

    summary_payload = {
        "run_id": run_dir.name,
        "output_dir": str(run_dir),
        "status": "completed",
        "stage_a": {"analyzers": list(stage_a_results.keys()), "tokens": _aggregate_tokens(stage_a_results)},
        "stage_b": {"analyzers": list(stage_b_results.keys()), "tokens": _aggregate_tokens(stage_b_results)},
        "total_tokens": total_tokens,
        "cpu_time_seconds": cpu_time_seconds,
        "wall_clock_seconds": wall_clock_seconds,
        "timestamps": {
            "start_time": start_ts.isoformat(),
            "end_time": end_ts.isoformat(),
        },
    }
    _finalize_metadata(
        metadata_path,
        {
            "total_analyzers": len(stage_a_results) + len(stage_b_results),
            "successful_analyzers": sum(1 for r in list(stage_a_results.values()) + list(stage_b_results.values()) if r.status.value == "completed"),
            "total_tokens": total_tokens,
            "cpu_time_seconds": cpu_time_seconds,
            "wall_clock_seconds": wall_clock_seconds,
        },
        status="completed",
    )

    # Write machine-readable final status and sentinel file
    try:
        with open(run_dir / "final_status.json", "w") as f:
            json.dump(summary_payload, f, indent=2)
        (run_dir / "COMPLETED").write_text("ok\n")
    except Exception as e:
        logger.warning(f"Failed to write final status artifacts: {e}")

    # Notify pipeline completion
    try:
        nm.pipeline_completed(run_dir.name, summary_payload)
    except Exception:
        pass

    return OrchestratorResult(
        stage_a_results=stage_a_results,
        stage_b_results=stage_b_results,
        total_tokens=total_tokens,
        total_time_seconds=cpu_time_seconds,
        run_dir=run_dir,
    )
