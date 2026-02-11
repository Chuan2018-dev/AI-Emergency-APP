const form = document.getElementById("incident-form");
const submitBtn = document.getElementById("submit-btn");
const triageCard = document.getElementById("triage-card");
const recommendations = document.getElementById("recommendations");
const actions = document.getElementById("actions");

function severityClass(score) {
  if (score >= 8) return "severity-high";
  if (score >= 5) return "severity-medium";
  return "severity-low";
}

function listMarkup(items, formatter) {
  if (!items.length) return '<li class="empty-state">No data available.</li>';
  return items.map((item) => `<li>${formatter(item)}</li>`).join("");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  submitBtn.textContent = "Analyzing...";

  const payload = {
    incident_text: document.getElementById("incident-text").value,
    latitude: Number(document.getElementById("latitude").value),
    longitude: Number(document.getElementById("longitude").value),
  };

  try {
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not process request");

    triageCard.classList.remove("empty-state");
    triageCard.innerHTML = `
      <div class="metric">
        <span class="metric-label">Incident type</span>
        <span class="metric-value">${result.triage.incident_type}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Severity</span>
        <span class="metric-value severity-pill ${severityClass(result.triage.severity_score)}">${result.triage.severity_score}/10</span>
      </div>
      <div class="metric">
        <span class="metric-label">Urgent signals</span>
        <span class="metric-value">${result.triage.urgent_signals.join(", ") || "None"}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Risk context</span>
        <span class="metric-value">${result.risk_context.join(", ") || "None"}</span>
      </div>
    `;

    recommendations.classList.remove("empty-state");
    recommendations.innerHTML = listMarkup(result.recommendations, (rec) => {
      return `<strong>${rec.unit_id}</strong> • Suitability ${rec.suitability} • ETA ${rec.eta_minutes} min • ${rec.distance_km} km`;
    });

    actions.classList.remove("empty-state");
    actions.innerHTML = listMarkup(result.actions, (step) => step);
  } catch (err) {
    triageCard.classList.add("empty-state");
    triageCard.textContent = `Error: ${err.message}`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Generate AI Response Plan";
  }
});
