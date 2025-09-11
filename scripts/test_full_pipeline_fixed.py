#!/usr/bin/env python3
"""
Fixed test script for the full pipeline with proper Stage B context passing.
Ensures Stage B analyzers receive the aggregated Stage A results.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.models import (
    AnalysisContext, 
    ProcessedTranscript,
    TranscriptSegment,
    Speaker,
    TranscriptMetadata,
    AnalysisResult
)
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
from src.analyzers.stage_a.premises_assertions import PremisesAssertionsAnalyzer
from src.analyzers.stage_a.postulate_theorem import PostulateTheoremAnalyzer
from src.analyzers.stage_b.competing_hypotheses import CompetingHypothesesAnalyzer
from src.analyzers.stage_b.first_principles import FirstPrinciplesAnalyzer
from src.analyzers.stage_b.determining_factors import DeterminingFactorsAnalyzer
from src.analyzers.stage_b.patentability import PatentabilityAnalyzer
from src.app.notify import get_notification_manager

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")

def load_sample_transcript() -> str:
    """Load the sample transcript."""
    sample_path = Path("input sample transcripts/sample1.md")
    if not sample_path.exists():
        # Fallback to a simple test transcript
        return """
        Speaker 1: We have 20 years of scientific data sitting in our systems that we've never monetized.
        
        Speaker 2: That's interesting. What kind of data are we talking about?
        
        Speaker 1: Lab results, experimental data, all stored in Chromeleon and our LIMS systems. 
        It's a goldmine for AI applications if we can figure out how to use it properly.
        
        Speaker 2: Have we considered the privacy and regulatory implications?
        
        Speaker 1: That's the first thing we need to address. But the opportunity is massive - 
        we could create entirely new revenue streams from data we already have.
        """
    
    with open(sample_path, 'r') as f:
        return f.read()

def create_run_metadata(run_dir: Path, config: Dict[str, Any]) -> Path:
    """Create and save run metadata file."""
    metadata_path = run_dir / "metadata.json"
    
    metadata = {
        "run_id": run_dir.name,
        "start_time": datetime.now().isoformat(),
        "configuration": config,
        "status": "in_progress",
        "stages": {
            "stage_a": {"status": "pending", "analyzers": []},
            "stage_b": {"status": "pending", "analyzers": []},
            "final": {"status": "pending", "outputs": []}
        }
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return metadata_path

def update_run_metadata(metadata_path: Path, updates: Dict[str, Any]):
    """Update the run metadata file."""
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Deep merge updates
    for key, value in updates.items():
        if isinstance(value, dict) and key in metadata and isinstance(metadata[key], dict):
            metadata[key].update(value)
        else:
            metadata[key] = value
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def run_fixed_pipeline():
    """Run the pipeline with fixed Stage B context passing."""
    
    print("\n" + "="*80)
    print("  TRANSCRIPT ANALYSIS PIPELINE - FIXED CONTEXT PASSING")
    print("="*80)
    
    # Create run-specific directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"output/runs/run_{timestamp}")
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (run_dir / "intermediate" / "stage_a").mkdir(parents=True, exist_ok=True)
    (run_dir / "intermediate" / "stage_b").mkdir(parents=True, exist_ok=True)
    (run_dir / "final").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Run directory created: {run_dir}")
    print("="*80)
    # Proactive notification: pipeline started (best-effort)
    try:
        get_notification_manager().pipeline_started(run_dir.name, {"output_dir": str(run_dir), "mechanism": "cli_sync"})
    except Exception:
        pass
    
    # Create run metadata
    config = {
        "model": "gpt-5",
        "temperature": 1.0,
        "save_intermediate": True,
        "stages": ["stage_a", "stage_b", "final"]
    }
    metadata_path = create_run_metadata(run_dir, config)
    
    # Load transcript
    print("\n📄 Loading sample transcript...")
    transcript_text = load_sample_transcript()
    print(f"✅ Loaded {len(transcript_text)} characters")
    
    # Parse transcript to create ProcessedTranscript
    segments = []
    speakers_dict = {}
    
    for i, line in enumerate(transcript_text.strip().split('\n')):
        line = line.strip()
        if not line:
            continue
            
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[0].startswith('Speaker'):
                speaker = parts[0].strip()
                text = parts[1].strip()
                
                if speaker not in speakers_dict:
                    speakers_dict[speaker] = {"count": 0, "words": 0}
                speakers_dict[speaker]["count"] += 1
                speakers_dict[speaker]["words"] += len(text.split())
                
                segments.append({
                    "segment_id": i,
                    "speaker": speaker,
                    "text": text
                })
            else:
                segments.append({
                    "segment_id": i,
                    "speaker": None,
                    "text": line
                })
        else:
            segments.append({
                "segment_id": i,
                "speaker": None,
                "text": line
            })
    
    # Create ProcessedTranscript
    speakers = [
        Speaker(
            id=speaker_name,
            name=speaker_name,
            segments_count=info["count"],
            total_words=info["words"]
        )
        for speaker_name, info in speakers_dict.items()
    ]
    
    metadata = TranscriptMetadata(
        filename="sample_transcript.md",
        word_count=len(transcript_text.split()),
        segment_count=len(segments),
        speaker_count=len(speakers)
    )
    
    transcript = ProcessedTranscript(
        segments=[TranscriptSegment(**seg) for seg in segments if seg["text"]],
        speakers=speakers,
        metadata=metadata,
        raw_text=transcript_text,
        has_speaker_names=bool(speakers)
    )
    
    # Create initial context for Stage A
    context = AnalysisContext(
        transcript=transcript,
        previous_analyses={},
        metadata={"run_id": run_dir.name, "timestamp": timestamp}
    )
    
    # Initialize analyzers
    stage_a_analyzers = [
        SayMeansAnalyzer(),
        PerspectivePerceptionAnalyzer(),
        PremisesAssertionsAnalyzer(),
        PostulateTheoremAnalyzer()
    ]
    
    stage_b_analyzers = [
        CompetingHypothesesAnalyzer(),
        FirstPrinciplesAnalyzer(),
        DeterminingFactorsAnalyzer(),
        PatentabilityAnalyzer()
    ]
    
    # Track results
    all_results = []
    stage_a_results = {}
    
    print("\n" + "="*80)
    print("  STAGE A ANALYSIS")
    print("="*80)
    print("Running 4 analyzers on raw transcript...\n")
    
    # Update metadata
    update_run_metadata(metadata_path, {
        "stages": {
            "stage_a": {"status": "in_progress", "start_time": datetime.now().isoformat()}
        }
    })
    
    # Run Stage A analyzers
    for analyzer in stage_a_analyzers:
        print(f"📊 Running {analyzer.name.replace('_', ' ').title()}...")
        
        try:
            # Run with organized output directory
            result = analyzer.analyze_sync(context, save_intermediate=True, output_dir=run_dir)
            
            if result.status.value == "completed":
                stage_a_results[analyzer.name] = result
                all_results.append(result)
                
                # Display summary
                tokens = result.token_usage.total_tokens if result.token_usage else 0
                print(f"✅ Success in {result.processing_time:.2f}s")
                print(f"📊 Tokens used: {tokens:,}")
                print(f"💾 Saved to: {run_dir}/intermediate/stage_a/{analyzer.name}.json")
                
                # Show sample insights
                if result.insights:
                    print("  Sample insights:")
                    for insight in result.insights[:2]:
                        text = insight.text[:80] + "..." if len(insight.text) > 80 else insight.text
                        print(f"    • {text}")
            else:
                print(f"❌ Failed: {result.error_message}")
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Stage A analyzer {analyzer.name} failed: {e}")
        
        print()
    
    # Update metadata for Stage A completion
    update_run_metadata(metadata_path, {
        "stages": {
            "stage_a": {
                "status": "completed",
                "end_time": datetime.now().isoformat(),
                "analyzers": list(stage_a_results.keys()),
                "total_tokens": sum(r.token_usage.total_tokens if r.token_usage else 0 
                                  for r in stage_a_results.values())
            }
        }
    })
    
    print("\n" + "="*80)
    print("  STAGE B ANALYSIS")
    print("="*80)
    print("Running 4 analyzers on Stage A results...\n")
    
    # CRITICAL FIX: Ensure Stage A results are properly passed to Stage B
    # Create a new context with Stage A results in previous_analyses
    stage_b_context = AnalysisContext(
        transcript=None,  # Stage B doesn't get the transcript
        previous_analyses=stage_a_results,  # Pass the actual AnalysisResult objects
        metadata={
            "source": "stage_a_aggregation",
            "stage": "stage_b",
            "run_id": run_dir.name,
            "stage_a_analyzers": list(stage_a_results.keys()),
            "total_stage_a_insights": sum(len(r.insights) for r in stage_a_results.values()),
            "total_stage_a_concepts": sum(len(r.concepts) for r in stage_a_results.values())
        }
    )
    
    # Debug: Verify context is not empty
    combined_context = stage_b_context.get_combined_context(include_transcript=False)
    if combined_context:
        print(f"✅ Stage B context prepared: {len(combined_context)} characters")
        print(f"   Contains results from: {', '.join(stage_a_results.keys())}")
        
        # Save the context for debugging
        context_debug_path = run_dir / "intermediate" / "stage_b_context_debug.txt"
        with open(context_debug_path, 'w') as f:
            f.write("=== STAGE B CONTEXT (as passed to analyzers) ===\n\n")
            f.write(combined_context)
        print(f"💾 Context saved for debugging: {context_debug_path}")
    else:
        print("⚠️  WARNING: Stage B context appears to be empty!")
    
    print()
    
    # Update metadata
    update_run_metadata(metadata_path, {
        "stages": {
            "stage_b": {"status": "in_progress", "start_time": datetime.now().isoformat()}
        }
    })
    
    # Run Stage B analyzers
    stage_b_results = {}
    for analyzer in stage_b_analyzers:
        print(f"📊 Running {analyzer.name.replace('_', ' ').title()}...")
        
        try:
            result = analyzer.analyze_sync(stage_b_context, save_intermediate=True, output_dir=run_dir)
            
            if result.status.value == "completed":
                stage_b_results[analyzer.name] = result
                all_results.append(result)
                
                tokens = result.token_usage.total_tokens if result.token_usage else 0
                print(f"✅ Success in {result.processing_time:.2f}s")
                print(f"📊 Tokens used: {tokens:,}")
                print(f"💾 Saved to: {run_dir}/intermediate/stage_b/{analyzer.name}.json")
                
                # Check if token usage is suspiciously low
                if tokens < 1000:
                    print(f"⚠️  WARNING: Low token usage ({tokens}) may indicate context issue")
                
                if result.structured_data:
                    data_keys = list(result.structured_data.keys())[:3]
                    print(f"  Extracted data categories: {', '.join(data_keys)}")
                
                if result.insights:
                    print(f"  Generated {len(result.insights)} insights")
            else:
                print(f"❌ Failed: {result.error_message}")
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Stage B analyzer {analyzer.name} failed: {e}")
        
        print()
    
    # Update metadata for Stage B completion
    update_run_metadata(metadata_path, {
        "stages": {
            "stage_b": {
                "status": "completed",
                "end_time": datetime.now().isoformat(),
                "analyzers": list(stage_b_results.keys()),
                "total_tokens": sum(r.token_usage.total_tokens if r.token_usage else 0 
                                  for r in stage_b_results.values())
            }
        }
    })
    
    # Generate summary report
    print("\n" + "="*80)
    print("  GENERATING SUMMARY REPORT")
    print("="*80)
    
    # Create executive summary
    exec_summary_path = run_dir / "final" / "executive_summary.md"
    with open(exec_summary_path, 'w') as f:
        f.write(f"# Executive Summary\n\n")
        f.write(f"**Run ID:** {run_dir.name}\n")
        f.write(f"**Date:** {datetime.now().strftime('%B %d, %Y %H:%M')}\n\n")
        
        # Stage A Summary
        f.write("## Stage A - Transcript Analysis\n\n")
        stage_a_tokens = sum(r.token_usage.total_tokens if r.token_usage else 0 
                           for r in stage_a_results.values())
        f.write(f"- **Analyzers Run:** {len(stage_a_results)}\n")
        f.write(f"- **Total Tokens:** {stage_a_tokens:,}\n")
        f.write(f"- **Total Insights:** {sum(len(r.insights) for r in stage_a_results.values())}\n\n")
        
        for name, result in stage_a_results.items():
            if result.insights:
                f.write(f"### {name.replace('_', ' ').title()}\n")
                for insight in result.insights[:3]:
                    f.write(f"- {insight.text}\n")
                f.write("\n")
        
        # Stage B Summary
        f.write("## Stage B - Meta-Analysis\n\n")
        stage_b_tokens = sum(r.token_usage.total_tokens if r.token_usage else 0 
                           for r in stage_b_results.values())
        f.write(f"- **Analyzers Run:** {len(stage_b_results)}\n")
        f.write(f"- **Total Tokens:** {stage_b_tokens:,}\n")
        f.write(f"- **Total Insights:** {sum(len(r.insights) for r in stage_b_results.values())}\n\n")
        
        if stage_b_tokens < 4000:  # Expected minimum for Stage B
            f.write("⚠️ **Warning:** Stage B token usage is lower than expected, ")
            f.write("which may indicate the Stage A results were not properly passed.\n\n")
        
        for name, result in stage_b_results.items():
            if result.insights:
                f.write(f"### {name.replace('_', ' ').title()}\n")
                for insight in result.insights[:3]:
                    f.write(f"- {insight.text}\n")
                f.write("\n")
    
    print(f"📝 Executive summary saved to: {exec_summary_path}")
    
    # Final metadata update
    total_tokens = sum(r.token_usage.total_tokens if r.token_usage else 0 for r in all_results)
    total_time = sum(r.processing_time for r in all_results)
    
    update_run_metadata(metadata_path, {
        "end_time": datetime.now().isoformat(),
        "status": "completed",
        "summary": {
            "total_analyzers": len(all_results),
            "successful_analyzers": sum(1 for r in all_results if r.status.value == "completed"),
            "total_tokens": total_tokens,
            "total_time_seconds": total_time,
            "estimated_cost": (total_tokens / 1000) * 0.01,
            "stage_b_context_size": len(combined_context) if combined_context else 0
        }
    })
    
    # Final summary
    print("\n" + "="*80)
    print("  FINAL SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in all_results if r.status.value == "completed")
    print(f"✅ Successful analyzers: {successful}/{len(all_results)}")
    print(f"📊 Total tokens used: {total_tokens:,}")
    print(f"  - Stage A: {stage_a_tokens:,} tokens")
    print(f"  - Stage B: {stage_b_tokens:,} tokens")
    
    if stage_b_tokens < 4000:
        print(f"⚠️  Stage B token usage is suspiciously low!")
        print(f"   Expected: 4,000-16,000 tokens")
        print(f"   Actual: {stage_b_tokens:,} tokens")
        print(f"   This suggests Stage A results may not be reaching Stage B properly")
    
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"💰 Estimated cost: ${(total_tokens / 1000) * 0.01:.2f}")
    
    print(f"\n📁 All files saved to: {run_dir}/")
    print("\n" + "="*80)
    print("  PIPELINE COMPLETE")
    print("="*80)
    # Proactive notification: pipeline completed (best-effort)
    try:
        summary_payload = {
            "output_dir": str(run_dir),
            "status": "completed",
            "stage_a": {"analyzers": list(stage_a_results.keys()), "tokens": stage_a_tokens},
            "stage_b": {"analyzers": list(stage_b_results.keys()), "tokens": stage_b_tokens},
            "total_tokens": total_tokens,
            "wall_clock_seconds": total_time,
        }
        get_notification_manager().pipeline_completed(run_dir.name, summary_payload)
    except Exception:
        pass
    
    return run_dir

if __name__ == "__main__":
    try:
        run_dir = run_fixed_pipeline()
        print(f"\n✨ Success! All files saved to: {run_dir}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        # Proactive notification: pipeline error (best-effort)
        try:
            get_notification_manager().pipeline_error("cli_run", {"message": str(e)}, meta={"output_dir": None})
        except Exception:
            pass
        import traceback
        traceback.print_exc()
        sys.exit(1)
