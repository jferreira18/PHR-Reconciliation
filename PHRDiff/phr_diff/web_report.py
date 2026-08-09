HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PHR Reconciliation</title>
<style>
:root {
  color-scheme: dark;
  --bg: #0d1117;
  --panel: #161b22;
  --panel-2: #0f1620;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --green: #3fb950;
  --red: #f85149;
  --yellow: #d29922;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
}
header {
  height: 78px;
  padding: 14px 22px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
}
h1 { margin: 0; font-size: 18px; }
button, select {
  background: #21262d;
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
}
button:hover { border-color: #8b949e; }
.layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: calc(100vh - 78px);
}
aside {
  border-right: 1px solid var(--border);
  background: var(--panel-2);
  overflow: auto;
}
.stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border);
}
.stat {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px;
}
.stat b { display: block; font-size: 18px; }
.stat span { color: var(--muted); font-size: 12px; }
.filters { padding: 12px; border-bottom: 1px solid var(--border); }
.filters select { width: 100%; }
.change-list { list-style: none; margin: 0; padding: 0; }
.change-list button {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
  text-align: left;
  background: transparent;
  padding: 10px 12px;
}
.change-list button.active { background: #1f6feb22; }
.kind { color: var(--muted); font-size: 12px; text-transform: uppercase; }
main { overflow: auto; }
.toolbar {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 12px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}
.viewer { padding: 18px; }
.change-title {
  border: 1px solid var(--border);
  background: var(--panel);
  border-radius: 6px 6px 0 0;
  padding: 12px 14px;
}
.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border: 1px solid var(--border);
  border-top: 0;
}
.side { min-width: 0; padding: 12px; overflow: auto; }
.side + .side { border-left: 1px solid var(--border); }
.label {
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0;
  margin-bottom: 8px;
}
.image-scroll { max-width: 100%; overflow: auto; }
.image-wrap {
  position: relative;
  display: inline-block;
  background: white;
}
.image-wrap img { display: block; max-width: none; height: auto; }
.overlay {
  position: absolute;
  pointer-events: none;
  border: 2px solid;
}
.overlay.added { background: rgba(46, 160, 67, .24); border-color: var(--green); }
.overlay.removed { background: rgba(248, 81, 73, .24); border-color: var(--red); }
.overlay.context { background: rgba(210, 153, 34, .08); border-color: var(--yellow); }
.placeholder {
  min-height: 180px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--border);
  color: var(--muted);
}
.diff-line {
  border: 1px solid var(--border);
  border-top: 0;
  padding: 12px 14px;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}
.minus { color: #ffa198; display: block; }
.plus { color: #7ee787; display: block; }
.warnings {
  margin-top: 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--panel);
  padding: 12px 14px;
}
.warning-row {
  border-top: 1px solid var(--border);
  padding: 10px 0;
}
.warning-row:first-of-type { border-top: 0; }
.warning-tag {
  display: inline-block;
  min-width: 108px;
  margin-right: 8px;
  border: 1px solid var(--yellow);
  border-radius: 999px;
  padding: 2px 8px;
  color: #f2cc60;
  font-size: 12px;
  text-align: center;
}
.warning-message { color: var(--text); }
.warning-help { color: var(--muted); font-size: 12px; margin-top: 4px; }
.hidden { display: none; }
@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  aside { max-height: 320px; border-right: 0; border-bottom: 1px solid var(--border); }
  .split { grid-template-columns: 1fr; }
  .side + .side { border-left: 0; border-top: 1px solid var(--border); }
}
</style>
</head>
<body>
<header>
  <div>
    <h1>PHR Reconciliation</h1>
    <div id="subtitle"></div>
  </div>
  <div><span id="counter"></span></div>
</header>
<div class="layout">
  <aside>
    <div class="stats" id="stats"></div>
    <div class="filters">
      <select id="filter">
        <option value="all">All</option>
        <option value="item_added">Added</option>
        <option value="item_removed">Removed</option>
        <option value="quantity_changed">Quantity</option>
        <option value="serial">Serial</option>
        <option value="serial_swap">Serial Swap</option>
        <option value="warnings">Warnings</option>
      </select>
    </div>
    <ul class="change-list" id="changeList"></ul>
  </aside>
  <main>
    <div class="toolbar">
      <div>
        <button id="prev">Previous Change</button>
        <button id="next">Next Change</button>
      </div>
      <button id="toggleFull">View Full Page</button>
    </div>
    <div class="viewer" id="viewer"></div>
  </main>
</div>
<script>
const data = __PHR_DATA__;
let filtered = data.changes.slice();
let active = 0;
let full = false;
let listMode = "changes";

function classify(change) {
  if (change.change_type.startsWith("serial_swap")) return "serial_swap";
  if (change.change_type.startsWith("serial_")) return "serial";
  return change.change_type;
}

function matches(change, filter) {
  if (filter === "all") return true;
  return classify(change) === filter || change.change_type === filter;
}

function warningEntries() {
  const details = data.warning_details && data.warning_details.length
    ? data.warning_details
    : (data.warnings || []).map(message => ({
        tag: "VALIDATION",
        message,
        explanation: "The reconciliation completed, but this item needs human review."
      }));
  return details.map((warning, i) => ({...warning, index: i + 1}));
}

function renderStats() {
  const keys = [
    ["baseline_records", "Baseline"],
    ["current_records", "Current"],
    ["added", "Added"],
    ["removed", "Removed"],
    ["modified", "Modified"],
    ["serial_additions", "Serial +"],
    ["serial_removals", "Serial -"],
    ["validation_warnings", "Warnings"],
  ];
  document.getElementById("stats").innerHTML = keys.map(([key, label]) =>
    `<div class="stat"><b>${data.summary[key]}</b><span>${label}</span></div>`
  ).join("");
}

function imageHtml(image, placeholder) {
  if (!image) return `<div class="placeholder">${placeholder}</div>`;
  const overlays = image.overlays.map(o =>
    `<div class="overlay ${o.kind}" style="left:${o.left}px;top:${o.top}px;width:${o.width}px;height:${o.height}px"></div>`
  ).join("");
  return `<div class="image-scroll"><div class="image-wrap"><img src="${image.src}" width="${image.width}" height="${image.height}">${overlays}</div></div>`;
}

function renderList() {
  const list = document.getElementById("changeList");
  if (listMode === "warnings") {
    list.innerHTML = filtered.map((warning, i) =>
      `<li><button class="${i === active ? "active" : ""}" data-index="${i}">
        <div><span class="warning-tag">${escapeHtml(warning.tag)}</span></div>
        <div class="kind">${escapeHtml(shortWarningLabel(warning.message))}</div>
      </button></li>`
    ).join("");
  } else {
    list.innerHTML = filtered.map((change, i) =>
      `<li><button class="${i === active ? "active" : ""}" data-index="${i}">
        <div>${escapeHtml(change.stock_number)}</div>
        <div class="kind">${escapeHtml(change.change_type)}</div>
      </button></li>`
    ).join("");
  }
  list.querySelectorAll("button").forEach(button => {
    button.addEventListener("click", () => {
      active = Number(button.dataset.index);
      render();
    });
  });
}

function shortWarningLabel(message) {
  const parts = String(message).split(":").map(part => part.trim()).filter(Boolean);
  if (parts.length >= 2) return parts[1];
  return String(message).slice(0, 80);
}

function renderWarningViewer() {
  const viewer = document.getElementById("viewer");
  if (!filtered.length) {
    viewer.innerHTML = `<div class="placeholder">No validation warnings</div>`;
    document.getElementById("counter").textContent = "0 of 0";
    return;
  }
  const warning = filtered[active];
  viewer.innerHTML = `
    <section class="warnings">
      <b>Warning ${warning.index}: <span class="warning-tag">${escapeHtml(warning.tag)}</span></b>
      <div class="warning-row">
        <div class="warning-message">${escapeHtml(warning.message)}</div>
        <div class="warning-help">${escapeHtml(warning.explanation)}</div>
      </div>
    </section>
  `;
  document.getElementById("counter").textContent = `${active + 1} of ${filtered.length}`;
}

function renderViewer() {
  if (listMode === "warnings") {
    renderWarningViewer();
    return;
  }
  const viewer = document.getElementById("viewer");
  if (!filtered.length) {
    viewer.innerHTML = `<div class="placeholder">No changes match the selected filter</div>`;
    document.getElementById("counter").textContent = "0 of 0";
    return;
  }
  const change = filtered[active];
  const oldImage = full ? change.old_full_page : change.old_crop;
  const newImage = full ? change.new_full_page : change.new_crop;
  const oldText = change.old_value ? `<span class="minus">- ${escapeHtml(change.old_value)}</span>` : "";
  const newText = change.new_value ? `<span class="plus">+ ${escapeHtml(change.new_value)}</span>` : "";
  const warningHtml = data.warning_details && data.warning_details.length
    ? `<section class="warnings"><b>Validation warnings</b>${data.warning_details.map(w => `
        <div class="warning-row">
          <span class="warning-tag">${escapeHtml(w.tag)}</span>
          <span class="warning-message">${escapeHtml(w.message)}</span>
          <div class="warning-help">${escapeHtml(w.explanation)}</div>
        </div>`).join("")}</section>`
    : "";
  viewer.innerHTML = `
    <section>
      <div class="change-title"><b>Change ${change.index}: ${escapeHtml(change.stock_number)}</b> - ${escapeHtml(change.description)} - ${escapeHtml(change.change_type)}</div>
      <div class="split">
        <div class="side"><div class="label">OLD / BASELINE${change.old_page ? " - PAGE " + change.old_page : ""}</div>${imageHtml(oldImage, "No record in baseline receipt")}</div>
        <div class="side"><div class="label">NEW / CURRENT${change.new_page ? " - PAGE " + change.new_page : ""}</div>${imageHtml(newImage, "No record in current receipt")}</div>
      </div>
      <div class="diff-line">${oldText}${newText}</div>
    </section>
    ${warningHtml}
  `;
  document.getElementById("counter").textContent = `${active + 1} of ${filtered.length}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function render() {
  active = Math.max(0, Math.min(active, filtered.length - 1));
  renderList();
  renderViewer();
}

document.getElementById("subtitle").textContent = `${data.old.name} -> ${data.new.name}`;
const hasFullPages = data.changes.some(change => change.old_full_page || change.new_full_page);
document.getElementById("toggleFull").disabled = !hasFullPages;
if (!hasFullPages) document.getElementById("toggleFull").textContent = "Full Page Not Generated";
document.getElementById("filter").addEventListener("change", event => {
  if (event.target.value === "warnings") {
    listMode = "warnings";
    filtered = warningEntries();
  } else {
    listMode = "changes";
    filtered = data.changes.filter(change => matches(change, event.target.value));
  }
  active = 0;
  render();
});
document.getElementById("prev").addEventListener("click", () => { active -= 1; render(); });
document.getElementById("next").addEventListener("click", () => { active += 1; render(); });
document.getElementById("toggleFull").addEventListener("click", () => {
  full = !full;
  document.getElementById("toggleFull").textContent = full ? "View Record Crop" : "View Full Page";
  renderViewer();
});
renderStats();
render();
</script>
</body>
</html>"""
