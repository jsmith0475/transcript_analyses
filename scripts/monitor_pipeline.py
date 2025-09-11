#!/usr/bin/env python3
"""
Monitor the progress of a running pipeline by checking the output directory.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

def monitor_run(run_dir: str):
    """Monitor a pipeline run."""
    run_path = Path(run_dir)
    
    if not run_path.exists():
        print(f"❌ Run directory not found: {run_dir}")
        return
    
    print(f"\n📊 Monitoring: {run_dir}")
    print("=" * 60)
    
    # Check metadata
    metadata_path = run_path / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        print(f"Status: {metadata.get('status', 'unknown')}")
        
        # Check stages
        stages = metadata.get('stages', {})
        
        # Stage A
        stage_a = stages.get('stage_a', {})
        print(f"\n📁 Stage A: {stage_a.get('status', 'pending')}")
        if stage_a.get('analyzers'):
            print(f"   Completed: {', '.join(stage_a['analyzers'])}")
            if 'total_tokens' in stage_a:
                print(f"   Tokens: {stage_a['total_tokens']:,}")
        
        # Stage B
        stage_b = stages.get('stage_b', {})
        print(f"\n📁 Stage B: {stage_b.get('status', 'pending')}")
        if stage_b.get('analyzers'):
            print(f"   Completed: {', '.join(stage_b['analyzers'])}")
            if 'total_tokens' in stage_b:
                print(f"   Tokens: {stage_b['total_tokens']:,}")
                if stage_b['total_tokens'] < 4000:
                    print(f"   ⚠️  WARNING: Low token count!")
    
    # Check files
    print("\n📂 Files created:")
    
    # Stage A files
    stage_a_dir = run_path / "intermediate" / "stage_a"
    if stage_a_dir.exists():
        files = list(stage_a_dir.glob("*.json"))
        print(f"   Stage A: {len(files)} analyzer outputs")
        for f in files:
            size_kb = f.stat().st_size / 1024
            print(f"      - {f.stem}: {size_kb:.1f} KB")
    
    # Stage B files
    stage_b_dir = run_path / "intermediate" / "stage_b"
    if stage_b_dir.exists():
        files = list(stage_b_dir.glob("*.json"))
        if files:
            print(f"   Stage B: {len(files)} analyzer outputs")
            for f in files:
                size_kb = f.stat().st_size / 1024
                print(f"      - {f.stem}: {size_kb:.1f} KB")
                
                # Check token usage in Stage B files
                with open(f, 'r') as jf:
                    data = json.load(jf)
                    tokens = data.get('token_usage', {}).get('total_tokens', 0)
                    if tokens < 1000:
                        print(f"        ⚠️  Only {tokens} tokens used!")
    
    # Check for context debug file
    context_debug = run_path / "intermediate" / "stage_b_context_debug.txt"
    if context_debug.exists():
        size_kb = context_debug.stat().st_size / 1024
        print(f"\n📝 Stage B context debug file: {size_kb:.1f} KB")
    
    # Final outputs
    final_dir = run_path / "final"
    if final_dir.exists():
        files = list(final_dir.glob("*"))
        if files:
            print(f"\n📄 Final outputs: {len(files)} files")
            for f in files:
                print(f"      - {f.name}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        monitor_run(sys.argv[1])
    else:
        # Default to the most recent run
        output_dir = Path("output/runs")
        if output_dir.exists():
            runs = sorted(output_dir.glob("run_*"))
            if runs:
                monitor_run(str(runs[-1]))
            else:
                print("No runs found in output/runs/")
        else:
            print("Output directory not found")
