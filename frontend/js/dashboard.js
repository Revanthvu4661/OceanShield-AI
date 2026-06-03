let factorChart;
let importanceChart;

function asPct(value) {
  return `${(value * 100).toFixed(2)}%`;
}

export function renderMetricCards(health) {
  const grid = document.getElementById("metricGrid");
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
      <div class="metric-ring" style="--fill:${Math.round(value * 100)}%">
        <span>${Math.round(value * 100)}%</span>
      </div>
    </article>
  `).join("");

  document.getElementById("rocBanner").textContent = `ROC-AUC: ${asPct(health.roc_auc)} - Near-perfect discrimination`;

  const cm = health.confusion_matrix;
  document.getElementById("confusionMatrix").innerHTML = `
    <div class="cm-cell"><div><strong>${cm.tp}</strong>TP</div></div>
    <div class="cm-cell"><div><strong>${cm.fp}</strong>FP</div></div>
    <div class="cm-cell"><div><strong>${cm.fn}</strong>FN</div></div>
    <div class="cm-cell"><div><strong>${cm.tn}</strong>TN</div></div>
  `;
}

export function renderFactorsChart(topFactors = []) {
  const ctx = document.getElementById("factorsChart");
  if (!ctx || !window.Chart) return;
  const labels = topFactors.map((item) => item.feature);
  const values = topFactors.map((item) => Number(item.importance ?? item.contribution ?? 0) || 0);
  if (factorChart) factorChart.destroy();
  factorChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Contribution",
        data: values,
        backgroundColor: "rgba(0,180,216,0.78)",
        borderRadius: 8,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#caf0f8" }, grid: { display: false } },
        y: { ticks: { color: "#caf0f8" }, grid: { display: false } },
      },
    },
  });
}

export function renderHistoryFeed(predictions = []) {
  const feed = document.getElementById("historyFeed");
  if (!predictions.length) {
    feed.innerHTML = `<div class="empty-state">No predictions yet. Run an analysis to populate the feed.</div>`;
    return;
  }
  feed.innerHTML = predictions.map((item) => `
    <article class="history-item">
      <div>
        <strong>${new Date(item.timestamp).toLocaleString()}</strong>
        <div>${item.top_factor}</div>
        <div>Score: ${Number(item.risk_score).toFixed(2)}</div>
      </div>
      <div class="badge ${item.risk_level === "HIGH RISK" ? "high" : item.risk_level === "ELEVATED" ? "elevated" : "safe"}">${item.risk_level}</div>
    </article>
  `).join("");
}

export function renderImportanceChart(health) {
  const ctx = document.getElementById("importanceChart");
  if (!ctx || !window.Chart) return;
  const rows = health.top_feature_importance.slice(0, 10);
  if (importanceChart) importanceChart.destroy();
  importanceChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: rows.map((row) => row.feature),
      datasets: [{
        label: "Importance",
        data: rows.map((row) => row.importance),
        backgroundColor: "rgba(144,224,239,0.75)",
        borderRadius: 8,
      }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#caf0f8" }, grid: { display: false } },
        y: { ticks: { color: "#caf0f8" }, grid: { display: false } },
      },
    },
  });
}

