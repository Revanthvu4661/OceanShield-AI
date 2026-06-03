const SESSION_KEY = "oceanshield_gemini_key";

function typeText(el, text) {
  el.innerHTML = "";
  const textNode = document.createTextNode("");
  const cursor = document.createElement("span");
  cursor.className = "typing-cursor";
  cursor.textContent = "▍";
  el.appendChild(textNode);
  el.appendChild(cursor);

  let i = 0;
  const tick = () => {
    if (i < text.length) {
      textNode.data += text[i++];
      setTimeout(tick, 14);
    } else {
      cursor.remove();
    }
  };
  tick();
}

function renderAnswer(target, data) {
  const points = data.key_points || [];
  const factors = data.risk_factors || [];

  target.innerHTML = `
    <h4>Answer</h4>
    <div class="ai-answer-text"></div>
    <h4>Key Points</h4>
    <ul>${points.length ? points.map((p) => `<li>${p}</li>`).join("") : "<li>No key points returned.</li>"}</ul>
    <h4>Risk Factors</h4>
    <div>${factors.length ? factors.join(", ") : "None explicitly listed."}</div>
    <p><em>${data.sources_note}</em></p>
  `;

  const answerText = (data.answer || "").trim() || "No answer returned.";
  const textEl = target.querySelector(".ai-answer-text");
  textEl.style.whiteSpace = "pre-wrap";
  textEl.style.lineHeight = "1.6";
  typeText(textEl, answerText);
}

export function initAiSearch(showLoading, hideLoading, showToast) {
  const query = document.getElementById("aiQuery");
  const key = document.getElementById("geminiKey");
  const answer = document.getElementById("aiAnswer");
  const btn = document.getElementById("aiSearchBtn");

  key.value = sessionStorage.getItem(SESSION_KEY) || "";
  key.addEventListener("change", () => sessionStorage.setItem(SESSION_KEY, key.value));

  const chips = document.querySelectorAll("#suggestions .chip");
  chips.forEach((chip) => chip.addEventListener("click", () => {
    query.value = chip.textContent;
    query.focus();
  }));

  const runSearch = async () => {
    const queryText = query.value.trim();
    const apiKey = key.value.trim();
    if (!queryText) return showToast("Please enter a maritime research question.", "info");
    if (!apiKey) return showToast("Add a Gemini API key to search the ocean knowledge panel.", "info");
    sessionStorage.setItem(SESSION_KEY, apiKey);
    showLoading("Searching oceanic knowledge...");
    try {
      const response = await fetch("/api/ai-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText, gemini_api_key: apiKey }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail?.detail || data?.detail || "Gemini request failed");
      renderAnswer(answer, data);
    } catch (error) {
      answer.innerHTML = `<div class="empty-state">⚠ Lost signal from the deep — ${error.message}</div>`;
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

