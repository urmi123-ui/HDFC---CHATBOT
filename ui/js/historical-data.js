(function () {
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function formatDisplayDate(date) {
    return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
  }

  function formatMonthYear(date) {
    return `${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
  }

  function isWeekend(date) {
    const day = date.getDay();
    return day === 0 || day === 6;
  }

  function previousBusinessDay(date) {
    const copy = new Date(date);
    do {
      copy.setDate(copy.getDate() - 1);
    } while (isWeekend(copy));
    return copy;
  }

  function getOneYearRangeLabel(endDate) {
    const start = new Date(endDate);
    start.setFullYear(start.getFullYear() - 1);
    return `${formatMonthYear(start)} – ${formatMonthYear(endDate)}`;
  }

  function hashSlug(slug) {
    let hash = 0;
    for (let i = 0; i < slug.length; i += 1) {
      hash = (hash * 31 + slug.charCodeAt(i)) >>> 0;
    }
    return hash;
  }

  function generateSampleNavRows(slug, rowCount) {
    const rows = [];
    const endDate = new Date();
    let cursor = previousBusinessDay(endDate);
    const baseNav = 1200 + (hashSlug(slug || "") % 400);

    for (let i = 0; i < rowCount; i += 1) {
      const nav = (baseNav + (rowCount - i) * 2.15 + (hashSlug(slug) % 10) * 0.05).toFixed(2);
      rows.push([formatDisplayDate(cursor), Number(nav).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })]);
      cursor = previousBusinessDay(cursor);
    }

    return rows;
  }

  window.initHistoricalDataPage = function initHistoricalDataPage() {
    if (!window.SCHEMES?.length) return;

    const select = document.getElementById("scheme-select");
    const tableBody = document.getElementById("nav-table-body");
    const disclosureLink = document.getElementById("scheme-disclosure-link");
    const dateRange = document.getElementById("date-range");
    const tableFooter = document.getElementById("nav-table-footer");

    if (!select || !tableBody || !disclosureLink || !dateRange) return;

    const today = new Date();
    dateRange.value = getOneYearRangeLabel(today);

    select.innerHTML = window.SCHEMES.map(
      (scheme) => `<option value="${scheme.slug}">${scheme.shortName}</option>`
    ).join("");

    function renderTable(slug) {
      const scheme = window.SCHEMES.find((item) => item.slug === slug) || window.SCHEMES[0];
      disclosureLink.href = scheme.sourceUrl;

      const rows = generateSampleNavRows(scheme.slug, 5);
      tableBody.innerHTML = rows
        .map(([date, nav]) => `<tr><td>${date}</td><td>${nav}</td></tr>`)
        .join("");

      if (tableFooter) {
        tableFooter.textContent = "Sample placeholder NAV rows — full history export coming soon.";
      }
    }

    select.addEventListener("change", () => renderTable(select.value));
    renderTable(select.value);
  };

  window.HistoricalDataUtils = {
    formatDisplayDate,
    getOneYearRangeLabel,
    generateSampleNavRows,
  };
})();
