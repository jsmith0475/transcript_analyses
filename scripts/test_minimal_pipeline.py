#!/usr/bin/env python3
"""
Minimal pipeline test script.

Runs 2 Stage A analyzers and 1 Stage B analyzer to test the complete pipeline
with minimal resource usage. Saves comprehensive results to output files.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import AnalysisContext, ProcessedTranscript, TranscriptSegment, TranscriptMetadata, AnalyzerStatus
from src.transcript_processor import get_transcript_processor
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
from src.analyzers.stage_b.competing_hypotheses import CompetingHypothesesAnalyzer


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_status(emoji, text):
    """Print a status message with emoji."""
    print(f"{emoji} {text}")


def save_results(results, output_dir):
    """Save results to JSON and markdown files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON results
    json_file = output_dir / f"minimal_pipeline_results_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print_status("💾", f"Saved JSON results to {json_file}")
    
    # Generate markdown report
    md_file = output_dir / f"minimal_pipeline_report_{timestamp}.md"
    with open(md_file, "w") as f:
        f.write(generate_markdown_report(results))
    print_status("📝", f"Saved markdown report to {md_file}")
    
    return json_file, md_file


def generate_markdown_report(results):
    """Generate a human-readable markdown report."""
    lines = []
    
    # Header
    lines.append(f"# Minimal Pipeline Test Report")
    lines.append(f"\n**Generated:** {results['timestamp']}")
    lines.append(f"\n**Transcript:** {results['transcript_info']['file']}")
    lines.append(f"- Size: {results['transcript_info']['size']:,} characters")
    lines.append(f"- Segments: {results['transcript_info']['segments']}")
    
    # Summary
    lines.append(f"\n## Summary")
    summary = results['summary']
    lines.append(f"- **Total Tokens Used:** {summary['total_tokens']:,}")
    lines.append(f"- **Total Processing Time:** {summary['total_time']:.2f} seconds")
    lines.append(f"- **Success Rate:** {summary['success_rate']}")
    lines.append(f"- **Stage A Tokens:** {summary['stage_a_tokens']:,}")
    lines.append(f"- **Stage B Tokens:** {summary['stage_b_tokens']:,}")
    
    # Stage A Results
    lines.append(f"\n## Stage A Results")
    
    for analyzer_name, result in results['stage_a_results'].items():
        lines.append(f"\n### {analyzer_name.replace('_', ' ').title()}")
        lines.append(f"- **Status:** {result['status']}")
        lines.append(f"- **Processing Time:** {result['processing_time']:.2f}s")
        if result.get('token_usage'):
            lines.append(f"- **Tokens:** {result['token_usage']['total_tokens']:,}")
        
        if result.get('insights'):
            lines.append(f"\n**Key Insights ({len(result['insights'])} total):**")
            for insight in result['insights'][:3]:  # Top 3 insights
                lines.append(f"- {insight['text']}")
        
        if result.get('structured_data'):
            lines.append(f"\n**Structured Data:**")
            for key, value in list(result['structured_data'].items())[:3]:
                if isinstance(value, list):
                    lines.append(f"- {key}: {len(value)} items")
                elif isinstance(value, dict):
                    lines.append(f"- {key}: {len(value)} entries")
                else:
                    lines.append(f"- {key}: {str(value)[:100]}...")
    
    # Stage B Context
    lines.append(f"\n## Stage B Context")
    context = results['stage_b_context']
    lines.append(f"- **Total Concepts:** {context['metadata']['total_concepts']}")
    lines.append(f"- **Total Insights:** {context['metadata']['total_insights']}")
    lines.append(f"- **Context Size:** {len(json.dumps(context)):,} characters")
    
    # Stage B Results
    lines.append(f"\n## Stage B Results")
    
    for analyzer_name, result in results['stage_b_results'].items():
        lines.append(f"\n### {analyzer_name.replace('_', ' ').title()}")
        lines.append(f"- **Status:** {result['status']}")
        lines.append(f"- **Processing Time:** {result['processing_time']:.2f}s")
        if result.get('token_usage'):
            lines.append(f"- **Tokens:** {result['token_usage']['total_tokens']:,}")
        
        if result.get('structured_data'):
            lines.append(f"\n**Analysis Output:**")
            data = result['structured_data']
            
            if 'hypotheses' in data and data['hypotheses']:
                lines.append(f"\n**Hypotheses ({len(data['hypotheses'])}):**")
                for h in data['hypotheses'][:3]:
                    lines.append(f"- {h}")
            
            if 'rankings' in data and data['rankings']:
                lines.append(f"\n**Rankings:**")
                for r in data['rankings'][:3]:
                    if isinstance(r, dict):
                        lines.append(f"- Rank {r.get('rank', '?')}: {r.get('hypothesis', r)[:100]}...")
                    else:
                        lines.append(f"- {str(r)[:100]}...")
    
    # Footer
    lines.append(f"\n---")
    lines.append(f"\n*Report generated by test_minimal_pipeline.py*")
    
    return "\n".join(lines)


def main():
    """Run minimal pipeline test."""
    
    print_header("MINIMAL PIPELINE TEST")
    print("Testing with 2 Stage A analyzers and 1 Stage B analyzer")
    
    # Initialize results structure
    results = {
        "timestamp": datetime.now().isoformat(),
        "transcript_info": {},
        "stage_a_results": {},
        "stage_b_context": {},
        "stage_b_results": {},
        "summary": {
            "total_tokens": 0,
            "stage_a_tokens": 0,
            "stage_b_tokens": 0,
            "total_time": 0,
            "success_rate": "0/0"
        }
    }
    
    start_time = time.time()
    
    # Load sample transcript
    print_header("LOADING TRANSCRIPT")
    sample_file = Path("input sample transcripts/sample1.md")
    if not sample_file.exists():
        print_status("❌", f"Sample file not found at {sample_file}")
        return 1
    
    with open(sample_file, "r") as f:
        transcript_text = f.read()
    
    results["transcript_info"] = {
        "file": str(sample_file),
        "size": len(transcript_text),
        "segments": 0
    }
    
    print_status("✅", f"Loaded transcript: {len(transcript_text):,} characters")
    
    # Process transcript
    print_status("🔄", "Processing transcript...")
    processor = get_transcript_processor()
    processed = processor.process(transcript_text, filename=str(sample_file))
    
    results["transcript_info"]["segments"] = len(processed.segments)
    print_status("✅", f"Processed into {len(processed.segments)} segments")
    
    # Create analysis context for Stage A
    ctx = AnalysisContext(
        transcript=processed,
        metadata={"source": "test_minimal_pipeline.py"}
    )
    
    # Run Stage A analyzers
    print_header("STAGE A ANALYSIS")
    print("Running 2 analyzers on transcript...")
    
    stage_a_analyzers = [
        ("say_means", SayMeansAnalyzer),
        ("perspective_perception", PerspectivePerceptionAnalyzer),
    ]
    
    stage_a_tokens = 0
    successful_a = 0
    
    for name, analyzer_class in stage_a_analyzers:
        print(f"\n📊 Running {name.replace('_', ' ').title()}...")
        analyzer_start = time.time()
        
        try:
            analyzer = analyzer_class()
            result = analyzer.analyze_sync(ctx)
            
            elapsed = time.time() - analyzer_start
            
            if result.status == AnalyzerStatus.COMPLETED:
                successful_a += 1
                print_status("✅", f"Success in {elapsed:.2f}s")
                
                if result.token_usage:
                    tokens = result.token_usage.total_tokens
                    stage_a_tokens += tokens
                    print_status("📊", f"Tokens used: {tokens:,}")
                
                # Store result
                results["stage_a_results"][name] = {
                    "status": "completed",
                    "processing_time": elapsed,
                    "token_usage": result.token_usage.dict() if result.token_usage else None,
                    "raw_output": result.raw_output[:1000] if result.raw_output else None,  # First 1000 chars
                    "structured_data": result.structured_data,
                    "insights": [i.dict() for i in result.insights],
                    "concepts": [c.dict() for c in result.concepts],
                }
                
                # Show sample insights
                if result.insights:
                    print(f"  Sample insights:")
                    for insight in result.insights[:2]:
                        print(f"    • {insight.text[:100]}...")
                        
            else:
                print_status("❌", f"Failed: {result.error_message}")
                results["stage_a_results"][name] = {
                    "status": "error",
                    "error_message": result.error_message,
                    "processing_time": elapsed
                }
                
        except Exception as e:
            print_status("❌", f"Exception: {str(e)}")
            results["stage_a_results"][name] = {
                "status": "error",
                "error_message": str(e),
                "processing_time": time.time() - analyzer_start
            }
    
    print(f"\n📊 Stage A Summary: {successful_a}/2 successful, {stage_a_tokens:,} tokens")
    
    # Create Stage B context
    print_header("STAGE B PREPARATION")
    print("Creating context from Stage A results...")
    
    stage_b_context = {
        "stage_a_results": results["stage_a_results"],
        "metadata": {
            "total_concepts": sum(len(r.get("concepts", [])) for r in results["stage_a_results"].values()),
            "total_insights": sum(len(r.get("insights", [])) for r in results["stage_a_results"].values()),
            "processing_time": sum(r.get("processing_time", 0) for r in results["stage_a_results"].values()),
            "analyzers_run": list(results["stage_a_results"].keys())
        }
    }
    
    results["stage_b_context"] = stage_b_context
    
    context_str = json.dumps(stage_b_context, indent=2)
    print_status("✅", f"Context created: {len(context_str):,} characters")
    print_status("📊", f"Total insights: {stage_b_context['metadata']['total_insights']}")
    print_status("📊", f"Total concepts: {stage_b_context['metadata']['total_concepts']}")
    
    # Create AnalysisContext for Stage B with Stage A results
    # Stage B analyzers expect previous_analyses, not a transcript
    stage_b_ctx = AnalysisContext(
        transcript=None,  # No transcript for Stage B
        previous_analyses={},  # Will populate with Stage A results
        metadata={"source": "stage_a_aggregation", "stage": "stage_b"}
    )
    
    # Convert Stage A results to AnalysisResult objects for context
    for name, result_data in results["stage_a_results"].items():
        if result_data["status"] == "completed":
            # Create AnalysisResult object from the stored data
            from src.models import AnalysisResult, TokenUsage, Insight, Concept
            
            analysis_result = AnalysisResult(
                analyzer_name=name,
                raw_output=result_data.get("raw_output", ""),
                structured_data=result_data.get("structured_data", {}),
                insights=[
                    Insight(**insight) if isinstance(insight, dict) else Insight(text=str(insight), source_analyzer=name)
                    for insight in result_data.get("insights", [])[:10]  # Limit insights
                ],
                concepts=[
                    Concept(**concept) if isinstance(concept, dict) else Concept(name=str(concept))
                    for concept in result_data.get("concepts", [])[:10]  # Limit concepts
                ],
                processing_time=result_data.get("processing_time", 0),
                token_usage=TokenUsage(**result_data["token_usage"]) if result_data.get("token_usage") else None,
                status=AnalyzerStatus.COMPLETED
            )
            stage_b_ctx.previous_analyses[name] = analysis_result
    
    # Run Stage B analyzer
    print_header("STAGE B ANALYSIS")
    print("Running Competing Hypotheses analyzer on Stage A context...")
    
    stage_b_tokens = 0
    successful_b = 0
    
    analyzer_start = time.time()
    
    try:
        analyzer = CompetingHypothesesAnalyzer()
        result = analyzer.analyze_sync(stage_b_ctx)
        
        elapsed = time.time() - analyzer_start
        
        if result.status == AnalyzerStatus.COMPLETED:
            successful_b += 1
            print_status("✅", f"Success in {elapsed:.2f}s")
            
            if result.token_usage:
                tokens = result.token_usage.total_tokens
                stage_b_tokens += tokens
                print_status("📊", f"Tokens used: {tokens:,}")
            
            # Store result
            results["stage_b_results"]["competing_hypotheses"] = {
                "status": "completed",
                "processing_time": elapsed,
                "token_usage": result.token_usage.dict() if result.token_usage else None,
                "raw_output": result.raw_output[:1000] if result.raw_output else None,
                "structured_data": result.structured_data,
                "insights": [i.dict() for i in result.insights],
                "concepts": [c.dict() for c in result.concepts],
            }
            
            # Show sample output
            if result.structured_data:
                data = result.structured_data
                if 'hypotheses' in data and data['hypotheses']:
                    print(f"  Hypotheses identified: {len(data['hypotheses'])}")
                    for h in data['hypotheses'][:2]:
                        print(f"    • {h[:100]}...")
                if 'rankings' in data and data['rankings']:
                    print(f"  Rankings generated: {len(data['rankings'])}")
                    
        else:
            print_status("❌", f"Failed: {result.error_message}")
            results["stage_b_results"]["competing_hypotheses"] = {
                "status": "error",
                "error_message": result.error_message,
                "processing_time": elapsed
            }
            
    except Exception as e:
        print_status("❌", f"Exception: {str(e)}")
        results["stage_b_results"]["competing_hypotheses"] = {
            "status": "error",
            "error_message": str(e),
            "processing_time": time.time() - analyzer_start
        }
    
    # Calculate summary
    total_time = time.time() - start_time
    total_successful = successful_a + successful_b
    
    results["summary"] = {
        "total_tokens": stage_a_tokens + stage_b_tokens,
        "stage_a_tokens": stage_a_tokens,
        "stage_b_tokens": stage_b_tokens,
        "total_time": total_time,
        "success_rate": f"{total_successful}/3"
    }
    
    # Print final summary
    print_header("FINAL SUMMARY")
    print(f"✅ Successful analyzers: {total_successful}/3")
    print(f"📊 Total tokens used: {stage_a_tokens + stage_b_tokens:,}")
    print(f"  • Stage A: {stage_a_tokens:,} tokens")
    print(f"  • Stage B: {stage_b_tokens:,} tokens")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    
    # Save results
    print_header("SAVING RESULTS")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    json_file, md_file = save_results(results, output_dir)
    
    print_header("TEST COMPLETE")
    print(f"✅ All results saved to output directory")
    print(f"📊 View JSON: {json_file}")
    print(f"📝 View Report: {md_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
