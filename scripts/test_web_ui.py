#!/usr/bin/env python3
"""Test the web UI and full pipeline integration."""

import requests
import json
import time
import sys

API_BASE = "http://localhost:5001/api"

def test_full_system():
    """Test the complete system with a real transcript."""
    
    print("=" * 60)
    print("TRANSCRIPT ANALYSIS TOOL - SYSTEM TEST")
    print("=" * 60)
    
    # Test transcript
    test_transcript = """
    Interviewer: Welcome to our product development meeting. Let's discuss the new AI-powered features we're planning.
    
    Product Manager: Thanks for having me. I believe we should focus on three key areas: natural language processing, predictive analytics, and automated decision support.
    
    Engineer: From a technical perspective, we'll need to consider scalability. The NLP models require significant computational resources.
    
    Product Manager: That's a valid concern. What about using cloud-based solutions to handle the processing load?
    
    Engineer: Cloud services could work, but we need to consider data privacy and latency issues. Perhaps a hybrid approach would be better.
    
    Designer: From a user experience standpoint, we need to ensure these AI features are transparent and explainable to users.
    
    Product Manager: Absolutely. User trust is crucial. We should implement clear explanations for AI-driven recommendations.
    
    Engineer: I can work on an explainability module that breaks down the decision-making process.
    
    Designer: That would be great. We could visualize it in a user-friendly dashboard.
    
    Interviewer: Excellent discussion. Let's summarize the key points and action items.
    """
    
    # Submit analysis
    payload = {
        "transcriptText": test_transcript,
        "selected": {
            "stageA": ["say_means", "perspective_perception", "premises_assertions", "postulate_theorem"],
            "stageB": ["competing_hypotheses", "first_principles", "determining_factors", "patentability"],
            "final": ["meeting_notes", "composite_note"]
        },
        "promptSelection": {}
    }
    
    print("\n1. SUBMITTING TRANSCRIPT")
    print("-" * 40)
    print(f"   Length: {len(test_transcript)} characters")
    print(f"   Analyzers: 10 total (4 Stage A, 4 Stage B, 2 Final)")
    
    response = requests.post(f"{API_BASE}/analyze", json=payload)
    
    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   {response.text}")
        return False
    
    job_data = response.json()
    job_id = job_data.get("jobId")
    print(f"   ✅ Job created: {job_id}")
    
    # Monitor progress
    print("\n2. MONITORING PROGRESS")
    print("-" * 40)
    
    start_time = time.time()
    last_status = None
    completed_analyzers = set()
    stage_times = {}
    
    while True:
        response = requests.get(f"{API_BASE}/status/{job_id}")
        
        if response.status_code != 200:
            print(f"   ❌ Error getting status: {response.status_code}")
            return False
        
        data = response.json()
        doc = data.get("doc", {})
        status = doc.get("status")
        
        # Track status changes
        if status != last_status:
            elapsed = time.time() - start_time
            print(f"   Status: {status} ({elapsed:.1f}s)")
            last_status = status
        
        # Track analyzer completions
        for stage in ["stageA", "stageB", "final"]:
            stage_data = doc.get(stage, {})
            for analyzer_name, analyzer_info in stage_data.items():
                if analyzer_info.get("status") == "completed" and analyzer_name not in completed_analyzers:
                    elapsed = time.time() - start_time
                    print(f"   ✓ {analyzer_name}: completed ({elapsed:.1f}s)")
                    completed_analyzers.add(analyzer_name)
                    
                    if stage not in stage_times:
                        stage_times[stage] = []
                    stage_times[stage].append(elapsed)
        
        # Check completion
        if status == "completed":
            total_time = time.time() - start_time
            print(f"\n   ✅ ANALYSIS COMPLETED in {total_time:.1f} seconds")
            
            # Show token usage
            token_usage = doc.get("tokenUsageTotal", {})
            if token_usage:
                print(f"\n3. TOKEN USAGE")
                print("-" * 40)
                print(f"   Prompt tokens: {token_usage.get('prompt', 0):,}")
                print(f"   Completion tokens: {token_usage.get('completion', 0):,}")
                print(f"   Total tokens: {token_usage.get('total', 0):,}")
            
            # Show stage timing
            print(f"\n4. PERFORMANCE METRICS")
            print("-" * 40)
            for stage, times in stage_times.items():
                if times:
                    stage_name = {"stageA": "Stage A", "stageB": "Stage B", "final": "Final"}.get(stage, stage)
                    print(f"   {stage_name}: {max(times):.1f}s")
            
            print(f"\n5. RESULTS")
            print("-" * 40)
            print(f"   Job ID: {job_id}")
            print(f"   Status: SUCCESS")
            print(f"   Total analyzers: {len(completed_analyzers)}")
            print(f"   Total time: {total_time:.1f}s")
            
            return True
            
        elif status == "failed":
            print(f"\n   ❌ Analysis failed: {doc.get('error', 'Unknown error')}")
            return False
        
        # Wait before next check
        time.sleep(2)
        
        # Timeout after 5 minutes
        if time.time() - start_time > 300:
            print(f"\n   ⚠️ Timeout after 5 minutes")
            return False

def main():
    """Main test function."""
    
    print("\nChecking system components...")
    
    # Check API health
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print("✅ API is running")
        else:
            print("❌ API health check failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        sys.exit(1)
    
    # Run full system test
    print("\nStarting full system test with real GPT calls...")
    print("This will make actual API calls and may take 2-3 minutes.\n")
    
    success = test_full_system()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ SYSTEM TEST PASSED")
        print("=" * 60)
        print("\nThe Transcript Analysis Tool is fully operational!")
        print("You can now access the web interface at: http://localhost:5001")
    else:
        print("\n" + "=" * 60)
        print("❌ SYSTEM TEST FAILED")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
