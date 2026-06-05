function asPct(value) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function riskBadgeClass(level) {
  if (level === "HIGH RISK") return "high";
  if (level === "CAUTION" || level === "ELEVATED") return "caution";
  return "safe";
}

export function renderMetricCards(health) {
  const grid = document.getElementById("metricGrid");
  if (!grid) return;

  const metrics = [
    ["Accuracy", health.accuracy],
    ["Precision", health.precision],
    ["Recall", health.recall],
    ["F1 Score", health.f1],
  ];

  grid.innerHTML = metrics.map(([name, value]) => `
    <article class="metric-card">
      <div class="metric-name">${name}</div>
      <div class="metric-value">${asPct(value)}</div>
      <div class="metric-ring" style="--fill:${Math.round(Number(value) * 100)}%">
        <span>${Math.round(Number(value) * 100)}%</span>
      </div>
    </article>
  `).join("");

  const rocBanner = document.getElementById("rocBanner");
  if (rocBanner) {
    rocBanner.textContent = `ROC-AUC ${asPct(health.roc_auc)} - near-perfect discrimination from the trained XGBoost model.`;
  }

  const cm = health.confusion_matrix ?? {};
  const confusionMatrix = document.getElementById("confusionMatrix");
  if (confusionMatrix) {
    confusionMatrix.innerHTML = `
      <div class="cm-cell"><div><span>TP</span><strong>${cm.tp ?? 0}</strong></div></div>
      <div class="cm-cell"><div><span>FP</span><strong>${cm.fp ?? 0}</strong></div></div>
      <div class="cm-cell"><div><span>FN</span><strong>${cm.fn ?? 0}</strong></div></div>
      <div class="cm-cell"><div><span>TN</span><strong>${cm.tn ?? 0}</strong></div></div>
    `;
  }
}

export function renderFactorsChart(topFactors = []) {
  const list = document.getElementById("topFactorsList");
  if (!list) return;

  if (!topFactors.length) {
    list.innerHTML = `<div class="empty-state">No explanatory factors yet. Run a prediction to populate the signal list.</div>`;
    return;
  }

  const maxWeight = Math.max(
    ...topFactors.map((item) => Math.abs(Number(item.importance ?? item.contribution ?? 0)) || 0),
    0.001,
  );

  list.innerHTML = topFactors.map((item, index) => {
    const weight = Math.abs(Number(item.importance ?? item.contribution ?? 0)) || 0;
    const share = Math.max(10, Math.round((weight / maxWeight) * 100));
    const sign = Number(item.contribution ?? 0) >= 0 ? "up" : "down";
    return `
      <article class="factor-row">
        <div class="factor-head">
          <div>
            <div class="factor-index">0${index + 1}</div>
            <strong>${item.feature}</strong>
          </div>
          <span class="badge ${sign}">${item.direction || (sign === "up" ? "Pushes risk up" : "Pushes risk down")}</span>
        </div>
        <div class="factor-bar"><span style="width:${share}%"></span></div>
        <div class="factor-meta">
          <span>Value: ${item.value ?? "n/a"}</span>
          <span>Contribution: ${Number(item.contribution ?? item.importance ?? 0).toFixed(3)}</span>
        </div>
      </article>
    `;
  }).join("");
}

export function renderHistoryFeed(predictions = []) {
  const feed = document.getElementById("historyFeed");
  if (!feed) return;

  if (!predictions.length) {
    feed.innerHTML = `<div class="empty-state">No predictions yet. Run an analysis to populate the feed.</div>`;
    return;
  }

  feed.innerHTML = predictions.map((item) => `
    <article class="history-item">
      <div>
        <strong>${new Date(item.timestamp).toLocaleString()}</strong>
        <div>${item.top_factor || "n/a"}</div>
        <div>Score: ${Number(item.risk_score).toFixed(2)}</div>
      </div>
      <div class="badge ${riskBadgeClass(item.risk_level)}">${item.risk_level}</div>
    </article>
  `).join("");
}
