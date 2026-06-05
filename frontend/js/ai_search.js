function typeText(el, text) {
  el.textContent = "";
  const cursor = document.createElement("span");
  cursor.className = "typing-cursor";
  cursor.textContent = "|";
  el.appendChild(document.createTextNode(""));
  el.appendChild(cursor);

  let index = 0;
  const tick = () => {
    if (index < text.length) {
      const node = el.firstChild;
      node.data += text[index++];
      window.setTimeout(tick, 14);
    } else {
      cursor.remove();
    }
  };
  tick();
}

function riskBadgeClass(level) {
  if (level === "HIGH RISK") return "high";
  if (level === "CAUTION" || level === "ELEVATED") return "caution";
  return "safe";
}

function renderRouteAdvice(routeAdvice) {
  if (!routeAdvice) return "";

  return `
    <section class="route-advice">
      <div class="route-advice-head">
        <div>
          <span class="eyebrow">Route Advisory</span>
          <h4>${routeAdvice.start} to ${routeAdvice.end}</h4>
        </div>
        <div class="route-meta">
          <span>Recommended: ${routeAdvice.recommended_route}</span>
          <span>Threshold: ${Number(routeAdvice.risk_threshold).toFixed(0)}</span>
        </div>
      </div>
      <p class="route-summary">${routeAdvice.route_summary}</p>
      <div class="route-table-wrap">
        <table class="route-table">
          <thead>
            <tr>
              <th>Route</th>
              <th>Avg Risk</th>
              <th>Peak Risk</th>
              <th>High-Risk Waypoints</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${(routeAdvice.comparison_table || []).map((row) => `
              <tr>
                <td>${row.route}</td>
                <td>${Number(row.average_risk_score).toFixed(2)}</td>
                <td>${Number(row.peak_risk_score).toFixed(2)}</td>
                <td>${row.high_risk_waypoints}</td>
                <td><span class="badge ${riskBadgeClass(row.status)}">${row.status}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderAnswer(target, data) {
  const points = data.key_points || [];
  const factors = data.risk_factors || [];
  const routeAdvice = data.route_advice;

  target.innerHTML = `
    <div class="answer-stack">
      <section class="answer-block">
        <div class="section-kicker">Answer</div>
        <div class="ai-answer-text"></div>
      </section>
      ${renderRouteAdvice(routeAdvice)}
      <section class="answer-block">
        <div class="section-kicker">Key Points</div>
        <ul class="answer-list">
          ${points.length ? points.map((point) => `<li>${point}</li>`).join("") : "<li>No key points returned.</li>"}
        </ul>
      </section>
      <section class="answer-block">
        <div class="section-kicker">Risk Factors</div>
        <p class="answer-text">${factors.length ? factors.join(", ") : "None explicitly listed."}</p>
      </section>
      <p class="answer-source"><em>${data.sources_note || "Based on oceanographic reasoning and the trained risk model."}</em></p>
    </div>
  `;

  const textEl = target.querySelector(".ai-answer-text");
  typeText(textEl, (data.answer || "").trim() || "No answer returned.");
}

export function initAiSearch(showLoading, hideLoading, showToast) {
  const query = document.getElementById("aiQuery");
  const answer = document.getElementById("aiAnswer");
  const btn = document.getElementById("aiSearchBtn");

  document.querySelectorAll("#suggestions .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      query.value = chip.textContent;
      query.focus();
    });
  });

  const runSearch = async () => {
    const queryText = query.value.trim();
    if (!queryText) {
      showToast("Please enter a maritime research question.", "info");
      return;
    }

    showLoading("Searching oceanic knowledge...");
    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail?.detail || data?.detail || "Gemini request failed");
      }
      renderAnswer(answer, data);
    } catch (error) {
      answer.innerHTML = `<div class="empty-state">Warning: Lost signal from the deep - ${error.message}</div>`;
      showToast("Lost signal from the deep - check your connection.", "warning");
    } finally {
      hideLoading();
    }
  };

  btn.addEventListener("click", runSearch);
  query.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) runSearch();
  });
}
