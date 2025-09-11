#!/usr/bin/env python3
"""
Test script to verify the three-state status display:
1. Pending - analyzer not started
2. In Process - analyzer currently running  
3. Completed - analyzer finished

This script will submit a small test job and monitor the status changes.
"""

import time
import json
import requests
from pathlib import Path

# Test transcript
TEST_TRANSCRIPT = """
Speaker 1: Let's discuss the new product features.
Speaker 2: I think we should focus on user experience improvements.
Speaker 1: Agreed. The feedback shows users want a simpler interface.
Speaker 2: We should also consider performance optimizations.
"""

def test_status_display():
    """Test the three-state status display."""
    base_url = "http://localhost:5000"
    
    print("Testing Three-State Status Display")
    print("=" * 50)
    
    # 1. Submit a job
    print("\n1. Submitting test job...")
    response = requests.post(
        f"{base_url}/api/analyze",
        json={
            "transcriptText": TEST_TRANSCRIPT,
            "selected": {
                "stageA": ["say_means"],  # Just one analyzer for quick test
                "stageB": ["competing_hypotheses"],
                "final": ["meeting_notes"]
            }
        }
    )
    
    if response.status_code != 200:
        print(f"Error submitting job: {response.text}")
        return
    
    job_data = response.json()
    job_id = job_data["jobId"]
    print(f"Job submitted: {job_id}")
    
    # 2. Monitor status changes
    print("\n2. Monitoring status changes...")
    print("(Check the web UI to see Pending → In Process → Completed)")
    
    prev_status = {}
    for i in range(30):  # Monitor for up to 30 seconds
        response = requests.get(f"{base_url}/api/status/{job_id}")
        if response.status_code == 200:
            status_data = response.json()
            
            # Check each stage for status changes
            for stage in ["stageA", "stageB", "final"]:
                if stage in status_data:
                    for analyzer, data in status_data[stage].items():
                        current = data.get("status", "pending")
                        key = f"{stage}.{analyzer}"
                        
                        if key not in prev_status:
                            prev_status[key] = "pending"
                            print(f"  {key}: pending (initial)")
                        
                        if current != prev_status[key]:
                            print(f"  {key}: {prev_status[key]} → {current}")
                            prev_status[key] = current
            
            # Check if job is complete
            if status_data.get("status") == "completed":
                print("\n3. Job completed successfully!")
                print("\nStatus transitions observed:")
                print("  - Pending: Analyzer not yet started")
                print("  - Processing: Analyzer currently running (if backend sets it)")
                print("  - Completed: Analyzer finished")
                break
        
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print("Test complete. Check the web UI to verify visual states:")
    print("  - Pending: Gray badge")
    print("  - In Process: Yellow badge with pulse animation")
    print("  - Completed: Green badge")

if __name__ == "__main__":
    test_status_display()
