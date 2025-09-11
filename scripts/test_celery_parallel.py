#!/usr/bin/env python3
"""
Test the Celery parallel pipeline execution.
Submits a job via API and monitors its progress.
"""

import sys
import time
import json
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 80)
    print("CELERY PARALLEL PIPELINE TEST")
    print("=" * 80)
    
    # Load sample transcript
    sample_path = Path("input sample transcripts/sample1.md")
    if sample_path.exists():
        transcript_text = sample_path.read_text(encoding="utf-8")
    else:
        transcript_text = """Speaker 1: Let's discuss the new product features.
Speaker 2: We should focus on user experience first.
Speaker 1: I agree, but we also need to consider the technical implementation.
Speaker 2: What about using a modular architecture?"""
    
    print(f"\n📄 Transcript length: {len(transcript_text)} characters")
    
    # Submit job
    print("\n🚀 Submitting job to API...")
    response = requests.post(
        "http://localhost:5001/api/analyze",
        json={
            "transcriptText": transcript_text,
            "selected": {
                "stageA": ["say_means", "perspective_perception", "premises_assertions", "postulate_theorem"],
                "stageB": ["competing_hypotheses", "first_principles", "determining_factors", "patentability"],
                "final": ["meeting_notes", "composite_note"]
            }
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to submit job: {response.status_code}")
        print(response.text)
        return 1
    
    job_data = response.json()
    job_id = job_data["jobId"]
    print(f"✅ Job created: {job_id}")
    
    # Monitor job progress
    print("\n📊 Monitoring job progress...")
    print("-" * 40)
    
    start_time = time.time()
    last_status = None
    stage_times = {}
    
    while True:
        # Get job status
        status_response = requests.get(f"http://localhost:5001/api/status/{job_id}")
        if status_response.status_code != 200:
            print(f"❌ Failed to get job status: {status_response.status_code}")
            break
        
        response_json = status_response.json()
        status_data = response_json.get("doc", {})
        current_status = status_data.get("status", "unknown")
        
        # Print status changes
        if current_status != last_status:
            elapsed = time.time() - start_time
            print(f"[{elapsed:6.1f}s] Status: {current_status}")
            last_status = current_status
        
        # Check for stage completions
        for stage in ["stageA", "stageB", "final"]:
            if stage in status_data and stage not in stage_times:
                # Check if all analyzers in stage are complete
                stage_data = status_data[stage]
                if isinstance(stage_data, dict):
                    completed = sum(1 for v in stage_data.values() 
                                  if isinstance(v, dict) and v.get("status") == "completed")
                    total = len(stage_data)
                    if completed == total and total > 0:
                        elapsed = time.time() - start_time
                        stage_times[stage] = elapsed
                        print(f"[{elapsed:6.1f}s] ✅ {stage} completed ({completed}/{total} analyzers)")
                        
                        # Show parallel execution evidence
                        if stage in ["stageA", "stageB"]:
                            times = []
                            for name, result in stage_data.items():
                                if isinstance(result, dict) and "processing_time" in result:
                                    times.append((name, result["processing_time"]))
                            if times:
                                times.sort(key=lambda x: x[1])
                                print(f"         Parallel execution times:")
                                for name, t in times:
                                    print(f"           - {name}: {t:.2f}s")
        
        # Check if job is complete
        if current_status in ["completed", "error", "failed"]:
            elapsed = time.time() - start_time
            print(f"[{elapsed:6.1f}s] Job finished with status: {current_status}")
            break
        
        # Timeout after 5 minutes
        if time.time() - start_time > 300:
            print("⏱️  Timeout after 5 minutes")
            break
        
        time.sleep(2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if status_data and status_data.get("status") == "completed":
        print("✅ Pipeline completed successfully!")
        
        # Show token usage
        token_usage = status_data.get("tokenUsageTotal", {})
        if token_usage:
            print(f"\n📊 Token Usage:")
            print(f"   - Prompt tokens: {token_usage.get('prompt', 0):,}")
            print(f"   - Completion tokens: {token_usage.get('completion', 0):,}")
            print(f"   - Total tokens: {token_usage.get('total', 0):,}")
        
        # Show timing
        total_time = time.time() - start_time
        print(f"\n⏱️  Timing:")
        print(f"   - Total wall-clock time: {total_time:.2f}s")
        for stage, stage_time in stage_times.items():
            print(f"   - {stage} completed at: {stage_time:.2f}s")
        
        # Check for parallel execution
        print(f"\n🔄 Parallel Execution Verification:")
        
        # Stage A verification
        stage_a_data = status_data.get("stageA", {})
        if stage_a_data:
            stage_a_times = [v.get("processing_time", 0) for v in stage_a_data.values() 
                           if isinstance(v, dict)]
            if stage_a_times:
                max_time = max(stage_a_times)
                sum_time = sum(stage_a_times)
                print(f"   Stage A: Max time={max_time:.1f}s, Sum={sum_time:.1f}s")
                if sum_time > max_time * 1.5:
                    print(f"   ✅ Stage A ran in parallel (sum >> max)")
                else:
                    print(f"   ⚠️  Stage A may not have run in parallel")
        
        # Stage B verification
        stage_b_data = status_data.get("stageB", {})
        if stage_b_data:
            stage_b_times = [v.get("processing_time", 0) for v in stage_b_data.values() 
                           if isinstance(v, dict)]
            if stage_b_times:
                max_time = max(stage_b_times)
                sum_time = sum(stage_b_times)
                print(f"   Stage B: Max time={max_time:.1f}s, Sum={sum_time:.1f}s")
                if sum_time > max_time * 1.5:
                    print(f"   ✅ Stage B ran in parallel (sum >> max)")
                else:
                    print(f"   ⚠️  Stage B may not have run in parallel")
        
        # Check output directory
        output_dir = Path(f"output/jobs/{job_id}")
        if output_dir.exists():
            print(f"\n📁 Output directory: {output_dir}")
            
            # Check for final outputs
            final_dir = output_dir / "final"
            if final_dir.exists():
                files = list(final_dir.glob("*.md"))
                if files:
                    print(f"   Final outputs generated:")
                    for f in files:
                        print(f"   - {f.name}")
    else:
        print(f"❌ Pipeline failed with status: {status_data.get('status')}")
        
        # Show errors if any
        errors = status_data.get("errors", [])
        if errors:
            print("\nErrors:")
            for error in errors:
                print(f"   - {error}")
    
    print("\n" + "=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
