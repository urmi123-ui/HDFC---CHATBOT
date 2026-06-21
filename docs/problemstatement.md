# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview

The objective of this project is to build a **facts-only FAQ assistant** for mutual fund schemes, using **Groww** as the reference product context. The assistant answers objective, verifiable queries related to mutual funds by retrieving information **exclusively from official public sources**, such as:

- AMC (Asset Management Company) websites
- AMFI (Association of Mutual Funds in India)
- SEBI (Securities and Exchange Board of India)

The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a single, clear source link and adhere to defined constraints around clarity, accuracy, and compliance.

---

## Objective

Design and implement a lightweight **Retrieval-Augmented Generation (RAG)**-based assistant that:

- Answers factual queries about mutual fund schemes and fund management data
- Uses a curated corpus of official documents
- Provides concise, source-backed responses

---

## Target Users

- **Retail investors** comparing mutual fund schemes
- **Customer support and content teams** handling repetitive mutual fund queries

---

## Scope of Work

### 1. Corpus Definition

**Selected AMC:** HDFC Asset Management Company (HDFC Mutual Fund)

For the initial build, the corpus is limited to **12 HDFC scheme pages on Groww** (reference product context). Each URL serves as a single scheme-level source for factual retrieval.

| # | Scheme | URL |
|---|--------|-----|
| 1 | HDFC Pharma and Healthcare Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-pharma-and-healthcare-fund-direct-growth |
| 2 | HDFC Nifty 50 Index Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth |
| 3 | HDFC Balanced Advantage Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |
| 4 | HDFC Gold ETF Fund of Fund (Direct Plan Growth) | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth |
| 5 | HDFC Small Cap Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 6 | HDFC Equity Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 7 | HDFC Defence Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth |
| 8 | HDFC Mid Cap Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| 9 | HDFC Silver ETF FoF (Direct Growth) | https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth |
| 10 | HDFC Short Term Opportunities Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-short-term-opportunities-fund-direct-growth |
| 11 | HDFC Focused Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth |
| 12 | HDFC Multi Cap Fund (Direct Growth) | https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth |

**Future expansion (optional):** Broaden the corpus to **15–25 official public URLs**, including scheme factsheets, KIM, SID, AMC FAQ/help pages, and AMFI/SEBI guidance pages.

### 2. FAQ Assistant Requirements

The assistant must answer **facts-only queries** about scheme details and **fund management data** (e.g., fund manager name, tenure, and stated investment approach), such as:

| Query Type | Example |
|------------|---------|
| Expense ratio | What is the expense ratio of a scheme? |
| Exit load | What are the exit load details? |
| Minimum SIP | What is the minimum SIP amount? |
| ELSS lock-in | What is the ELSS lock-in period? |
| Riskometer | What is the riskometer classification? |
| Benchmark | What is the benchmark index? |
| Fund management | Who manages this fund? What is the fund manager's tenure or investment approach? |
| Documents | How do I download statements or capital gains reports? |

**Response rules:**

- Maximum of **3 sentences** per response
- Exactly **one citation link** per response
- Include a footer on every response:
  ```
  Last updated from sources: <date>
  ```

### 3. Refusal Handling

The assistant must **refuse** non-factual or advisory queries, such as:

- *"Should I invest in this fund?"*
- *"Which fund is better?"*

Refusal responses should:

- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., AMFI or SEBI resource)

### 4. User Interface (Minimal)

The solution should include a simple interface with:

- A welcome message
- Three example questions
- A visible disclaimer:
  > **Facts-only. No investment advice.**

---

## Constraints

### Data and Sources

- **Current phase:** Answers are retrieved from the 12 curated Groww scheme pages listed above (HDFC funds only)
- **Long-term target:** Prefer official public sources (AMC, AMFI, SEBI) and avoid third-party blogs or unrelated aggregator content

### Privacy and Security

Do **not** collect, store, or process:

- PAN or Aadhaar numbers
- Account numbers
- OTPs
- Email addresses or phone numbers

### Content Restrictions

- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries, provide a link to the official factsheet only

### Transparency

- Responses must be short, factual, and verifiable
- Every answer must include a source link and last updated date

---

## Expected Deliverables

| Deliverable | Details |
|-------------|---------|
| **README** | Setup instructions, selected AMC (HDFC) and 12 Groww scheme URLs, architecture overview (RAG approach), known limitations |
| **Disclaimer snippet** | *"Facts-only. No investment advice."* |

---

## Success Criteria

- [ ] Accurate retrieval of factual mutual fund and fund management information
- [ ] Strict adherence to facts-only responses
- [ ] Consistent inclusion of valid source citations
- [ ] Proper refusal of advisory queries
- [ ] Clean, minimal, and user-friendly interface

---

## Summary

The goal is to build a **trustworthy, transparent, and compliant** mutual fund FAQ assistant that prioritizes **accuracy over intelligence**. The system should ensure that users receive only verified, source-backed financial information, without any advisory bias or speculative content.
