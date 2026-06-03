import { initMap, addRiskMarker } from "./map.js";
import { renderFactorsChart, renderHistoryFeed, renderMetricCards } from "./dashboard.js";
import { initAiSearch } from "./ai_search.js";

const state = {
  health: null,
  lastPrediction: null,
  lastExplain: null,
  historyTimer: null,
};

const SAFE_SCENARIO = {
  sigheight: 0.8,
  swellheight: 0.7,
  period: 7.5,
  windspeed: 8,
  windgust: 10,
  pressure: 1018,
  swelldir: 120,
  winddirdegree: 90,
  humidity: 60,
  precipitation: 0,
  moon_illumination: 35,
  tide_height_max: 0.8,
  tide_height_min: -0.1,
  latitude: 28.6,
  longitude: -15.4,
  hour: 13,
};

const HIGH_RISK_SCENARIO = {
  sigheight: 3.5,
  swellheight: 3.0,
  period: 16,
  windspeed: 45,
  windgust: 58,
  pressure: 990,
  swelldir: 270,
  winddirdegree: 260,
  humidity: 90,
  moon_illumination: 95,
  tide_height_max: 2.8,
  tide_height_min: -1.2,
  latitude: 15.5,
  longitude: 68.2,
  hour: 3,
};

function $(id) { return document.getElementById(id); }

function showLoading(message = "Listening for signals from the deep...") {
  $("loadingOverlay").classList.remove("hidden");
  $("loadingOverlay").querySelector(".loading-text").textContent = message;
}

function hideLoading() {
  $("loadingOverlay").classList.add("hidden");
}

function toast(title, message, kind = "info") {
  const node = document.createElement("div");
  node.className = "toast";
  node.innerHTML = `<strong>${title}</strong><div>${message}</div>`;
  $("toastContainer").appendChild(node);
  setTimeout(() => node.remove(), 3800);
}

function updateGauge(score, level) {
  const gauge = $("riskGauge");
  gauge.style.setProperty("--score", Math.max(0, Math.min(100, score)));
  gauge.querySelector(".gauge-score").textContent = score.toFixed(1);
  gauge.querySelector(".gauge-label").textContent = level;
  $("riskLevel").textContent = level;
  $("riskMeta").textContent = level === "HIGH RISK"
    ? "Dangerous wave and wind alignment detected."
    : level === "ELEVATED"
      ? "Noticeable marine stress. Monitor conditions closely."
      : "Conditions currently appear manageable.";
  $("gaugePanel").classList.toggle("high-risk", level === "HIGH RISK");
}

function updateHeader(health) {
  $("healthPill").textContent = `${health.model} | Acc ${(health.accuracy * 100).toFixed(2)}%`;
  renderMetricCards(health);
}

function fillScenario(values) {
  Object.entries(values).forEach(([key, value]) => {
    const field = document.querySelector(`[name="${key}"]`);
    if (field) field.value = value;
  });
}

function collectFormData() {
  const form = $("oceanForm");
  const data = Object.fromEntries(new FormData(form).entries());
  const numericFields = new Set([
    "windspeed","winddirdegree","precipitation","humidity","pressure","cloudcover","dewpoint","windgust",
    "sigheight","swellheight","swelldir","period","watertemp","moon_illumination","maxtemp","mintemp",
    "tide_events","tide_height_mean","tide_height_max","tide_height_min","tide_height_range","high_tide_count",
    "low_tide_count","hour","latitude","longitude"
  ]);
  for (const [key, value] of Object.entries(data)) {
    if (numericFields.has(key)) data[key] = key === "idbeach" ? String(value) : Number(value);
  }
  data.tide_events = Number(data.tide_events || 4);
  data.high_tide_count = Number(data.high_tide_count || 2);
  data.low_tide_count = Number(data.low_tide_count || 2);
  data.idbeach = String(data.idbeach ?? "1");
  return data;
}

async function fetchHealth() {
  const response = await fetch("/api/health");
  const health = await response.json();
  state.health = health;
  updateHeader(health);
}

async function fetchHistory() {
  try {
    const response = await fetch("/api/history");
    if (!response.ok) return;
    const items = await response.json();
    renderHistoryFeed(items);
  } catch {
    /* ignore transient fetch errors */
  }
}

function showAlert(level, score, topFactor) {
  const overlay = $("riskAlertOverlay");
  const text = level === "HIGH RISK"
    ? `Severe marine conditions detected. ${topFactor || "Wave severity is elevated."}`
    : `Risk is elevated. ${topFactor || "Monitor wave and wind changes."}`;
  $("riskAlertScore").textContent = score.toFixed(1);
  $("riskAlertText").textContent = text;
  overlay.classList.toggle("hidden", level !== "HIGH RISK");
  if (level === "HIGH RISK") {
    overlay.onclick = () => overlay.classList.add("hidden");
    setTimeout(() => overlay.classList.add("hidden"), 8000);
  }
}

function renderExplanation(explain) {
  const target = $("riskMeta");
  const rows = explain.feature_contributions.slice(0, 5).map((item) => {
    const direction = item.contribution >= 0 ? "up" : "down";
    const width = Math.min(100, Math.max(12, Math.abs(item.contribution) * 35));
    return `
      <div class="explain-row">
        <div class="explain-head">
          <strong>${item.feature}</strong>
          <span class="badge ${direction}">${item.direction || ""}</span>
        </div>
        <div class="explain-bar"><span style="width:${width}%"></span></div>
        <div class="explain-meta">${String(item.value)} | SHAP ${Number(item.contribution).toFixed(3)}</div>
      </div>
    `;
  }).join("");
  target.innerHTML = `<div>${explain.interpretation}</div><div style="margin-top:12px; display:grid; gap:8px;">${rows}</div>`;
}

async function submitPrediction() {
  showLoading("Analyzing ocean conditions...");
  try {
    const payload = collectFormData();
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result?.detail || "Prediction request failed");

    state.lastPrediction = result;
    updateGauge(result.risk_score, result.risk_level);
    renderFactorsChart(result.top_factors);
    addRiskMarker(result.latitude, result.longitude, result.risk_score, result.risk_level, result.top_factors?.[0]?.feature);
    showAlert(result.risk_level, result.risk_score, result.top_factors?.[0]?.feature);

    const explainRes = await fetch(`/api/explain/${result.prediction_id}`);
    if (explainRes.ok) {
      const explain = await explainRes.json();
      state.lastExplain = explain;
      renderExplanation(explain);
    }

    if (result.risk_level === "HIGH RISK") {
      toast("High Risk", "A pulsing alert has been triggered.", "danger");
    } else if (result.risk_level === "ELEVATED") {
      toast("Elevated Risk", "Conditions are trending upward.", "warning");
    } else {
      toast("Safe", "Conditions are currently manageable.", "success");
    }
    await fetchHistory();
  } catch (error) {
    toast("Lost signal from the deep", error.message, "warning");
  } finally {
    hideLoading();
  }
}

function bindUI() {
  $("analyzeBtn").addEventListener("click", submitPrediction);
  $("safeScenarioBtn").addEventListener("click", () => fillScenario(SAFE_SCENARIO));
  $("highRiskScenarioBtn").addEventListener("click", () => fillScenario(HIGH_RISK_SCENARIO));
  $("dismissAlertBtn").addEventListener("click", () => $("riskAlertOverlay").classList.add("hidden"));
  $("menuToggle").addEventListener("click", () => $("mainNav").classList.toggle("open"));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") $("riskAlertOverlay").classList.add("hidden");
    if (event.key === "Enter" && event.target.tagName !== "TEXTAREA") {
      if (event.target.closest("#oceanForm")) submitPrediction();
    }
  });
}

async function bootstrap() {
  initMap();
  bindUI();
  initAiSearch(showLoading, hideLoading, (msg) => toast("OceanShield", msg));
  await fetchHealth();
  await fetchHistory();
  state.historyTimer = setInterval(fetchHistory, 30000);
  updateGauge(0, "SAFE");
}

document.addEventListener("DOMContentLoaded", bootstrap);
