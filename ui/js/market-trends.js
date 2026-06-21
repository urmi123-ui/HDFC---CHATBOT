(function () {
  const API_OVERVIEW = "/api/market-overview";
  const API_CHAT = "/api/chat";

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function renderLoading() {
    return `
      <div class="trends-loading">
        <p>Loading corpus-backed market overview…</p>
      </div>`;
  }

  function renderError(message) {
    return `
      <div class="trends-error" role="alert">
        <p>${escapeHtml(message)}</p>
        <button type="button" class="btn btn-outline btn-sm" id="trends-retry">Retry</button>
      </div>`;
  }

  function renderCategoryBars(groups) {
    if (!groups.length) return "";
    const maxCount = Math.max(...groups.map((g) => g.count));

    const rows = groups
      .map((group) => {
        const width = Math.max(12, Math.round((group.count / maxCount) * 100));
        const schemes = group.schemes
          .map((s) => `<li><a href="/investment-faq.html?scheme=${encodeURIComponent(s.slug)}">${escapeHtml(s.short_name || s.scheme_name)}</a></li>`)
          .join("");
        return `
          <article class="category-bar-card">
            <div class="category-bar-head">
              <strong>${escapeHtml(group.category)}</strong>
              <span>${group.count} scheme${group.count === 1 ? "" : "s"}</span>
            </div>
            <div class="category-bar-track"><div class="category-bar-fill" style="width:${width}%"></div></div>
            <ul class="category-scheme-list">${schemes}</ul>
          </article>`;
      })
      .join("");

    return `
      <section class="trends-section">
        <div class="section-header">
          <h2>Scheme mix in corpus</h2>
          <p>Factual category breakdown from the 12 indexed HDFC schemes.</p>
        </div>
        <div class="category-bars">${rows}</div>
      </section>`;
  }

  function renderHighlightCards(title, cards, cardClass) {
    if (!cards.length) return "";

    const items = cards
      .map(
        (card) => `
        <article class="fact-card ${cardClass || ""}">
          <div class="fact-card-label">${escapeHtml(card.label)}</div>
          <h3>${escapeHtml(card.subtitle || card.label)}</h3>
          <p>${escapeHtml(card.fact)}</p>
          ${
            card.source_url
              ? `<a class="source-link" href="${escapeHtml(card.source_url)}" target="_blank" rel="noopener noreferrer">View source →</a>`
              : ""
          }
          ${
            card.last_updated
              ? `<div class="fact-card-date">Last updated from sources: ${escapeHtml(card.last_updated)}</div>`
              : ""
          }
        </article>`
      )
      .join("");

    return `
      <section class="trends-section">
        <h2>${escapeHtml(title)}</h2>
        <div class="fact-card-grid">${items}</div>
      </section>`;
  }

  function renderSectorCards(cards) {
    if (!cards.length) return "";

    const items = cards
      .map(
        (card) => `
        <article class="sector-fact-card">
          <span class="scheme-tag">${escapeHtml(card.category)}</span>
          <h3>${escapeHtml(card.title)}</h3>
          <p>${escapeHtml(card.fact)}</p>
          <a class="source-link" href="${escapeHtml(card.source_url)}" target="_blank" rel="noopener noreferrer">View source →</a>
        </article>`
      )
      .join("");

    return `
      <section class="trends-section">
        <div class="sector-header">
          <h2>Sector &amp; thematic schemes</h2>
        </div>
        <div class="sector-fact-grid">${items}</div>
      </section>`;
  }

  function renderAskPanel(questions) {
    const chips = (questions || [])
      .map((q) => `<button type="button" class="chip trends-ask-chip">${escapeHtml(q)}</button>`)
      .join("");

    return `
      <section class="trends-section trends-ask-panel">
        <div class="section-header">
          <h2>Ask about market-linked scheme facts</h2>
          <p>Live Q&amp;A using the same facts-only assistant — benchmarks, objectives, and scheme categories from indexed sources.</p>
        </div>
        <div class="chip-row">${chips}</div>
        <div class="trends-chat-log" id="trends-chat-log" aria-live="polite"></div>
        <form class="trends-chat-form" id="trends-chat-form">
          <input class="chat-input" id="trends-chat-input" type="text" maxlength="500" placeholder="e.g. What is the benchmark of HDFC Nifty 50 Index Fund?" required />
          <button class="btn btn-primary" type="submit">Ask</button>
        </form>
        <p class="privacy-note">Facts-only. No investment advice. Do not share personal details.</p>
      </section>`;
  }

  function renderOverview(data) {
    const refresh = data.last_corpus_refresh
      ? `Corpus last refreshed: ${escapeHtml(data.last_corpus_refresh)}`
      : "";

    return `
      <p class="trends-corpus-note">${escapeHtml(data.corpus_note)}</p>
      <p class="trends-refresh-note">${refresh}</p>
      ${renderCategoryBars(data.category_groups || [])}
      ${renderHighlightCards("Index exposure in corpus", data.index_cards || [], "fact-card--index")}
      ${renderHighlightCards("Commodity-linked schemes", data.commodity_cards || [], "fact-card--commodity")}
      ${renderSectorCards(data.sector_cards || [])}
      ${renderAskPanel(data.suggested_questions || [])}`;
  }

  function appendTrendsMessage(container, role, payload) {
    const wrap = document.createElement("div");
    wrap.className = `trends-chat-message trends-chat-message--${role}${payload.is_refusal ? " trends-chat-message--refusal" : ""}`;

    if (role === "user") {
      wrap.textContent = payload.text;
    } else {
      wrap.innerHTML = `
        <p>${escapeHtml(payload.answer || payload.message)}</p>
        ${
          payload.citation_url
            ? `<a class="source-link" href="${escapeHtml(payload.citation_url)}" target="_blank" rel="noopener noreferrer">View source →</a>`
            : ""
        }
        ${
          payload.last_updated
            ? `<div class="fact-card-date">Last updated from sources: ${escapeHtml(payload.last_updated)}</div>`
            : ""
        }`;
    }

    container.appendChild(wrap);
    container.scrollTop = container.scrollHeight;
  }

  async function askTrendsQuestion(text, logEl, inputEl, submitBtn) {
    const trimmed = text.trim();
    if (!trimmed) return;

    appendTrendsMessage(logEl, "user", { text: trimmed });
    inputEl.disabled = true;
    submitBtn.disabled = true;

    const loading = document.createElement("div");
    loading.className = "trends-chat-loading";
    loading.textContent = "Retrieving verified facts…";
    logEl.appendChild(loading);

    try {
      const response = await fetch(API_CHAT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      });

      loading.remove();

      if (!response.ok) {
        let detail = "Could not fetch an answer. Please try again.";
        try {
          const err = await response.json();
          if (typeof err.detail === "string") detail = err.detail;
        } catch (_) {
          /* ignore */
        }
        throw new Error(detail);
      }

      appendTrendsMessage(logEl, "assistant", await response.json());
    } catch (err) {
      loading.remove();
      appendTrendsMessage(logEl, "assistant", {
        answer: err.message || "Something went wrong.",
        is_refusal: true,
      });
    } finally {
      inputEl.disabled = false;
      submitBtn.disabled = false;
      inputEl.focus();
    }
  }

  function bindAskPanel(questions) {
    const form = document.getElementById("trends-chat-form");
    const input = document.getElementById("trends-chat-input");
    const log = document.getElementById("trends-chat-log");
    if (!form || !input || !log) return;

    const submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value;
      input.value = "";
      askTrendsQuestion(text, log, input, submitBtn);
    });

    document.querySelectorAll(".trends-ask-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        askTrendsQuestion(chip.textContent || "", log, input, submitBtn);
      });
    });
  }

  async function loadMarketTrends() {
    const mount = document.getElementById("trends-content");
    if (!mount) return;

    mount.innerHTML = renderLoading();

    try {
      const response = await fetch(API_OVERVIEW);
      if (!response.ok) {
        throw new Error("Unable to load market overview. Ensure ingestion has been run.");
      }
      const data = await response.json();
      mount.innerHTML = renderOverview(data);
      bindAskPanel(data.suggested_questions);
    } catch (err) {
      mount.innerHTML = renderError(err.message || "Failed to load market trends.");
      document.getElementById("trends-retry")?.addEventListener("click", loadMarketTrends);
    }
  }

  window.initMarketTrendsPage = loadMarketTrends;
})();
