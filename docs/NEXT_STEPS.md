# Transcript Analysis Tool - Next Development Steps

**Last Updated**: September 6, 2025, 5:28 PM  
**Current Status**: Stage A Complete (All 4 analyzers working), Ready for Stage B

## 🎯 Immediate Next Task: Implement Stage B Analyzers

### Why This Is Next
- All Stage A analyzers are complete and tested
- Stage B analyzers will process the combined Stage A outputs
- Infrastructure is proven with 100% success rate

### Step-by-Step Implementation Guide for Stage B

#### 1. Create the First Stage B Analyzer
```bash
# Create the stage_b directory
mkdir -p src/analyzers/stage_b

# Create the competing hypotheses analyzer
touch src/analyzers/stage_b/competing_hypotheses.py
```

#### 2. Implement Competing Hypotheses Analyzer
```python
# src/analyzers/stage_b/competing_hypotheses.py

from typing import Dict, Any, List
from src.analyzers.base_analyzer import BaseAnalyzer
import json
import re

class CompetingHypothesesAnalyzer(BaseAnalyzer):
    """Applies Analysis of Competing Hypotheses methodology to Stage A results."""
    
    def __init__(self):
        super().__init__(
            name="competing_hypotheses",
            stage="stage_b"  # Important: Stage B processes context, not transcript
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the perspective-perception analysis response."""
        result = {
            "perspectives": [],
            "perception_gaps": [],
            "viewpoint_alignments": [],
            "conflicting_views": []
        }
        
        # Extract perspectives section
        perspectives_match = re.search(
            r'(?:PERSPECTIVES?|VIEWPOINTS?)[:\s]*\n(.*?)(?=\n(?:PERCEPTION|GAPS|CONFLICTS|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if perspectives_match:
            # Parse individual perspectives
            perspective_lines = perspectives_match.group(1).strip().split('\n')
            for line in perspective_lines:
                if line.strip() and not line.strip().startswith('#'):
                    result["perspectives"].append(line.strip())
        
        # Extract perception gaps
        gaps_match = re.search(
            r'(?:PERCEPTION GAPS?|GAPS?)[:\s]*\n(.*?)(?=\n(?:ALIGNMENTS?|CONFLICTS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if gaps_match:
            gap_lines = gaps_match.group(1).strip().split('\n')
            for line in gap_lines:
                if line.strip() and not line.strip().startswith('#'):
                    result["perception_gaps"].append(line.strip())
        
        # Extract alignments
        alignments_match = re.search(
            r'(?:ALIGNMENTS?|AGREEMENTS?)[:\s]*\n(.*?)(?=\n(?:CONFLICTS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if alignments_match:
            alignment_lines = alignments_match.group(1).strip().split('\n')
            for line in alignment_lines:
                if line.strip() and not line.strip().startswith('#'):
                    result["viewpoint_alignments"].append(line.strip())
        
        # Extract conflicts
        conflicts_match = re.search(
            r'(?:CONFLICTS?|DISAGREEMENTS?)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if conflicts_match:
            conflict_lines = conflicts_match.group(1).strip().split('\n')
            for line in conflict_lines:
                if line.strip() and not line.strip().startswith('#'):
                    result["conflicting_views"].append(line.strip())
        
        return result
```

#### 3. Add to Orchestration Pipeline
```python
# Update src/app/orchestration.py

# Add import at the top
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer

# Update the run_pipeline function to include the new analyzer
@celery_app.task(name='orchestration.run_pipeline')
def run_pipeline(job_id: str, transcript: str, config: dict):
    """Run the complete analysis pipeline."""
    try:
        # ... existing code ...
        
        # Stage A: Transcript Analysis
        stage_a_results = {}
        
        # Say-Means Analysis (existing)
        update_status(job_id, "processing", "Running Say-Means analysis...")
        say_means = SayMeansAnalyzer()
        say_means_result = say_means.analyze(transcript)
        stage_a_results["say_means"] = say_means_result
        
        # Perspective-Perception Analysis (NEW)
        update_status(job_id, "processing", "Running Perspective-Perception analysis...")
        perspective = PerspectivePerceptionAnalyzer()
        perspective_result = perspective.analyze(transcript)
        stage_a_results["perspective_perception"] = perspective_result
        
        # ... rest of the pipeline ...
```

#### 4. Test the Implementation
```bash
# Start Docker services if not running
docker compose up -d

# Run the test script
python3 scripts/analyze_sample.py

# Or create a specific test for the new analyzer
python3 -c "
from src.analyzers.stage_a.perspective_perception import PerspectivePerceptionAnalyzer
analyzer = PerspectivePerceptionAnalyzer()
with open('input sample transcripts/sample1.md', 'r') as f:
    transcript = f.read()
result = analyzer.analyze(transcript)
print(json.dumps(result, indent=2))
"
```

## 📋 Complete Task List for Today

### Phase 1: Perspective-Perception Analyzer (1-2 hours)
- [ ] Create `perspective_perception.py` file
- [ ] Implement class with proper parsing logic
- [ ] Add to orchestration pipeline
- [ ] Test with sample transcript
- [ ] Verify token usage is within budget
- [ ] Save test output to `output/` directory

### Phase 2: Premises-Assertions Analyzer (1-2 hours)
- [ ] Create `premises_assertions.py` file
- [ ] Implement premise and assertion extraction
- [ ] Add logical consistency validation
- [ ] Add to orchestration pipeline
- [ ] Test and validate output

### Phase 3: Postulate-Theorem Analyzer (1-2 hours)
- [ ] Create `postulate_theorem.py` file
- [ ] Implement theory-evidence mapping
- [ ] Add hypothesis extraction logic
- [ ] Add to orchestration pipeline
- [ ] Test complete Stage A pipeline

### Phase 4: Integration Testing (1 hour)
- [ ] Run all Stage A analyzers together
- [ ] Verify combined context generation
- [ ] Check total token usage
- [ ] Generate comprehensive Stage A report

## 🔍 Testing Checklist

For each analyzer implementation:
1. ✓ Verify prompt file exists and loads correctly
2. ✓ Test with sample transcript
3. ✓ Check token usage (should be < 4000)
4. ✓ Validate output structure matches expected format
5. ✓ Ensure error handling works properly
6. ✓ Confirm results are saved to Redis
7. ✓ Verify Socket.IO updates are sent

## 🚀 Quick Commands

### Start Development
```bash
# 1. Ensure Docker is running
docker compose up -d

# 2. Check service health
curl http://localhost:5001/api/health

# 3. Watch logs
docker compose logs -f worker
```

### Test New Analyzer
```bash
# Test individual analyzer
python3 scripts/test_analyzer.py perspective_perception

# Test full pipeline
python3 scripts/analyze_sample.py
```

### Debug Issues
```bash
# Check Redis for job status
docker compose exec redis redis-cli
> GET job:status:<job_id>

# View Celery worker logs
docker compose logs worker --tail=100

# Restart services if needed
docker compose restart
```

## 📊 Expected Outputs

### Perspective-Perception Analyzer
```json
{
  "perspectives": [
    "Speaker A views the problem from a technical standpoint",
    "Speaker B focuses on business implications",
    "Speaker C considers user experience"
  ],
  "perception_gaps": [
    "Technical team underestimates implementation complexity",
    "Business team not aware of technical constraints"
  ],
  "viewpoint_alignments": [
    "All agree on the importance of user satisfaction",
    "Consensus on timeline urgency"
  ],
  "conflicting_views": [
    "Disagreement on resource allocation",
    "Different priorities for feature implementation"
  ]
}
```

### Premises-Assertions Analyzer
```json
{
  "premises": [
    {
      "statement": "The market is growing at 20% annually",
      "speaker": "Speaker A",
      "type": "factual_claim"
    }
  ],
  "assertions": [
    {
      "claim": "We need to double our team size",
      "supporting_premises": ["market growth", "competitor activity"],
      "logical_validity": "strong"
    }
  ],
  "logical_gaps": [
    "Assumption about market continuity not validated"
  ]
}
```

### Postulate-Theorem Analyzer
```json
{
  "postulates": [
    {
      "hypothesis": "Increasing automation will reduce costs by 30%",
      "confidence": "medium",
      "evidence": ["industry benchmarks", "pilot results"]
    }
  ],
  "theorems": [
    {
      "theory": "Customer retention correlates with response time",
      "supporting_data": ["Q3 metrics", "customer surveys"],
      "strength": "strong"
    }
  ],
  "theoretical_frameworks": [
    "Lean methodology",
    "Agile development principles"
  ]
}
```

## 🎯 Success Criteria

By end of today, you should have:
1. ✅ All 4 Stage A analyzers implemented
2. ✅ Each analyzer tested individually
3. ✅ Complete Stage A pipeline working
4. ✅ Combined context generation validated
5. ✅ Documentation updated with progress

## 📝 Notes for Tomorrow

Once Stage A is complete, the next priority will be:
1. **Stage B Analyzers** - These will process the combined Stage A outputs
2. **Context Aggregation** - Ensure proper formatting of Stage A results for Stage B
3. **Pipeline Optimization** - Consider parallel processing for Stage A analyzers

## 🔗 Related Documentation

- [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) - Complete roadmap
- [DEVELOPMENT_STATUS.md](./DEVELOPMENT_STATUS.md) - Current progress
- [RESTART.md](../RESTART.md) - Quick start guide
- [PRD_Transcript_Analysis_Tool.md](../PRD_Transcript_Analysis_Tool.md) - Requirements

## 💡 Pro Tips

1. **Use Say-Means as Template**: The structure is proven to work
2. **Test Incrementally**: Don't wait until all analyzers are done
3. **Monitor Token Usage**: Keep an eye on the 4000 token budget
4. **Check Logs Often**: `docker compose logs -f worker` is your friend
5. **Save Outputs**: Keep test results in `output/` for comparison

---

**Ready to Start?** Begin with creating the Perspective-Perception analyzer file and follow the implementation guide above. The infrastructure is ready and waiting for your code!
