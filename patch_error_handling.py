#!/usr/bin/env python3
"""Apply error handling patches to fix Stage B/Final starting while Stage A errors."""

from pathlib import Path
import re

def patch_sockets():
    """Add analyzer_error emitter to sockets.py"""
    p = Path('src/app/sockets.py')
    src = p.read_text()
    
    # Check if already patched
    if 'analyzer_error' in src:
        print('✓ sockets.py already has analyzer_error')
        return
    
    # Find job_error function and add analyzer_error before it
    needle = '''def job_error(job_id: str, error_code: str, message: str) -> None:
    emit_progress(
        "job.error",
        {
            "jobId": job_id,
            "errorCode": error_code,
            "message": message,
        },
    )'''
    
    insert = '''def analyzer_error(job_id: str, stage: str, analyzer: str, error_message: str, processing_time_ms: int | None = None) -> None:
    """Emit analyzer error event."""
    emit_progress(
        "analyzer.error",
        {
            "jobId": job_id,
            "stage": stage,
            "analyzer": analyzer,
            "errorMessage": error_message,
            "processingTimeMs": processing_time_ms,
        },
    )


'''
    
    if needle in src:
        src = src.replace(needle, insert + needle)
        p.write_text(src)
        print('✓ Patched sockets.py: added analyzer_error emitter')
    else:
        print('✗ Could not find job_error in sockets.py')

def patch_orchestrator_imports():
    """Update imports to include analyzer_error"""
    p = Path('src/app/parallel_orchestration.py')
    src = p.read_text()
    
    if 'analyzer_error' in src:
        print('✓ parallel_orchestration.py already imports analyzer_error')
        return
    
    old = '''from src.app.sockets import (
    job_queued,
    analyzer_started,
    analyzer_completed,
    stage_completed,
    job_completed,
    job_error,
)'''
    
    new = '''from src.app.sockets import (
    job_queued,
    analyzer_started,
    analyzer_completed,
    analyzer_error,
    stage_completed,
    job_completed,
    job_error,
)'''
    
    if old in src:
        src = src.replace(old, new)
        p.write_text(src)
        print('✓ Updated parallel_orchestration.py imports')
    else:
        print('✗ Could not update imports in parallel_orchestration.py')

def patch_stage_a_error():
    """Persist Stage A errors to Redis and emit analyzer_error"""
    p = Path('src/app/parallel_orchestration.py')
    src = p.read_text()
    
    # Check if already patched
    if 'Persist error state to Redis' in src:
        print('✓ Stage A error handling already patched')
        return
    
    # Find Stage A except block
    pattern = r'(    except Exception as e:\n        logger\.exception\(f"Error in Stage A analyzer \{analyzer_name\}: \{e\}"\)\n        return \{"error": str\(e\), "status": "error"\})'
    
    replacement = '''    except Exception as e:
        logger.exception(f"Error in Stage A analyzer {analyzer_name}: {e}")
        
        # Persist error state to Redis so UI reflects failure
        try:
            status_doc = _load_status(job_id)
            if "stageA" not in status_doc:
                status_doc["stageA"] = {}
            status_doc["stageA"][analyzer_name] = {
                "status": "error",
                "error_message": str(e),
            }
            _save_status(job_id, status_doc)
        except Exception:
            pass
        
        # Emit analyzer.error so UI can render red tile
        try:
            analyzer_error(job_id, "stage_a", analyzer_name, str(e))
        except Exception:
            pass
        
        return {"status": "error", "error_message": str(e)}'''
    
    src_new = re.sub(pattern, replacement, src)
    if src_new != src:
        p.write_text(src_new)
        print('✓ Patched Stage A error handling')
    else:
        print('✗ Could not patch Stage A error handling')

def patch_stage_b_error():
    """Persist Stage B errors to Redis and emit analyzer_error"""
    p = Path('src/app/parallel_orchestration.py')
    src = p.read_text()
    
    # Find Stage B except block
    pattern = r'(    except Exception as e:\n        logger\.exception\(f"Error in Stage B analyzer \{analyzer_name\}: \{e\}"\)\n        return \{"error": str\(e\), "status": "error"\})'
    
    replacement = '''    except Exception as e:
        logger.exception(f"Error in Stage B analyzer {analyzer_name}: {e}")
        
        # Persist error state to Redis so UI reflects failure
        try:
            status_doc = _load_status(job_id)
            if "stageB" not in status_doc:
                status_doc["stageB"] = {}
            status_doc["stageB"][analyzer_name] = {
                "status": "error",
                "error_message": str(e),
            }
            _save_status(job_id, status_doc)
        except Exception:
            pass
        
        # Emit analyzer.error so UI can render red tile
        try:
            analyzer_error(job_id, "stage_b", analyzer_name, str(e))
        except Exception:
            pass
        
        return {"status": "error", "error_message": str(e)}'''
    
    src_new = re.sub(pattern, replacement, src)
    if src_new != src:
        p.write_text(src_new)
        print('✓ Patched Stage B error handling')
    else:
        print('✗ Could not patch Stage B error handling')

def patch_ui_error_handling():
    """Update UI to handle analyzer.error events"""
    p = Path('src/app/static/js/ui.js')
    src = p.read_text()
    
    # Check if already patched
    if 'analyzer.error' in src:
        print('✓ ui.js already handles analyzer.error')
        return
    
    # Expand condition to include analyzer.error
    src = src.replace(
        'if (type === "analyzer.started" || type === "analyzer.completed") {',
        'if (type === "analyzer.started" || type === "analyzer.completed" || type === "analyzer.error") {'
    )
    
    # Replace the completed status block to handle both completed and error
    old_block = '''      } else {
        statusEl.textContent = "Completed";
        statusEl.className = "badge bg-green-100 text-green-700";
        tile.setAttribute("data-status", "completed");'''
    
    new_block = '''      } else if (type === "analyzer.completed") {
        statusEl.textContent = "Completed";
        statusEl.className = "badge bg-green-100 text-green-700";
        tile.setAttribute("data-status", "completed");
      } else if (type === "analyzer.error") {
        statusEl.textContent = "Error";
        statusEl.className = "badge bg-red-100 text-red-700";
        tile.setAttribute("data-status", "error");
        // Store error message for display
        if (payload.errorMessage) {
          tile.setAttribute("data-error", payload.errorMessage);
        }'''
    
    src = src.replace(old_block, new_block)
    
    # Ensure errors count as completed for progress
    # Find the incProgress() call and ensure it runs for errors too
    src = src.replace(
        'if (tile.getAttribute("data-complete") !== "1") {',
        'if (tile.getAttribute("data-complete") !== "1" && (type === "analyzer.completed" || type === "analyzer.error")) {'
    )
    
    p.write_text(src)
    print('✓ Patched ui.js to handle analyzer.error events')

if __name__ == '__main__':
    print('Applying error handling patches...\n')
    patch_sockets()
    patch_orchestrator_imports()
    patch_stage_a_error()
    patch_stage_b_error()
    patch_ui_error_handling()
    print('\n✅ All patches applied successfully!')
