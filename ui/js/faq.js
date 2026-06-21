(function () {
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  let activeCategory = "expense_ratio";
  let activeScheme = window.SCHEMES[0];

  function renderTabs() {
    const container = document.getElementById("category-tabs");
    if (!container) return;

    container.innerHTML = window.FAQ_CATEGORIES.map(
      (cat) =>
        `<button type="button" class="tab-pill${cat.id === activeCategory ? " tab-pill--active" : ""}" data-category="${cat.id}">${cat.label}</button>`
    ).join("");

    container.querySelectorAll(".tab-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        activeCategory = btn.dataset.category;
        renderTabs();
        renderFaqContent();
      });
    });
  }

  function renderFaqContent() {
    const subtitle = document.getElementById("faq-subtitle");
    const content = document.getElementById("faq-content");
    if (!content || !activeScheme) return;

    const category = window.FAQ_CONTENT[activeCategory];
    if (!category) return;

    if (subtitle) {
      subtitle.textContent = `Select a category below to view specific details for ${activeScheme.shortName}.`;
    }

    const items = category.items
      .map(
        (item, index) => `
        <div class="accordion-item${index === 0 ? " accordion-item--open" : ""}">
          <button type="button" class="accordion-trigger" aria-expanded="${index === 0 ? "true" : "false"}">
            <span>${escapeHtml(item.question)}</span>
            <span class="accordion-chevron" aria-hidden="true">▾</span>
          </button>
          <div class="accordion-panel">
            <p>${escapeHtml(item.answer.replace("{scheme}", activeScheme.shortName))}</p>
            <a class="source-link" href="${escapeHtml(activeScheme.sourceUrl)}" target="_blank" rel="noopener noreferrer">View source on Groww →</a>
          </div>
        </div>`
      )
      .join("");

    content.innerHTML = `
      <div class="faq-card">
        <div class="faq-card-header">
          <h2>${escapeHtml(category.title)}</h2>
          <span class="faq-scheme-badge">${escapeHtml(activeScheme.shortName)}</span>
        </div>
        ${items}
      </div>`;

    content.querySelectorAll(".accordion-trigger").forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const item = trigger.closest(".accordion-item");
        const isOpen = item.classList.contains("accordion-item--open");
        content.querySelectorAll(".accordion-item").forEach((el) => {
          el.classList.remove("accordion-item--open");
          el.querySelector(".accordion-trigger")?.setAttribute("aria-expanded", "false");
        });
        if (!isOpen) {
          item.classList.add("accordion-item--open");
          trigger.setAttribute("aria-expanded", "true");
        }
      });
    });
  }

  window.initFaqPage = function initFaqPage() {
    if (!window.SCHEMES?.length) return;

    renderTabs();

    const params = new URLSearchParams(window.location.search);
    const initialSlug = params.get("scheme");
    const validSlug = window.SCHEMES.some((s) => s.slug === initialSlug) ? initialSlug : undefined;

    if (typeof window.renderSchemeSidebar !== "function") {
      activeScheme = window.SCHEMES.find((s) => s.slug === validSlug) || window.SCHEMES[0];
      renderFaqContent();
      return;
    }

    window.renderSchemeSidebar(
      "faq-sidebar",
      (scheme) => {
        activeScheme = scheme;
        renderFaqContent();
      },
      { initialSlug: validSlug }
    );
  };
})();
