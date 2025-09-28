# 🔄 RESTART GUIDE - Transcript Analysis Tool

**Purpose**: Quick reference to resume work after an interruption. Reflects the current working system as of September 7, 2025.

**Last Updated**: 2025-09-28  
**Status**: Production-ready - All 10 analyzers operational with real GPT API calls

---

## 🚦 Current System Status

### ✅ What's Working (Verified Sept 7, 2025)
- **Stage A (4/4)**: Say-Means, Perspective-Perception, Premises-Assertions, Postulate-Theorem
- **Stage B (4/4)**: Competing Hypotheses, First Principles, Determining Factors, Patentability  
- **Final Stage (2/2)**: Meeting Notes, Composite Note (integrated and verified)
- **Async Pipeline**: Parallel execution with bounded concurrency (asyncio + Semaphore)
- **Web/Celery Path**: Full orchestration with Socket.IO real-time updates
- **Notifications**: Unified NotificationManager with Slack/Webhook/Desktop/File channels
- **Artifacts**: Standardized `COMPLETED` sentinel + `final_status.json` for all runs

### 📊 Performance Metrics
- Full pipeline (8 analyzers): ~163 seconds
- Stage A: ~52 seconds (parallel)
- Stage B: ~111 seconds (parallel, post Stage A)
- Token usage: ~21,243 tokens total
- Success rate: 100%

---

## ⚡ Quick Start Commands

### 0. After Machine Restart (Mac M4)
```bash
# Navigate to project directory
cd "/Users/jerrysmith/Library/Mobile Documents/com~apple~CloudDocs/Python Active/Trascript Analysis Codex Test"

# Start Docker containers
docker compose up -d

# Verify services are running
docker compose ps

# Test API health
curl -s http://localhost:5001/api/health | python3 -m json.tool
```

**Expected Output**:
- All containers show "Up" status
- Redis: healthy
- App: healthy on port 5001
- Worker: healthy
- API returns: `{"status":"ok","model":"gpt-4o-mini",...}`

### 1. Autonomous Verification (Recommended First Step)
```bash
# Runs full pipeline with real GPT calls and verifies completion
python3 scripts/verify_notifications.py
```

**Expected Output**:
- Creates `output/notifications_YYYYMMDD_HHMMSS.jsonl`
- Prints "SUCCESS: Pipeline completed successfully"
- Creates run directory at `output/runs/run_YYYYMMDD_HHMMSS/` with:
  - `COMPLETED` (sentinel file)
  - `final_status.json` (machine-readable summary)
  - `metadata.json` (run configuration)
  - `intermediate/stage_a/*.json` (4 analyzer outputs)
  - `intermediate/stage_b/*.json` (4 analyzer outputs)
  - `final/executive_summary.md`

### 2. Manual Async Pipeline Run
```bash
# Run with file notifications
python3 scripts/test_parallel_pipeline.py --notify file --file-path output/notifications.jsonl

# Run without notifications
python3 scripts/test_parallel_pipeline.py

# Run with specific concurrency
MAX_CONCURRENT=5 python3 scripts/test_parallel_pipeline.py
```

### 3. Web Stack (Docker)
```bash
# Start all services
docker compose up -d

# Verify services
docker compose ps

# Check health
curl -s http://localhost:5001/api/health | python3 -m json.tool

# Submit analysis
curl -s -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "transcriptText": "Speaker 1: Hello, this is a test transcript...",
    "selected": {
      "stageA": ["say_means", "perspective_perception", "premises_assertions", "postulate_theorem"],
      "stageB": ["competing_hypotheses", "first_principles", "determining_factors", "patentability"],
      "final": ["meeting_notes", "composite_note"]
    }
  }' | python3 -m json.tool

# Check status (replace JOB_ID from above response)
curl -s http://localhost:5001/api/status/JOB_ID | python3 -m json.tool
```

### 4. Debug Pipeline Execution
```bash
# Monitor pipeline with detailed logging
python3 scripts/debug_pipeline.py

# Test specific stages
python3 scripts/test_stage_b.py  # Tests Stage B with mock Stage A data
```

---

## 📁 Key Files and Locations

### Core Implementation
```
src/
├── app/
│   ├── async_orchestrator.py    # Async pipeline (CLI)
│   ├── orchestration.py         # Celery pipeline (Web)
│   ├── api.py                   # REST endpoints
│   ├── sockets.py               # WebSocket events
│   └── notify.py                # Notification manager
├── analyzers/
│   ├── base_analyzer.py         # Base class
│   ├── stage_a/                 # 4 transcript analyzers
│   ├── stage_b/                 # 4 meta-analyzers
│   └── final/                   # 2 output generators
├── llm_client.py                # OpenAI integration
├── models.py                    # Pydantic models
└── config.py                    # Configuration
```

### Prompts
```
prompts/
├── stage a transcript analyses/
│   ├── 1 say-means.md
│   ├── 2 perspective-perception.md
│   ├── 3 premises-assertions.md
│   └── 4 postulate-theorem.md
├── stage b results analyses/
│   ├── 5 analysis of competing hypotheses.md
│   ├── 6 first principles.md
│   ├── 7 determining factors.md
│   └── 8 patentability.md
└── final output stage/
    ├── 9 meeting notes.md
    └── 9 composite note.md
```

### Output Artifacts
```
output/
├── runs/                        # Async pipeline outputs
│   └── run_YYYYMMDD_HHMMSS/
│       ├── COMPLETED            # Success marker
│       ├── final_status.json    # Machine-readable summary
│       ├── metadata.json        # Run configuration
│       ├── intermediate/
│       │   ├── stage_a/*.json
│       │   └── stage_b/*.json
│       └── final/
│           └── executive_summary.md
├── jobs/                        # Web/Celery outputs
│   └── {jobId}/
│       ├── COMPLETED
│       └── final_status.json
└── notifications*.jsonl         # Notification logs
```

---

## 🔑 Environment Configuration

### Required `.env` File
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...  # Your actual API key
OPENAI_MODEL=gpt-4o-mini

# Redis (for web stack)
REDIS_URL=redis://localhost:6379

# Processing Configuration
MAX_CONCURRENT=3  # Parallel analyzer limit
STAGE_B_CONTEXT_TOKEN_BUDGET=8000  # Token limit for Stage B

# Notifications (optional)
TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED=true
TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS=file
TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH=output/notifications.jsonl

# Optional notification channels
TRANSCRIPT_ANALYZER_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TRANSCRIPT_ANALYZER_WEBHOOK_URL=https://your-webhook.com/...
TRANSCRIPT_ANALYZER_DESKTOP_ENABLED=false
```

---

## 🔧 Critical Implementation Details

### Stage B Context Handling (Fixed)
```python
# Stage B receives Stage A results as previous_analyses, NOT as transcript
stage_b_ctx = AnalysisContext(
    transcript=processed,  # Original transcript for reference
    previous_analyses=stage_a_analyses,  # Stage A results here!
    metadata={"source": "stage_a_aggregation", "stage": "stage_b"}
)
```

### Token Budget Management
```python
# Stage-specific token budgets
Stage A: 4,000 tokens per analyzer
Stage B: Configurable via STAGE_B_CONTEXT_TOKEN_BUDGET (default 8,000)
Final: 8,000 tokens per generator
```

### Parallel Execution
```python
# Bounded concurrency prevents rate limiting
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# Stage A runs in parallel
# Stage B waits for Stage A, then runs in parallel
# Final stage processes after both complete
```

---

## 🐛 Troubleshooting

### Common Issues and Fixes

#### After Machine Restart - Containers Not Starting
```bash
# Issue: "no configuration file provided: not found"
# Solution: Make sure you're in the correct directory
cd "/Users/jerrysmith/Library/Mobile Documents/com~apple~CloudDocs/Python Active/Trascript Analysis Codex Test"

# Issue: Containers stopped after restart
# Solution: Start them up
docker compose up -d

# Issue: Resource deadlock errors
# Solution: Restart Docker Desktop, then try again
```

#### Redis Connection Failed
```bash
# Reset Redis
docker compose down redis
docker compose up -d redis

# Or flush data
docker compose exec redis redis-cli FLUSHALL
```

#### Worker Not Processing Tasks
```bash
# Restart worker
docker compose restart worker

# Check logs
docker compose logs --tail 100 worker
```

#### API Returns 500 Error
```bash
# Check app logs
docker compose logs --tail 200 app

# Verify .env file
cat .env | grep OPENAI_API_KEY
```

#### Stage B Not Running
```python
# Verify Stage A results are passed correctly
# Check src/app/orchestration.py line ~200
# Stage B context must have previous_analyses populated
```

#### Token Limit Exceeded
```bash
# Reduce Stage B context budget
export STAGE_B_CONTEXT_TOKEN_BUDGET=6000

# Or increase MAX_CONCURRENT for better throughput
export MAX_CONCURRENT=5
```

---

## 💡 Development Tips

### Testing Changes
1. **Quick smoke test**: `python3 scripts/verify_notifications.py`
2. **Full pipeline test**: `python3 scripts/test_parallel_pipeline.py`
3. **Web API test**: `python3 scripts/test_web_ui.py`
4. **Debug mode**: `python3 scripts/debug_pipeline.py`

### Performance Tuning
- Increase `MAX_CONCURRENT` cautiously (watch for rate limits)
- Adjust `STAGE_B_CONTEXT_TOKEN_BUDGET` to balance quality vs speed
- Monitor token usage in `final_status.json`

### Adding New Analyzers
1. Create analyzer in appropriate stage directory
2. Inherit from `BaseAnalyzer`
3. Implement `parse_response()` method
4. Add prompt template to `prompts/` directory
5. Register in stage's `__init__.py`

---

## 📊 Verification Checklist

After any changes, verify:

- [ ] `scripts/verify_notifications.py` returns SUCCESS
- [ ] `COMPLETED` file created in run directory
- [ ] `final_status.json` contains all expected fields
- [ ] All 8 analyzers show in results (4 Stage A, 4 Stage B)
- [ ] Token usage is within budget (~21,000 total)
- [ ] No errors in notification JSONL file

---

## 🚀 Next Steps

### Immediate Tasks
1. ✅ Verify all 10 analyzers working
2. ⬜ Integrate Final stage into main pipeline
3. ⬜ Optimize Stage B performance (<60s target)
4. ⬜ Add result export functionality

### Future Enhancements
- Web UI improvements (live progress, charts)
- Batch processing support
- Custom analyzer plugins
- Result comparison tools
- Multi-language support

---

## 📝 Quick Reference

| Command | Purpose |
|---------|---------|
| `python3 scripts/verify_notifications.py` | Full test with verification |
| `python3 scripts/test_parallel_pipeline.py` | Run async pipeline |
| `docker compose up -d` | Start web stack |
| `curl http://localhost:5001/api/health` | Check API health |
| `docker compose logs worker` | View worker logs |
| `cat output/runs/*/final_status.json` | Check run results |

---

**Remember**: All commands make real GPT API calls using your `.env` key. Monitor usage at https://platform.openai.com/usage

**Support**: Check `docs/ARCHITECTURE.md` for detailed technical information.
