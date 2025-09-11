/**
 * App bootstrap: wire UI, API, and WS for end-to-end flow.
 */
(function () {
  const el = window.UI.elements;

  // Simple state
  let pollingTimer = null;
  let loadedCtxAtoB = false;
  let loadedCtxBtoFinal = false;

  // Helpers for fast per-analyzer result population when WS analyzer.completed fires
  function normalizeStageKeyLocal(stage) {
    const s = String(stage || "").toLowerCase();
    if (s === "stage_a" || s === "stagea") return "stageA";
    if (s === "stage_b" || s === "stageb") return "stageB";
    if (s === "final" || s === "final_stage" || s === "finalstage") return "final";
    return s;
  }

  function getCurrentJobId() {
    const txt = (window.UI && window.UI.elements && window.UI.elements.jobIndicator().textContent) || "";
    return String(txt).replace(/^Job:\s*/, "").trim();
  }

  function hasStageSelection(stageKey) {
    // Detect if any tile for this stage currently has selection ring
    return !!document.querySelector(`#progressGrid [id^="tile-${stageKey}-"].ring-2`);
  }

  async function fetchAndSetAnalyzerMarkdown(stageKey, analyzerName) {
    try {
      const jobId = getCurrentJobId();
      if (!jobId) return;
      const { ok, doc } = await window.API.getStatus(jobId);
      if (!ok || !doc) return;
      if (stageKey === "final") {
        // For final, prefer files-first loader handled elsewhere; no-op here
        return;
      }
      const bag = stageKey === "stageA" ? (doc.stageA || {}) : (doc.stageB || {});
      const r = bag[analyzerName] || {};
      const md = typeof r.raw_output === "string" ? r.raw_output : "";
      if (md) {
        window.UI.setAnalyzerMarkdown(stageKey, analyzerName, md);
      }
    } catch (e) {
      // ignore
    }
  }

  function setProgressBar(percent) {
    const pct = Math.max(0, Math.min(100, Math.round(percent || 0)));
    const bar = document.querySelector("#progressInner");
    const label = document.querySelector("#progressLabel");
    if (bar) bar.style.width = `${pct}%`;
    if (label) label.textContent = `${pct}%`;
  }

  async function init() {
    window.UI.wireStaticHandlers();

    // File choose -> load into textarea (client-only for now)
    el.chooseFileBtn().addEventListener("click", () => el.fileInput().click());
    el.fileInput().addEventListener("change", onFileChosen);

    // Load prompt options and render analyzer lists
    try {
      // Ensure filesystem prompts are registered on initial load
      try { await window.API.rescanAnalyzers(); } catch (e) { /* non-fatal */ }
      const options = await window.API.getPromptOptions();
      window.UI.renderAnalyzerLists(options);
    } catch (e) {
      alert("Failed to load prompt options: " + e.message);
    }

    // Start/reset handlers
    el.startBtn().addEventListener("click", onStartAnalysis);
    el.resetBtn().addEventListener("click", onReset);

    // WS progress subscription
    window.WS.onEvent((evt) => {
      // Ignore WS events belonging to a different job to prevent
      // stale updates from prior runs affecting the current UI.
      try {
        const evtJob = evt && evt.payload && String(evt.payload.jobId || "").trim();
        const curJob = getCurrentJobId();
        if (evtJob && curJob && evtJob !== curJob) {
          return;
        }
      } catch {}

      window.UI.updateProgress(evt);
      
      // Handle log events
      if (evt && evt.type && evt.type.startsWith("log.")) {
        const level = evt.type.replace("log.", "").toUpperCase();
        const message = evt.payload && evt.payload.message || "No message";
        const timestamp = evt.payload && evt.payload.timestamp || new Date().toISOString();
        
        // Add to debug log panel if function exists
        if (typeof addDebugLogEntry === 'function') {
          addDebugLogEntry(level, message, timestamp);
        }

        // Surface inter-stage context to the new bottom panel
        if (evt.type === 'log.info') {
          try {
            if (message === 'Stage B context assembled' && typeof window.setInterstageContext === 'function') {
              window.setInterstageContext('AtoB', evt.payload || {});
            }
            if (message === 'Final context assembled' && typeof window.setInterstageContext === 'function') {
              window.setInterstageContext('BtoFinal', evt.payload || {});
            }
          } catch (e) {
            // ignore UI errors
          }
        }
      }
      
      // Also log analyzer events to debug panel
      if (evt && evt.type === "analyzer.started") {
        const stage = evt.payload && evt.payload.stage || "unknown";
        const analyzer = evt.payload && evt.payload.analyzer || "unknown";
        if (typeof addDebugLogEntry === 'function') {
          addDebugLogEntry("INFO", `Starting ${stage} analyzer: ${analyzer}`, new Date().toISOString());
        }
      }
      
      if (evt && evt.type === "analyzer.completed") {
        const stage = (evt.payload && evt.payload.stage) || "unknown";
        const analyzer = (evt.payload && evt.payload.analyzer) || "unknown";
        const tokens = (evt.payload && evt.payload.tokenUsage && evt.payload.tokenUsage.total) || 0;
        if (typeof addDebugLogEntry === 'function') {
          addDebugLogEntry("INFO", `Completed ${stage} analyzer: ${analyzer} (${tokens} tokens)`, new Date().toISOString());
        }
        // Immediately fetch and populate this analyzer's markdown so it becomes selectable/viewable
        (async () => {
          const stageKey = normalizeStageKeyLocal(stage);
          await fetchAndSetAnalyzerMarkdown(stageKey, analyzer);
          // If nothing is selected for this stage yet, auto-select this analyzer to reveal the output
          if (!hasStageSelection(stageKey)) {
            try {
              window.UI.setActiveAnalyzer(stageKey, analyzer);
            } catch (e) {
              // ignore
            }
          }
        })();
      }
      
      if (evt && evt.type === "stage.completed") {
        const stage = (evt.payload && evt.payload.stage) || "unknown";
        if (typeof addDebugLogEntry === 'function') {
          addDebugLogEntry("INFO", `Stage ${stage} completed`, new Date().toISOString());
        }
        // If Final stage completed, fetch Final outputs immediately
        if (String(stage).toLowerCase() === "final" || String(stage).toLowerCase() === "final_stage") {
          fetchFinalOutputs();
          // Socket-driven insights disabled; polling path will load after files exist
        }
      }
      
      if (evt && evt.type === "job.error") {
        const error = evt.payload && evt.payload.error || "Unknown error";
        if (typeof addDebugLogEntry === 'function') {
          addDebugLogEntry("ERROR", `Job error: ${error}`, new Date().toISOString());
        }
        // Re-enable run controls on error
        if (window.UI && typeof window.UI.enableRunControls === "function") {
          window.UI.enableRunControls();
        }
      }
      
      if (evt && evt.type === "job.completed") {
        // stop polling and fetch final deliverables
        if (pollingTimer) {
          clearInterval(pollingTimer);
          pollingTimer = null;
        }
        fetchFinalOutputs();
        // Re-enable run controls on completion
        if (window.UI && typeof window.UI.enableRunControls === "function") {
          window.UI.enableRunControls();
        }

        if (typeof addDebugLogEntry === 'function') {
          const totalTokens = evt.payload && evt.payload.totalTokenUsage && evt.payload.totalTokenUsage.total || 0;
          const timeMs = evt.payload && evt.payload.totalProcessingTimeMs || 0;
          addDebugLogEntry("INFO", `Pipeline completed: ${totalTokens} tokens, ${(timeMs/1000).toFixed(2)}s`, new Date().toISOString());
        }
        // Socket-driven insights disabled; polling path will load after files exist
      }
      // insights.updated ignored (simplify to file-based loading only)
    });
  }

  async function onFileChosen(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    // Validate extension and size
    const allowed = [".txt", ".md", ".markdown"];
    const name = (file.name || "").toLowerCase();
    const okExt = allowed.some((ext) => name.endsWith(ext));
    if (!okExt) {
      alert("Unsupported file type. Allowed: .txt, .md, .markdown");
      e.target.value = "";
      return;
    }
    const maxBytes = 10 * 1024 * 1024; // 10MB
    if (file.size > maxBytes) {
      alert("File exceeds 10MB limit.");
      e.target.value = "";
      return;
    }
    el.chosenFileName().textContent = file.name;

    // Read file and place in textarea
    try {
      const text = await file.text();
      el.transcriptText().value = text || "";
    } catch (err) {
      alert("Failed to read file: " + err.message);
    }
  }

  function onReset() {
    if (window.UI && typeof window.UI.enableRunControls === "function") { window.UI.enableRunControls(); }
    el.transcriptText().value = "";
    if (el.fileInput()) el.fileInput().value = "";
    el.chosenFileName().textContent = "";
    window.UI.setJobIndicator("");
    window.UI.clearProgress();
    // Clear results
    window.UI.showResults("stageA", "");
    window.UI.showResults("stageB", "");
    window.UI.showResults("final", "");
    // Clear Insights panel on reset
    try { if (typeof window.clearInsights === 'function') window.clearInsights(); } catch {}
  }

  function buildPayload() {
    const transcriptText = (el.transcriptText().value || "").trim();
    const { selected, promptSelection, stageBOptions, finalOptions, models } = window.UI.getSelections();

    if (!transcriptText) {
      throw new Error("Please paste transcript text or choose a file.");
    }

    const payload = {
      transcriptText,
      selected,
      options: {
        stageBOptions,
        finalOptions,
        models, // per-stage model overrides
      },
      promptSelection,
    };
    return payload;
  }

  async function onStartAnalysis() {
    // Prevent duplicate submissions if a run is already active
    const startEl = el.startBtn && el.startBtn();
    if (startEl && startEl.disabled) return;

    // Clear prior indicators
    window.UI.clearProgress();
    window.UI.setJobIndicator("");

    // Seed pending tiles and progress bar immediately so user sees activity
    // Use current selections to determine expected analyzers (Stage A + Stage B)
    let selections;
    try {
      selections = window.UI.getSelections();
    } catch (e) {
      // Fallback: no selections available
      selections = { selected: { stageA: [], stageB: [] } };
    }
    try {
      window.UI.seedPendingTiles(
        (selections.selected && selections.selected.stageA) || [],
        (selections.selected && selections.selected.stageB) || [],
        (selections.selected && selections.selected.final) || []
      );
    } catch {}

    // Build payload for API
    let payload;
    try {
      payload = buildPayload();
    } catch (e) {
      alert(e.message || "Invalid input");
      return;
    }

    try {
      // Disable run controls while the job is in progress
      if (window.UI && typeof window.UI.disableRunControls === "function") {
        window.UI.disableRunControls();
      }
      // Clear Insights at the start of a new run
      try { if (typeof window.clearInsights === 'function') window.clearInsights(); } catch {}
      const { jobId } = await window.API.analyze(payload);
      if (!jobId) {
        alert("Failed to start analysis: missing jobId");
        return;
      }
      window.UI.setJobIndicator(jobId);

      // Begin polling status doc to surface incremental raw outputs for Stage A/B
      startStatusPolling(jobId);
      // Do not auto-load insights here; final completion/polling will load when files are ready
    } catch (e) {
      alert("Error starting analysis: " + e.message);
    }
  }

  function startStatusPolling(jobId) {
    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
    const poll = async () => {
      try {
        const { ok, doc } = await window.API.getStatus(jobId);
        if (!ok || !doc) return;

        // Update per-analyzer markdown so user can view each analyzer individually
        const stageA = doc.stageA || {};
        const stageB = doc.stageB || {};
        const finalStage = doc.final || {};
        for (const name of Object.keys(stageA)) {
          const r = stageA[name] || {};
          const md = typeof r.raw_output === "string" ? r.raw_output : "";
          if (md) window.UI.setAnalyzerMarkdown("stageA", name, md);
        }
        for (const name of Object.keys(stageB)) {
          const r = stageB[name] || {};
          const md = typeof r.raw_output === "string" ? r.raw_output : "";
          if (md) window.UI.setAnalyzerMarkdown("stageB", name, md);
        }

        // Attempt to load inter-stage contexts from job files as a fallback
        try {
          // Stage A -> Stage B context: when any Stage B entry exists
          if (!loadedCtxAtoB && Object.keys(stageB).length > 0 && typeof window.setInterstageContext === 'function') {
            const params = new URLSearchParams();
            params.set('jobId', jobId);
            params.set('path', 'intermediate/stage_b_context.txt');
            const res = await fetch(`/api/job-file?${params.toString()}`);
            const j = await res.json().catch(() => ({}));
            if (res.ok && j && j.ok && typeof j.content === 'string' && j.content.length) {
              window.setInterstageContext('AtoB', { contextText: j.content });
              loadedCtxAtoB = true;
            }
          }
          // Stage B -> Final context: when any Final entry exists
          if (!loadedCtxBtoFinal && Object.keys(finalStage).length > 0 && typeof window.setInterstageContext === 'function') {
            const params2 = new URLSearchParams();
            params2.set('jobId', jobId);
            params2.set('path', 'final/context_combined.txt');
            const res2 = await fetch(`/api/job-file?${params2.toString()}`);
            const j2 = await res2.json().catch(() => ({}));
            if (res2.ok && j2 && j2.ok && typeof j2.content === 'string' && j2.content.length) {
              window.setInterstageContext('BtoFinal', { contextText: j2.content });
              loadedCtxBtoFinal = true;
            }
          }
        } catch (e) {
          // ignore
        }

        // Update progress bar and tiles even if WS events are not received
        const namesA = Object.keys(stageA);
        const namesB = Object.keys(stageB);
        const namesF = Object.keys(finalStage);
        
        // Get the actual selected analyzers from the UI
        const selections = window.UI.getSelections();
        const selectedA = selections.selected.stageA || [];
        const selectedB = selections.selected.stageB || [];
        const selectedF = selections.selected.final || [];
        const expected = selectedA.length + selectedB.length + selectedF.length;
        
        if (expected > 0) {
          let completed = 0;
          
          // Update tiles and count completed for Stage A
          for (const n of namesA) {
            const info = stageA[n];
            const tile = document.querySelector(`#tile-stageA-${n.replace(/_/g, "_")}`);
            if (tile) {
              const statusEl = tile.querySelector('[data-role="status"]');
              // Only update if status has changed to avoid overwriting "In Process"
              if (info && info.status === "completed") {
                completed += 1;
                if (statusEl && statusEl.textContent !== "Completed") {
                  statusEl.textContent = "Completed";
                  statusEl.className = "badge bg-green-100 text-green-700";
                  tile.setAttribute("data-status", "completed");
                  const timeEl = tile.querySelector('[data-role="time"]');
                  const tokensEl = tile.querySelector('[data-role="tokens"]');
                  const maxEl = tile.querySelector('[data-role="max"]');
                  const modelEl = tile.querySelector('[data-role="model"]');
                  if (timeEl && info.processing_time) {
                    timeEl.textContent = info.processing_time.toFixed(2) + "s";
                  }
                  if (tokensEl && info.token_usage) {
                    const tokens = info.token_usage.total || info.token_usage.total_tokens || 0;
                    tokensEl.textContent = String(tokens);
                  }
                  if (maxEl && info.token_usage && (info.token_usage.max_tokens != null || info.token_usage.max != null)) {
                    const maxTok = info.token_usage.max_tokens != null ? info.token_usage.max_tokens : info.token_usage.max;
                    maxEl.textContent = String(maxTok);
                  }
                  if (modelEl && info.model_used) {
                    modelEl.textContent = String(info.model_used);
                  }
                }
              } else if (info && info.status === "error") {
                // Reflect error state when polling (WS may have been missed)
                if (statusEl && statusEl.textContent !== "Error") {
                  statusEl.textContent = "Error";
                  statusEl.className = "badge bg-red-100 text-red-700";
                  tile.setAttribute("data-status", "error");
                }
              } else if (info && info.status === "processing" && tile.getAttribute("data-status") !== "processing") {
                // Show "In Process" state
                if (statusEl) {
                  statusEl.textContent = "In Process";
                  statusEl.className = "badge bg-yellow-100 text-yellow-700 animate-pulse";
                  tile.setAttribute("data-status", "processing");
                }
              }
            }
          }
          
          // Update tiles and count completed for Stage B
          for (const n of namesB) {
            const info = stageB[n];
            const tile = document.querySelector(`#tile-stageB-${n.replace(/_/g, "_")}`);
            if (info && info.status === "completed") {
              completed += 1;
              if (tile) {
                const statusEl = tile.querySelector('[data-role="status"]');
                if (statusEl && statusEl.textContent !== "Completed") {
                  statusEl.textContent = "Completed";
                  statusEl.className = "badge bg-green-100 text-green-700";
                  tile.setAttribute("data-status", "completed");
                  const timeEl = tile.querySelector('[data-role="time"]');
                  const tokensEl = tile.querySelector('[data-role="tokens"]');
                  const maxEl = tile.querySelector('[data-role="max"]');
                  const modelEl = tile.querySelector('[data-role="model"]');
                  if (timeEl && info.processing_time) {
                    timeEl.textContent = info.processing_time.toFixed(2) + "s";
                  }
                  if (tokensEl && info.token_usage) {
                    const tokens = info.token_usage.total || info.token_usage.total_tokens || 0;
                    tokensEl.textContent = String(tokens);
                  }
                  if (maxEl && info.token_usage && (info.token_usage.max_tokens != null || info.token_usage.max != null)) {
                    const maxTok = info.token_usage.max_tokens != null ? info.token_usage.max_tokens : info.token_usage.max;
                    maxEl.textContent = String(maxTok);
                  }
                  if (modelEl && info.model_used) {
                    modelEl.textContent = String(info.model_used);
                  }
                }
              }
            } else if (info && info.status === "error") {
              if (tile) {
                const statusEl = tile.querySelector('[data-role="status"]');
                if (statusEl && statusEl.textContent !== "Error") {
                  statusEl.textContent = "Error";
                  statusEl.className = "badge bg-red-100 text-red-700";
                  tile.setAttribute("data-status", "error");
                }
              }
            } else if (info && info.status === "processing") {
              if (tile && tile.getAttribute("data-status") !== "processing") {
                const statusEl = tile.querySelector('[data-role="status"]');
                if (statusEl) {
                  statusEl.textContent = "In Process";
                  statusEl.className = "badge bg-yellow-100 text-yellow-700 animate-pulse";
                  tile.setAttribute("data-status", "processing");
                }
              }
            }
          }
          
          // Update tiles and count completed for Final stage
          for (const n of namesF) {
            const info = finalStage[n];
            const tile = document.querySelector(`#tile-final-${n.replace(/_/g, "_")}`);
            if (info && info.status === "completed") {
              completed += 1;
              if (tile) {
                const statusEl = tile.querySelector('[data-role="status"]');
                if (statusEl && statusEl.textContent !== "Completed") {
                  statusEl.textContent = "Completed";
                  statusEl.className = "badge bg-green-100 text-green-700";
                  tile.setAttribute("data-status", "completed");
                }
                // Populate model and max tokens if available for Final entries
                const maxEl = tile.querySelector('[data-role="max"]');
                const modelEl = tile.querySelector('[data-role="model"]');
                if (maxEl && info && info.token_usage && (info.token_usage.max_tokens != null || info.token_usage.max != null)) {
                  const maxTok = info.token_usage.max_tokens != null ? info.token_usage.max_tokens : info.token_usage.max;
                  maxEl.textContent = String(maxTok);
                }
                if (modelEl && info && info.model_used) {
                  modelEl.textContent = String(info.model_used);
                }
              }
            } else if (info && info.status === "processing") {
              if (tile && tile.getAttribute("data-status") !== "processing") {
                const statusEl = tile.querySelector('[data-role="status"]');
                if (statusEl) {
                  statusEl.textContent = "In Process";
                  statusEl.className = "badge bg-yellow-100 text-yellow-700 animate-pulse";
                  tile.setAttribute("data-status", "processing");
                }
              }
            }
          }
          
          setProgressBar((completed / expected) * 100);
        }

        if (doc.status === "completed" || doc.status === "error") {
          // If polling detects completion (e.g., WS missed), fetch Final outputs here as well
          if (doc.status === "completed") {
            try {
              await fetchFinalOutputs();
            } catch (e) {
              // ignore
            }
            // Load insights dashboard by polling the insights file (no sockets)
            try {
              if (typeof loadInsights === 'function') {
                await loadInsights(jobId, 60);
              }
            } catch (e) {}
          }
          clearInterval(pollingTimer);
          pollingTimer = null;
        }
      } catch (e) {
        // ignore transient
      }
    };
    // Poll every 2s
    poll();
    pollingTimer = setInterval(poll, 2000);
  }

  function renderStageMarkdown(stageObj, title) {
    const lines = [`# ${title} Results`];
    const names = Object.keys(stageObj || {});
    if (!names.length) {
      lines.push("\n_No results yet._");
      return lines.join("\n");
    }
    for (const name of names) {
      const r = stageObj[name] || {};
      const status = r.status || "unknown";
      const tok = (r.token_usage && (r.token_usage.total || r.token_usage.total_tokens)) || 0;
      lines.push(`\n## ${name.replace(/_/g, " ")}`);
      lines.push(`- Status: ${status}`);
      if (tok) lines.push(`- Tokens: ${tok}`);
      if (typeof r.processing_time === "number") {
        lines.push(`- Time: ${r.processing_time.toFixed(2)}s`);
      }
      if (r.prompt_path) {
        lines.push(`- Prompt: ${r.prompt_path}`);
      }
      if (r.raw_output) {
        lines.push(`\n### Raw Output\n`);
        lines.push("```");
        lines.push(String(r.raw_output));
        lines.push("```");
      }
    }
    return lines.join("\n");
  }

  async function fetchFinalOutputs() {
    const jobId = (window.UI.elements.jobIndicator().textContent || "").replace(/^Job:\s*/, "");
    if (!jobId) return;

    const maxAttempts = 6;
    let populated = false;

    for (let attempt = 0; attempt < maxAttempts && !populated; attempt++) {
      try {
        // Read latest status doc to access inline final.* as fallback
        const { doc } = await window.API.getStatus(jobId).catch(() => ({ doc: null }));
        const finalDoc = (doc && doc.final) || {};
        const keys = Object.keys(finalDoc || {}).filter((k) => k && k !== "status");
        if (typeof console !== "undefined") { console.debug("[FinalLoader] keys", { jobId, keys }); }

        let filledAny = false;

        // For every final analyzer (built-in or custom), prefer file-based artifact, then fall back to inline raw_output
        for (const key of keys) {
          let md = "";

          // Try files-first: output/jobs/<jobId>/final/<key>.md
          try {
            const res = await fetch(
              `/api/job-file?jobId=${encodeURIComponent(jobId)}&path=${encodeURIComponent(`final/${key}.md`)}`
            );
            const j = await res.json();
            if (res.ok && j.ok && j.content) {
              md = j.content;
            }
          } catch {
            // ignore
          }
          if (!md && typeof console !== "undefined") { console.debug("[FinalLoader] no file for final key", { key }); }

          // Fallback to inline raw_output from status doc
          if (!md) {
            const entry = finalDoc[key] || {};
            if (typeof entry.raw_output === "string" && entry.raw_output) {
              md = entry.raw_output;
              if (typeof console !== "undefined") { console.debug("[FinalLoader] loaded inline raw_output", { key, length: md.length }); }
            }
          }

          if (md) {
            window.UI.setFinalContent(key, md);
            filledAny = true;
            if (typeof console !== "undefined") { console.debug("[FinalLoader] populated final content", { key, length: md.length }); }
          }
        }

        if (filledAny) {
          // If nothing is selected yet for Final, select the first available key
          if (!document.querySelector(`#progressGrid [id^="tile-final-"].ring-2`)) {
            const firstKey = keys.find((k) => typeof finalDocs !== "undefined" ? true : true); // pick first
            if (firstKey) {
              if (typeof console !== "undefined") { console.debug("[FinalLoader] auto-selecting first final key", { firstKey }); }
              window.UI.setActiveFinal(firstKey);
            }
          }
          populated = true;
          break;
        }

        // If we got here without populating, wait briefly and retry
        if (attempt < maxAttempts - 1) {
          await new Promise((r) => setTimeout(r, 800));
        }
      } catch (e) {
        // ignore and retry
        if (attempt < maxAttempts - 1) {
          await new Promise((r) => setTimeout(r, 800));
        }
      }
    }
  }

  // Init on DOM ready
  document.addEventListener("DOMContentLoaded", init);
})();
