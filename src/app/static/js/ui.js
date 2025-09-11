/**
 * UI helpers: render analyzer lists with per-analyzer prompt dropdowns,
 * progress tiles, results tabs, and prompt editor modal.
 */
(function () {
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const el = {
    stageAList: () => qs("#stageAList"),
    stageBList: () => qs("#stageBList"),
    finalList: () => qs("#finalList"),
    selectAllBtns: () => qsa(".selectAll"),
    deselectAllBtns: () => qsa(".deselectAll"),
    startBtn: () => qs("#startBtn"),
    resetBtn: () => qs("#resetBtn"),
    transcriptText: () => qs("#transcriptText"),
    fileInput: () => qs("#fileInput"),
    chooseFileBtn: () => qs("#chooseFileBtn"),
    chosenFileName: () => qs("#chosenFileName"),
    jobIndicator: () => qs("#jobIndicator"),
    progressGrid: () => qs("#progressGrid"),
    tabBtns: () => qsa(".tabBtn"),
    resultsContent: () => qs("#resultsContent"),
    copyBtn: () => qs("#copyBtn"),
    downloadBtn: () => qs("#downloadBtn"),
    // Stage B options
    optStageBIncludeTranscript: () => qs("#optStageBIncludeTranscript"),
    optStageBMode: () => qs("#optStageBMode"),
    optStageBMaxChars: () => qs("#optStageBMaxChars"),
    // Final options
    optFinalIncludeTranscript: () => qs("#optFinalIncludeTranscript"),
    optFinalMode: () => qs("#optFinalMode"),
    optFinalMaxChars: () => qs("#optFinalMaxChars"),
    // Stage model selectors
    optModelStageA: () => qs("#optModelStageA"),
    optModelStageB: () => qs("#optModelStageB"),
    optModelFinal: () => qs("#optModelFinal"),
    // Prompt editor modal
    promptEditorModal: () => qs("#promptEditorModal"),
    closeEditorBtn: () => qs("#closeEditorBtn"),
    editorPath: () => qs("#editorPath"),
    editorContent: () => qs("#editorContent"),
    savePromptBtn: () => qs("#savePromptBtn"),
    resetPromptBtn: () => qs("#resetPromptBtn"),
    deleteAllPromptsBtn: () => qs("#deleteAllPromptsBtn"),
    editorStatus: () => qs("#editorStatus"),
    // Analyzer CRUD modal
    analyzerCrudModal: () => qs("#analyzerCrudModal"),
    closeAnalyzerCrudBtn: () => qs("#closeAnalyzerCrudBtn"),
    analyzerStage: () => qs("#analyzerStage"),
    analyzerSlug: () => qs("#analyzerSlug"),
    analyzerDisplayName: () => qs("#analyzerDisplayName"),
    analyzerPromptContent: () => qs("#analyzerPromptContent"),
    createAnalyzerBtn: () => qs("#createAnalyzerBtn"),
    analyzerCrudStatus: () => qs("#analyzerCrudStatus"),
  };

  let promptOptions = null; // loaded from API.getPromptOptions()
  let currentTab = "stageA";
  let currentJobId = null;
  // Analyzer meta (built-ins vs custom)
  let analyzersBySlug = {}; // { slug: { slug, stage, displayName, defaultPromptPath, isBuiltIn } }
  function isCustomSlug(slug) {
    const meta = analyzersBySlug[slug];
    if (!meta) return false; // default to built-in if unknown
    return meta.isBuiltIn === false;
  }
  // Results cache
  // - perAnalyzer: store markdown per analyzer for Stage A/B
  // - finalDocs: store markdown for Final outputs separately
  const perAnalyzer = { stageA: {}, stageB: {} };
  const finalDocs = {};
  let resultsCache = { stageA: "", stageB: "", final: "" };
  const activeSelection = { stageA: null, stageB: null, final: null };

  // Simple progress state
  let expectedTotal = 0;
  let completedCount = 0;

  function sanitizeIdPart(s) {
    return String(s).replace(/[^a-zA-Z0-9_-]/g, "_");
  }

  // Normalize backend stage keys to UI stage keys used for tile IDs
  function normalizeStageKey(stage) {
    const s = String(stage || "").toLowerCase();
    if (s === "stage_a" || s === "stagea") return "stageA";
    if (s === "stage_b" || s === "stageb") return "stageB";
    if (s === "final" || s === "final_stage" || s === "finalstage") return "final";
    return stage; // assume already normalized (e.g., "stageA", "stageB")
  }

  function mkAnalyzerRow(stageKey, analyzerName, optsForAnalyzer) {
    const idBase = `${stageKey}-${sanitizeIdPart(analyzerName)}`;
    const defaultPath = (optsForAnalyzer && optsForAnalyzer.default) || "";
    const files = (optsForAnalyzer && optsForAnalyzer.options) || [];
    const optionsHtml = files
      .map(
        (f) =>
          `<option value="${encodeURIComponent(f.path)}" ${
            f.isDefault ? "selected" : ""
          }>${f.name}${f.isDefault ? " (default)" : ""}</option>`
      )
      .join("");

    const custom = isCustomSlug(analyzerName);
    const deleteBtn = `<button class="px-2 py-1 border rounded text-xs text-red-700 deletePromptBtn" data-stage="${stageKey}" data-analyzer="${analyzerName}" title="Delete currently selected prompt file">Delete</button>`;
    const makeDefaultBtn = custom
      ? `<button class="px-2 py-1 border rounded text-xs makeDefaultBtn" data-stage="${stageKey}" data-analyzer="${analyzerName}" title="Set selected prompt as default for this analyzer">Make Default</button>`
      : `<button class="px-2 py-1 border rounded text-xs opacity-40 cursor-not-allowed" disabled title="Default prompt fixed for built-in">Make Default</button>`;

    return `
      <div class="flex items-center gap-2 p-2 border rounded">
        <label class="flex items-center gap-2 w-2/5">
          <input type="checkbox" id="${idBase}-chk" class="analyzerChk accent-blue-600" data-stage="${stageKey}" data-name="${analyzerName}" checked />
          <span class="text-sm">${analyzerName.replace(/_/g, " ")}</span>
        </label>
        <div class="flex items-center gap-2 w-3/5">
          <select id="${idBase}-prompt" class="w-full border rounded p-1 text-sm">
            ${optionsHtml}
          </select>
          <button class="px-2 py-1 border rounded text-xs editPromptBtn" data-stage="${stageKey}" data-analyzer="${analyzerName}" data-path="${encodeURIComponent(defaultPath)}">Edit</button>
          ${deleteBtn}
          ${makeDefaultBtn}
      </div>
    </div>
    `;
  }

  async function renderAnalyzerLists(_promptOptions) {
    promptOptions = _promptOptions || {};

    // Fetch analyzer meta (built-ins/custom)
    try {
      const list = await window.API.getAnalyzers();
      analyzersBySlug = {};
      list.forEach((a) => {
        analyzersBySlug[a.slug] = a;
      });
    } catch (e) {
      // Non-fatal; treat all as built-ins
      analyzersBySlug = {};
    }

    // Helper: compute hidden slugs that look like built-ins (cosmetic differences)
    function normSlug(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
    function computeHidden() {
      const hidden = { stageA: new Set(), stageB: new Set(), final: new Set() };
      // Build per-stage lists
      const byStage = { stageA: [], stageB: [], final: [] };
      Object.values(analyzersBySlug || {}).forEach(a => {
        if (!a || !a.slug || !a.stage) return;
        byStage[a.stage] = byStage[a.stage] || [];
        byStage[a.stage].push(a);
      });
      [ 'stageA', 'stageB', 'final' ].forEach(stage => {
        const builtins = (byStage[stage] || []).filter(a => a.isBuiltIn).map(a => a.slug);
        const customs  = (byStage[stage] || []).filter(a => !a.isBuiltIn).map(a => a.slug);
        const nb = builtins.map(normSlug);
        customs.forEach(cs => {
          const ncs = normSlug(cs);
          // Hide if identical after normalization OR substring in either direction for meaningful lengths
          const dup = nb.some((bn) => ncs === bn || (ncs.length >= 4 && (bn.includes(ncs) || ncs.includes(bn))));
          if (dup) hidden[stage].add(cs);
        });
      });
      return hidden;
    }
    const hiddenSlugs = computeHidden();

    const stageA = promptOptions.stageA || {};
    const stageB = promptOptions.stageB || {};
    const finalS = promptOptions.final || {};

    // Stage A
    el.stageAList().innerHTML = Object.keys(stageA)
      .map((name) => mkAnalyzerRow("stageA", name, stageA[name]))
      .join("");

    // Stage B
    el.stageBList().innerHTML = Object.keys(stageB)
      .map((name) => mkAnalyzerRow("stageB", name, stageB[name]))
      .join("");

    // Final
    el.finalList().innerHTML = Object.keys(finalS)
      .map((name) => mkAnalyzerRow("final", name, finalS[name]))
      .join("");

    // When a Final analyzer is toggled, immediately show its output in the Final tab
    try {
      qsa('input.analyzerChk[data-stage="final"]').forEach((cb) => {
        cb.addEventListener('change', () => {
          if (cb.checked) {
            const name = cb.getAttribute('data-name');
            if (name) {
              try { setActiveFinal(name); } catch {}
            }
          }
        });
        // Clicking label area also toggles; bind click to update view proactively
        cb.addEventListener('click', () => {
          if (cb.checked) {
            const name = cb.getAttribute('data-name');
            if (name) {
              try { setActiveFinal(name); } catch {}
            }
          }
        });
      });
    } catch {}

    // Wire Edit buttons
    qsa(".editPromptBtn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const stage = e.currentTarget.getAttribute("data-stage");
        const analyzer = e.currentTarget.getAttribute("data-analyzer");
        const selectEl = qs(
          `#${stage}-${sanitizeIdPart(analyzer)}-prompt`
        );
        const selectedPath = decodeURIComponent(selectEl.value);
        openPromptEditor({ path: selectedPath, analyzer });
      });
    });

    // Wire Make Default (custom only)
    qsa(".makeDefaultBtn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const stage = e.currentTarget.getAttribute("data-stage");
        const analyzer = e.currentTarget.getAttribute("data-analyzer");
        const selectEl = qs(`#${stage}-${sanitizeIdPart(analyzer)}-prompt`);
        const selectedPath = decodeURIComponent(selectEl.value || "");
        if (!selectedPath) return;
        try {
          await window.API.updateAnalyzer(analyzer, { defaultPromptPath: selectedPath });
          alert("Default prompt updated.");
          // Refresh prompt options to reflect new default
          const options = await window.API.getPromptOptions();
          await renderAnalyzerLists(options);
        } catch (err) {
          alert("Failed to update default prompt: " + (err.message || err));
        }
      });
    });

    // Wire Delete (deletes the selected prompt file for this analyzer)
    qsa('.deletePromptBtn').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const stage = e.currentTarget.getAttribute('data-stage');
        const analyzer = e.currentTarget.getAttribute('data-analyzer');
        const selectEl = qs(`#${stage}-${sanitizeIdPart(analyzer)}-prompt`);
        const selectedPath = decodeURIComponent(selectEl && selectEl.value || '');
        if (!selectedPath) { alert('Select a prompt first.'); return; }
        const confirmMsg = `Delete prompt file?\n${selectedPath}\n\nThis cannot be undone.`;
        if (!confirm(confirmMsg)) return;
        try {
          await window.API.deletePrompt({ path: selectedPath });
          // Refresh prompt options to reflect removal
          const options = await window.API.getPromptOptions();
          await renderAnalyzerLists(options);
        } catch (err) {
          alert('Delete failed: ' + (err && err.message || err));
        }
      });
    });

    // Wire select all/none buttons
    el.selectAllBtns().forEach((b) =>
      b.addEventListener("click", () => toggleStageSelection(b.getAttribute("data-sel"), true))
    );
    el.deselectAllBtns().forEach((b) =>
      b.addEventListener("click", () => toggleStageSelection(b.getAttribute("data-sel"), false))
    );

    // Wire "Add" buttons in stage headers
    qsa(".addAnalyzer").forEach((b) => {
      b.addEventListener("click", () => openAnalyzerCrud(b.getAttribute("data-stage")));
    });

    // Wire "Rescan" buttons in stage headers
    qsa(".rescanAnalyzers").forEach((b) => {
      b.addEventListener("click", async () => {
        const stage = b.getAttribute("data-stage");
        try {
          const res = await window.API.rescanAnalyzers(stage);
          // Refresh options and re-render list
          const options = await window.API.getPromptOptions();
          await renderAnalyzerLists(options);
          // Optional: display a quick status
          if (res && res.summary) {
            console.debug("Rescan summary", res.summary);
          }
        } catch (e) {
          alert("Rescan failed: " + (e.message || e));
        }
      });
    });

    // Wire "Cleanup" buttons: detect custom slugs similar to built-ins and delete them
    qsa(".cleanupDuplicates").forEach((b) => {
      b.addEventListener("click", async () => {
        try {
          // Recompute hidden set as duplicates list
          const dups = computeHidden();
          const stage = b.getAttribute("data-stage");
          const toDelete = Array.from((dups[stage] || new Set()));
          if (!toDelete.length) {
            alert("No duplicates found for this stage.");
            return;
          }
          if (!confirm(`Delete ${toDelete.length} duplicate analyzer(s)?`)) return;
          for (const slug of toDelete) {
            try { await window.API.deleteAnalyzer(slug); } catch {}
          }
          const options = await window.API.getPromptOptions();
          await renderAnalyzerLists(options);
          alert("Cleanup complete.");
        } catch (e) {
          alert("Cleanup failed: " + (e.message || e));
        }
      });
    });
  }

  function toggleStageSelection(stageKey, checked) {
    qsa(`input.analyzerChk[data-stage="${stageKey}"]`).forEach((cb) => {
      cb.checked = !!checked;
    });
  }

  function getSelections() {
    const selected = { stageA: [], stageB: [], final: [] };
    const promptSelection = { stageA: {}, stageB: {}, final: {} };

    qsa("input.analyzerChk").forEach((cb) => {
      const stageKey = cb.getAttribute("data-stage");
      const name = cb.getAttribute("data-name");
      if (cb.checked) {
        selected[stageKey].push(name);
      }
      const selectEl = qs(
        `#${stageKey}-${sanitizeIdPart(name)}-prompt`
      );
      if (selectEl && selectEl.value) {
        promptSelection[stageKey][name] = decodeURIComponent(selectEl.value);
      }
    });

    // Stage B options payload
    const stageBOptions = {
      includeTranscript: !!el.optStageBIncludeTranscript().checked,
      mode: el.optStageBMode().value || "full",
      maxChars: parseInt(el.optStageBMaxChars().value || "20000", 10),
    };

    // Final options payload
    const finalOptions = {
      includeTranscript: !!(el.optFinalIncludeTranscript() && el.optFinalIncludeTranscript().checked),
      mode: (el.optFinalMode() && el.optFinalMode().value) || "full",
      maxChars: parseInt((el.optFinalMaxChars() && el.optFinalMaxChars().value) || "20000", 10),
    };

    // Per-stage model selections
    const models = {
      stageA: (el.optModelStageA() && el.optModelStageA().value) || "",
      stageB: (el.optModelStageB() && el.optModelStageB().value) || "",
      final: (el.optModelFinal() && el.optModelFinal().value) || "",
    };

    return { selected, promptSelection, stageBOptions, finalOptions, models };
  }

  function setJobIndicator(jobId) {
    currentJobId = jobId;
    el.jobIndicator().textContent = jobId ? `Job: ${jobId}` : "";
  }

  function clearProgress() {
    el.progressGrid().innerHTML = "";
    resetProgress(0);
  }

  function ensureTile(stage, analyzer) {
    const id = `tile-${stage}-${sanitizeIdPart(analyzer)}`;
    let tile = qs(`#${id}`);
    if (!tile) {
      tile = document.createElement("div");
      tile.id = id;
      tile.className = "border rounded p-2 cursor-pointer";
      tile.setAttribute("data-complete", "0");
      tile.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="font-medium text-sm">${analyzer.replace(/_/g, " ")} <span class="text-xs text-gray-500">(${stage})</span></div>
          <span class="badge bg-gray-100 text-gray-700" data-role="status">Pending</span>
        </div>
        <div class="mt-2 text-xs text-gray-600 space-y-1">
          <div>Time: <span data-role="time">-</span></div>
          <div>Tokens: <span data-role="tokens">-</span></div>
          <div>Max: <span data-role="max">-</span></div>
          <div>Model: <span data-role="model">-</span></div>
          <div>Cost: <span data-role="cost">-</span></div>
        </div>
      `;
      // annotate and wire click-to-view
      tile.setAttribute("data-stage", stage);
      tile.setAttribute("data-analyzer", analyzer);
      tile.addEventListener("click", () => {
        setActiveAnalyzer(stage, analyzer);
      });
      el.progressGrid().appendChild(tile);
    }
    return tile;
  }

  // Progress bar helpers
  function setProgressBarPercent(pct) {
    const bar = qs("#progressInner");
    const label = qs("#progressLabel");
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
    if (label) label.textContent = `${Math.max(0, Math.min(100, Math.round(pct)))}%`;
  }
  function resetProgress(total) {
    expectedTotal = total || 0;
    completedCount = 0;
    setProgressBarPercent(0);
  }
  function incProgress() {
    if (expectedTotal > 0) {
      completedCount = Math.min(expectedTotal, completedCount + 1);
      setProgressBarPercent((completedCount / expectedTotal) * 100);
    }
  }
  function seedPendingTiles(stageA = [], stageB = [], finalStage = []) {
    // Create tiles upfront so the user immediately sees Pending
    el.progressGrid().innerHTML = "";
    const all = [
      ...stageA.map((n) => ["stageA", n]),
      ...stageB.map((n) => ["stageB", n]),
      ...finalStage.map((n) => ["final", n]),
    ];
    for (const [stage, name] of all) ensureTile(stage, name);
    resetProgress(all.length);
  }

  function updateProgress(evt) {
    const { type, payload } = evt || {};
    if (!payload) return;
    // Ignore events for other jobs to prevent stale WS updates from
    // marking tiles in the current view. All WS payloads include jobId.
    try {
      const evtJob = String(payload.jobId || "").trim();
      const curJob = String(currentJobId || "").trim();
      if (evtJob && curJob && evtJob !== curJob) return;
    } catch {}

    if (type === "job.queued") {
      // overall indicator already set
      return;
    }

    if (type === "analyzer.started" || type === "analyzer.completed" || type === "analyzer.error") {
      const { stage, analyzer } = payload;
      const stageKey = normalizeStageKey(stage);
      const tile = ensureTile(stageKey, analyzer);
      const statusEl = qs('[data-role="status"]', tile);

      if (type === "analyzer.started") {
        statusEl.textContent = "In Process";
        statusEl.className = "badge bg-yellow-100 text-yellow-700 animate-pulse";
        tile.setAttribute("data-status", "processing");
      } else if (type === "analyzer.completed") {
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
        }
        const tEl = qs('[data-role="time"]', tile);
        const tokEl = qs('[data-role="tokens"]', tile);
        const costEl = qs('[data-role="cost"]', tile);
        if (tEl && typeof payload.processingTimeMs === "number") {
          tEl.textContent = (payload.processingTimeMs / 1000).toFixed(2) + "s";
        }
        if (tokEl && payload.tokenUsage) {
          const tu = payload.tokenUsage || {};
          const total =
            (tu.total || tu.total_tokens || 0) ||
            ((tu.prompt || 0) + (tu.completion || 0));
          tokEl.textContent = String(total);
        }
        if (costEl) {
          costEl.textContent = payload.costUSD != null ? `$${payload.costUSD.toFixed(4)}` : "-";
        }
      }
      // Increment progress once per tile when it reaches a terminal state
      if (tile.getAttribute("data-complete") !== "1" && (type === "analyzer.completed" || type === "analyzer.error")) {
        tile.setAttribute("data-complete", "1");
        incProgress();
      }
      return;
    }

    if (type === "stage.completed") {
      // noop for now
      return;
    }

    if (type === "job.completed") {
      // overall stats
      const stats = el.overallStats && el.overallStats();
      if (stats) {
        const tu = payload.totalTokenUsage || {};
        const total =
          (tu.total || 0) ||
          ((tu.prompt || 0) + (tu.completion || 0));
        stats.textContent = `Total time: ${(payload.totalProcessingTimeMs / 1000).toFixed(
          2
        )}s • Tokens: ${total}`;
      }
      return;
    }

    if (type === "job.error") {
      // Could display toast
      return;
    }
  }

  function setActiveTab(tabKey) {
    currentTab = tabKey;
    el.tabBtns().forEach((b) => {
      const k = b.getAttribute("data-tab");
      if (k === tabKey) {
        b.classList.add("tab-active");
      } else {
        b.classList.remove("tab-active");
      }
    });
  }

  function renderMarkdown(md) {
    try {
      const html = marked.parse(md || "");
      // Highlight code blocks
      const container = document.createElement("div");
      container.innerHTML = html;
      container.querySelectorAll("pre code").forEach((block) => {
        try {
          hljs.highlightElement(block);
        } catch {}
      });
      return container.innerHTML;
    } catch (e) {
      return `<pre class="whitespace-pre-wrap">${md || ""}</pre>`;
    }
  }

  function showResults(tabKey, markdown) {
    setActiveTab(tabKey);
    resultsCache[tabKey] = markdown || "";
    el.resultsContent().innerHTML = renderMarkdown(markdown || "");
  }

  // Prompt editor modal
  async function openPromptEditor({ path, analyzer }) {
    try {
      const { content, path: resolved, stage } = await window.API.getPromptContent({
        path,
        analyzer,
      });
      el.editorPath().textContent = resolved || path || "";
      el.editorContent().value = content || "";
      el.editorStatus().textContent = "";
      // Stash stage on the modal for reset-to-default to use
      try {
        el.promptEditorModal().dataset.stage = stage || "";
      } catch {}
      el.promptEditorModal().classList.remove("hidden");
      el.promptEditorModal().classList.add("flex");
    } catch (e) {
      alert("Failed to load prompt: " + e.message);
    }
  }

  function closePromptEditor() {
    el.promptEditorModal().classList.add("hidden");
    el.promptEditorModal().classList.remove("flex");
  }

  async function savePromptEditor() {
    const path = el.editorPath().textContent.trim();
    const content = el.editorContent().value;
    try {
      await window.API.savePrompt({ path, content });
      el.editorStatus().textContent = "Saved.";
      setTimeout(closePromptEditor, 600);
    } catch (e) {
      el.editorStatus().textContent = "Error: " + e.message;
    }
  }

  async function resetPromptPath() {
    // Reset the editor content to the default stage template (content reset, not path mapping)
    try {
      const path = (el.editorPath() && el.editorPath().textContent.trim()) || "";
      // Prefer stage stored on the modal (set by openPromptEditor)
      let stage = (el.promptEditorModal() && el.promptEditorModal().dataset.stage) || "";
      if (!stage) {
        const rp = path.toLowerCase();
        if (rp.includes("stage a transcript analyses")) stage = "stage_a";
        else if (rp.includes("stage b results analyses")) stage = "stage_b";
        else if (rp.includes("final output stage")) stage = "final";
      }
      if (!stage) {
        el.editorStatus().textContent = "Unable to infer stage for default template reset.";
        return;
      }
      const tmpl = await window.API.getPromptTemplate(stage);
      if (el.editorContent()) {
        el.editorContent().value = tmpl || "";
      }
      el.editorStatus().textContent = "Reset to default template for " + stage + ".";
    } catch (e) {
      el.editorStatus().textContent = "Reset failed: " + (e.message || e);
    }
  }

  async function deleteAllPromptsDanger() {
    try {
      const sure = window.confirm("Delete ALL .md files under prompts/? This cannot be undone. Continue?");
      if (!sure) return;
      const ack = window.prompt('Type DELETE to confirm');
      if (!ack || ack.trim().toUpperCase() !== 'DELETE') return;
      if (el.editorStatus()) el.editorStatus().textContent = 'Deleting…';
      const res = await window.API.deleteAllPrompts();
      // Show quick summary
      const del = (res && typeof res.deleted === 'number') ? res.deleted : 0;
      const errs = (res && Array.isArray(res.errors)) ? res.errors.length : 0;
      if (el.editorStatus()) el.editorStatus().textContent = `Deleted ${del} file(s)${errs ? `, ${errs} error(s)` : ''}. Refreshing…`;
      // Refresh options and re-render lists so selects reflect empty directories
      const options = await window.API.getPromptOptions();
      await renderAnalyzerLists(options);
      // Clear editor content if the current file was removed
      try {
        el.editorContent().value = '';
      } catch {}
      setTimeout(() => { if (el.editorStatus()) el.editorStatus().textContent = ''; }, 2500);
    } catch (e) {
      if (el.editorStatus()) el.editorStatus().textContent = 'Delete failed: ' + (e.message || e);
    }
  }

  // Clipboard and downloads for current tab
  async function copyCurrent() {
    const md = resultsCache[currentTab] || "";
    try {
      await navigator.clipboard.writeText(md);
      alert("Copied current tab content to clipboard.");
    } catch {
      alert("Copy failed. Select and copy manually.");
    }
  }

  function downloadCurrent() {
    const md = resultsCache[currentTab] || "";
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `results_${currentTab}.md`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function wireStaticHandlers() {
    // Tabs
    el.tabBtns().forEach((b) =>
      b.addEventListener("click", () => showResults(b.getAttribute("data-tab"), resultsCache[b.getAttribute("data-tab")] || ""))
    );
    // Editor modal
    el.closeEditorBtn().addEventListener("click", closePromptEditor);
    el.savePromptBtn().addEventListener("click", savePromptEditor);
    el.resetPromptBtn().addEventListener("click", resetPromptPath);
    if (el.deleteAllPromptsBtn()) {
      el.deleteAllPromptsBtn().addEventListener('click', deleteAllPromptsDanger);
    }
    // Copy/Download
    el.copyBtn().addEventListener("click", copyCurrent);
    el.downloadBtn().addEventListener("click", downloadCurrent);

    // Analyzer CRUD modal
    if (el.closeAnalyzerCrudBtn()) {
      el.closeAnalyzerCrudBtn().addEventListener("click", closeAnalyzerCrud);
    }
    if (el.createAnalyzerBtn()) {
      el.createAnalyzerBtn().addEventListener("click", createAnalyzerSubmit);
    }
  }

  // Run controls (disable/enable during active analysis)
  function disableRunControls() {
    const start = el.startBtn && el.startBtn();
    if (start) {
      start.disabled = true;
      start.setAttribute("aria-disabled", "true");
      start.setAttribute("aria-busy", "true");
      start.classList.add("opacity-50", "cursor-not-allowed");
      // Preserve original label
      if (!start.dataset.prevLabel) start.dataset.prevLabel = start.textContent || "Start Analysis";
      start.textContent = "Running…";
    }
    // Disable analyzer selection controls
    el.selectAllBtns().forEach((b) => {
      b.disabled = true;
      b.classList.add("opacity-50", "cursor-not-allowed");
    });
    el.deselectAllBtns().forEach((b) => {
      b.disabled = true;
      b.classList.add("opacity-50", "cursor-not-allowed");
    });
    // Disable analyzer checkboxes
    qsa("input.analyzerChk").forEach((cb) => {
      cb.disabled = true;
    });
    // Disable prompt selects and options controls (global select catch)
    qsa("select").forEach((s) => {
      s.disabled = true;
      s.classList.add("opacity-50", "cursor-not-allowed");
    });
    // But keep Insights panel interactive during runs
    try {
      const infSel = document.getElementById('insightsFilter');
      if (infSel) {
        infSel.disabled = false;
        infSel.classList.remove('opacity-50', 'cursor-not-allowed');
      }
      const jobInput = document.getElementById('insightsJobId');
      if (jobInput) jobInput.disabled = false;
      const loadBtn = document.getElementById('loadInsightsBtn');
      if (loadBtn) {
        loadBtn.disabled = false;
        loadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      }
      ['exportInsightsJson','exportInsightsCsv','exportInsightsMd'].forEach((id) => {
        const b = document.getElementById(id);
        if (b) { b.disabled = false; b.classList.remove('opacity-50', 'cursor-not-allowed'); }
      });
    } catch (e) { /* no-op */ }
    // Prevent new file selection during run
    const choose = el.chooseFileBtn && el.chooseFileBtn();
    if (choose) {
      choose.disabled = true;
      choose.classList.add("opacity-50", "cursor-not-allowed");
      choose.setAttribute("aria-disabled", "true");
    }
    const file = el.fileInput && el.fileInput();
    if (file) file.disabled = true;
  }

  function enableRunControls() {
    const start = el.startBtn && el.startBtn();
    if (start) {
      start.disabled = false;
      start.removeAttribute("aria-disabled");
      start.removeAttribute("aria-busy");
      start.classList.remove("opacity-50", "cursor-not-allowed");
      start.textContent = start.dataset.prevLabel || "Start Analysis";
      delete start.dataset.prevLabel;
    }
    // Enable analyzer selection controls
    el.selectAllBtns().forEach((b) => {
      b.disabled = false;
      b.classList.remove("opacity-50", "cursor-not-allowed");
    });
    el.deselectAllBtns().forEach((b) => {
      b.disabled = false;
      b.classList.remove("opacity-50", "cursor-not-allowed");
    });
    // Enable analyzer checkboxes
    qsa("input.analyzerChk").forEach((cb) => {
      cb.disabled = false;
    });
    // Enable selects
    qsa("select").forEach((s) => {
      s.disabled = false;
      s.classList.remove("opacity-50", "cursor-not-allowed");
    });
    // Re-enable file chooser
    const choose = el.chooseFileBtn && el.chooseFileBtn();
    if (choose) {
      choose.disabled = false;
      choose.classList.remove("opacity-50", "cursor-not-allowed");
      choose.removeAttribute("aria-disabled");
    }
    const file = el.fileInput && el.fileInput();
    if (file) file.disabled = false;
  }

  // Per-analyzer and Final selection helpers
  function updateTileSelectionStyles(stageKey) {
    const tiles = qsa(`#progressGrid [id^="tile-${stageKey}-"]`);
    tiles.forEach((t) => t.classList.remove("ring-2", "ring-blue-500"));
    const selectedId = `#tile-${stageKey}-${sanitizeIdPart((activeSelection[stageKey] || ""))}`;
    const sel = qs(selectedId);
    if (sel) sel.classList.add("ring-2", "ring-blue-500");
  }

  async function setActiveFinal(kind) {
    const k = String(kind || "").trim();
    activeSelection.final = k;
    updateTileSelectionStyles("final");

    let md = finalDocs[k];

    // On-demand load if not already populated
    if (!md) {
      try {
        const jobTxt = (el.jobIndicator() && el.jobIndicator().textContent) || "";
        const jobId = (jobTxt || "").replace(/^Job:\s*/, "").trim();

        if (jobId) {
          // Try file first
          try {
            const params = new URLSearchParams();
            params.set("jobId", jobId);
            params.set("path", `final/${k}.md`);
            const resp = await fetch(`/api/job-file?${params.toString()}`);
            const j = await resp.json().catch(() => ({}));
            if (resp.ok && j && j.ok && j.content) {
              md = j.content;
            }
          } catch {
            // ignore
          }

          // Fallback to inline raw_output from status doc
          if (!md && window.API && typeof window.API.getStatus === "function") {
            try {
              const { doc } = await window.API.getStatus(jobId);
              const entry = (doc && doc.final && doc.final[k]) || {};
              if (entry && typeof entry.raw_output === "string" && entry.raw_output) {
                md = entry.raw_output;
              }
            } catch {
              // ignore
            }
          }

          // Cache for subsequent views
          if (md) {
            finalDocs[k] = md;
          }
        }
      } catch {
        // ignore fetch errors; we'll show placeholder below
      }
    }

    showResults("final", md || "_Result not available yet._");
  }

  function setFinalContent(kind, markdown) {
    const k = String(kind || "").trim();
    finalDocs[k] = markdown || "";
    // If Final tab and this is the active selection, refresh view
    if (currentTab === "final" && activeSelection.final === k) {
      showResults("final", finalDocs[k] || "_Result not available yet._");
    }
  }

  function setActiveAnalyzer(stageKey, analyzerName) {
    const key = normalizeStageKey(stageKey);
    if (key === "final") {
      // Delegate to final selector
      return setActiveFinal(analyzerName);
    }
    activeSelection[key] = analyzerName;
    updateTileSelectionStyles(key);
    const md = (perAnalyzer[key] && perAnalyzer[key][analyzerName]) || "_Result not available yet._";
    showResults(key, md);
  }

  function setAnalyzerMarkdown(stageKey, analyzerName, markdown /*, meta */) {
    const key = normalizeStageKey(stageKey);
    if (!perAnalyzer[key]) return;
    perAnalyzer[key][analyzerName] = markdown || "";
    // Auto-select first available if not selected yet
    if (!activeSelection[key] && (perAnalyzer[key][analyzerName] || "").length) {
      setActiveAnalyzer(key, analyzerName);
    }
  }

  // Analyzer CRUD helpers
  async function openAnalyzerCrud(stageKey) {
    try {
      if (stageKey && el.analyzerStage()) {
        el.analyzerStage().value = stageKey;
      }
      if (el.analyzerSlug()) el.analyzerSlug().value = "";
      if (el.analyzerDisplayName()) el.analyzerDisplayName().value = "";
      if (el.analyzerPromptContent()) el.analyzerPromptContent().value = "";
      if (el.analyzerCrudStatus()) el.analyzerCrudStatus().textContent = "";

      // Prefill with a stage-appropriate default template so required variables are present
      try {
        const tmpl = await window.API.getPromptTemplate(stageKey);
        if (el.analyzerPromptContent()) {
          el.analyzerPromptContent().value = tmpl || el.analyzerPromptContent().value;
        }
      } catch (e) {
        // Non-fatal; leave blank if template fetch fails
      }

      // Populate "from existing file" controls
      try {
        const toggle = document.getElementById('analyzerFromFileToggle');
        const select = document.getElementById('analyzerFromFileSelect');
        if (toggle && select) {
          toggle.checked = false;
          select.disabled = true;
          const files = [];
          const seen = new Set();
          const bucket = (promptOptions && promptOptions[(stageKey === 'stageA' ? 'stageA' : (stageKey === 'stageB' ? 'stageB' : 'final'))]) || {};
          Object.values(bucket).forEach(entry => {
            (entry.options || []).forEach(f => {
              const p = String(f.path || '');
              if (p && !seen.has(p)) { seen.add(p); files.push({ name: f.name, path: p }); }
            });
          });
          select.innerHTML = '<option value="">— Select a file —</option>' + files.map(f => `<option value="${encodeURIComponent(f.path)}">${f.name}</option>`).join('');
          toggle.onchange = () => { select.disabled = !toggle.checked; };
        }
      } catch {}

      el.analyzerCrudModal().classList.remove("hidden");
      el.analyzerCrudModal().classList.add("flex");

      // Wire Normalize button for free-form prompt content
      try {
        const normBtn = document.getElementById('normalizePromptBtn');
        const status = document.getElementById('normalizeStatus');
        const ta = el.analyzerPromptContent && el.analyzerPromptContent();
        const stageSel = el.analyzerStage && el.analyzerStage();
        const fromFileToggle = document.getElementById('analyzerFromFileToggle');
        if (normBtn && ta && stageSel) {
          normBtn.onclick = async () => {
            try {
              if (fromFileToggle && fromFileToggle.checked) {
                if (status) status.textContent = 'Disable "from file" to normalize pasted text.';
                return;
              }
              const raw = (ta.value || '').trim();
              if (!raw) { if (status) status.textContent = 'Paste a prompt first.'; return; }
              normBtn.disabled = true;
              if (status) status.textContent = 'Normalizing…';
              const stageVal = stageSel.value || 'stageA';
              const res = await window.API.normalizePrompt({ promptContent: raw, stage: stageVal });
              if (!res || res.ok === false) throw new Error(res && res.error || 'Normalize failed');
              const { stageDetected, normalized } = res;
              ta.value = normalized || raw;
              if (stageDetected && ['stageA','stageB','final'].includes(stageDetected)) {
                stageSel.value = stageDetected;
              }
              if (status) status.textContent = `Normalized (${stageDetected || 'stageA'})`;
            } catch (e) {
              if (status) status.textContent = 'Normalize error: ' + (e.message || e);
            } finally {
              normBtn.disabled = false;
              setTimeout(() => { if (status) status.textContent = ''; }, 2500);
            }
          };
        }
      } catch {}
    } catch {}
  }
  function closeAnalyzerCrud() {
    el.analyzerCrudModal().classList.add("hidden");
    el.analyzerCrudModal().classList.remove("flex");
  }
  async function createAnalyzerSubmit() {
    let stage = (el.analyzerStage() && el.analyzerStage().value) || "stageA";
    let slug = (el.analyzerSlug() && el.analyzerSlug().value || "").trim();
    const displayName = (el.analyzerDisplayName() && el.analyzerDisplayName().value || "").trim();
    let promptContent = (el.analyzerPromptContent() && el.analyzerPromptContent().value) || "";
    const toggle = document.getElementById('analyzerFromFileToggle');
    const select = document.getElementById('analyzerFromFileSelect');

    if (!slug) {
      // If creating from file and no slug provided, derive it from filename
      if (toggle && toggle.checked && select && select.value) {
        try {
          const decoded = decodeURIComponent(select.value);
          const base = (decoded.split('/').pop() || '').replace(/\.md$/i, '');
          const namePart = base.replace(/^\d+\s+/, '');
          slug = namePart.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
          if (el.analyzerSlug()) el.analyzerSlug().value = slug;
        } catch {}
      }
      if (!slug) {
        if (el.analyzerCrudStatus()) el.analyzerCrudStatus().textContent = "Slug is required (or select a file to derive it).";
        return;
      }
    }
    try {
      if (el.analyzerCrudStatus()) el.analyzerCrudStatus().textContent = "Creating...";
      const stageLabel = stage === 'stageA' ? 'A' : (stage === 'stageB' ? 'B' : 'Final');
      if (toggle && toggle.checked && select && select.value) {
        const defaultPromptPath = decodeURIComponent(select.value);
        await window.API.createAnalyzer({ stage: stageLabel, slug, displayName, defaultPromptPath });
      } else {
        // Auto-normalize if free-form
        const raw = (promptContent || '').trim();
        if (raw && !/^<prompt>/i.test(raw)) {
          try {
            const res = await window.API.normalizePrompt({ promptContent: raw, stage });
            if (res && res.ok && res.normalized) {
              promptContent = res.normalized;
              if (res.stageDetected && ['stageA','stageB','final'].includes(res.stageDetected)) {
                stage = res.stageDetected;
              }
            }
          } catch (e) { /* proceed */ }
        }
        const sLabel = stage === 'stageA' ? 'A' : (stage === 'stageB' ? 'B' : 'Final');
        await window.API.createAnalyzer({ stage: sLabel, slug, displayName, promptContent });
      }
      if (el.analyzerCrudStatus()) el.analyzerCrudStatus().textContent = "Created.";
      // Refresh options and re-render
      const options = await window.API.getPromptOptions();
      await renderAnalyzerLists(options);
      // Pre-select newly created analyzer
      const cb = qs(`input.analyzerChk[data-stage="${stage}"][data-name="${slug}"]`);
      if (cb) cb.checked = true;
      // Close modal
      setTimeout(closeAnalyzerCrud, 400);
    } catch (err) {
      if (el.analyzerCrudStatus()) el.analyzerCrudStatus().textContent = "Error: " + (err.message || err);
    }
  }

  // Expose
  window.UI = {
    renderAnalyzerLists,
    getSelections,
    setJobIndicator,
    clearProgress,
    updateProgress,
    showResults,
    wireStaticHandlers,
    seedPendingTiles,
    disableRunControls,
    enableRunControls,
    // New per-analyzer/final methods
    setAnalyzerMarkdown,
    setActiveAnalyzer,
    setFinalContent,
    setActiveFinal,
    // Expose progress helpers for main.js
    resetProgress,
    elements: el,
  };
})();
