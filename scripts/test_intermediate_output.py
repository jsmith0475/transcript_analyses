#!/usr/bin/env python3
"""
Test script to demonstrate intermediate file output for each analyzer.
This script runs the full pipeline and saves intermediate results for each analyzer.
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

def run_pipeline_with_intermediate_output():
    """Run the full pipeline with intermediate output saving."""
    
    print("\n" + "="*80)
    print("  TRANSCRIPT ANALYSIS PIPELINE - INTERMEDIATE OUTPUT TEST")
    print("="*80)
    
    # Create output directory for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"output/intermediate_{timestamp}")
    
    print(f"\n📁 Intermediate files will be saved to: {output_dir}")
    print("="*80)
    
    # Load transcript
    print("\n📄 Loading sample transcript...")
    transcript_text = load_sample_transcript()
    print(f"✅ Loaded {len(transcript_text)} characters")
    
    # Create initial context with proper ProcessedTranscript structure
    # Parse the transcript to create segments
    segments = []
    speakers_dict = {}
    
    for i, line in enumerate(transcript_text.strip().split('\n')):
        line = line.strip()
        if not line:
            continue
            
        # Try to parse speaker format
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
                # Line with colon but not speaker format
                segments.append({
                    "segment_id": i,
                    "speaker": None,
                    "text": line
                })
        else:
            # Regular text line
            segments.append({
                "segment_id": i,
                "speaker": None,
                "text": line
            })
    
    # Create speaker objects
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
    
    # Create metadata
    metadata = TranscriptMetadata(
        filename="sample_transcript.md",
        word_count=len(transcript_text.split()),
        segment_count=len(segments),
        speaker_count=len(speakers)
    )
    
    # Create ProcessedTranscript
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
        metadata={"test_type": "intermediate_output", "timestamp": timestamp}
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
    print("Running 4 analyzers on raw transcript with intermediate output...\n")
    
    # Run Stage A analyzers
    for analyzer in stage_a_analyzers:
        print(f"📊 Running {analyzer.name.replace('_', ' ').title()}...")
        
        # Run with intermediate output saving
        result = analyzer.analyze_sync(context, save_intermediate=True, output_dir=output_dir)
        
        # Check if completed (the enum value is lowercase)
        if result.status.value == "completed":
            stage_a_results[analyzer.name] = result
            all_results.append(result)
            
            # Display summary
            tokens = result.token_usage.total_tokens if result.token_usage else 0
            print(f"✅ Success in {result.processing_time:.2f}s")
            print(f"📊 Tokens used: {tokens:,}")
            print(f"💾 Saved to: {output_dir}/stage_a/{analyzer.name}_{timestamp}.json")
            
            # Show sample insights
            if result.insights:
                print("  Sample insights:")
                for insight in result.insights[:2]:
                    text = insight.text[:100] + "..." if len(insight.text) > 100 else insight.text
                    print(f"    • {text}")
        else:
            print(f"❌ Failed: {result.error_message}")
        
        print()
    
    # Prepare Stage B context
    print("\n" + "="*80)
    print("  STAGE B PREPARATION")
    print("="*80)
    
    # Save Stage A context
    stage_a_context_path = output_dir / f"stage_a_context_{timestamp}.json"
    stage_a_context_path.parent.mkdir(parents=True, exist_ok=True)
    
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
    
    print(f"💾 Saved Stage A context to: {stage_a_context_path}")
    print(f"✅ Context created with {len(stage_a_results)} Stage A results")
    print(f"📊 Total insights: {stage_a_context_data['total_insights']}")
    print(f"📊 Total concepts: {stage_a_context_data['total_concepts']}")
    
    # Create Stage B context
    stage_b_context = AnalysisContext(
        transcript=None,  # Stage B doesn't get the transcript
        previous_analyses=stage_a_results,
        metadata={"source": "stage_a_aggregation", "stage": "stage_b", "timestamp": timestamp}
    )
    
    print("\n" + "="*80)
    print("  STAGE B ANALYSIS")
    print("="*80)
    print("Running 4 analyzers on Stage A context with intermediate output...\n")
    
    # Run Stage B analyzers
    stage_b_results = {}
    for analyzer in stage_b_analyzers:
        print(f"📊 Running {analyzer.name.replace('_', ' ').title()}...")
        
        # Run with intermediate output saving
        result = analyzer.analyze_sync(stage_b_context, save_intermediate=True, output_dir=output_dir)
        
        # Check if completed (the enum value is lowercase)
        if result.status.value == "completed":
            stage_b_results[analyzer.name] = result
            all_results.append(result)
            
            # Display summary
            tokens = result.token_usage.total_tokens if result.token_usage else 0
            print(f"✅ Success in {result.processing_time:.2f}s")
            print(f"📊 Tokens used: {tokens:,}")
            print(f"💾 Saved to: {output_dir}/stage_b/{analyzer.name}_{timestamp}.json")
            
            # Show analysis summary
            if result.structured_data:
                data_keys = list(result.structured_data.keys())[:3]
                print(f"  Analysis complete - extracted {len(result.structured_data)} data categories")
        else:
            print(f"❌ Failed: {result.error_message}")
        
        print()
    
    # Generate final summary
    print("\n" + "="*80)
    print("  FINAL SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in all_results if r.status.value == "completed")
    total_tokens = sum(r.token_usage.total_tokens if r.token_usage else 0 for r in all_results)
    total_time = sum(r.processing_time for r in all_results)
    
    print(f"✅ Successful analyzers: {successful}/{len(all_results)}")
    print(f"📊 Total tokens used: {total_tokens:,}")
    print(f"  • Stage A ({len(stage_a_results)}/{len(stage_a_analyzers)}): "
          f"{sum(r.token_usage.total_tokens if r.token_usage else 0 for r in stage_a_results.values()):,} tokens")
    print(f"  • Stage B ({len(stage_b_results)}/{len(stage_b_analyzers)}): "
          f"{sum(r.token_usage.total_tokens if r.token_usage else 0 for r in stage_b_results.values()):,} tokens")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"⚡ Average time per analyzer: {total_time/len(all_results):.2f} seconds")
    
    # List all generated files
    print("\n" + "="*80)
    print("  GENERATED FILES")
    print("="*80)
    
    print(f"\n📁 All intermediate files saved to: {output_dir}/")
    
    # Count files
    stage_a_files = list((output_dir / "stage_a").glob("*")) if (output_dir / "stage_a").exists() else []
    stage_b_files = list((output_dir / "stage_b").glob("*")) if (output_dir / "stage_b").exists() else []
    
    print(f"\n📊 File Summary:")
    print(f"  • Stage A: {len(stage_a_files)} files ({len(stage_a_files)//2} analyzers × 2 formats)")
    print(f"  • Stage B: {len(stage_b_files)} files ({len(stage_b_files)//2} analyzers × 2 formats)")
    print(f"  • Context: 1 file (stage_a_context.json)")
    print(f"  • Total: {len(stage_a_files) + len(stage_b_files) + 1} files")
    
    print("\n📂 Directory Structure:")
    print(f"  {output_dir}/")
    print(f"  ├── stage_a/")
    for f in sorted(stage_a_files)[:4]:  # Show first 4 files
        print(f"  │   ├── {f.name}")
    if len(stage_a_files) > 4:
        print(f"  │   └── ... ({len(stage_a_files)-4} more files)")
    print(f"  ├── stage_b/")
    for f in sorted(stage_b_files)[:4]:  # Show first 4 files
        print(f"  │   ├── {f.name}")
    if len(stage_b_files) > 4:
        print(f"  │   └── ... ({len(stage_b_files)-4} more files)")
    print(f"  └── stage_a_context_{timestamp}.json")
    
    # Cost estimate
    cost_per_1k = 0.01  # Estimated cost per 1k tokens
    estimated_cost = (total_tokens / 1000) * cost_per_1k
    print(f"\n💰 Estimated API cost: ${estimated_cost:.2f}")
    
    print("\n" + "="*80)
    print("  TEST COMPLETE")
    print("="*80)
    print(f"✅ All intermediate results saved to {output_dir}/")
    print("📊 Each analyzer generated both JSON and Markdown output files")
    print("🔍 Review the files to see detailed analysis results for each stage")
    
    return output_dir

if __name__ == "__main__":
    try:
        output_dir = run_pipeline_with_intermediate_output()
        print(f"\n✨ Success! Check {output_dir}/ for all intermediate files.")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
