(function () {
  const API_OVERVIEW = "/api/market-overview";
  const API_CHAT = "/api/chat";

  const SECTOR_ICONS = {
    Defence: "🛡️",
    Pharma: "💊",
    Healthcare: "🏥",
    Thematic: "📈",
    Sectoral: "🏭",
    default: "📊",
  };

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function sparklineValues(seed, count) {
    const values = [];
    let current = 40 + (seed % 20);
    for (let i = 0; i < count; i += 1) {
      current += Math.sin(i / 2 + seed) * 3 + (seed % 5) * 0.2;
      values.push(Math.max(8, Math.min(92, current)));
    }
    return values;
  }

  function renderSparkline(values, stroke) {
    const width = 120;
    const height = 48;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const points = values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * width;
        const y = height - ((value - min) / range) * (height - 6) - 3;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

    return `
      <svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
        <polyline fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${points}" />
      </svg>`;
  }

  function renderLoading() {
    return `<div class="trends-loading"><p>Loading market overview…</p></div>`;
  }

  function renderError(message) {
    return `
      <div class="trends-error" role="alert">
        <p>${escapeHtml(message)}</p>
        <button type="button" class="btn btn-outline btn-sm" id="trends-retry">Retry</button>
      </div>`;
  }

  function renderHero(data) {
    return `
      <section class="groww-hero">
        <div class="groww-hero-copy">
          <p class="groww-eyebrow">Market overview</p>
          <h2>Track index, sector &amp; commodity-linked scheme facts</h2>
          <p>${escapeHtml(data.corpus_note)}</p>
          ${
            data.last_corpus_refresh
              ? `<span class="groww-meta-pill">Updated ${escapeHtml(data.last_corpus_refresh)}</span>`
              : ""
          }
        </div>
        <div class="groww-hero-stats">
          <div class="groww-stat">
            <span class="groww-stat-value">${data.scheme_count || 12}</span>
            <span class="groww-stat-label">Schemes indexed</span>
          </div>
          <div class="groww-stat">
            <span class="groww-stat-value">${(data.category_groups || []).length}</span>
            <span class="groww-stat-label">Categories</span>
          </div>
          <div class="groww-stat">
            <span class="groww-stat-value">${(data.sector_cards || []).length}</span>
            <span class="groww-stat-label">Thematic funds</span>
          </div>
        </div>
      </section>`;
  }

  function renderIndexStrip(indexCards, commodityCards) {
    const cards = [...(indexCards || []), ...(commodityCards || [])];
    if (!cards.length) return "";

    const items = cards
      .map((card, index) => {
        const seed = (card.label || card.id || "x").length * 17 + index * 11;
        const spark = renderSparkline(sparklineValues(seed, 14), card.label === "Gold" ? "#d4a017" : card.label === "Silver" ? "#94a3b8" : "#22704a");
        const commodityClass =
          card.label === "Gold" ? "groww-index-card--gold" : card.label === "Silver" ? "groww-index-card--silver" : "";

        return `
          <article class="groww-index-card ${commodityClass}">
            <div class="groww-index-card-top">
              <div>
                <span class="groww-index-label">${escapeHtml(card.label)}</span>
                <h3>${escapeHtml(card.subtitle || card.label)}</h3>
              </div>
              ${card.label === "Gold" || card.label === "Silver" ? `<span class="commodity-dot commodity-dot--${card.label.toLowerCase()}"></span>` : ""}
            </div>
            ${spark}
            <p class="groww-index-fact">${escapeHtml(card.fact)}</p>
            ${
              card.source_url
                ? `<a class="source-link" href="${escapeHtml(card.source_url)}" target="_blank" rel="noopener noreferrer">View source →</a>`
                : ""
            }
          </article>`;
      })
      .join("");

    return `
      <section class="trends-section">
        <div class="groww-section-head">
          <h2>Indices &amp; commodities</h2>
          <p>Corpus-backed facts — not live exchange prices.</p>
        </div>
        <div class="groww-index-grid">${items}</div>
      </section>`;
  }

  function renderCategoryTabs(groups) {
    if (!groups.length) return "";

    const tabs = groups
      .map(
        (group, index) =>
          `<button type="button" class="groww-filter-tab${index === 0 ? " groww-filter-tab--active" : ""}" data-category="${escapeHtml(group.category)}">${escapeHtml(group.category)} <span>${group.count}</span></button>`
      )
      .join("");

    const panels = groups
      .map((group, index) => {
        const schemes = group.schemes
          .map(
            (scheme) => `
            <a class="groww-scheme-row" href="/investment-faq.html?scheme=${encodeURIComponent(scheme.slug)}">
              <span>${escapeHtml(scheme.short_name || scheme.scheme_name)}</span>
              <span class="groww-scheme-arrow">→</span>
            </a>`
          )
          .join("");

        return `
          <div class="groww-category-panel${index === 0 ? "" : " hidden"}" data-category-panel="${escapeHtml(group.category)}">
            ${schemes}
          </div>`;
      })
      .join("");

    return `
      <section class="trends-section">
        <div class="groww-section-head">
          <h2>Explore by category</h2>
          <p>Browse indexed HDFC schemes grouped by investment style.</p>
        </div>
        <div class="groww-filter-tabs" id="groww-category-tabs">${tabs}</div>
        <div class="groww-category-panels">${panels}</div>
      </section>`;
  }

  function sectorIcon(category) {
    const key = Object.keys(SECTOR_ICONS).find((name) => (category || "").includes(name));
    return SECTOR_ICONS[key || "default"];
  }

  function renderSectorGrid(cards) {
    if (!cards.length) return "";

    const items = cards
      .map((card) => {
        const icon = sectorIcon(card.category);
        return `
          <article class="groww-sector-card">
            <div class="groww-sector-icon" aria-hidden="true">${icon}</div>
            <span class="scheme-tag">${escapeHtml(card.category)}</span>
            <h3>${escapeHtml(card.title)}</h3>
            <p>${escapeHtml(card.fact)}</p>
            <a class="source-link" href="${escapeHtml(card.source_url)}" target="_blank" rel="noopener noreferrer">View source →</a>
          </article>`;
      })
      .join("");

    return `
      <section class="trends-section sector-section">
        <div class="groww-section-head">
          <h2>Sector &amp; thematic</h2>
          <p>Defence, pharma, and other thematic exposures in the corpus.</p>
        </div>
        <div class="groww-sector-grid">${items}</div>
      </section>`;
  }

  function renderAskPanel(questions) {
    const chips = (questions || [])
      .map((q) => `<button type="button" class="chip trends-ask-chip">${escapeHtml(q)}</button>`)
      .join("");

    return `
      <section class="trends-section groww-ask-panel">
        <div class="groww-section-head">
          <h2>Ask the assistant</h2>
          <p>Get source-backed answers about benchmarks, objectives, and scheme facts.</p>
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
    return `
      ${renderHero(data)}
      ${renderIndexStrip(data.index_cards, data.commodity_cards)}
      ${renderCategoryTabs(data.category_groups || [])}
      ${renderSectorGrid(data.sector_cards || [])}
      ${renderAskPanel(data.suggested_questions || [])}`;
  }

  function bindCategoryTabs() {
    const tabs = document.querySelectorAll(".groww-filter-tab");
    const panels = document.querySelectorAll(".groww-category-panel");
    if (!tabs.length) return;

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const category = tab.dataset.category;
        tabs.forEach((item) => item.classList.toggle("groww-filter-tab--active", item === tab));
        panels.forEach((panel) => {
          panel.classList.toggle("hidden", panel.dataset.categoryPanel !== category);
        });
      });
    });
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

  function bindAskPanel() {
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
      bindCategoryTabs();
      bindAskPanel();
    } catch (err) {
      mount.innerHTML = renderError(err.message || "Failed to load market trends.");
      document.getElementById("trends-retry")?.addEventListener("click", loadMarketTrends);
    }
  }

  window.initMarketTrendsPage = loadMarketTrends;
})();
