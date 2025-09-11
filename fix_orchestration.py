#!/usr/bin/env python3
"""Fix orchestration to ensure stages run sequentially."""

from pathlib import Path

def fix_orchestration():
    """Fix the run_final_stage to ensure it properly waits for Stage B results."""
    
    p = Path('src/app/parallel_orchestration.py')
    content = p.read_text()
    
    # Fix 1: Make run_final_stage require all_results (not optional)
    # Change the function signature to make all_results required
    old_sig = '''def run_final_stage(
    all_results: Optional[Dict[str, Any]],
    job_id: str,'''
    
    new_sig = '''def run_final_stage(
    all_results: Dict[str, Any],  # Made required - must receive from Stage B
    job_id: str,'''
    
    content = content.replace(old_sig, new_sig)
    
    # Fix 2: Remove the fallback to Redis loading
    # This prevents Final from running if Stage B hasn't completed
    old_fallback = '''        # If all_results not provided, load from Redis
        if all_results is None:
            status_doc = _load_status(job_id)
            all_results = {
                "stageA": status_doc.get("stageA", {}),
                "stageB": status_doc.get("stageB", {})
            }'''
    
    new_fallback = '''        # all_results must be provided by Stage B completion
        if all_results is None:
            logger.error(f"Final stage called without Stage B results for job {job_id}")
            raise ValueError("Final stage requires completed Stage B results")'''
    
    content = content.replace(old_fallback, new_fallback)
    
    # Write the fixed content
    p.write_text(content)
    print("✅ Fixed run_final_stage to require Stage B completion")
    
    # Fix 3: Ensure complete_stage_b returns proper results
    # Check if it's already returning the combined results
    if 'return all_results' not in content:
        print("⚠️  Warning: complete_stage_b might not be returning all_results properly")

if __name__ == '__main__':
    fix_orchestration()
