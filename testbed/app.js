// ------------------------------ API client ------------------------------

const API = "/api/v1";
const TOK = { access: null, refresh: null };

const loadTokens = () => {
  TOK.access = localStorage.getItem("access_token");
  TOK.refresh = localStorage.getItem("refresh_token");
  refreshAuthLabel();
};
const saveTokens = (access, refresh) => {
  TOK.access = access; TOK.refresh = refresh;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
  refreshAuthLabel();
};
const clearTokens = () => {
  TOK.access = null; TOK.refresh = null;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  refreshAuthLabel();
};

function refreshAuthLabel() {
  const label = document.getElementById("auth-label");
  if (TOK.access) { label.textContent = "Logged in"; label.className = "pill pill-on"; }
  else { label.textContent = "Logged out"; label.className = "pill pill-off"; }
}

async function api(method, path, { body = null, isForm = false, raw = false } = {}) {
  const url = API + path;
  const headers = {};
  if (TOK.access) headers["Authorization"] = "Bearer " + TOK.access;
  let fetchBody = null;
  if (body !== null) {
    if (isForm) { fetchBody = body; }
    else { headers["Content-Type"] = "application/json"; fetchBody = JSON.stringify(body); }
  }
  let res = await fetch(url, { method, headers, body: fetchBody });
  if (res.status === 401 && TOK.refresh && path !== "/auth/refresh") {
    const ok = await silentRefresh();
    if (ok) {
      headers["Authorization"] = "Bearer " + TOK.access;
      res = await fetch(url, { method, headers, body: fetchBody });
    }
  }
  if (raw) return res;
  let data;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    data = await res.json();
  } else if (ct.startsWith("image/")) {
    // Binary image → wrap in a sentinel so renderResp can show an <img> tag
    // instead of dumping hex garbage into the response viewer.
    const blob = await res.blob();
    data = {
      __kind: "image",
      url: URL.createObjectURL(blob),
      size: blob.size,
      type: ct,
    };
  } else {
    data = await res.text();
  }
  return { ok: res.ok, status: res.status, data };
}

async function silentRefresh() {
  if (!TOK.refresh) return false;
  try {
    const r = await fetch(API + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: TOK.refresh }),
    });
    if (!r.ok) return false;
    const body = await r.json();
    saveTokens(body.access_token, body.refresh_token);
    return true;
  } catch { return false; }
}

function renderResp(key, result) {
  const node = document.querySelector(`[data-response="${key}"]`);
  const status = result.status;
  const cls = result.ok ? "ok" : "err";
  const header = `<div class="status ${cls}">HTTP ${status} ${result.ok ? "✓" : "✗"}</div>`;

  // Image response → show it instead of the raw bytes
  if (result.data && typeof result.data === "object" && result.data.__kind === "image") {
    const kb = (result.data.size / 1024).toFixed(1);
    node.innerHTML = `${header}
      <div class="meta">Content-Type: ${result.data.type} · ${kb} KB</div>
      <img src="${result.data.url}" alt="response" style="max-width:100%;max-height:480px;border-radius:6px;border:1px solid var(--border);margin-top:8px;" />`;
    return;
  }

  const body = typeof result.data === "string" ? result.data : JSON.stringify(result.data, null, 2);
  node.innerHTML = `${header}\n${escapeHtml(body)}`;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function formData(form) {
  const out = {};
  new FormData(form).forEach((v, k) => {
    if (v === "" || v === null) return;
    out[k] = v;
  });
  return out;
}

async function fileToBase64(file) {
  const buf = await file.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

// ------------------------------ global state ------------------------------

const STATE = {
  sessions: [],
  activeSession: null,
  lastImageId: null,
  cart: [],
  selectedProductIds: new Set(),   // for multi-product visualization
};

// ------------------------------ init ------------------------------

document.addEventListener("DOMContentLoaded", () => {
  loadTokens();
  bindNav();
  bindHealth();
  bindAuth();
  bindUsers();
  bindUpload();
  bindSessions();
  bindChat();
  bindVisualize();
  bindSelectedProductsBar();
  bindCart();
  bindProducts();
  document.getElementById("logout-btn").addEventListener("click", () => { clearTokens(); toast("Logged out"); });

  // if we already have a token, refresh sessions + cart
  if (TOK.access) {
    reloadSessions().catch(() => {});
    reloadCart().catch(() => {});
  }
});

function bindNav() {
  const links = document.querySelectorAll(".nav-link");
  const onScroll = () => {
    let current = links[0];
    const offset = 120;
    links.forEach(l => {
      const el = document.querySelector(l.getAttribute("href"));
      if (el && el.getBoundingClientRect().top - offset < 0) current = l;
    });
    links.forEach(l => l.classList.toggle("active", l === current));
  };
  window.addEventListener("scroll", onScroll);
}

// ------------------------------ health ------------------------------

function bindHealth() {
  document.querySelectorAll("#health [data-action]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const which = btn.dataset.action;
      const r = await fetch("/" + which);
      const text = await r.text();
      renderResp("health", { ok: r.ok, status: r.status, data: text });
    });
  });
}

// ------------------------------ auth ------------------------------

function bindAuth() {
  document.getElementById("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    const result = await api("POST", "/auth/register", { body });
    renderResp("auth", result);
    if (result.ok) {
      // auto-login
      const login = await api("POST", "/auth/login", { body: { email: body.email, password: body.password } });
      if (login.ok) { saveTokens(login.data.access_token, login.data.refresh_token); toast("Registered & logged in"); }
    }
  });

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const result = await api("POST", "/auth/login", { body: formData(e.target) });
    renderResp("auth", result);
    if (result.ok) {
      saveTokens(result.data.access_token, result.data.refresh_token);
      toast("Logged in");
      reloadSessions().catch(() => {});
      reloadCart().catch(() => {});
    }
  });

  document.getElementById("refresh-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!TOK.refresh) { toast("No refresh token"); return; }
    const result = await api("POST", "/auth/refresh", { body: { refresh_token: TOK.refresh } });
    renderResp("auth", result);
    if (result.ok) saveTokens(result.data.access_token, result.data.refresh_token);
  });
}

// ------------------------------ users ------------------------------

function bindUsers() {
  document.querySelector("[data-action='me-get']").addEventListener("click", async () => {
    const r = await api("GET", "/users/me");
    renderResp("users", r);
  });
  document.getElementById("me-patch-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const r = await api("PATCH", "/users/me", { body: formData(e.target) });
    renderResp("users", r);
  });
}

// ------------------------------ upload ------------------------------

function bindUpload() {
  document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = document.getElementById("upload-file").files[0];
    if (!file) return;
    const b64 = await fileToBase64(file);
    const r = await api("POST", "/upload/room-image", {
      body: { image_base64: b64, media_type: file.type || "image/jpeg" },
    });
    renderResp("upload", r);
    if (r.ok) {
      STATE.lastImageId = r.data.id;
      document.getElementById("last-image-id").textContent = r.data.id;
      const prev = document.getElementById("uploaded-preview");
      const url = URL.createObjectURL(file);
      prev.innerHTML = `<img src="${url}" alt="uploaded room" />
        <div class="meta">image_id: ${r.data.id} · ${r.data.byte_size} bytes · ${r.data.media_type}</div>`;
    }
  });
  document.getElementById("copy-image-id").addEventListener("click", () => {
    if (STATE.lastImageId) navigator.clipboard.writeText(STATE.lastImageId);
    toast("Copied");
  });
}

// ------------------------------ sessions ------------------------------

function bindSessions() {
  document.querySelector("[data-action='sessions-list']").addEventListener("click", async () => {
    const r = await reloadSessions();
    renderResp("sessions", r);
  });

  document.getElementById("session-create-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    if (!body.room_image_id && STATE.lastImageId) body.room_image_id = STATE.lastImageId;
    const r = await api("POST", "/sessions/", { body });
    renderResp("sessions", r);
    if (r.ok) {
      STATE.activeSession = r.data.id;
      await reloadSessions();
    }
  });

  document.getElementById("session-reload").addEventListener("click", async () => {
    await reloadSessions();
  });

  document.getElementById("active-session").addEventListener("change", (e) => {
    STATE.activeSession = e.target.value || null;
    reloadChatHistory();
  });

  document.getElementById("session-patch-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!STATE.activeSession) return toast("Pick a session first");
    const body = formData(e.target);
    if (Object.keys(body).length === 0) return toast("Nothing to patch");
    const r = await api("PATCH", `/sessions/${STATE.activeSession}`, { body });
    renderResp("sessions", r);
    if (r.ok) reloadSessions();
  });

  document.querySelector("[data-action='session-delete']").addEventListener("click", async () => {
    if (!STATE.activeSession) return toast("Pick a session first");
    if (!confirm("Delete this session and all its messages?")) return;
    const r = await api("DELETE", `/sessions/${STATE.activeSession}`);
    renderResp("sessions", r);
    if (r.ok) {
      STATE.activeSession = null;
      await reloadSessions();
    }
  });
}

async function reloadSessions() {
  const r = await api("GET", "/sessions/");
  if (r.ok) {
    STATE.sessions = r.data;
    const sel = document.getElementById("active-session");
    sel.innerHTML = "";
    const blank = document.createElement("option");
    blank.value = ""; blank.textContent = "(none)";
    sel.appendChild(blank);
    r.data.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `${s.title} — ${s.status} — ${s.id.slice(0, 8)}`;
      sel.appendChild(opt);
    });
    if (STATE.activeSession) sel.value = STATE.activeSession;
    else if (r.data[0]) { STATE.activeSession = r.data[0].id; sel.value = STATE.activeSession; }
    reloadChatHistory();
  }
  return r;
}

// ------------------------------ chat ------------------------------

function bindChat() {
  document.getElementById("chat-analyze-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!STATE.activeSession) return toast("Pick a session first");
    const file = document.getElementById("analyze-file").files[0];
    if (!file) return toast("Pick an image first");
    const b64 = await fileToBase64(file);
    const r = await api("POST", "/chat/analyze", {
      body: { session_id: STATE.activeSession, image_base64: b64, media_type: file.type || "image/jpeg" },
    });
    renderResp("chat", r);
    reloadChatHistory();
  });

  document.getElementById("chat-send-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!STATE.activeSession) return toast("Pick a session first");
    const body = formData(e.target);
    const input = e.target.querySelector("input[name='content']");
    const btn = e.target.querySelector("button[type='submit']");
    input.value = "";
    // Optimistically append user msg
    appendChatMsg("user", body.content);
    btn.disabled = true; btn.textContent = "…";
    const r = await api("POST", "/chat/", { body: { session_id: STATE.activeSession, content: body.content } });
    btn.disabled = false; btn.textContent = "Send";
    renderResp("chat", r);
    if (r.ok) {
      appendChatMsg("assistant", r.data.content, r.data.ui_payload);
    } else {
      appendChatMsg("system", `Error ${r.status}: ${JSON.stringify(r.data)}`);
    }
  });

  document.getElementById("chat-reload").addEventListener("click", reloadChatHistory);
}

async function reloadChatHistory() {
  const box = document.getElementById("chat-window");
  box.innerHTML = "";
  if (!STATE.activeSession) return;
  const r = await api("GET", `/chat/${STATE.activeSession}/messages`);
  if (r.ok) {
    r.data.forEach(m => appendChatMsg(m.role, m.content, m.ui_payload));
  }
}

function appendChatMsg(role, content, uiPayload) {
  const box = document.getElementById("chat-window");
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.textContent = content;
  box.appendChild(div);

  if (uiPayload && uiPayload.type === "product_carousel" && uiPayload.products) {
    const carousel = document.createElement("div");
    carousel.className = "carousel";
    uiPayload.products.forEach(p => carousel.appendChild(productCard(p, { inChat: true })));
    box.appendChild(carousel);
  }

  if (uiPayload && uiPayload.type === "room_preview" && uiPayload.image_id) {
    const img = document.createElement("img");
    img.style.maxWidth = "300px";
    img.style.borderRadius = "8px";
    fetchAuthedImage(`/upload/room-image/${uiPayload.image_id}`).then(u => { if (u) img.src = u; });
    box.appendChild(img);
  }

  // Sumi suggested a multi-product composite preview
  if (uiPayload && uiPayload.type === "preview_request" && uiPayload.product_ids) {
    const ids = uiPayload.product_ids;
    const note = document.createElement("div");
    note.className = "meta";
    note.style.cssText = "margin:6px 0;font-size:12px;";
    note.textContent = `Sumi suggests a composite preview with ${ids.length} products.`;
    const previewBtn = document.createElement("button");
    previewBtn.textContent = "Preview all together in room";
    previewBtn.style.marginTop = "4px";
    previewBtn.addEventListener("click", async () => {
      if (!STATE.activeSession || !STATE.lastImageId) return toast("Need active session + uploaded room");
      const r = await api("POST", "/visualize/", {
        body: { session_id: STATE.activeSession, product_ids: ids, room_image_id: STATE.lastImageId },
      });
      renderResp("visualize", r);
      if (r.ok) {
        toast("Composite render started ✓");
        handleVisualizeResponse(r);
      }
    });
    box.appendChild(note);
    box.appendChild(previewBtn);
  }

  // Sumi suggested a single-product preview
  if (uiPayload && uiPayload.type === "preview_request" && uiPayload.product_id && !uiPayload.product_ids) {
    const previewBtn = document.createElement("button");
    previewBtn.textContent = "Preview this product in room";
    previewBtn.style.marginTop = "4px";
    previewBtn.addEventListener("click", async () => {
      if (!STATE.activeSession || !STATE.lastImageId) return toast("Need active session + uploaded room");
      const r = await api("POST", "/visualize/", {
        body: { session_id: STATE.activeSession, product_id: uiPayload.product_id, room_image_id: STATE.lastImageId },
      });
      renderResp("visualize", r);
      if (r.ok) {
        toast("Render started ✓");
        handleVisualizeResponse(r);
      }
    });
    box.appendChild(previewBtn);
  }

  box.scrollTop = box.scrollHeight;
}

async function fetchAuthedImage(path) {
  const r = await api("GET", path, { raw: true });
  if (!r.ok) return null;
  const blob = await r.blob();
  return URL.createObjectURL(blob);
}

// ------------------------------ visualize ------------------------------

/**
 * Kick off polling for one or more task_ids.
 * Works for both VisualizeResponse (single task_id) and VisualizeMultiResponse (jobs[]).
 */
async function handleVisualizeResponse(submitResult) {
  const preview = document.getElementById("visualize-preview");
  const respNode = document.querySelector(`[data-response="visualize"]`);
  const btn = document.getElementById("viz-generate-btn");

  const data = submitResult.data;

  // Normalise to a list of task_ids
  let taskIds = [];
  let sceneType = "individual";
  if (data.task_id) {
    taskIds = [data.task_id];
  } else if (data.jobs && Array.isArray(data.jobs)) {
    taskIds = data.jobs.map(j => j.task_id);
    sceneType = data.scene_type || "individual";
  }

  if (!taskIds.length) {
    if (btn) { btn.disabled = false; btn.textContent = "Generate"; }
    return;
  }

  const startedAt = Date.now();
  const label = sceneType === "composite" ? "composite scene" : taskIds.length > 1 ? `${taskIds.length} renders` : "render";
  toast(`Started ${label} ✓`);

  // poll all tasks in parallel, collecting results
  const resultSlots = taskIds.map(() => null);
  const pollOne = async (taskId, idx) => {
    let polls = 0;
    while (true) {
      polls++;
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      const mins = Math.floor(elapsed / 60), secs = elapsed % 60;
      const elapsedStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
      const liveMsg = `⏳ Generating… ${elapsedStr} (poll #${polls} task ${idx + 1}/${taskIds.length})`;
      preview.querySelector(`#viz-slot-${idx}`)?.setAttribute("data-status", liveMsg);

      const status = await api("GET", `/visualize/${taskId}`);
      if (!status.ok) { resultSlots[idx] = { error: `HTTP ${status.status}` }; return; }
      if (status.data.status === "done" && status.data.image_id) { resultSlots[idx] = status.data; return; }
      if (status.data.status === "failed") { resultSlots[idx] = { error: status.data.error || "failed" }; return; }
      await new Promise(r => setTimeout(r, 4000));
    }
  };

  // Build placeholder grid
  preview.innerHTML = taskIds.map((id, i) =>
    `<div id="viz-slot-${i}" data-task-id="${id}" data-status="⏳ Starting…" class="viz-slot"
      style="min-height:80px;border:1px dashed var(--border);border-radius:6px;padding:10px;font-size:13px;
             color:var(--text-dim);display:flex;align-items:center;justify-content:center;">
      <span>⏳ Task ${i + 1} starting…</span>
    </div>`
  ).join("");

  // Animate slot text while polling
  const animTimer = setInterval(() => {
    taskIds.forEach((_, i) => {
      const slot = preview.querySelector(`#viz-slot-${i}`);
      if (slot) {
        const s = slot.getAttribute("data-status");
        const sp = slot.querySelector("span");
        if (sp && s) sp.textContent = s;
      }
    });
  }, 1000);

  await Promise.all(taskIds.map((id, i) => pollOne(id, i)));
  clearInterval(animTimer);

  // Render results
  preview.innerHTML = "";
  let anyOk = false;
  for (let i = 0; i < taskIds.length; i++) {
    const slot = document.createElement("div");
    slot.style.cssText = "margin-bottom:16px;";
    const res = resultSlots[i];
    if (!res || res.error) {
      slot.innerHTML = `<div class="demo-note">Task ${i + 1} failed: ${escapeHtml(res?.error || "unknown")}</div>`;
    } else {
      anyOk = true;
      slot.innerHTML = `<div class="meta" style="font-size:12px;margin-bottom:4px;">Task ${i + 1} · image_id: ${res.image_id}</div>`;
      await renderImagePreview(slot, res.image_id);
    }
    preview.appendChild(slot);
  }

  if (btn) { btn.disabled = false; btn.textContent = "Generate"; }
  if (anyOk) toast("Preview ready ✓");
  renderResp("visualize", { ok: true, status: 200, data: resultSlots });
}

function bindVisualize() {
  document.getElementById("visualize-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    if (!body.session_id) body.session_id = STATE.activeSession;
    if (!body.room_image_id) body.room_image_id = STATE.lastImageId;
    if (!body.session_id || !body.room_image_id) return toast("Need session_id and room_image_id");

    // Multi-product: parse the textarea
    const textarea = e.target.querySelector("textarea[name='product_ids']");
    const rawIds = (textarea?.value || "").split(/[\n,;\s]+/).map(s => s.trim()).filter(Boolean);

    if (rawIds.length > 0) {
      body.product_ids = rawIds;
      delete body.product_id;
    } else if (!body.product_id) {
      return toast("Provide a product_id or paste UUIDs in the multi-product box");
    }

    // placement
    if (!body.placement) delete body.placement;

    const btn = e.target.querySelector("button[type='submit']");
    btn.disabled = true; btn.textContent = "Submitting…";
    btn.id = "viz-generate-btn";

    const preview = document.getElementById("visualize-preview");
    preview.innerHTML = `<div class="meta" style="font-size:13px;">⏳ Submitting…</div>`;

    const submit = await api("POST", "/visualize/", { body });
    if (!submit.ok) {
      renderResp("visualize", submit);
      btn.disabled = false; btn.textContent = "Generate";
      preview.innerHTML = `<div class="demo-note">Failed to start: ${escapeHtml(JSON.stringify(submit.data))}</div>`;
      return;
    }
    await handleVisualizeResponse(submit);
    btn.disabled = false; btn.textContent = "Generate";
  });
}

/** Load the given image_id into the preview container with metadata + demo-mode detection. */
async function renderImagePreview(container, imageId) {
  const url = await fetchAuthedImage(`/upload/room-image/${imageId}`);
  if (!url) {
    container.innerHTML = `<div class="meta">Failed to fetch image ${imageId}</div>`;
    return;
  }
  container.innerHTML = `
    <img id="preview-${imageId}" alt="preview" />
    <div class="meta">image_id: ${imageId}</div>
  `;
  const img = container.querySelector(`#preview-${imageId}`);
  img.onload = () => {
    // Demo-mode detection: if server has no image deployment configured, it
    // returns a 1×1 placeholder. Tell the user instead of showing a dot.
    if (img.naturalWidth <= 4 && img.naturalHeight <= 4) {
      const note = document.createElement("div");
      note.className = "demo-note";
      note.innerHTML = `⚠️ Got a ${img.naturalWidth}×${img.naturalHeight} placeholder.
        Likely the backend has no image deployment configured — set
        <code>AZURE_IMAGE_EDIT_DEPLOYMENT</code> (gpt-image-1 / gpt-image-1.5)
        in <code>.env</code> and restart.`;
      container.appendChild(note);
    } else {
      const size = document.createElement("div");
      size.className = "meta";
      size.textContent = `${img.naturalWidth}×${img.naturalHeight}px`;
      container.appendChild(size);
    }
  };
  img.src = url;
}

// ------------------------------ cart ------------------------------

function bindCart() {
  document.querySelector("[data-action='cart-get']").addEventListener("click", async () => {
    const r = await reloadCart(); renderResp("cart", r);
  });
  document.querySelector("[data-action='cart-clear']").addEventListener("click", async () => {
    const r = await api("DELETE", "/cart/");
    renderResp("cart", r);
    reloadCart();
  });
  document.getElementById("cart-add-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    body.quantity = parseInt(body.quantity, 10) || 1;
    const r = await api("POST", "/cart/", { body });
    renderResp("cart", r);
    if (r.ok) { STATE.cart = r.data.items; renderCartTable(r.data); }
  });
}

async function reloadCart() {
  const r = await api("GET", "/cart/");
  if (r.ok) { STATE.cart = r.data.items; renderCartTable(r.data); }
  return r;
}

function renderCartTable(summary) {
  const root = document.getElementById("cart-table");
  root.innerHTML = "";
  if (!summary || !summary.items || summary.items.length === 0) {
    root.innerHTML = `<div style="color: var(--text-dim); padding: 8px;">Cart is empty</div>`;
    return;
  }
  summary.items.forEach(item => {
    const p = item.product;
    const row = document.createElement("div");
    row.className = "cart-row";
    row.innerHTML = `
      <img src="${p.image_url || ""}" onerror="this.style.visibility='hidden'" />
      <div><div>${escapeHtml(p.title.slice(0, 80))}</div><small style="color:var(--text-dim)">₹${p.price}</small></div>
      <input type="number" min="1" max="10" value="${item.quantity}" data-item-id="${item.id}" />
      <button class="btn-ghost" data-patch="${item.id}">Update</button>
      <button class="btn-danger" data-remove="${item.id}">Remove</button>`;
    root.appendChild(row);
  });
  const total = document.createElement("div");
  total.className = "cart-total";
  total.textContent = `Total: ₹${summary.estimated_total} (${summary.item_count} items)`;
  root.appendChild(total);
  // wire row buttons
  root.querySelectorAll("[data-patch]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.patch;
      const qty = parseInt(root.querySelector(`input[data-item-id='${id}']`).value, 10);
      const r = await api("PATCH", `/cart/${id}`, { body: { quantity: qty } });
      renderResp("cart", r);
      reloadCart();
    });
  });
  root.querySelectorAll("[data-remove]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.remove;
      const r = await api("DELETE", `/cart/${id}`);
      renderResp("cart", r);
      reloadCart();
    });
  });
}

// ------------------------------ products ------------------------------

function bindProducts() {
  document.getElementById("products-search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    const qs = new URLSearchParams({ q: body.q, limit: body.limit || 10 });
    const r = await api("GET", `/products/search?${qs}`);
    renderResp("products", r);
    if (r.ok) renderProductGrid(r.data);
  });

  document.getElementById("products-filter-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    const params = new URLSearchParams();
    if (body.category) params.set("category", body.category);
    if (body.max_price) params.set("max_price", body.max_price);
    params.set("limit", body.limit || 20);
    params.set("offset", body.offset || 0);
    const r = await api("GET", `/products/?${params}`);
    renderResp("products", r);
    if (r.ok) renderProductGrid(r.data);
  });

  document.getElementById("products-get-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = formData(e.target);
    const r = await api("GET", `/products/${body.id}`);
    renderResp("products", r);
    if (r.ok) renderProductGrid([r.data]);
  });
}

function renderProductGrid(products) {
  const grid = document.getElementById("products-grid");
  grid.innerHTML = "";
  if (!Array.isArray(products)) products = [products];
  products.forEach(p => grid.appendChild(productCard(p)));
}

function productCard(p, { inChat = false } = {}) {
  const div = document.createElement("div");
  div.className = "prod-card";
  const isSelected = STATE.selectedProductIds.has(p.id);
  div.innerHTML = `
    <img src="${p.image_url || ""}" onerror="this.style.visibility='hidden'" alt="" />
    <div class="title">${escapeHtml((p.title || "").slice(0, 100))}</div>
    <div class="meta">${escapeHtml(p.category || "")} · ${p.rating ? p.rating + "★" : "no rating"}</div>
    <div class="price">₹${p.price ?? "—"}</div>
    <div class="pid">${p.id}</div>
    <div class="row">
      <button data-action="copy-id">copy id</button>
      <button data-action="add-cart">add to cart</button>
    </div>
    ${inChat ? `
      <div class="row" style="margin-top:4px;">
        <button data-action="preview" style="flex:1;">preview in room</button>
        <button data-action="select" style="flex:1;${isSelected ? 'background:var(--accent,#6366f1);color:#fff;' : ''}">
          ${isSelected ? "✓ Selected" : "+ Select"}
        </button>
      </div>` : ""}`;

  div.querySelector("[data-action='copy-id']").addEventListener("click", () => {
    navigator.clipboard.writeText(p.id); toast("Copied " + p.id.slice(0, 8));
  });
  div.querySelector("[data-action='add-cart']").addEventListener("click", async () => {
    const r = await api("POST", "/cart/", { body: { product_id: p.id, quantity: 1 } });
    renderResp("cart", r);
    if (r.ok) { reloadCart(); toast("Added to cart"); }
  });

  const previewBtn = div.querySelector("[data-action='preview']");
  if (previewBtn) {
    previewBtn.addEventListener("click", async () => {
      if (!STATE.activeSession || !STATE.lastImageId) return toast("Need active session + uploaded room");
      const r = await api("POST", "/visualize/", {
        body: { session_id: STATE.activeSession, product_id: p.id, room_image_id: STATE.lastImageId },
      });
      renderResp("visualize", r);
      if (r.ok) {
        toast("Render started ✓");
        handleVisualizeResponse(r);
      }
    });
  }

  const selectBtn = div.querySelector("[data-action='select']");
  if (selectBtn) {
    selectBtn.addEventListener("click", () => {
      if (STATE.selectedProductIds.has(p.id)) {
        STATE.selectedProductIds.delete(p.id);
        selectBtn.textContent = "+ Select";
        selectBtn.style.background = "";
        selectBtn.style.color = "";
      } else {
        STATE.selectedProductIds.add(p.id);
        selectBtn.textContent = "✓ Selected";
        selectBtn.style.background = "var(--accent,#6366f1)";
        selectBtn.style.color = "#fff";
      }
      refreshSelectedBar();
    });
  }

  return div;
}

// ------------------------------ selected-products bar ------------------------------

function refreshSelectedBar() {
  const bar = document.getElementById("selected-products-bar");
  const list = document.getElementById("selected-products-list");
  const count = document.getElementById("selected-count");
  const ids = Array.from(STATE.selectedProductIds);

  count.textContent = ids.length;
  list.innerHTML = "";

  ids.forEach(id => {
    const chip = document.createElement("div");
    chip.style.cssText = "display:flex;align-items:center;gap:4px;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:12px;font-family:monospace;";
    chip.innerHTML = `<span>${id.slice(0, 8)}…</span><button style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:14px;padding:0 2px;" data-remove-id="${id}">×</button>`;
    chip.querySelector("[data-remove-id]").addEventListener("click", () => {
      STATE.selectedProductIds.delete(id);
      refreshSelectedBar();
      // un-highlight matching select buttons in chat
      document.querySelectorAll(`[data-action='select']`).forEach(btn => {
        if (btn.closest(".prod-card")?.querySelector(".pid")?.textContent === id) {
          btn.textContent = "+ Select";
          btn.style.background = "";
          btn.style.color = "";
        }
      });
    });
    list.appendChild(chip);
  });

  bar.style.display = ids.length > 0 ? "block" : "none";
  // Scroll visualize section into view when first item added
  if (ids.length === 1) document.getElementById("visualize").scrollIntoView({ behavior: "smooth", block: "start" });
}

function bindSelectedProductsBar() {
  document.getElementById("clear-selection").addEventListener("click", () => {
    STATE.selectedProductIds.clear();
    refreshSelectedBar();
    document.querySelectorAll("[data-action='select']").forEach(btn => {
      btn.textContent = "+ Select";
      btn.style.background = "";
      btn.style.color = "";
    });
    toast("Selection cleared");
  });

  document.getElementById("visualize-selected-btn").addEventListener("click", async () => {
    const ids = Array.from(STATE.selectedProductIds);
    if (!ids.length) return toast("Select at least one product");
    if (!STATE.activeSession || !STATE.lastImageId) return toast("Need active session + uploaded room");
    const placement = document.getElementById("selected-placement").value.trim() || undefined;
    const btn = document.getElementById("visualize-selected-btn");
    btn.disabled = true; btn.textContent = "Submitting…";
    const r = await api("POST", "/visualize/", {
      body: { session_id: STATE.activeSession, product_ids: ids, room_image_id: STATE.lastImageId, placement },
    });
    renderResp("visualize", r);
    btn.disabled = false; btn.textContent = "Preview selected in room";
    if (r.ok) {
      await handleVisualizeResponse(r);
    } else {
      toast("Failed to start: " + (r.data?.detail || r.status));
    }
  });
}

// ------------------------------ toast ------------------------------

let toastTimer = null;
function toast(msg) {
  let node = document.getElementById("toast");
  if (!node) {
    node = document.createElement("div");
    node.id = "toast";
    node.style.cssText = `
      position: fixed; bottom: 20px; right: 20px; z-index: 100;
      background: var(--bg-card); border: 1px solid var(--border);
      color: var(--text); padding: 10px 16px; border-radius: 6px;
      font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      transition: opacity 0.2s;`;
    document.body.appendChild(node);
  }
  node.textContent = msg;
  node.style.opacity = "1";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.style.opacity = "0"; }, 2500);
}
