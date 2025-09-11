#!/usr/bin/env python3
"""
Test script for Stage B analyzers.

This script:
1. Runs all Stage A analyzers on a sample transcript
2. Aggregates Stage A results into context
3. Tests each Stage B analyzer with the context
4. Saves outputs for inspection
"""

import json
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import AnalysisContext
from src.transcript_processor import get_transcript_processor
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
from src.analyzers.stage_a.premises_assertions import PremisesAssertionsAnalyzer
from src.analyzers.stage_a.postulate_theorem import PostulateTheoremAnalyzer
from src.analyzers.stage_b.competing_hypotheses import CompetingHypothesesAnalyzer
from src.analyzers.stage_b.first_principles import FirstPrinciplesAnalyzer
from src.analyzers.stage_b.determining_factors import DeterminingFactorsAnalyzer
from src.analyzers.stage_b.patentability import PatentabilityAnalyzer


def main():
    """Test Stage B analyzers with Stage A context."""
    
    # Load sample transcript
    sample_file = Path("input sample transcripts/sample1.md")
    if not sample_file.exists():
        print(f"Error: Sample file not found at {sample_file}")
        return 1
    
    with open(sample_file, "r") as f:
        transcript_text = f.read()
    
    print(f"Loaded transcript: {len(transcript_text)} characters")
    print("=" * 60)
    
    # Process transcript
    processor = get_transcript_processor()
    processed = processor.process(transcript_text, filename=str(sample_file))
    
    # Create analysis context for Stage A
    ctx = AnalysisContext(
        transcript=processed,
        metadata={"source": "test_stage_b.py"}
    )
    
    # Run Stage A analyzers
    print("\n🔄 Running Stage A analyzers...")
    stage_a_results = {}
    stage_a_analyzers = [
        ("say_means", SayMeansAnalyzer),
        ("perspective_perception", PerspectivePerceptionAnalyzer),
        ("premises_assertions", PremisesAssertionsAnalyzer),
        ("postulate_theorem", PostulateTheoremAnalyzer),
    ]
    
    total_stage_a_tokens = 0
    
    for name, analyzer_class in stage_a_analyzers:
        print(f"\n  Running {name}...")
        start_time = time.time()
        
        analyzer = analyzer_class()
        result = analyzer.analyze_sync(ctx)
        
        elapsed = time.time() - start_time
        
        if result.status.value == "success":
            print(f"    ✅ Success in {elapsed:.2f}s")
            if result.token_usage:
                print(f"    📊 Tokens: {result.token_usage.total_tokens}")
                total_stage_a_tokens += result.token_usage.total_tokens
            
            # Store result for Stage B
            stage_a_results[name] = {
                "status": result.status.value,
                "processing_time": elapsed,
                "token_usage": result.token_usage.dict() if result.token_usage else None,
                "raw_output": result.raw_output,
                "structured_data": result.structured_data,
                "insights": [i.dict() for i in result.insights],
                "concepts": [c.dict() for c in result.concepts],
            }
        else:
            print(f"    ❌ Failed: {result.error_message}")
            stage_a_results[name] = {
                "status": "error",
                "error_message": result.error_message
            }
    
    print(f"\n📊 Stage A Total Tokens: {total_stage_a_tokens}")
    
    # Create Stage B context
    print("\n🔄 Creating Stage B context...")
    stage_b_context = {
        "stage_a_results": stage_a_results,
        "metadata": {
            "total_concepts": sum(len(r.get("concepts", [])) for r in stage_a_results.values()),
            "total_insights": sum(len(r.get("insights", [])) for r in stage_a_results.values()),
            "processing_time": sum(r.get("processing_time", 0) for r in stage_a_results.values()),
            "analyzers_run": list(stage_a_results.keys())
        }
    }
    
    # Convert to string for Stage B input
    context_str = json.dumps(stage_b_context, indent=2)
    print(f"  Context size: {len(context_str)} characters")
    
    # Save Stage A context for inspection
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    context_file = output_dir / "stage_a_context.json"
    with open(context_file, "w") as f:
        json.dump(stage_b_context, f, indent=2)
    print(f"  Saved context to {context_file}")
    
    # Create Stage B analysis context
    # For Stage B, we need to pass the context as a ProcessedTranscript
    from src.models import ProcessedTranscript, TranscriptSegment, Speaker, TranscriptMetadata
    
    # Create a ProcessedTranscript with the context as the content
    processed_context = ProcessedTranscript(
        raw_text=context_str,
        segments=[TranscriptSegment(
            segment_id=1,
            text=context_str,
            speaker=None
        )],
        speakers=[],  # No speakers for context
        metadata=TranscriptMetadata(
            title="Stage A Context",
            word_count=len(context_str.split()),
            segment_count=1,
            speaker_count=0
        )
    )
    
    stage_b_ctx = AnalysisContext(
        transcript=processed_context,
        metadata={"source": "stage_a_aggregation", "stage": "stage_b"}
    )
    
    # Run Stage B analyzers
    print("\n🔄 Running Stage B analyzers...")
    stage_b_analyzers = [
        ("competing_hypotheses", CompetingHypothesesAnalyzer),
        ("first_principles", FirstPrinciplesAnalyzer),
        ("determining_factors", DeterminingFactorsAnalyzer),
        ("patentability", PatentabilityAnalyzer),
    ]
    
    total_stage_b_tokens = 0
    stage_b_results = {}
    
    for name, analyzer_class in stage_b_analyzers:
        print(f"\n  Running {name}...")
        start_time = time.time()
        
        try:
            analyzer = analyzer_class()
            result = analyzer.analyze_sync(stage_b_ctx)
            
            elapsed = time.time() - start_time
            
            if result.status.value == "success":
                print(f"    ✅ Success in {elapsed:.2f}s")
                if result.token_usage:
                    print(f"    📊 Tokens: {result.token_usage.total_tokens}")
                    total_stage_b_tokens += result.token_usage.total_tokens
                
                # Save individual result
                output_file = output_dir / f"stage_b_{name}.json"
                with open(output_file, "w") as f:
                    json.dump({
                        "analyzer": name,
                        "status": result.status.value,
                        "processing_time": elapsed,
                        "token_usage": result.token_usage.dict() if result.token_usage else None,
                        "structured_data": result.structured_data,
                        "insights": [i.dict() for i in result.insights],
                        "concepts": [c.dict() for c in result.concepts],
                    }, f, indent=2)
                print(f"    💾 Saved to {output_file}")
                
                # Store for summary
                stage_b_results[name] = {
                    "status": "success",
                    "processing_time": elapsed,
                    "tokens": result.token_usage.total_tokens if result.token_usage else 0
                }
                
                # Print sample of structured data
                if result.structured_data:
                    print(f"    📝 Sample output:")
                    for key in list(result.structured_data.keys())[:3]:
                        value = result.structured_data[key]
                        if isinstance(value, list) and value:
                            print(f"       - {key}: {len(value)} items")
                        elif isinstance(value, dict):
                            print(f"       - {key}: {len(value)} entries")
                        else:
                            print(f"       - {key}: {str(value)[:50]}...")
            else:
                print(f"    ❌ Failed: {result.error_message}")
                stage_b_results[name] = {
                    "status": "error",
                    "error": result.error_message
                }
                
        except Exception as e:
            print(f"    ❌ Exception: {str(e)}")
            stage_b_results[name] = {
                "status": "error",
                "error": str(e)
            }
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    print(f"\nStage A:")
    print(f"  Total tokens: {total_stage_a_tokens}")
    print(f"  Analyzers run: {len(stage_a_results)}")
    
    print(f"\nStage B:")
    print(f"  Total tokens: {total_stage_b_tokens}")
    print(f"  Successful: {sum(1 for r in stage_b_results.values() if r['status'] == 'success')}/{len(stage_b_results)}")
    
    print(f"\nTotal tokens used: {total_stage_a_tokens + total_stage_b_tokens}")
    
    # Save complete results
    complete_results = {
        "stage_a": stage_a_results,
        "stage_b": stage_b_results,
        "totals": {
            "stage_a_tokens": total_stage_a_tokens,
            "stage_b_tokens": total_stage_b_tokens,
            "total_tokens": total_stage_a_tokens + total_stage_b_tokens
        }
    }
    
    results_file = output_dir / "complete_pipeline_results.json"
    with open(results_file, "w") as f:
        json.dump(complete_results, f, indent=2)
    
    print(f"\n💾 Complete results saved to {results_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
