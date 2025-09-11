#!/usr/bin/env python3
"""Test the API directly to verify the pipeline is working."""

import requests
import json
import time
import sys

API_BASE = "http://localhost:5001/api"

def test_analyze():
    """Submit a test transcript for analysis."""
    
    # Simple test transcript
    test_transcript = """
    Speaker 1: Let's discuss the new product features.
    Speaker 2: I think we should focus on user experience first.
    Speaker 1: Good point. What about the technical implementation?
    Speaker 2: We can use a modular architecture for flexibility.
    """
    
    # Prepare the request
    payload = {
        "transcriptText": test_transcript,
        "selected": {
            "stageA": ["say_means", "perspective_perception", "premises_assertions", "postulate_theorem"],
            "stageB": ["competing_hypotheses", "first_principles", "determining_factors", "patentability"],
            "final": ["meeting_notes", "composite_note"]
        },
        "promptSelection": {}  # Use default prompts
    }
    
    print("Submitting transcript for analysis...")
    print(f"Transcript length: {len(test_transcript)} characters")
    
    # Submit the analysis request
    response = requests.post(f"{API_BASE}/analyze", json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    job_data = response.json()
    job_id = job_data.get("jobId")
    print(f"Job created: {job_id}")
    
    return job_id

def monitor_job(job_id):
    """Monitor the job status."""
    
    print(f"\nMonitoring job {job_id}...")
    print("-" * 50)
    
    last_status = None
    completed_analyzers = set()
    
    while True:
        response = requests.get(f"{API_BASE}/status/{job_id}")
        
        if response.status_code != 200:
            print(f"Error getting status: {response.status_code}")
            break
        
        data = response.json()
        status = data.get("status")
        
        # Print status change
        if status != last_status:
            print(f"\nJob Status: {status}")
            last_status = status
        
        # Print analyzer updates
        analyzers = data.get("analyzers", {})
        for name, info in analyzers.items():
            if info.get("status") == "completed" and name not in completed_analyzers:
                print(f"  ✓ {name}: completed")
                completed_analyzers.add(name)
            elif info.get("status") == "running":
                print(f"  ⟳ {name}: running...")
            elif info.get("status") == "error":
                print(f"  ✗ {name}: ERROR - {info.get('error')}")
        
        # Check if complete
        if status == "completed":
            print("\n✅ Analysis completed successfully!")
            print(f"Total analyzers completed: {len(completed_analyzers)}")
            
            # Show results summary
            results = data.get("results", {})
            if results:
                print("\nResults available for:")
                for stage in ["stage_a", "stage_b", "final"]:
                    if stage in results:
                        print(f"  - {stage}: {len(results[stage])} analyzers")
            break
        elif status == "failed":
            print("\n❌ Analysis failed!")
            print(f"Error: {data.get('error', 'Unknown error')}")
            break
        
        # Wait before next check
        time.sleep(2)

def main():
    """Main test function."""
    
    print("=" * 50)
    print("API Pipeline Test")
    print("=" * 50)
    
    # Test the analyze endpoint
    job_id = test_analyze()
    
    if job_id:
        # Monitor the job
        monitor_job(job_id)
    else:
        print("Failed to create job")
        sys.exit(1)

if __name__ == "__main__":
    main()
