/** HDFC scheme metadata — mirrors config/corpus.yaml */
window.SCHEMES = [
  {
    slug: "hdfc-pharma-and-healthcare-fund-direct-growth",
    name: "HDFC Pharma and Healthcare Fund Direct Growth",
    shortName: "HDFC Pharma & Healthcare",
    category: "Equity — Sectoral",
    description: "Sectoral equity fund focused on pharma and healthcare themes.",
    sourceUrl:
      "https://groww.in/mutual-funds/hdfc-pharma-and-healthcare-fund-direct-growth",
  },
  {
    slug: "hdfc-nifty-50-index-fund-direct-growth",
    name: "HDFC Nifty 50 Index Fund Direct Growth",
    shortName: "Nifty 50 Index",
    category: "Equity — Index",
    description: "Index fund tracking the Nifty 50 benchmark.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth",
  },
  {
    slug: "hdfc-balanced-advantage-fund-direct-growth",
    name: "HDFC Balanced Advantage Fund Direct Growth",
    shortName: "Balanced Advantage",
    category: "Hybrid — Dynamic Asset Allocation",
    description: "Dynamic asset allocation across equity and debt.",
    sourceUrl:
      "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
  },
  {
    slug: "hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    name: "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    shortName: "Gold ETF FoF",
    category: "Commodities — Gold FoF",
    description: "Fund of fund investing in gold ETF units.",
    sourceUrl:
      "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
  },
  {
    slug: "hdfc-small-cap-fund-direct-growth",
    name: "HDFC Small Cap Fund Direct Growth",
    shortName: "HDFC Small Cap",
    category: "Equity — Small Cap",
    description: "Equity fund investing predominantly in small-cap stocks.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
  },
  {
    slug: "hdfc-equity-fund-direct-growth",
    name: "HDFC Equity Fund Direct Growth",
    shortName: "HDFC Equity Fund",
    category: "Equity — Large Cap",
    description: "Large-cap equity fund with diversified holdings.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
  },
  {
    slug: "hdfc-defence-fund-direct-growth",
    name: "HDFC Defence Fund Direct Growth",
    shortName: "HDFC Defence Fund",
    category: "Equity — Sectoral/Thematic",
    description: "Thematic equity fund focused on defence sector companies.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
  },
  {
    slug: "hdfc-mid-cap-fund-direct-growth",
    name: "HDFC Mid Cap Fund Direct Growth",
    shortName: "HDFC Mid Cap Fund",
    category: "Equity — Mid Cap",
    description: "Mid-cap equity fund for long-term capital appreciation.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  },
  {
    slug: "hdfc-silver-etf-fof-direct-growth",
    name: "HDFC Silver ETF FoF Direct Growth",
    shortName: "Silver ETF FoF",
    category: "Commodities — Silver FoF",
    description: "Fund of fund providing exposure to silver ETFs.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
  },
  {
    slug: "hdfc-short-term-opportunities-fund-direct-growth",
    name: "HDFC Short Term Opportunities Fund Direct Growth",
    shortName: "Short Term Opportunities",
    category: "Debt — Short Duration",
    description: "Short-duration debt fund for stable income.",
    sourceUrl:
      "https://groww.in/mutual-funds/hdfc-short-term-opportunities-fund-direct-growth",
  },
  {
    slug: "hdfc-focused-fund-direct-growth",
    name: "HDFC Focused Fund Direct Growth",
    shortName: "HDFC Focused Fund",
    category: "Equity — Focused",
    description: "Focused equity fund with a concentrated portfolio.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
  },
  {
    slug: "hdfc-multi-cap-fund-direct-growth",
    name: "HDFC Multi Cap Fund Direct Growth",
    shortName: "HDFC Multi Cap Fund",
    category: "Equity — Multi Cap",
    description: "Multi-cap equity fund across market capitalizations.",
    sourceUrl: "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth",
  },
];

window.EXAMPLE_QUESTIONS = [
  "What is the expense ratio of HDFC Mid Cap Fund Direct Growth?",
  "What is the exit load on HDFC Defence Fund Direct Growth?",
  "Who manages HDFC Gold ETF Fund of Fund Direct Plan Growth?",
];

window.FAQ_CATEGORIES = [
  { id: "expense_ratio", label: "Expense ratio" },
  { id: "exit_load", label: "Exit load" },
  { id: "minimum_investment", label: "Minimum SIP" },
  { id: "benchmark", label: "Benchmark" },
  { id: "fund_management", label: "Fund management" },
  { id: "overview", label: "Risk & category" },
];

window.FAQ_CONTENT = {
  expense_ratio: {
    title: "Expense Ratio Disclosures",
    items: [
      {
        question: "What is the current expense ratio of the direct plan?",
        answer:
          "The direct plan expense ratio is disclosed on the official scheme page and reflects annual fund operating costs as a percentage of average net assets.",
      },
      {
        question: "How does the direct plan expense ratio compare to the regular plan?",
        answer:
          "Direct plans typically carry a lower expense ratio than regular plans because distributor commissions are not included in direct plan costs.",
      },
      {
        question: "Where can I find the latest expense ratio update?",
        answer:
          "The most recent expense ratio is published on the scheme factsheet and the official Groww scheme page linked below.",
      },
    ],
  },
  exit_load: {
    title: "Exit Load Structure",
    items: [
      {
        question: "What is the exit load for early redemptions?",
        answer:
          "Exit load terms specify a percentage charged on redeemed units if withdrawn before the stated holding period on the scheme page.",
      },
      {
        question: "Is exit load applicable on SIP redemptions?",
        answer:
          "Exit load rules apply based on the holding period of each SIP instalment unit, as described in the scheme documentation.",
      },
    ],
  },
  minimum_investment: {
    title: "Minimum Investment Details",
    items: [
      {
        question: "What is the minimum SIP amount?",
        answer:
          "The minimum SIP and lump-sum investment amounts are listed under minimum investment details on the official scheme page.",
      },
      {
        question: "Can I increase my SIP amount later?",
        answer:
          "SIP top-up and modification options depend on your platform; minimum thresholds remain as stated on the scheme page.",
      },
    ],
  },
  benchmark: {
    title: "Benchmark Information",
    items: [
      {
        question: "What benchmark index does this scheme track or compare against?",
        answer:
          "The benchmark index name is disclosed on the scheme page and reflects the index used for performance comparison in factsheets.",
      },
    ],
  },
  fund_management: {
    title: "Fund Management",
    items: [
      {
        question: "Who manages this fund?",
        answer:
          "Fund manager names, tenure, and professional background are listed in the fund management section of the scheme page.",
      },
      {
        question: "What is the fund manager's stated investment approach?",
        answer:
          "The investment approach and manager profile are described factually in the fund management section of official disclosures.",
      },
    ],
  },
  overview: {
    title: "Risk & Category",
    items: [
      {
        question: "What is the scheme category and risk level?",
        answer:
          "The scheme category and riskometer classification are published on the scheme page as part of regulatory disclosures.",
      },
      {
        question: "What is the investment objective?",
        answer:
          "The stated investment objective is available in the scheme overview section of the official page.",
      },
    ],
  },
};
