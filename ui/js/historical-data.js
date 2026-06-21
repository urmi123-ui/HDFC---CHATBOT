(function () {
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const PERIOD_YEARS = { "1": 1, "3": 3, "5": 5 };

  function formatDisplayDate(date) {
    return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
  }

  function formatMonthYear(date) {
    return `${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
  }

  function formatIsoDate(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function parseIsoDate(value) {
    const [y, m, d] = value.split("-").map(Number);
    return new Date(y, m - 1, d);
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

  function addYears(date, years) {
    const copy = new Date(date);
    copy.setFullYear(copy.getFullYear() - years);
    return copy;
  }

  function hashSlug(slug) {
    let hash = 0;
    for (let i = 0; i < slug.length; i += 1) {
      hash = (hash * 31 + slug.charCodeAt(i)) >>> 0;
    }
    return hash;
  }

  function generateNavSeries(slug, startDate, endDate) {
    const points = [];
    const seed = hashSlug(slug || "default");
    const baseNav = 800 + (seed % 600);
    const totalDays = Math.max(1, Math.round((endDate - startDate) / (1000 * 60 * 60 * 24)));
    const step = Math.max(1, Math.floor(totalDays / 120));

    let cursor = new Date(startDate);
    let index = 0;

    while (cursor <= endDate) {
      if (!isWeekend(cursor)) {
        const wave = Math.sin(index / 8 + seed * 0.01) * 12;
        const trend = index * (0.08 + (seed % 7) * 0.01);
        const nav = baseNav + trend + wave + (seed % 13) * 0.07;
        points.push({
          date: new Date(cursor),
          nav: Math.round(nav * 100) / 100,
        });
      }
      cursor.setDate(cursor.getDate() + step);
      index += 1;
    }

    if (!points.length || points[points.length - 1].date < endDate) {
      points.push({
        date: new Date(endDate),
        nav: points.length ? points[points.length - 1].nav + 1.2 : baseNav,
      });
    }

    return points;
  }

  function generateTableRows(points, maxRows) {
    const rows = [];
    const slice = points.slice(-maxRows).reverse();
    slice.forEach((point) => {
      rows.push([
        formatDisplayDate(point.date),
        point.nav.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
        point.nav,
        point.date,
      ]);
    });
    return rows;
  }

  function renderChart(svgEl, axisEl, points) {
    if (!svgEl || !points.length) return;

    const width = 640;
    const height = 220;
    const pad = { top: 16, right: 16, bottom: 8, left: 16 };
    const minNav = Math.min(...points.map((p) => p.nav));
    const maxNav = Math.max(...points.map((p) => p.nav));
    const navRange = maxNav - minNav || 1;

    const coords = points.map((point, i) => {
      const x = pad.left + (i / Math.max(points.length - 1, 1)) * (width - pad.left - pad.right);
      const y = pad.top + (1 - (point.nav - minNav) / navRange) * (height - pad.top - pad.bottom);
      return { x, y };
    });

    const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
    const areaPath = `${linePath} L${coords[coords.length - 1].x.toFixed(1)},${height} L${coords[0].x.toFixed(1)},${height} Z`;

    svgEl.innerHTML = `
      <defs>
        <linearGradient id="navFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#22704a" stop-opacity="0.22" />
          <stop offset="100%" stop-color="#22704a" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      <path d="${areaPath}" fill="url(#navFill)" />
      <path d="${linePath}" fill="none" stroke="#22704a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
    `;

    if (axisEl) {
      const labels = [
        formatMonthYear(points[0].date),
        formatMonthYear(points[Math.floor(points.length / 2)].date),
        formatMonthYear(points[points.length - 1].date),
      ];
      axisEl.innerHTML = labels.map((label) => `<span>${label}</span>`).join("");
    }
  }

  function setActivePeriodTab(years) {
    document.querySelectorAll(".period-tab").forEach((tab) => {
      const active = tab.dataset.years === String(years);
      tab.classList.toggle("period-tab--active", active);
    });
  }

  function clearActivePeriodTabs() {
    document.querySelectorAll(".period-tab").forEach((tab) => {
      tab.classList.remove("period-tab--active");
    });
  }

  function downloadCsv(filename, rows) {
    const header = "Date,NAV (INR)\n";
    const body = rows.map(([date, nav]) => `"${date}",${nav}`).join("\n");
    const blob = new Blob([header + body], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  window.initHistoricalDataPage = function initHistoricalDataPage() {
    if (!window.SCHEMES?.length) return;

    const select = document.getElementById("scheme-select");
    const tableBody = document.getElementById("nav-table-body");
    const disclosureLink = document.getElementById("scheme-disclosure-link");
    const dateFrom = document.getElementById("date-from");
    const dateTo = document.getElementById("date-to");
    const tableFooter = document.getElementById("nav-table-footer");
    const chartEl = document.getElementById("nav-chart");
    const chartAxis = document.getElementById("nav-chart-axis");
    const csvExport = document.getElementById("csv-export");
    const periodTabs = document.getElementById("period-tabs");

    if (!select || !tableBody || !disclosureLink || !dateFrom || !dateTo) return;

    let activeYears = 1;
    let tableRows = [];

    select.innerHTML = window.SCHEMES.map(
      (scheme) => `<option value="${scheme.slug}">${scheme.shortName}</option>`
    ).join("");

    function applyRange(startDate, endDate, years) {
      dateFrom.value = formatIsoDate(startDate);
      dateTo.value = formatIsoDate(endDate);
      if (years) {
        activeYears = years;
        setActivePeriodTab(years);
      }
      renderCurrentScheme();
    }

    function applyPeriodYears(years) {
      const end = parseIsoDate(dateTo.value) || previousBusinessDay(new Date());
      const start = addYears(end, years);
      applyRange(start, end, years);
    }

    function renderCurrentScheme() {
      const scheme = window.SCHEMES.find((item) => item.slug === select.value) || window.SCHEMES[0];
      disclosureLink.href = scheme.sourceUrl;

      const start = parseIsoDate(dateFrom.value);
      const end = parseIsoDate(dateTo.value);
      if (!start || !end || start > end) return;

      const points = generateNavSeries(scheme.slug, start, end);
      const rowCount = activeYears === 1 ? 8 : activeYears === 3 ? 12 : 15;
      tableRows = generateTableRows(points, rowCount);

      tableBody.innerHTML = tableRows
        .map(([date, nav]) => `<tr><td>${date}</td><td>${nav}</td></tr>`)
        .join("");

      renderChart(chartEl, chartAxis, points);

      if (tableFooter) {
        tableFooter.textContent = `${points.length} sample data points · ${formatMonthYear(start)} – ${formatMonthYear(end)}`;
      }
    }

    periodTabs?.addEventListener("click", (event) => {
      const tab = event.target.closest(".period-tab");
      if (!tab?.dataset.years) return;
      applyPeriodYears(Number(tab.dataset.years));
    });

    dateFrom.addEventListener("change", () => {
      clearActivePeriodTabs();
      activeYears = 0;
      renderCurrentScheme();
    });

    dateTo.addEventListener("change", () => {
      clearActivePeriodTabs();
      activeYears = 0;
      renderCurrentScheme();
    });

    select.addEventListener("change", renderCurrentScheme);

    csvExport?.addEventListener("click", () => {
      const scheme = window.SCHEMES.find((item) => item.slug === select.value) || window.SCHEMES[0];
      downloadCsv(`${scheme.slug}-nav-sample.csv`, tableRows.map(([date, nav]) => [date, nav]));
    });

    const end = previousBusinessDay(new Date());
    applyRange(addYears(end, 1), end, 1);
  };

  window.HistoricalDataUtils = {
    formatDisplayDate,
    formatIsoDate,
    generateNavSeries,
  };
})();
