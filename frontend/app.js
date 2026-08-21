const API_BASE = "http://127.0.0.1:8000";

const el = (selector) => document.querySelector(selector);
const statusBadge = el("#api-status");

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

function renderCheck(target, value) {
  target.textContent = value === true ? "LULUS" : value === false ? "TIDAK LULUS" : "BELUM ADA";
}

function renderResult(evaluation, trace, created) {
  const decision = el("#decision");
  const normalized = evaluation.status.toLowerCase().replaceAll("_", "-");
  decision.className = `decision ${normalized}`;
  el("#decision-status").textContent = evaluation.status.replaceAll("_", " ");
  el("#decision-note").textContent = evaluation.disclaimer;
  renderCheck(el("#check-temperature"), evaluation.checks.temperature);
  renderCheck(el("#check-nutrition"), evaluation.checks.nutrition);
  renderCheck(el("#check-delivery"), evaluation.checks.delivery);
  renderCheck(el("#check-documents"), evaluation.checks.documents);
  el("#batch-code").textContent = created.batch_code;
  el("#ledger-count").textContent = trace.integrity.record_count;
  el("#integrity-status").textContent = trace.integrity.valid ? "VALID" : "TIDAK VALID";
  el("#qr-token").textContent = created.qr_token.slice(0, 12) + "…";
  el("#qr-token").title = created.qr_token;
  el("#payment-status").textContent = evaluation.payment_recommendation.replaceAll("_", " ");
  el("#result-json").textContent = JSON.stringify({ evaluation, trace }, null, 2);
}

async function checkApi() {
  try {
    const data = await api("/health");
    statusBadge.textContent = `API aktif · v${data.version}`;
    statusBadge.className = "api-status online";
  } catch (_error) {
    statusBadge.textContent = "API belum aktif";
    statusBadge.className = "api-status offline";
  }
}

el("#quality-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = el("#run-demo");
  button.disabled = true;
  button.textContent = "Memproses jejak batch…";
  try {
    const suffix = Date.now().toString().slice(-8);
    const batchCode = `SGE-DEMO-${suffix}`;
    const now = new Date();
    const scheduled = new Date(now.getTime() - Number(el("#delay").value) * 60_000);
    const created = await api("/api/v1/batches", {
      method: "POST",
      body: JSON.stringify({
        batch_code: batchCode,
        supplier_name: "Penyedia Sintetis",
        food_description: "Paket pangan demonstrasi",
        production_date: now.toISOString().slice(0, 10),
        documents_complete: el("#documents").checked,
      }),
    });

    await api(`/api/v1/batches/${batchCode}/iot`, {
      method: "POST",
      body: JSON.stringify({
        observed_at: now.toISOString(),
        temperature_c: Number(el("#temperature").value),
        humidity_percent: Number(el("#humidity").value),
        location_label: "Hub agregat demonstrasi",
        device_id: "SIMULATED-IOT-001",
      }),
    });
    await api(`/api/v1/batches/${batchCode}/nutrition`, {
      method: "POST",
      body: JSON.stringify({
        compliance_percent: Number(el("#nutrition").value),
        lab_reference: "LAB-SYNTHETIC-001",
        verified_by: "Verifier Demonstrasi",
        verified_at: now.toISOString(),
      }),
    });
    await api(`/api/v1/batches/${batchCode}/delivery`, {
      method: "POST",
      body: JSON.stringify({
        scheduled_at: scheduled.toISOString(),
        delivered_at: now.toISOString(),
        received_by: "Sekolah Demonstrasi",
      }),
    });
    const evaluation = await api(`/api/v1/batches/${batchCode}/evaluate`, { method: "POST" });
    const trace = await api(`/api/v1/batches/${batchCode}/trace`);
    renderResult(evaluation, trace, created);
  } catch (error) {
    el("#decision").className = "decision failed";
    el("#decision-status").textContent = "PROSES GAGAL";
    el("#decision-note").textContent = error.message;
    el("#result-json").textContent = JSON.stringify({ error: error.message }, null, 2);
  } finally {
    button.disabled = false;
    button.textContent = "Jalankan Alur Traceability";
  }
});

checkApi();
