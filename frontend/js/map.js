const MAX_MARKERS = 20;
let map;
const markers = [];

function riskColor(level) {
  if (level === "HIGH RISK") return "#ff4757";
  if (level === "ELEVATED") return "#ffb830";
  return "#00d68f";
}

export function initMap() {
  if (!window.L) return null;
  if (map) return map;
  map = window.L.map("riskMap", {
    zoomControl: true,
    worldCopyJump: true,
    preferCanvas: true,
  }).setView([18, 0], 2);
  window.L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap &copy; CARTO",
  }).addTo(map);
  window.setTimeout(() => map?.invalidateSize?.(), 150);
  window.addEventListener("resize", () => {
    if (map) map.invalidateSize();
  }, { passive: true });
  return map;
}

export function addRiskMarker(lat, lon, riskScore, riskLevel, topFactor) {
  if (!map) initMap();
  if (!map) return;

  const marker = window.L.circleMarker([lat || 0, lon || 0], {
    radius: 10,
    color: riskColor(riskLevel),
    fillColor: riskColor(riskLevel),
    fillOpacity: 0.7,
    weight: 2,
  }).addTo(map);

  marker.bindPopup(`
    <strong>${riskLevel}</strong><br>
    Score: ${riskScore.toFixed(2)}<br>
    Top factor: ${topFactor || "n/a"}
  `);
  markers.push(marker);
  if (markers.length > MAX_MARKERS) {
    const oldest = markers.shift();
    map.removeLayer(oldest);
  }
  if (lat || lon) {
    map.flyTo([lat || 0, lon || 0], 3, { animate: true, duration: 0.8 });
  }
}
