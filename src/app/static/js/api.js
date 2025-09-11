/**
 * API helpers for Transcript Analysis Tool
 * Uses fetch to talk to Flask backend endpoints under /api
 */
(function () {
  const BASE = "/api";

  async function jsonFetch(url, opts = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      const errMsg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
      throw new Error(errMsg);
    }
    return data;
  }

  // Health/config (optional)
  async function getHealth() {
    return jsonFetch(`${BASE}/health`);
  }
  async function getConfig() {
    return jsonFetch(`${BASE}/config`);
  }

  // Prompt discovery (for per-analyzer dropdowns)
  async function getPromptOptions() {
    const data = await jsonFetch(`${BASE}/prompt-options`);
    // shape: { ok: true, options: { stageA: {analyzer: {default, options:[{name,path,isDefault}]}}, ... } }
    return data.options || {};
  }

  // Prompt editor endpoints
  async function getPromptContent({ path, analyzer } = {}) {
    const params = new URLSearchParams();
    if (path) params.set("path", path);
    if (!path && analyzer) params.set("analyzer", analyzer);
    const data = await jsonFetch(`${BASE}/prompts?` + params.toString());
    return data;
  }

  async function savePrompt({ path, content }) {
    return jsonFetch(`${BASE}/prompts`, {
      method: "POST",
      body: JSON.stringify({ path, content }),
    });
  }

  async function resetPrompt({ analyzer }) {
    return jsonFetch(`${BASE}/prompts/reset`, {
      method: "POST",
      body: JSON.stringify({ analyzer }),
    });
  }

  // Delete a single prompt file by path or analyzer
  async function deletePrompt({ path, analyzer } = {}) {
    const params = {};
    if (path) params.path = path;
    if (!path && analyzer) params.analyzer = analyzer;
    return jsonFetch(`${BASE}/prompts` + (Object.keys(params).length ? `?${new URLSearchParams(params).toString()}` : ''), {
      method: "DELETE",
      body: JSON.stringify(params),
    });
  }

  // Danger: delete all prompt files under prompts/
  async function deleteAllPrompts() {
    return jsonFetch(`${BASE}/prompts/all`, {
      method: "DELETE",
      body: JSON.stringify({ confirm: true }),
    });
  }

  // Default prompt template by stage
  async function getPromptTemplate(stage) {
    // Accept "stageA"|"stageB"|"final" or "stage_a"|"stage_b"|"final"
    const s = String(stage || "").toLowerCase();
    const map = {
      stagea: "stage_a",
      "stage_a": "stage_a",
      stageb: "stage_b",
      "stage_b": "stage_b",
      final: "final",
      "final_stage": "final",
    };
    const stageParam = map[s] || s;
    const params = new URLSearchParams();
    params.set("stage", stageParam);
    const data = await jsonFetch(`${BASE}/prompt-template?` + params.toString());
    return data.template || "";
  }

  // Launch analysis
  // payload = { transcriptText, fileId?, selected:{stageA:[],stageB:[],final:[]}, options:{...}, promptSelection:{stageA:{},stageB:{},final:{}} }
  async function analyze(payload) {
    const data = await jsonFetch(`${BASE}/analyze`, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    });
    // shape: { ok:true, jobId, queuedAt }
    return data;
  }

  // Poll status (Redis-backed)
  async function getStatus(jobId) {
    if (!jobId) throw new Error("jobId required");
    return jsonFetch(`${BASE}/status/${encodeURIComponent(jobId)}`);
  }

  // Insights dashboard for a job
  async function getInsights(jobId) {
    if (!jobId) throw new Error("jobId required");
    return jsonFetch(`${BASE}/insights/${encodeURIComponent(jobId)}`);
  }

  // Jobs listing
  async function getJobsLatest() {
    return jsonFetch(`${BASE}/jobs/latest`);
  }
  async function getJobs() {
    return jsonFetch(`${BASE}/jobs`);
  }

  // Analyzer registry CRUD
  async function getAnalyzers() {
    const data = await jsonFetch(`${BASE}/analyzers`);
    return data.analyzers || [];
  }
  async function rescanAnalyzers(stage) {
    const q = stage ? `?stage=${encodeURIComponent(stage)}` : '';
    return jsonFetch(`${BASE}/analyzers/rescan${q}`, { method: 'POST' });
  }

  async function createAnalyzer({ stage, slug, displayName, promptContent, defaultPromptPath }) {
    const body = { stage, slug, displayName };
    if (typeof promptContent === "string") body.promptContent = promptContent;
    if (defaultPromptPath) body.defaultPromptPath = defaultPromptPath;
    return jsonFetch(`${BASE}/analyzers`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async function updateAnalyzer(slug, { displayName, defaultPromptPath } = {}) {
    const body = {};
    if (typeof displayName === "string") body.displayName = displayName;
    if (defaultPromptPath) body.defaultPromptPath = defaultPromptPath;
    return jsonFetch(`${BASE}/analyzers/${encodeURIComponent(slug)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  async function deleteAnalyzer(slug, { deleteFile = false } = {}) {
    const q = deleteFile ? "?deleteFile=true" : "";
    const res = await fetch(`${BASE}/analyzers/${encodeURIComponent(slug)}${q}`, {
      method: "DELETE",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      const errMsg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
      throw new Error(errMsg);
    }
    return data;
  }

  // Prompt normalization
  async function normalizePrompt({ promptContent, stage } = {}) {
    const body = { promptContent };
    if (stage) body.stage = stage;
    return jsonFetch(`${BASE}/analyzers/normalize`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // Per-user API key
  async function userKeyStatus() {
    return jsonFetch(`${BASE}/user/key`);
  }
  async function userKeySet(apiKey) {
    return jsonFetch(`${BASE}/user/key`, {
      method: 'POST',
      body: JSON.stringify({ apiKey }),
    });
  }
  async function userKeyDelete() {
    return jsonFetch(`${BASE}/user/key`, { method: 'DELETE' });
  }

  async function userKeyValidate(apiKey) {
    const body = {};
    if (apiKey) body.apiKey = apiKey;
    return jsonFetch(`${BASE}/user/key/validate`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // Export
  window.API = {
    getHealth,
    getConfig,
    getPromptOptions,
    getPromptContent,
    savePrompt,
    resetPrompt,
    deletePrompt,
    deleteAllPrompts,
    getPromptTemplate,
    analyze,
    getStatus,
    getInsights,
    getJobsLatest,
    getJobs,
    // new
    getAnalyzers,
    createAnalyzer,
    updateAnalyzer,
    deleteAnalyzer,
    rescanAnalyzers,
    normalizePrompt,
    userKeyStatus,
    userKeySet,
    userKeyDelete,
    userKeyValidate,
  };
})();
