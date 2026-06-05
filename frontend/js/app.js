import { initMap, addRiskMarker } from "./map.js";
import { renderFactorsChart, renderHistoryFeed, renderMetricCards } from "./dashboard.js";
import { initAiSearch } from "./ai_search.js";

const state = {
  health: null,
  modelMeta: null,
  lastPrediction: null,
  lastExplain: null,
  historyTimer: null,
};

const SCENARIOS = {
  calm: {
    label: "Calm Sea",
    sigheight: 0.6,
    swellheight: 0.5,
    period: 7.2,
    windspeed: 7,
    windgust: 10,
    pressure: 1018,
    swelldir: 120,
    winddirdegree: 90,
    humidity: 58,
    cloudcover: 24,
    precipitation: 0,
    dewpoint: 17,
    moon_illumination: 34,
    moon_phase: "Waxing Crescent",
    tide_height_mean: 0.3,
    tide_height_max: 0.8,
    tide_height_min: -0.1,
    tide_height_range: 0.9,
    high_tide_count: 2,
    low_tide_count: 2,
    latitude: 20,
    longitude: 72,
    hour: 10,
    idbeach: "1",
  },
  moderate: {
    label: "Moderate Swell",
    sigheight: 1.5,
    swellheight: 1.2,
    period: 10.5,
    windspeed: 16,
    windgust: 22,
    pressure: 1012,
    swelldir: 180,
    winddirdegree: 225,
    humidity: 72,
    cloudcover: 58,
    precipitation: 0.4,
    dewpoint: 20,
    moon_illumination: 70,
    moon_phase: "Full Moon",
    tide_height_mean: 0.5,
    tide_height_max: 1.2,
    tide_height_min: -0.2,
    tide_height_range: 1.4,
    high_tide_count: 2,
    low_tide_count: 2,
    latitude: 15,
    longitude: 68,
    hour: 14,
    idbeach: "1",
  },
  storm: {
    label: "Storm Conditions",
    sigheight: 2.8,
    swellheight: 2.4,
    period: 14,
    windspeed: 31,
    windgust: 44,
    pressure: 998,
    swelldir: 250,
    winddirdegree: 245,
    humidity: 88,
    cloudcover: 92,
    precipitation: 1.6,
    dewpoint: 23,
    moon_illumination: 92,
    moon_phase: "Waning Gibbous",
    tide_height_mean: 0.9,
    tide_height_max: 2.1,
    tide_height_min: -0.5,
    tide_height_range: 2.6,
    high_tide_count: 3,
    low_tide_count: 1,
    latitude: 8,
    longitude: 60,
    hour: 2,
    idbeach: "1",
  },
  rogue: {
    label: "Rogue Event",
    sigheight: 4.2,
    swellheight: 3.6,
    period: 17.8,
    windspeed: 46,
    windgust: 58,
    pressure: 988,
    swelldir: 275,
    winddirdegree: 262,
    humidity: 93,
    cloudcover: 98,
    precipitation: 2.4,
    dewpoint: 26,
    moon_illumination: 97,
    moon_phase: "Last Quarter",
    tide_height_mean: 1.1,
    tide_height_max: 2.9,
    tide_height_min: -0.8,
    tide_height_range: 3.7,
    high_tide_count: 3,
    low_tide_count: 1,
    latitude: 12,
    longitude: 64,
    hour: 4,
    idbeach: "1",
  },
};

function $(id) {
  return document.getElementById(id);
}

function formatPct(value) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function showLoading(message = "Listening for signals from the deep...") {
  $("loadingOverlay").classList.remove("hidden");
  $("loadingOverlay").querySelector(".loading-text").textContent = message;
}

function hideLoading() {
  $("loadingOverlay").classList.add("hidden");
}

function toast(title, message, kind = "info") {
  const node = document.createElement("div");
  node.className = `toast toast-${kind}`;
  node.innerHTML = `<strong>${title}</strong><div>${message}</div>`;
  $("toastContainer").appendChild(node);
  window.setTimeout(() => node.remove(), 3800);
}

function updateHeroMetrics(health) {
  const confusion = health.confusion_matrix || {};
  $("heroModelName").textContent = health.model;
  $("heroAccuracyValue").textContent = formatPct(health.accuracy);
  $("heroPrecisionValue").textContent = formatPct(health.precision);
  $("heroRecallValue").textContent = formatPct(health.recall);
  $("heroRocValue").textContent = formatPct(health.roc_auc);
  $("heroSupportValue").textContent = `${confusion.tp ?? 0} TP / ${confusion.fn ?? 0} FN`;
  $("heroMetaCopy").textContent = "Bands: SAFE 0-29, CAUTION 30-64, HIGH RISK 65+.";
}

function updateGauge(score, level) {
  const gauge = $("riskGauge");
  const safeScore = Math.max(0, Math.min(100, score));
  gauge.style.setProperty("--score", safeScore);
  $("riskScore").textContent = safeScore.toFixed(1);
  $("riskLevel").textContent = level;
  $("riskMeta").textContent = level === "HIGH RISK"
    ? "Dangerous wave and wind alignment detected."
    : level === "CAUTION"
      ? "Marine stress is building. Tighten monitoring and adjust routing."
      : "Conditions currently appear manageable.";
  $("gaugePanel").classList.toggle("high-risk", level === "HIGH RISK");
  $("gaugePanel").classList.toggle("caution-risk", level === "CAUTION");
}

function updateHeader(health) {
  $("healthPill").textContent = `${health.model} | Acc ${(health.accuracy * 100).toFixed(2)}%`;
  $("heroModelBadge").textContent = health.model;
  renderMetricCards(health);
  updateHeroMetrics(health);
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
    "windspeed", "winddirdegree", "precipitation", "humidity", "pressure", "cloudcover", "dewpoint", "windgust",
    "sigheight", "swellheight", "swelldir", "period", "watertemp", "moon_illumination", "maxtemp", "mintemp",
    "tide_events", "tide_height_mean", "tide_height_max", "tide_height_min", "tide_height_range", "high_tide_count",
    "low_tide_count", "hour", "latitude", "longitude",
  ]);

  for (const [key, value] of Object.entries(data)) {
    if (numericFields.has(key)) {
      data[key] = key === "idbeach" ? String(value) : Number(value);
    }
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

async function fetchModelMeta() {
  try {
    const response = await fetch("/api/model-meta");
    if (!response.ok) return;
    state.modelMeta = await response.json();
    $("heroThresholdValue").textContent = `Model meta route ready • TP ${state.modelMeta.tp} / FP ${state.modelMeta.fp}`;
  } catch {
    /* ignore transient fetch errors */
  }
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
  if (level !== "HIGH RISK") {
    overlay.classList.add("hidden");
    return;
  }

  const text = `Severe marine conditions detected. ${topFactor || "Wave severity is elevated."}`;
  $("riskAlertScore").textContent = score.toFixed(1);
  $("riskAlertText").textContent = text;
  overlay.classList.remove("hidden");
  overlay.onclick = () => overlay.classList.add("hidden");
  window.setTimeout(() => overlay.classList.add("hidden"), 8000);
}

function renderExplanation(explain) {
  const target = $("riskMeta");
  const rows = explain.feature_contributions.slice(0, 5).map((item) => {
    const direction = Number(item.contribution) >= 0 ? "up" : "down";
    const width = Math.min(100, Math.max(12, Math.abs(Number(item.contribution) || 0) * 35));
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

  target.innerHTML = `
    <div class="explain-summary">${explain.interpretation}</div>
    <div class="explain-list">${rows}</div>
  `;
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
    addRiskMarker(
      result.latitude,
      result.longitude,
      result.risk_score,
      result.risk_level,
      result.top_factors?.[0]?.feature,
    );
    showAlert(result.risk_level, result.risk_score, result.top_factors?.[0]?.feature);

    const explainRes = await fetch(`/api/explain/${result.prediction_id}`);
    if (explainRes.ok) {
      const explain = await explainRes.json();
      state.lastExplain = explain;
      renderExplanation(explain);
    }

    if (result.risk_level === "HIGH RISK") {
      toast("High Risk", "A pulsing alert has been triggered.", "danger");
    } else if (result.risk_level === "CAUTION") {
      toast("Caution", "Conditions are trending upward.", "warning");
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

  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      const preset = SCENARIOS[button.dataset.preset];
      if (preset) fillScenario(preset);
    });
  });

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
  await Promise.all([fetchHealth(), fetchModelMeta()]);
  await fetchHistory();
  state.historyTimer = window.setInterval(fetchHistory, 30000);
  updateGauge(0, "SAFE");
}

document.addEventListener("DOMContentLoaded", bootstrap);
