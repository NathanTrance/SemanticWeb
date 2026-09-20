const endpointInput = document.getElementById("endpoint");
const presetSelect = document.getElementById("presets");
const queryBox = document.getElementById("query");
const runButton = document.getElementById("run");
const rawCheckbox = document.getElementById("raw");
const status = document.getElementById("status");
const output = document.getElementById("output");

let prologue = "";
let presets = [];

function splitQueries(text) {
  const parts = text.split(/^#\s*name:\s*(.+?)\s*$/m);
  return { prologue: parts[0].trim(), blocks: parts.slice(1) };
}

async function loadPresets() {
  try {
    const response = await fetch("queries/demo.rq");
    const text = await response.text();
    const { prologue: pre, blocks } = splitQueries(text);
    prologue = pre;
    presets = [];
    for (let i = 0; i < blocks.length; i += 2) {
      presets.push({ name: blocks[i], body: blocks[i + 1].trim() });
    }
    presetSelect.innerHTML = "";
    for (const [index, preset] of presets.entries()) {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = preset.name;
      presetSelect.appendChild(option);
    }
    selectPreset(0);
  } catch (error) {
    presetSelect.innerHTML = "<option value=''>presets unavailable</option>";
  }
}

function selectPreset(index) {
  const preset = presets[index];
  if (preset) {
    queryBox.value = `${prologue}\n\n${preset.body}`;
  }
}

function renderTable(data) {
  const vars = data.head.vars;
  const table = document.createElement("table");
  const head = table.createTHead().insertRow();
  for (const variable of vars) {
    const th = document.createElement("th");
    th.textContent = variable;
    head.appendChild(th);
  }
  const body = table.createTBody();
  for (const binding of data.bindings) {
    const row = body.insertRow();
    for (const variable of vars) {
      const cell = row.insertCell();
      const term = binding[variable];
      if (!term) continue;
      const value = document.createTextNode(term.value);
      if (term.type === "uri") {
        const link = document.createElement("a");
        link.href = term.value;
        link.target = "_blank";
        link.rel = "noopener";
        link.appendChild(value);
        cell.appendChild(link);
      } else {
        cell.appendChild(value);
      }
    }
  }
  return table;
}

function showRaw(text) {
  const pre = document.createElement("pre");
  pre.textContent = text;
  return pre;
}

async function runQuery() {
  const query = queryBox.value.trim();
  if (!query) return;
  status.textContent = "running…";
  output.innerHTML = "";
  const started = performance.now();
  try {
    const response = await fetch(endpointInput.value, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/sparql-results+json, text/turtle;q=0.5",
      },
      body: "query=" + encodeURIComponent(query),
    });
    const text = await response.text();
    const elapsed = Math.round(performance.now() - started);
    if (!response.ok) {
      status.textContent = `error (${response.status}, ${elapsed} ms)`;
      output.appendChild(showRaw(text));
      return;
    }
    if (rawCheckbox.checked) {
      output.appendChild(showRaw(text));
      status.textContent = `ok (${elapsed} ms)`;
      return;
    }
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("json") && !contentType.includes("ld+json")) {
      const data = JSON.parse(text);
      if (data.head && data.bindings) {
        status.textContent = `${data.bindings.length} row(s), ${elapsed} ms`;
        output.appendChild(renderTable(data));
      } else {
        output.appendChild(showRaw(text));
        status.textContent = `ok (${elapsed} ms)`;
      }
    } else {
      output.appendChild(showRaw(text));
      status.textContent = `ok (${elapsed} ms)`;
    }
  } catch (error) {
    status.textContent = "request failed";
    output.appendChild(showRaw(String(error)));
  }
}

presetSelect.addEventListener("change", (event) => selectPreset(Number(event.target.value)));
runButton.addEventListener("click", runQuery);
queryBox.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runQuery();
});

loadPresets();
