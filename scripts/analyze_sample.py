#!/usr/bin/env python3
"""
Submit sample transcript to the analysis pipeline and save results.
"""

import json
import time
import requests
from pathlib import Path

def main():
    # Read the sample transcript
    transcript_path = Path("input sample transcripts/sample1.md")
    with open(transcript_path, "r") as f:
        transcript_text = f.read()
    
    print(f"Loaded transcript: {len(transcript_text)} characters")
    
    # Submit to API
    api_url = "http://localhost:5001/api/analyze"
    payload = {
        "transcriptText": transcript_text,
        "selected": {
            "stageA": [
                "say_means", 
                "perspective_perception",
                "premises_assertions",
                "postulate_theorem"
            ],
            "stageB": [],
            "final": []
        }
    }
    
    print(f"Submitting to {api_url}...")
    response = requests.post(api_url, json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return
    
    job_data = response.json()
    if not job_data.get("ok"):
        print(f"Error: {job_data}")
        return
    
    job_id = job_data["jobId"]
    print(f"Job submitted successfully: {job_id}")
    
    # Save job info
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "sample1_job.json", "w") as f:
        json.dump(job_data, f, indent=2)
    
    # Poll for completion
    status_url = f"http://localhost:5001/api/status/{job_id}"
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    print("Waiting for analysis to complete...")
    while attempt < max_attempts:
        time.sleep(5)
        attempt += 1
        
        response = requests.get(status_url)
        if response.status_code != 200:
            print(f"Error checking status: {response.status_code}")
            continue
        
        status_data = response.json()
        if not status_data.get("ok"):
            print(f"Error: {status_data}")
            continue
        
        doc = status_data.get("doc", {})
        status = doc.get("status", "unknown")
        
        print(f"  Attempt {attempt}: Status = {status}")
        
        if status == "completed":
            print("Analysis completed!")
            
            # Save full results
            with open(output_dir / "sample1_results.json", "w") as f:
                json.dump(status_data, f, indent=2)
            
            # Extract and save Say-Means analysis
            if "stageA" in doc and "say_means" in doc["stageA"]:
                say_means = doc["stageA"]["say_means"]
                
                # Save Say-Means specific results
                with open(output_dir / "sample1_say_means.json", "w") as f:
                    json.dump(say_means, f, indent=2)
                
                # Create a markdown report
                with open(output_dir / "sample1_say_means_report.md", "w") as f:
                    f.write("# Say-Means Analysis Report\n\n")
                    f.write(f"**Status:** {say_means.get('status', 'N/A')}\n")
                    f.write(f"**Processing Time:** {say_means.get('processing_time', 0):.2f} seconds\n")
                    
                    if say_means.get('token_usage'):
                        tu = say_means['token_usage']
                        f.write(f"**Token Usage:** {tu.get('total_tokens', 0)} total ")
                        f.write(f"({tu.get('prompt_tokens', 0)} prompt, ")
                        f.write(f"{tu.get('completion_tokens', 0)} completion)\n")
                    
                    f.write("\n## Raw Output\n\n")
                    f.write(say_means.get('raw_output', 'No output'))
                    
                    f.write("\n\n## Insights\n\n")
                    for i, insight in enumerate(say_means.get('insights', []), 1):
                        f.write(f"{i}. {insight.get('text', '')}\n")
                    
                    if say_means.get('concepts'):
                        f.write("\n## Concepts Extracted\n\n")
                        for concept in say_means['concepts']:
                            f.write(f"- **{concept.get('name', '')}**: {concept.get('description', '')}\n")
                
                print(f"\nResults saved to output/")
                print(f"  - sample1_job.json (job info)")
                print(f"  - sample1_results.json (full results)")
                print(f"  - sample1_say_means.json (Say-Means analysis)")
                print(f"  - sample1_say_means_report.md (formatted report)")
                
                # Print summary
                print(f"\n=== Summary ===")
                print(f"Insights found: {len(say_means.get('insights', []))}")
                print(f"Concepts extracted: {len(say_means.get('concepts', []))}")
                
                if say_means.get('token_usage'):
                    tu = say_means['token_usage']
                    print(f"Total tokens used: {tu.get('total_tokens', 0)}")
            
            # Extract and save Perspective-Perception analysis
            if "stageA" in doc and "perspective_perception" in doc["stageA"]:
                perspective = doc["stageA"]["perspective_perception"]
                
                # Save Perspective-Perception specific results
                with open(output_dir / "sample1_perspective_perception.json", "w") as f:
                    json.dump(perspective, f, indent=2)
                
                # Create a markdown report
                with open(output_dir / "sample1_perspective_perception_report.md", "w") as f:
                    f.write("# Perspective-Perception Analysis Report\n\n")
                    f.write(f"**Status:** {perspective.get('status', 'N/A')}\n")
                    f.write(f"**Processing Time:** {perspective.get('processing_time', 0):.2f} seconds\n")
                    
                    if perspective.get('token_usage'):
                        tu = perspective['token_usage']
                        f.write(f"**Token Usage:** {tu.get('total_tokens', 0)} total ")
                        f.write(f"({tu.get('prompt_tokens', 0)} prompt, ")
                        f.write(f"{tu.get('completion_tokens', 0)} completion)\n")
                    
                    f.write("\n## Raw Output\n\n")
                    f.write(perspective.get('raw_output', 'No output'))
                    
                    # Extract structured data if available
                    if perspective.get('structured_data'):
                        data = perspective['structured_data']
                        
                        if data.get('perspectives'):
                            f.write("\n\n## Perspectives Identified\n\n")
                            for p in data['perspectives']:
                                f.write(f"- {p}\n")
                        
                        if data.get('perception_gaps'):
                            f.write("\n## Perception Gaps\n\n")
                            for gap in data['perception_gaps']:
                                f.write(f"- {gap}\n")
                        
                        if data.get('viewpoint_alignments'):
                            f.write("\n## Areas of Alignment\n\n")
                            for align in data['viewpoint_alignments']:
                                f.write(f"- {align}\n")
                        
                        if data.get('conflicting_views'):
                            f.write("\n## Conflicting Views\n\n")
                            for conflict in data['conflicting_views']:
                                f.write(f"- {conflict}\n")
                        
                        if data.get('key_insights'):
                            f.write("\n## Key Insights\n\n")
                            for insight in data['key_insights']:
                                f.write(f"- {insight}\n")
                
                print(f"  - sample1_perspective_perception.json (Perspective-Perception analysis)")
                print(f"  - sample1_perspective_perception_report.md (formatted report)")
                
                print(f"\n=== Perspective-Perception Summary ===")
                if perspective.get('structured_data'):
                    data = perspective['structured_data']
                    print(f"Perspectives found: {len(data.get('perspectives', []))}")
                    print(f"Perception gaps: {len(data.get('perception_gaps', []))}")
                    print(f"Alignments: {len(data.get('viewpoint_alignments', []))}")
                    print(f"Conflicts: {len(data.get('conflicting_views', []))}")
                
                if perspective.get('token_usage'):
                    tu = perspective['token_usage']
                    print(f"Tokens used: {tu.get('total_tokens', 0)}")
            
            # Print total token usage
            if doc.get('tokenUsageTotal'):
                total = doc['tokenUsageTotal']
                print(f"\n=== Total Token Usage ===")
                print(f"All analyzers combined: {total.get('total', 0)} tokens")
            
            break
        
        elif status == "error":
            print(f"Job failed: {doc.get('errors', [])}")
            with open(output_dir / "sample1_error.json", "w") as f:
                json.dump(status_data, f, indent=2)
            break
    
    else:
        print(f"Timeout: Job did not complete within {max_attempts * 5} seconds")

if __name__ == "__main__":
    main()
