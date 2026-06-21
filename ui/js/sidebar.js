(function () {
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderSchemeSidebar(containerId, onSelect, options) {
    const container = document.getElementById(containerId);
    if (!container || !window.SCHEMES?.length) return;

    const opts = options || {};
    const searchId = `${containerId}-search`;
    const listId = `${containerId}-list`;
    let activeSlug = opts.initialSlug || window.SCHEMES[0].slug;

    container.innerHTML = `
      <input type="search" class="search-input" id="${searchId}" placeholder="Search schemes..." aria-label="Search schemes">
      <ul class="scheme-list" id="${listId}"></ul>`;

    const list = document.getElementById(listId);
    const search = document.getElementById(searchId);
    if (!list || !search) return;

    function renderList(filter) {
      const query = (filter || "").trim().toLowerCase();
      const items = window.SCHEMES.filter(
        (s) =>
          !query ||
          s.name.toLowerCase().includes(query) ||
          s.shortName.toLowerCase().includes(query)
      );

      list.innerHTML = items
        .map(
          (scheme) => `
          <li class="scheme-list-item${scheme.slug === activeSlug ? " scheme-list-item--active" : ""}"
              data-slug="${scheme.slug}" role="button" tabindex="0">
            <span>${escapeHtml(scheme.shortName)}</span>
            ${scheme.slug === activeSlug ? '<span aria-hidden="true">›</span>' : ""}
          </li>`
        )
        .join("");

      list.querySelectorAll(".scheme-list-item").forEach((el) => {
        const select = () => {
          activeSlug = el.dataset.slug;
          renderList(search.value);
          const scheme = window.SCHEMES.find((s) => s.slug === activeSlug);
          if (scheme) onSelect(scheme);
        };

        el.addEventListener("click", select);
        el.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            select();
          }
        });
      });
    }

    search.addEventListener("input", () => renderList(search.value));
    renderList();

    const initial = window.SCHEMES.find((s) => s.slug === activeSlug) || window.SCHEMES[0];
    onSelect(initial);
  }

  window.renderSchemeSidebar = renderSchemeSidebar;
})();
