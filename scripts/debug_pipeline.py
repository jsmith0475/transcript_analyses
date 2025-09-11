#!/usr/bin/env python3
"""Debug script to check what's happening with the pipeline stages."""

import requests
import json
import time
import sys

API_BASE = "http://localhost:5001/api"

def debug_pipeline():
    """Submit a job and monitor what stages are actually running."""
    
    # Simple test transcript
    test_transcript = """
    Speaker 1: Let's discuss our new product strategy.
    Speaker 2: I think we should focus on AI integration.
    Speaker 1: That makes sense. What about the timeline?
    Speaker 2: We could launch in Q2 next year.
    """
    
    # Explicitly request all stages
    payload = {
        "transcriptText": test_transcript,
        "selected": {
            "stageA": ["say_means", "perspective_perception"],
            "stageB": ["competing_hypotheses", "first_principles"],
            "final": ["meeting_notes", "composite_note"]
        }
    }
    
    print("SUBMITTING JOB WITH PAYLOAD:")
    print(json.dumps(payload, indent=2))
    print("-" * 60)
    
    response = requests.post(f"{API_BASE}/analyze", json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return
    
    job_data = response.json()
    job_id = job_data.get("jobId")
    print(f"Job ID: {job_id}")
    print("-" * 60)
    
    # Monitor for 2 minutes
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < 120:
        response = requests.get(f"{API_BASE}/status/{job_id}")
        
        if response.status_code != 200:
            print(f"Error getting status: {response.status_code}")
            break
        
        data = response.json()
        doc = data.get("doc", {})
        status = doc.get("status")
        
        if status != last_status:
            print(f"\nStatus changed to: {status}")
            last_status = status
        
        # Check what's in each stage
        stage_a = doc.get("stageA", {})
        stage_b = doc.get("stageB", {})
        final = doc.get("final", {})
        
        print(f"\nCurrent state at {time.time() - start_time:.1f}s:")
        print(f"  Stage A analyzers: {list(stage_a.keys())}")
        print(f"  Stage B analyzers: {list(stage_b.keys())}")
        print(f"  Final outputs: {list(final.keys()) if isinstance(final, dict) else 'None'}")
        
        # Check if completed
        if status == "completed":
            print("\n" + "=" * 60)
            print("PIPELINE COMPLETED")
            print("=" * 60)
            
            # Show what actually ran
            print("\nFINAL RESULTS:")
            print(f"  Stage A completed: {len(stage_a)} analyzers")
            for name in stage_a:
                print(f"    - {name}: {stage_a[name].get('status', 'unknown')}")
            
            print(f"  Stage B completed: {len(stage_b)} analyzers")
            for name in stage_b:
                print(f"    - {name}: {stage_b[name].get('status', 'unknown')}")
            
            print(f"  Final stage: {final.get('status', 'not run') if isinstance(final, dict) else 'not run'}")
            
            # Check token usage
            tokens = doc.get("tokenUsageTotal", {})
            print(f"\nTotal tokens used: {tokens.get('total', 0)}")
            
            break
        
        elif status == "error" or status == "failed":
            print(f"\nPipeline failed: {doc.get('errors', 'Unknown error')}")
            break
        
        time.sleep(3)
    
    else:
        print("\nTimeout after 2 minutes")

if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE DEBUG TEST")
    print("=" * 60)
    
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
    
    debug_pipeline()
