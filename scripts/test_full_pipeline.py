#!/usr/bin/env python3
"""
Full pipeline test script.

Runs all Stage A analyzers, then all Stage B analyzers on a sample transcript.
Produces comprehensive output files with all analysis results.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import (
    AnalysisContext, 
    ProcessedTranscript, 
    TranscriptSegment, 
    TranscriptMetadata, 
    AnalyzerStatus,
    AnalysisResult,
    TokenUsage,
    Insight,
    Concept
)
from src.transcript_processor import get_transcript_processor

# Import all Stage A analyzers
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
from src.analyzers.stage_a.premises_assertions import PremisesAssertionsAnalyzer
from src.analyzers.stage_a.postulate_theorem import PostulateTheoremAnalyzer

# Import all Stage B analyzers
from src.analyzers.stage_b.competing_hypotheses import CompetingHypothesesAnalyzer
from src.analyzers.stage_b.first_principles import FirstPrinciplesAnalyzer
from src.analyzers.stage_b.determining_factors import DeterminingFactorsAnalyzer
from src.analyzers.stage_b.patentability import PatentabilityAnalyzer


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_status(emoji, text):
    """Print a status message with emoji."""
    print(f"{emoji} {text}")


def save_results(results, output_dir):
    """Save results to JSON and markdown files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON results
    json_file = output_dir / f"full_pipeline_results_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print_status("💾", f"Saved JSON results to {json_file}")
    
    # Generate markdown report
    md_file = output_dir / f"full_pipeline_report_{timestamp}.md"
    with open(md_file, "w") as f:
        f.write(generate_markdown_report(results))
    print_status("📝", f"Saved markdown report to {md_file}")
    
    # Generate executive summary
    summary_file = output_dir / f"executive_summary_{timestamp}.md"
    with open(summary_file, "w") as f:
        f.write(generate_executive_summary(results))
    print_status("📋", f"Saved executive summary to {summary_file}")
    
    return json_file, md_file, summary_file


def generate_markdown_report(results):
    """Generate a comprehensive markdown report."""
    lines = []
    
    # Header
    lines.append(f"# Full Pipeline Analysis Report")
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
    lines.append(f"\n## Stage A - Transcript Analysis")
    lines.append(f"\n*Direct analysis of the transcript content*\n")
    
    for analyzer_name, result in results['stage_a_results'].items():
        lines.append(f"\n### {analyzer_name.replace('_', ' ').title()}")
        lines.append(f"- **Status:** {result['status']}")
        lines.append(f"- **Processing Time:** {result['processing_time']:.2f}s")
        if result.get('token_usage'):
            lines.append(f"- **Tokens:** {result['token_usage']['total_tokens']:,}")
        
        if result.get('insights'):
            lines.append(f"\n**Key Insights ({len(result['insights'])} total):**")
            for i, insight in enumerate(result['insights'][:5], 1):  # Top 5 insights
                text = insight['text'] if isinstance(insight, dict) else str(insight)
                # Truncate long insights
                if len(text) > 200:
                    text = text[:197] + "..."
                lines.append(f"{i}. {text}")
        
        if result.get('structured_data'):
            lines.append(f"\n**Structured Data Summary:**")
            for key, value in list(result['structured_data'].items())[:5]:
                if isinstance(value, list):
                    lines.append(f"- {key}: {len(value)} items")
                elif isinstance(value, dict):
                    lines.append(f"- {key}: {len(value)} entries")
                else:
                    value_str = str(value)[:100]
                    if len(str(value)) > 100:
                        value_str += "..."
                    lines.append(f"- {key}: {value_str}")
    
    # Stage B Results
    lines.append(f"\n## Stage B - Meta-Analysis")
    lines.append(f"\n*Analysis of Stage A results to identify patterns and deeper insights*\n")
    
    for analyzer_name, result in results['stage_b_results'].items():
        lines.append(f"\n### {analyzer_name.replace('_', ' ').title()}")
        lines.append(f"- **Status:** {result['status']}")
        lines.append(f"- **Processing Time:** {result['processing_time']:.2f}s")
        if result.get('token_usage'):
            lines.append(f"- **Tokens:** {result['token_usage']['total_tokens']:,}")
        
        if result.get('structured_data'):
            lines.append(f"\n**Analysis Output:**")
            data = result['structured_data']
            
            # Competing Hypotheses specific output
            if 'hypotheses' in data and data['hypotheses']:
                lines.append(f"\n**Hypotheses ({len(data['hypotheses'])}):**")
                for i, h in enumerate(data['hypotheses'][:3], 1):
                    h_text = h if isinstance(h, str) else str(h)
                    if len(h_text) > 150:
                        h_text = h_text[:147] + "..."
                    lines.append(f"{i}. {h_text}")
            
            if 'rankings' in data and data['rankings']:
                lines.append(f"\n**Rankings:**")
                for r in data['rankings'][:3]:
                    if isinstance(r, dict):
                        rank_text = f"Rank {r.get('rank', '?')}: {r.get('hypothesis', r)}"
                    else:
                        rank_text = str(r)
                    if len(rank_text) > 150:
                        rank_text = rank_text[:147] + "..."
                    lines.append(f"- {rank_text}")
            
            # First Principles specific output
            if 'fundamental_truths' in data and data['fundamental_truths']:
                lines.append(f"\n**Fundamental Truths ({len(data['fundamental_truths'])}):**")
                for i, truth in enumerate(data['fundamental_truths'][:3], 1):
                    truth_text = truth if isinstance(truth, str) else str(truth)
                    if len(truth_text) > 150:
                        truth_text = truth_text[:147] + "..."
                    lines.append(f"{i}. {truth_text}")
            
            # Determining Factors specific output
            if 'causal_factors' in data and data['causal_factors']:
                lines.append(f"\n**Causal Factors ({len(data['causal_factors'])}):**")
                for i, factor in enumerate(data['causal_factors'][:3], 1):
                    factor_text = factor if isinstance(factor, str) else str(factor)
                    if len(factor_text) > 150:
                        factor_text = factor_text[:147] + "..."
                    lines.append(f"{i}. {factor_text}")
            
            # Patentability specific output
            if 'innovations' in data and data['innovations']:
                lines.append(f"\n**Potential Innovations ({len(data['innovations'])}):**")
                for i, innovation in enumerate(data['innovations'][:3], 1):
                    inn_text = innovation if isinstance(innovation, str) else str(innovation)
                    if len(inn_text) > 150:
                        inn_text = inn_text[:147] + "..."
                    lines.append(f"{i}. {inn_text}")
    
    # Processing Metrics
    lines.append(f"\n## Processing Metrics")
    lines.append(f"- **Total Processing Time:** {results['summary']['total_time']:.2f} seconds")
    lines.append(f"- **Average time per analyzer:** {results['summary']['total_time'] / (results['summary']['stage_a_count'] + results['summary']['stage_b_count']):.2f} seconds")
    lines.append(f"- **Total Tokens Used:** {results['summary']['total_tokens']:,}")
    lines.append(f"  - Stage A: {results['summary']['stage_a_tokens']:,} tokens")
    lines.append(f"  - Stage B: {results['summary']['stage_b_tokens']:,} tokens")
    lines.append(f"- **Success Rate:** {results['summary']['success_rate']}")
    
    # Footer
    lines.append(f"\n---")
    lines.append(f"\n*Report generated by test_full_pipeline.py*")
    lines.append(f"*Timestamp: {results['timestamp']}*")
    
    return "\n".join(lines)


def generate_executive_summary(results):
    """Generate an executive summary of the analysis."""
    lines = []
    
    lines.append(f"# Executive Summary")
    lines.append(f"\n**Date:** {datetime.now().strftime('%B %d, %Y')}")
    lines.append(f"**Analysis Type:** Full Pipeline (Stage A + Stage B)")
    
    # Key Findings
    lines.append(f"\n## Key Findings")
    
    # Collect top insights from all analyzers
    all_insights = []
    for stage_results in [results['stage_a_results'], results['stage_b_results']]:
        for analyzer_name, result in stage_results.items():
            if result.get('insights'):
                for insight in result['insights'][:2]:  # Top 2 from each
                    insight_text = insight['text'] if isinstance(insight, dict) else str(insight)
                    if len(insight_text) > 50:  # Skip very short insights
                        all_insights.append({
                            'text': insight_text,
                            'source': analyzer_name.replace('_', ' ').title()
                        })
    
    # Display top 10 insights
    for i, insight in enumerate(all_insights[:10], 1):
        text = insight['text']
        if len(text) > 200:
            text = text[:197] + "..."
        lines.append(f"\n{i}. **{text}**")
        lines.append(f"   - *Source: {insight['source']}*")
    
    # Hypotheses from Stage B
    if 'competing_hypotheses' in results['stage_b_results']:
        ch_data = results['stage_b_results']['competing_hypotheses'].get('structured_data', {})
        if ch_data.get('hypotheses'):
            lines.append(f"\n## Competing Hypotheses")
            for i, h in enumerate(ch_data['hypotheses'][:5], 1):
                h_text = h if isinstance(h, str) else str(h)
                if len(h_text) > 200:
                    h_text = h_text[:197] + "..."
                lines.append(f"{i}. {h_text}")
    
    # Recommendations
    lines.append(f"\n## Recommendations")
    lines.append(f"Based on the analysis, the following actions are recommended:")
    
    # Extract recommendations from various analyzers
    recommendations = []
    
    # From determining factors
    if 'determining_factors' in results['stage_b_results']:
        df_data = results['stage_b_results']['determining_factors'].get('structured_data', {})
        if df_data.get('critical_decisions'):
            for decision in df_data['critical_decisions'][:3]:
                recommendations.append(f"Critical Decision: {decision}")
    
    # From patentability
    if 'patentability' in results['stage_b_results']:
        p_data = results['stage_b_results']['patentability'].get('structured_data', {})
        if p_data.get('patent_opportunities'):
            for opp in p_data['patent_opportunities'][:2]:
                recommendations.append(f"Patent Opportunity: {opp}")
    
    # Display recommendations
    if recommendations:
        for i, rec in enumerate(recommendations[:5], 1):
            if len(rec) > 200:
                rec = rec[:197] + "..."
            lines.append(f"{i}. {rec}")
    else:
        lines.append("- Further analysis recommended to identify specific action items")
        lines.append("- Review Stage B results for strategic insights")
        lines.append("- Consider conducting follow-up analysis on specific areas of interest")
    
    # Metrics
    lines.append(f"\n## Analysis Metrics")
    lines.append(f"- **Processing Time:** {results['summary']['total_time']:.1f} seconds")
    lines.append(f"- **Analyzers Run:** {results['summary']['stage_a_count']} Stage A, {results['summary']['stage_b_count']} Stage B")
    lines.append(f"- **Success Rate:** {results['summary']['success_rate']}")
    lines.append(f"- **Total API Tokens:** {results['summary']['total_tokens']:,}")
    
    lines.append(f"\n---")
    lines.append(f"*For detailed results, see the full pipeline report*")
    
    return "\n".join(lines)


def main():
    """Run full pipeline test."""
    
    print_header("FULL PIPELINE TEST")
    print("Running all Stage A and Stage B analyzers")
    
    # Initialize results structure
    results = {
        "timestamp": datetime.now().isoformat(),
        "transcript_info": {},
        "stage_a_results": {},
        "stage_b_results": {},
        "summary": {
            "total_tokens": 0,
            "stage_a_tokens": 0,
            "stage_b_tokens": 0,
            "total_time": 0,
            "stage_a_count": 0,
            "stage_b_count": 0,
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
        metadata={"source": "test_full_pipeline.py"}
    )
    
    # Define all Stage A analyzers
    stage_a_analyzers = [
        ("say_means", SayMeansAnalyzer),
        ("perspective_perception", PerspectivePerceptionAnalyzer),
        ("premises_assertions", PremisesAssertionsAnalyzer),
        ("postulate_theorem", PostulateTheoremAnalyzer),
    ]
    
    # Run Stage A analyzers
    print_header("STAGE A ANALYSIS")
    print(f"Running {len(stage_a_analyzers)} analyzers on transcript...")
    
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
                    "token_usage": result.token_usage.model_dump() if result.token_usage else None,
                    "raw_output": result.raw_output[:2000] if result.raw_output else None,  # First 2000 chars
                    "structured_data": result.structured_data,
                    "insights": [i.model_dump() for i in result.insights],
                    "concepts": [c.model_dump() for c in result.concepts],
                }
                
                # Show sample insights
                if result.insights:
                    print(f"  Sample insights:")
                    for insight in result.insights[:2]:
                        text = insight.text[:100] + "..." if len(insight.text) > 100 else insight.text
                        print(f"    • {text}")
                        
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
    
    results["summary"]["stage_a_count"] = len(stage_a_analyzers)
    print(f"\n📊 Stage A Summary: {successful_a}/{len(stage_a_analyzers)} successful, {stage_a_tokens:,} tokens")
    
    # Create Stage B context
    print_header("STAGE B PREPARATION")
    print("Creating context from Stage A results...")
    
    # Create AnalysisContext for Stage B with Stage A results
    stage_b_ctx = AnalysisContext(
        transcript=None,  # No transcript for Stage B
        previous_analyses={},  # Will populate with Stage A results
        metadata={"source": "stage_a_aggregation", "stage": "stage_b"}
    )
    
    # Convert Stage A results to AnalysisResult objects for context
    for name, result_data in results["stage_a_results"].items():
        if result_data["status"] == "completed":
            # Create AnalysisResult object from the stored data
            analysis_result = AnalysisResult(
                analyzer_name=name,
                raw_output=result_data.get("raw_output", ""),
                structured_data=result_data.get("structured_data", {}),
                insights=[
                    Insight(**insight) if isinstance(insight, dict) else Insight(text=str(insight), source_analyzer=name)
                    for insight in result_data.get("insights", [])[:20]  # Limit insights
                ],
                concepts=[
                    Concept(**concept) if isinstance(concept, dict) else Concept(name=str(concept))
                    for concept in result_data.get("concepts", [])[:20]  # Limit concepts
                ],
                processing_time=result_data.get("processing_time", 0),
                token_usage=TokenUsage(**result_data["token_usage"]) if result_data.get("token_usage") else None,
                status=AnalyzerStatus.COMPLETED
            )
            stage_b_ctx.previous_analyses[name] = analysis_result
    
    total_insights = sum(len(r.get("insights", [])) for r in results["stage_a_results"].values())
    total_concepts = sum(len(r.get("concepts", [])) for r in results["stage_a_results"].values())
    print_status("✅", f"Context created with {len(stage_b_ctx.previous_analyses)} Stage A results")
    print_status("📊", f"Total insights: {total_insights}")
    print_status("📊", f"Total concepts: {total_concepts}")
    
    # Define all Stage B analyzers
    stage_b_analyzers = [
        ("competing_hypotheses", CompetingHypothesesAnalyzer),
        ("first_principles", FirstPrinciplesAnalyzer),
        ("determining_factors", DeterminingFactorsAnalyzer),
        ("patentability", PatentabilityAnalyzer),
    ]
    
    # Run Stage B analyzers
    print_header("STAGE B ANALYSIS")
    print(f"Running {len(stage_b_analyzers)} analyzers on Stage A context...")
    
    stage_b_tokens = 0
    successful_b = 0
    
    for name, analyzer_class in stage_b_analyzers:
        print(f"\n📊 Running {name.replace('_', ' ').title()}...")
        analyzer_start = time.time()
        
        try:
            analyzer = analyzer_class()
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
                results["stage_b_results"][name] = {
                    "status": "completed",
                    "processing_time": elapsed,
                    "token_usage": result.token_usage.model_dump() if result.token_usage else None,
                    "raw_output": result.raw_output[:2000] if result.raw_output else None,
                    "structured_data": result.structured_data,
                    "insights": [i.model_dump() for i in result.insights],
                    "concepts": [c.model_dump() for c in result.concepts],
                }
                
                # Show sample output
                if result.structured_data:
                    data = result.structured_data
                    print(f"  Analysis complete - extracted {len(data)} data categories")
                    
            else:
                print_status("❌", f"Failed: {result.error_message}")
                results["stage_b_results"][name] = {
                    "status": "error",
                    "error_message": result.error_message,
                    "processing_time": elapsed
                }
                
        except Exception as e:
            print_status("❌", f"Exception: {str(e)}")
            results["stage_b_results"][name] = {
                "status": "error",
                "error_message": str(e),
                "processing_time": time.time() - analyzer_start
            }
    
    results["summary"]["stage_b_count"] = len(stage_b_analyzers)
    print(f"\n📊 Stage B Summary: {successful_b}/{len(stage_b_analyzers)} successful, {stage_b_tokens:,} tokens")
    
    # Calculate summary
    total_time = time.time() - start_time
    total_successful = successful_a + successful_b
    total_analyzers = len(stage_a_analyzers) + len(stage_b_analyzers)
    
    results["summary"].update({
        "total_tokens": stage_a_tokens + stage_b_tokens,
        "stage_a_tokens": stage_a_tokens,
        "stage_b_tokens": stage_b_tokens,
        "total_time": total_time,
        "success_rate": f"{total_successful}/{total_analyzers}"
    })
    
    # Print final summary
    print_header("FINAL SUMMARY")
    print(f"✅ Successful analyzers: {total_successful}/{total_analyzers}")
    print(f"📊 Total tokens used: {stage_a_tokens + stage_b_tokens:,}")
    print(f"  • Stage A ({successful_a}/{len(stage_a_analyzers)}): {stage_a_tokens:,} tokens")
    print(f"  • Stage B ({successful_b}/{len(stage_b_analyzers)}): {stage_b_tokens:,} tokens")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"⚡ Average time per analyzer: {total_time/total_analyzers:.2f} seconds")
    
    # Save results
    print_header("SAVING RESULTS")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    json_file, md_file, summary_file = save_results(results, output_dir)
    
    print_header("TEST COMPLETE")
    print(f"✅ All results saved to output directory")
    print(f"📊 View JSON: {json_file}")
    print(f"📝 View Report: {md_file}")
    print(f"📋 View Summary: {summary_file}")
    
    # Print cost estimate
    estimated_cost = (stage_a_tokens + stage_b_tokens) * 0.00001  # Rough estimate
    print(f"\n💰 Estimated API cost: ${estimated_cost:.2f}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
