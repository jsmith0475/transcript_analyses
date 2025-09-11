# Intermediate Output Feature Documentation

## Overview
The Transcript Analysis Tool now supports saving intermediate results for each analyzer as it completes processing. This feature provides better debugging capability, audit trails, and allows for partial recovery if the pipeline fails.

## Implementation Details

### Base Analyzer Enhancement
The `BaseAnalyzer` class in `src/analyzers/base_analyzer.py` has been enhanced with:

1. **`save_intermediate_result()` method**: Automatically saves results after each analysis
2. **`format_result_as_markdown()` method**: Converts analysis results to readable Markdown format
3. **Optional parameters** in `analyze_sync()`:
   - `save_intermediate`: Boolean to enable/disable intermediate saving (default: True)
   - `output_dir`: Custom output directory (default: output/intermediate)

### File Structure (Organized by Run)
```
output/runs/
└── run_YYYYMMDD_HHMMSS/           # Each run gets its own directory
    ├── metadata.json               # Run metadata and configuration
    ├── intermediate/               # All intermediate analysis files
    │   ├── stage_a/
    │   │   ├── say_means.json
    │   │   ├── say_means.md
    │   │   ├── perspective_perception.json
    │   │   ├── perspective_perception.md
    │   │   ├── premises_assertions.json
    │   │   ├── premises_assertions.md
    │   │   ├── postulate_theorem.json
    │   │   └── postulate_theorem.md
    │   ├── stage_b/
    │   │   ├── competing_hypotheses.json
    │   │   ├── competing_hypotheses.md
    │   │   ├── first_principles.json
    │   │   ├── first_principles.md
    │   │   ├── determining_factors.json
    │   │   ├── determining_factors.md
    │   │   ├── patentability.json
    │   │   └── patentability.md
    │   └── stage_a_context.json   # Aggregated Stage A results
    ├── final/                      # Final output files
    │   ├── executive_summary.md
    │   └── full_report.json
    └── logs/                       # Run logs (optional)
```

### Run Metadata File
The `metadata.json` file tracks:
- Run ID and timestamps
- Configuration used (model, temperature, etc.)
- Stage progression and status
- Token usage and costs
- Success/failure information

## File Formats

### JSON Format
Each JSON file contains:
- `analyzer_name`: Name of the analyzer
- `status`: Processing status (completed/error)
- `timestamp`: When the analysis was performed
- `processing_time`: Time taken in seconds
- `token_usage`: Detailed token consumption
- `raw_output`: Complete LLM response
- `structured_data`: Parsed structured data
- `insights`: List of extracted insights
- `concepts`: List of identified concepts
- `error_message`: Error details if failed

### Markdown Format
Each Markdown file includes:
- **Header**: Analyzer name, date, stage, status
- **Processing Metrics**: Time and token usage
- **Key Insights**: Formatted list of insights
- **Identified Concepts**: Concepts with descriptions
- **Structured Analysis**: JSON data in code blocks
- **Raw Output**: Complete or truncated LLM response

## Usage Examples

### Running with Intermediate Output
```python
from src.analyzers.stage_a.say_means import SayMeansAnalyzer
from src.models import AnalysisContext

analyzer = SayMeansAnalyzer()
result = analyzer.analyze_sync(
    context=context,
    save_intermediate=True,  # Enable intermediate saving
    output_dir=Path("output/my_run")  # Custom directory
)
```

### Test Scripts
Two test scripts demonstrate the feature:

1. **Basic intermediate output** (`scripts/test_intermediate_output.py`):
```bash
python3 scripts/test_intermediate_output.py
```

2. **Organized run directories** (`scripts/test_organized_output.py`):
```bash
python3 scripts/test_organized_output.py
```

This will:
1. Run all 8 analyzers (4 Stage A + 4 Stage B)
2. Save intermediate results for each
3. Create a timestamped output directory
4. Generate both JSON and Markdown files
5. Display progress and file locations

## Benefits

### 1. Clean Organization
- Each run is completely self-contained in its own directory
- Easy to find all related files for a specific analysis
- No filename conflicts between runs

### 2. Debugging Capability
- See exactly what each analyzer produced
- Identify which analyzer had issues
- Review raw LLM responses

### 3. Audit Trail
- Track analysis progression via metadata.json
- Document processing time and token usage
- Maintain historical records of all runs

### 4. Partial Recovery
- If pipeline fails partway, completed analyses are saved
- Can resume from saved intermediate results
- No need to re-run successful analyzers

### 5. Individual Review
- Examine specific analyzer outputs in detail
- Share individual analysis results
- Compare different analyzer perspectives

### 6. Cost Tracking
- Monitor token usage per analyzer
- Track total costs per run
- Identify expensive operations
- Optimize prompt engineering

### 7. Easy Cleanup
- Delete entire run directory to remove all related files
- Archive completed runs by moving directories
- Compare multiple runs side by side

## Configuration

### Enable/Disable Globally
In `src/config.py`, add:
```python
class OutputConfig(BaseModel):
    save_intermediate: bool = True
    intermediate_dir: str = "output/intermediate"
```

### Per-Analyzer Control
Each analyzer call can override:
```python
result = analyzer.analyze_sync(
    context=context,
    save_intermediate=False  # Disable for this analyzer
)
```

## Performance Impact
- **Minimal overhead**: File I/O is fast compared to LLM calls
- **Disk usage**: ~10-50KB per analyzer (JSON + Markdown)
- **Total for full pipeline**: ~400KB for 8 analyzers

## Future Enhancements

1. **Compression**: Gzip intermediate files to save space
2. **Retention Policy**: Auto-delete files older than X days
3. **Web UI Integration**: Display intermediate results in real-time
4. **Comparison Tool**: Diff results between runs
5. **Resume Capability**: Restart pipeline from saved intermediates

## Troubleshooting

### Files Not Being Created
- Check `save_intermediate` parameter is True
- Verify output directory permissions
- Check disk space availability

### Incomplete Markdown Files
- Raw output may be truncated if >5000 characters
- Full output always available in JSON file

### Timestamp Mismatches
- Each analyzer saves with its completion timestamp
- Use run timestamp for grouping related files

## Example Output

### Sample Markdown Header
```markdown
# Say Means Analysis

**Date:** September 06, 2025 19:42:00
**Stage:** Stage A
**Status:** completed

## Processing Metrics
- **Processing Time:** 85.61 seconds
- **Tokens Used:** 8,672
  - Prompt: 3,832
  - Completion: 4,840
```

### Sample JSON Structure
```json
{
  "analyzer_name": "say_means",
  "status": "completed",
  "timestamp": "20250906_194200",
  "processing_time": 85.61,
  "token_usage": {
    "prompt_tokens": 3832,
    "completion_tokens": 4840,
    "total_tokens": 8672
  },
  "insights": [...],
  "concepts": [...],
  "structured_data": {...}
}
```

## Conclusion

The intermediate output feature significantly enhances the transparency and debuggability of the Transcript Analysis Tool. It provides comprehensive logging of each analysis step while maintaining minimal performance overhead. This feature is essential for production deployments where audit trails and error recovery are critical.
