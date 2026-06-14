const $ = (id) => document.getElementById(id);
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
};

let currentOrder = [];   // ordered track ids after "Build set"
let pollTimer = null;

// ---------- health / pills ----------
async function refreshHealth() {
  try {
    const h = await api("/api/health");
    const pills = [
      `<span class="pill ok">Spotify ✓ ${h.spotify_configured ? "API" : "public"}</span>`,
      `<span class="pill ${h.ollama ? "ok" : ""}">Gemma ${h.ollama ? "✓ " + h.ollama_model : "offline"}</span>`,
    ];
    $("pills").innerHTML = pills.join("");
    $("aiState").textContent = h.ollama ? `(${h.ollama_model} ready)` : "(Ollama offline)";
    $("aiToggle").disabled = !h.ollama;
  } catch (e) { /* ignore */ }
}

// ---------- library ----------
function statusBadge(s) {
  const map = {
    analyzed: "ok", downloaded: "", downloading: "", pending: "", error: "bad",
  };
  return `<span class="pill ${map[s] || ""}">${s || "?"}</span>`;
}

async function refreshLibrary() {
  const { tracks } = await api("/api/library");
  $("libCount").textContent = tracks.length ? `(${tracks.length})` : "";
  $("libBody").innerHTML = tracks.map((t, i) => `
    <tr class="border-b border-zinc-900">
      <td class="py-1.5 pr-2 text-zinc-600">${i + 1}</td>
      <td class="pr-2"><div class="text-zinc-200">${esc(t.title)}</div>
          <div class="text-xs text-zinc-500">${esc(t.artist)}</div></td>
      <td class="pr-2"><span class="cam">${t.camelot || "—"}</span></td>
      <td class="pr-2">${t.bpm ?? "—"}</td>
      <td class="pr-2">${t.energy != null ? Math.round(t.energy * 100) + "%" : "—"}</td>
      <td>${statusBadge(t.status)}</td>
    </tr>`).join("");
  return tracks;
}

const esc = (s) => (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// ---------- import ----------
$("importBtn").onclick = async () => {
  const url = $("playlistUrl").value.trim();
  if (!url) return;
  $("importMsg").textContent = "Importing…";
  try {
    const r = await api("/api/playlist", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    $("importMsg").textContent = `Imported ${r.imported} tracks from "${r.name}".`;
    if (r.name) $("setName").value = r.name;
    await refreshLibrary();
  } catch (e) {
    $("importMsg").textContent = "Error: " + e.message;
  }
};

// ---------- process ----------
$("processBtn").onclick = async () => {
  try {
    await api("/api/process", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ download: $("dlToggle").checked }),
    });
    $("progressWrap").classList.remove("hidden");
    startPolling();
  } catch (e) { alert(e.message); }
};

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const s = await api("/api/status");
    const pct = s.total ? Math.round((s.done / s.total) * 100) : 0;
    $("progressBar").style.width = pct + "%";
    $("progressPhase").textContent = s.phase;
    $("progressCount").textContent = `${s.done}/${s.total}`;
    $("progressCurrent").textContent = s.current || "";
    await refreshLibrary();
    if (!s.running && s.phase !== "downloading" && s.phase !== "analyzing") {
      clearInterval(pollTimer); pollTimer = null;
      $("progressCurrent").textContent = s.error ? "Error: " + s.error : "Done.";
    }
  }, 1500);
}

$("clearBtn").onclick = async () => {
  if (!confirm("Clear the entire library?")) return;
  await api("/api/library", { method: "DELETE" });
  await refreshLibrary();
};

// ---------- sliders ----------
[["harm", "vHarm"], ["bpm", "vBpm"], ["energy", "vEnergy"], ["peak", "vPeak"]].forEach(([i, v]) => {
  $(i).oninput = () => ($(v).textContent = parseFloat($(i).value).toFixed(2));
});

// ---------- build set ----------
$("sequenceBtn").onclick = async () => {
  $("sequenceBtn").disabled = true;
  $("sequenceBtn").textContent = "Building…";
  try {
    const r = await api("/api/sequence", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        harmonic: +$("harm").value, bpm: +$("bpm").value, energy: +$("energy").value,
        peak: +$("peak").value, use_ai: $("aiToggle").checked,
      }),
    });
    currentOrder = r.ordered.map((t) => t.id);
    renderSet(r.ordered);
    if (r.narrative) { $("narrative").classList.remove("hidden"); $("narrative").textContent = r.narrative; }
    else $("narrative").classList.add("hidden");
  } catch (e) { alert(e.message); }
  $("sequenceBtn").disabled = false;
  $("sequenceBtn").textContent = "Build set";
};

function renderSet(ordered) {
  $("setList").innerHTML = ordered.map((t, i) => {
    let tr = "";
    if (t.transition) {
      const cls = { perfect: "perfect", smooth: "smooth", "energy boost": "energy", risky: "risky" }[t.transition.harmonic] || "smooth";
      const d = t.transition.bpm_delta;
      tr = `<span class="trans ${cls}">→ ${t.transition.harmonic}${d != null ? `, ${d > 0 ? "+" : ""}${d} BPM` : ""}</span>`;
    }
    return `<li class="flex items-center gap-3 bg-zinc-900/50 rounded-lg px-3 py-2">
      <span class="text-zinc-600 w-6 text-right">${i + 1}</span>
      <span class="cam w-12">${t.camelot || "—"}</span>
      <span class="text-zinc-400 w-16 text-xs">${t.bpm ?? "—"} BPM</span>
      <span class="flex-1 truncate"><span class="text-zinc-200">${esc(t.title)}</span>
        <span class="text-zinc-500 text-xs"> — ${esc(t.artist)}</span></span>
      ${tr}
    </li>`;
  }).join("");
}

// ---------- export ----------
$("exportBtn").onclick = async () => {
  if (!currentOrder.length) { alert("Build a set first."); return; }
  try {
    const r = await api("/api/export", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: $("setName").value || "DJHelper Set", ids: currentOrder }),
    });
    $("exportMsg").innerHTML = `
      Saved to <code class="text-emerald-300">${esc(r.export_dir)}</code><br/>
      <a class="text-emerald-400 underline" href="/api/download/nml/${encodeURIComponent(r.nml_name)}">⬇ ${esc(r.nml_name)}</a> &nbsp;
      <a class="text-emerald-400 underline" href="/api/download/m3u/${encodeURIComponent(r.m3u_name)}">⬇ ${esc(r.m3u_name)}</a>
      <div class="mt-2 text-zinc-500">In Traktor: <b>File ▸ Import Collection</b> and pick the .nml, or drag the .m3u8 into a playlist.</div>`;
  } catch (e) { $("exportMsg").textContent = "Error: " + e.message; }
};

// ---------- init ----------
refreshHealth();
refreshLibrary();
