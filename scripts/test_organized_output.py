#!/usr/bin/env python3
"""
Test script demonstrating organized output directory structure.
Each run gets its own directory with all related files organized within.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.models import AnalysisContext, ProcessedTranscript
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
from src.analyzers.stage_a.premises_assertions import PremisesAssertionsAnalyzer
from src.analyzers.stage_a.postulate_theorem import PostulateTheoremAnalyzer
from src.analyzers.stage_b.competing_hypotheses import CompetingHypothesesAnalyzer
from src.analyzers.stage_b.first_principles import FirstPrinciplesAnalyzer
from src.analyzers.stage_b.determining_factors import DeterminingFactorsAnalyzer
from src.analyzers.stage_b.patentability import PatentabilityAnalyzer

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
    
    metadata.update(updates)
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def run_organized_pipeline():
    """Run the pipeline with organized output structure."""
    
    print("\n" + "="*80)
    print("  TRANSCRIPT ANALYSIS PIPELINE - ORGANIZED OUTPUT")
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
    print("📂 Directory structure:")
    print(f"  {run_dir.name}/")
    print(f"  ├── metadata.json")
    print(f"  ├── intermediate/")
    print(f"  │   ├── stage_a/")
    print(f"  │   └── stage_b/")
    print(f"  ├── final/")
    print(f"  └── logs/")
    print("="*80)
    
    # Create run metadata
    config = {
        "model": "gpt-5",
        "temperature": 0.7,
        "save_intermediate": True,
        "stages": ["stage_a", "stage_b"]
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
    from src.models import TranscriptSegment, Speaker, TranscriptMetadata
    
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
            "stage_a": {"status": "in_progress", "start_time": datetime.now().isoformat()},
            "stage_b": {"status": "pending", "analyzers": []},
            "final": {"status": "pending", "outputs": []}
        }
    })
    
    # Run Stage A analyzers
    for analyzer in stage_a_analyzers:
        print(f"📊 Running {analyzer.name.replace('_', ' ').title()}...")
        
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
        
        print()
    
    # Save Stage A context
    stage_a_context_path = run_dir / "intermediate" / "stage_a_context.json"
    stage_a_context_data = {
        "timestamp": timestamp,
        "analyzers_run": list(stage_a_results.keys()),
        "total_insights": sum(len(r.insights) for r in stage_a_results.values()),
        "total_concepts": sum(len(r.concepts) for r in stage_a_results.values()),
        "results": {}
    }
    
    for name, result in stage_a_results.items():
        stage_a_context_data["results"][name] = {
            "insights": [{"text": i.text, "source": i.source_analyzer} for i in result.insights],
            "concepts": [{"name": c.name, "description": c.description} for c in result.concepts],
            "structured_data": result.structured_data
        }
    
    with open(stage_a_context_path, 'w') as f:
        json.dump(stage_a_context_data, f, indent=2)
    
    # Update metadata for Stage A completion
    update_run_metadata(metadata_path, {
        "stages": {
            "stage_a": {
                "status": "completed",
                "end_time": datetime.now().isoformat(),
                "analyzers": list(stage_a_results.keys()),
                "total_tokens": sum(r.token_usage.total_tokens if r.token_usage else 0 
                                  for r in stage_a_results.values())
            },
            "stage_b": {"status": "in_progress", "start_time": datetime.now().isoformat()},
            "final": {"status": "pending", "outputs": []}
        }
    })
    
    print("\n" + "="*80)
    print("  STAGE B ANALYSIS")
    print("="*80)
    print("Running 4 analyzers on Stage A context...\n")
    
    # Create Stage B context
    stage_b_context = AnalysisContext(
        transcript=None,  # Stage B doesn't get the transcript
        previous_analyses=stage_a_results,
        metadata={"source": "stage_a_aggregation", "stage": "stage_b", "run_id": run_dir.name}
    )
    
    # Run Stage B analyzers
    stage_b_results = {}
    for analyzer in stage_b_analyzers:
        print(f"📊 Running {analyzer.name.replace('_', ' ').title()}...")
        
        result = analyzer.analyze_sync(stage_b_context, save_intermediate=True, output_dir=run_dir)
        
        if result.status.value == "completed":
            stage_b_results[analyzer.name] = result
            all_results.append(result)
            
            tokens = result.token_usage.total_tokens if result.token_usage else 0
            print(f"✅ Success in {result.processing_time:.2f}s")
            print(f"📊 Tokens used: {tokens:,}")
            print(f"💾 Saved to: {run_dir}/intermediate/stage_b/{analyzer.name}.json")
            
            if result.structured_data:
                print(f"  Analysis complete - extracted {len(result.structured_data)} data categories")
        else:
            print(f"❌ Failed: {result.error_message}")
        
        print()
    
    # Update metadata for Stage B completion
    update_run_metadata(metadata_path, {
        "stages": {
            "stage_a": metadata["stages"]["stage_a"],  # Keep existing
            "stage_b": {
                "status": "completed",
                "end_time": datetime.now().isoformat(),
                "analyzers": list(stage_b_results.keys()),
                "total_tokens": sum(r.token_usage.total_tokens if r.token_usage else 0 
                                  for r in stage_b_results.values())
            },
            "final": {"status": "pending", "outputs": []}
        }
    })
    
    # Generate final outputs
    print("\n" + "="*80)
    print("  GENERATING FINAL OUTPUTS")
    print("="*80)
    
    # Create executive summary
    exec_summary_path = run_dir / "final" / "executive_summary.md"
    with open(exec_summary_path, 'w') as f:
        f.write(f"# Executive Summary\n\n")
        f.write(f"**Run ID:** {run_dir.name}\n")
        f.write(f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n\n")
        f.write("## Key Findings\n\n")
        
        # Top insights from each analyzer
        for name, result in {**stage_a_results, **stage_b_results}.items():
            if result.insights:
                f.write(f"### {name.replace('_', ' ').title()}\n")
                for insight in result.insights[:2]:
                    f.write(f"- {insight.text}\n")
                f.write("\n")
    
    print(f"📝 Executive summary saved to: {run_dir}/final/executive_summary.md")
    
    # Create full report
    full_report_path = run_dir / "final" / "full_report.json"
    with open(full_report_path, 'w') as f:
        json.dump({
            "run_id": run_dir.name,
            "timestamp": timestamp,
            "stage_a_results": {
                name: {
                    "status": result.status.value,
                    "processing_time": result.processing_time,
                    "tokens": result.token_usage.total_tokens if result.token_usage else 0,
                    "insights_count": len(result.insights),
                    "concepts_count": len(result.concepts)
                }
                for name, result in stage_a_results.items()
            },
            "stage_b_results": {
                name: {
                    "status": result.status.value,
                    "processing_time": result.processing_time,
                    "tokens": result.token_usage.total_tokens if result.token_usage else 0,
                    "insights_count": len(result.insights),
                    "concepts_count": len(result.concepts)
                }
                for name, result in stage_b_results.items()
            }
        }, f, indent=2)
    
    print(f"📊 Full report saved to: {run_dir}/final/full_report.json")
    
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
            "estimated_cost": (total_tokens / 1000) * 0.01
        }
    })
    
    # Final summary
    print("\n" + "="*80)
    print("  FINAL SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in all_results if r.status.value == "completed")
    print(f"✅ Successful analyzers: {successful}/{len(all_results)}")
    print(f"📊 Total tokens used: {total_tokens:,}")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"💰 Estimated cost: ${(total_tokens / 1000) * 0.01:.2f}")
    
    print(f"\n📁 All files saved to: {run_dir}/")
    print("\n📂 Final directory structure:")
    print(f"  {run_dir.name}/")
    print(f"  ├── metadata.json (run information)")
    print(f"  ├── intermediate/")
    print(f"  │   ├── stage_a/ ({len(stage_a_results)*2} files)")
    print(f"  │   ├── stage_b/ ({len(stage_b_results)*2} files)")
    print(f"  │   └── stage_a_context.json")
    print(f"  └── final/")
    print(f"      ├── executive_summary.md")
    print(f"      └── full_report.json")
    
    print("\n" + "="*80)
    print("  PIPELINE COMPLETE")
    print("="*80)
    print(f"✅ Run completed successfully: {run_dir.name}")
    print("📊 All results organized in a single run directory")
    print("🔍 Review metadata.json for complete run information")
    
    return run_dir

if __name__ == "__main__":
    try:
        run_dir = run_organized_pipeline()
        print(f"\n✨ Success! All files saved to: {run_dir}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
