(function () {
  const NAV_ITEMS = [
    { id: "home", label: "Home", href: "/index.html" },
    { id: "faq", label: "Investment FAQ", href: "/investment-faq.html" },
    { id: "trends", label: "Market Trends", href: "/market-trends.html" },
    { id: "historical", label: "Historical Data", href: "/historical-data.html" },
    { id: "assistant", label: "Facts Only Assistant", href: "/assistant.html" },
  ];

  const CURRENT_YEAR = new Date().getFullYear();

  function renderHeader(activeId) {
    const navLinks = NAV_ITEMS.map(
      (item) =>
        `<a href="${item.href}" class="nav-link${item.id === activeId ? " nav-link--active" : ""}">${item.label}</a>`
    ).join("");

    return `
      <header class="site-header">
        <div class="container header-inner">
          <a href="/index.html" class="logo">HDFC Insights Hub</a>
          <nav class="main-nav" aria-label="Main navigation">${navLinks}</nav>
          <div class="header-actions">
            <span class="disclaimer-pill">Facts-only · No investment advice</span>
            <label class="header-search" aria-label="Search site">
              <span class="header-search-icon" aria-hidden="true">⌕</span>
              <input type="search" class="header-search-input" placeholder="Search..." disabled title="Site search coming soon" />
            </label>
          </div>
          <button class="nav-toggle" type="button" aria-label="Open menu" aria-expanded="false">
            <span></span><span></span><span></span>
          </button>
        </div>
      </header>`;
  }

  function renderFooter() {
    return `
      <footer class="site-footer">
        <div class="container footer-inner">
          <p class="footer-brand">HDFC Mutual Fund</p>
          <nav class="footer-links" aria-label="Footer links">
            <a href="https://www.amfiindia.com/investor/knowledge-center-info?faqs" target="_blank" rel="noopener">AMFI</a>
            <a href="https://investor.sebi.gov.in/" target="_blank" rel="noopener">SEBI</a>
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Use</a>
            <a href="#">Regulatory Disclosures</a>
          </nav>
          <p class="footer-copy">© ${CURRENT_YEAR} HDFC Mutual Fund. All rights reserved. For informational purposes only.</p>
        </div>
      </footer>`;
  }

  function initMobileNav() {
    const toggle = document.querySelector(".nav-toggle");
    const nav = document.querySelector(".main-nav");
    if (!toggle || !nav) return;

    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("main-nav--open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  window.initLayout = function initLayout(activeId) {
    const headerMount = document.getElementById("site-header");
    const footerMount = document.getElementById("site-footer");
    if (headerMount) headerMount.innerHTML = renderHeader(activeId);
    if (footerMount) footerMount.innerHTML = renderFooter();
    initMobileNav();
  };
})();
