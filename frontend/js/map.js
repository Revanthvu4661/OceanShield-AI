const MAX_MARKERS = 20;
let map;
let coordOverlay;
const markers = [];

function riskColor(level) {
  if (level === "HIGH RISK") return "#ff4757";
  if (level === "CAUTION" || level === "ELEVATED") return "#f59e0b";
  return "#00d68f";
}

export function initMap() {
  if (!window.L) return null;
  if (map) return map;
  map = window.L.map("riskMap", {
    zoomControl: true,
    worldCopyJump: true,
    preferCanvas: true,
  }).setView([10, 0], 2);
  window.L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap &copy; CARTO",
  }).addTo(map);
  map.getContainer().style.cursor = "crosshair";
  attachCursorOverlay();
  window.setTimeout(() => map?.invalidateSize?.(), 150);
  window.addEventListener("resize", () => {
    if (map) map.invalidateSize();
  }, { passive: true });
  return map;
}

function attachCursorOverlay() {
  if (!map || coordOverlay) return;
  const container = map.getContainer();
  container.style.position = "relative";

  coordOverlay = window.L.DomUtil.create("div", "map-coordinates-overlay", container);
  coordOverlay.innerHTML = `
    <div class="map-crosshair map-crosshair-x"></div>
    <div class="map-crosshair map-crosshair-y"></div>
    <div class="map-coordinate-pill">Move cursor over the map</div>
  `;

  const crosshairX = coordOverlay.querySelector(".map-crosshair-x");
  const crosshairY = coordOverlay.querySelector(".map-crosshair-y");
  const pill = coordOverlay.querySelector(".map-coordinate-pill");

  const updatePosition = (event) => {
    const point = map.latLngToContainerPoint(event.latlng);
    crosshairX.style.left = `${point.x}px`;
    crosshairY.style.top = `${point.y}px`;
    pill.textContent = `Lat ${event.latlng.lat.toFixed(4)}  •  Lon ${event.latlng.lng.toFixed(4)}`;
    coordOverlay.classList.add("visible");
  };

  const hidePosition = () => {
    coordOverlay.classList.remove("visible");
  };

  map.on("mousemove", updatePosition);
  map.on("mouseout", hidePosition);
  map.on("zoom", () => {
    if (coordOverlay.classList.contains("visible")) {
      coordOverlay.classList.remove("visible");
    }
  });
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
