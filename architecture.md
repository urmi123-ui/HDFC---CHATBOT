Architecture 
Architecture: Mutual Fund FAQ Assistant
This document describes the system architecture for a facts-only, RAG-based FAQ assistant scoped to twelve HDFC Mutual Fund scheme pages on Groww. It is derived from problemStatement.md.

A **daily scheduler** runs outside the online request path and triggers the **ingestion component** once every 24 hours to fetch, parse, chunk, embed, and re-index the corpus. User chat requests never invoke ingestion directly.

1. Design Goals
Goal
Architectural implication
Facts-only answers
Retrieval grounded in corpus; LLM constrained by system prompt and post-generation validation
Source-backed responses
Every answer carries exactly one citation URL from the active corpus
Compliance
Advisory/comparison queries are classified and refused before or instead of retrieval
Accuracy over intelligence
Prefer retrieved text over model inference; narrow corpus (12 URLs) reduces hallucination risk
Transparency
Fixed response format: ≤3 sentences + citation + Last updated from sources: <date> footer
Privacy
Stateless chat; no PII collection or persistence


2. High-Level Architecture
Offline Pipeline
Generation Layer
Retrieval Layer
Application Layer
Presentation Layer
Daily trigger
Advisory / Comparison
Factual
Web UI
(Chat + Disclaimer)
API Gateway / Chat Controller
Query Classifier
(Factual vs Advisory)
Refusal Handler
RAG Orchestrator
Response Formatter
Retriever
(Vector + Metadata Filter)
Vector Store
Scheme Metadata Index
LLM
(Constrained Generation)
Output Validator
Daily Scheduler
Ingestion & Crawler
Cleaner / Section Parser
Chunker
Embedding Service
Index Builder
Request path (online): User question → classify → retrieve relevant chunks → generate grounded answer → validate → format → display.
Index path (offline): **Daily Scheduler** → **Ingestion component** → fetch 12 Groww pages → parse into structured sections → chunk → embed → persist to vector store and metadata index.

The scheduler is the sole automatic trigger for ingestion; the chat API reads from the last successfully built index until the next scheduled run completes.

3. System Components
3.1 Presentation Layer (Minimal UI)
A lightweight single-page chat interface inspired by Groww's mutual fund detail pages as reference context.
Responsibilities:
Display welcome message and disclaimer: "Facts-only. No investment advice."
Show three clickable example questions (covering scheme facts and fund management)
Accept free-text user queries
Render assistant replies with citation link and last-updated footer
Never prompt for or accept PII (PAN, Aadhaar, account numbers, OTP, email, phone)
Suggested example questions:
What is the expense ratio of HDFC Mid Cap Fund Direct Growth?
What is the exit load on HDFC Defence Fund Direct Growth?
Who manages HDFC Gold ETF Fund of Fund Direct Plan Growth?

3.2 Application Layer
Chat Controller
Exposes a single endpoint, e.g. POST /api/chat
Accepts { "message": string } only — no session identifiers tied to identity
Routes to classifier, then RAG or refusal path
Returns structured JSON for the UI to render
{
  "answer": "The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.73%.",
  "citation_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "last_updated": "2026-05-29",
  "is_refusal": false
}

Query Classifier
Runs before retrieval to enforce compliance.
Class
Examples
Action
Factual
Expense ratio, exit load, min SIP, benchmark, fund manager name/tenure/experience
Proceed to RAG
Advisory
"Should I invest?", "Is this a good fund?"
Refusal handler
Comparison
"Which fund is better?", "Mid cap vs large cap?"
Refusal handler
Performance-seeking
"What returns will I get?", "Compare 3Y returns"
Refusal or link-only response to scheme page
Out of scope
Schemes not in corpus, unrelated topics
Polite refusal with scope explanation

Implementation options (in order of simplicity):
Rule-based keyword/pattern matcher for advisory and comparison phrases
Lightweight LLM classification with a fixed label set
Hybrid: rules first, LLM fallback for ambiguous cases
Refusal Handler
Produces a polite, templated response when classification blocks RAG:
States the facts-only limitation
Does not retrieve or invent fund data
Includes one educational link (AMFI or SEBI), e.g.:
AMFI — Mutual Funds
SEBI — Investor Education
RAG Orchestrator
Coordinates retrieval, prompt assembly, generation, and validation for factual queries.
Response Formatter
Enforces output contract:
Maximum 3 sentences in the answer body
Exactly one citation_url (must match one of the 12 corpus URLs when answering from corpus)
Footer: Last updated from sources: <date> where <date> comes from chunk metadata (page fetch or parse timestamp), not model inference

3.3 Retrieval Layer
Corpus (Active) — 12 HDFC schemes on Groww (see `config/corpus.yaml`)
Scheme
Source URL
HDFC Pharma and Healthcare Fund Direct Growth
https://groww.in/mutual-funds/hdfc-pharma-and-healthcare-fund-direct-growth
HDFC Nifty 50 Index Fund Direct Growth
https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth
HDFC Balanced Advantage Fund Direct Growth
https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth
HDFC Gold ETF Fund of Fund Direct Plan Growth
https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth
HDFC Small Cap Fund Direct Growth
https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
HDFC Equity Fund Direct Growth
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
HDFC Defence Fund Direct Growth
https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth
HDFC Mid Cap Fund Direct Growth
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
HDFC Silver ETF FoF Direct Growth
https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth
HDFC Short Term Opportunities Fund Direct Growth
https://groww.in/mutual-funds/hdfc-short-term-opportunities-fund-direct-growth
HDFC Focused Fund Direct Growth
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
HDFC Multi Cap Fund Direct Growth
https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth

Scheme Metadata Index
A small lookup table (JSON or embedded DB) keyed by scheme name / slug:
{
  "slug": "hdfc-mid-cap-fund-direct-growth",
  "scheme_name": "HDFC Mid Cap Fund Direct Growth",
  "category": "Equity — Mid Cap",
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "last_fetched_at": "2026-05-29"
}

Used to:
Resolve which scheme the user is asking about
Pre-filter retrieval to a single scheme when detected
Attach the correct citation URL
Vector Store
Stores embedded text chunks with rich metadata:
Metadata field
Purpose
source_url
Citation link
scheme_name
Scheme disambiguation
section
e.g. expense_ratio, exit_load, fund_management, benchmark
last_updated
Footer date
chunk_text
Raw passage for grounding

Recommended stores for a lightweight build: Chroma, FAISS, or LanceDB (local, file-backed).
Retriever
Two-stage retrieval for better precision on a small corpus:
Scheme resolution — Match user query to one of twelve schemes via slug, name, or alias (e.g. "mid cap", "defence fund")
Semantic search — Top-k chunks (k=3–5) filtered by source_url or scheme_name, optionally boosted by section if query intent is detected (e.g. "fund manager" → boost fund_management)
Because the corpus is small (~12 pages), a hybrid approach is viable: metadata filter first, then vector similarity within that subset.

3.4 Generation Layer
LLM (Constrained Generation)
The model receives:
System prompt: facts-only, no advice, use only provided context, max 3 sentences
Retrieved chunks with source URLs and dates
User question
Hard rules in the prompt:
Answer only from retrieved context; if context is insufficient, say so and point to the scheme page
Do not compare funds or compute returns
Do not recommend buy/sell/hold
Include no more than one URL in the answer (formatter may extract citation separately)
Output Validator
Post-generation checks before returning to the user:
Check
Failure action
Answer ≤ 3 sentences
Truncate or regenerate
Citation URL in allowlist
Replace with best matching corpus URL from retrieved chunks
No advisory language detected
Route to refusal template
Grounding: key facts appear in retrieved chunks
Regenerate or fallback to link-only response
Performance numbers not quoted (unless user asked for link)
Strip or refuse


3.5 Offline Ingestion Pipeline (Ingestion Component)
The ingestion component is responsible for rebuilding the corpus index. It is **not** invoked by user chat requests.

**Triggers:**
- **Primary:** Daily scheduler (see §3.6) — fires once per day and calls the ingestion entrypoint (`ingestion/run.py`)
- **Secondary:** Manual CLI run for ad-hoc refreshes outside the schedule

Pipeline steps:
Fetch 12 Groww URLs
Parse HTML / Markdown
Extract Sections
Chunk Text
Generate Embeddings
Upsert Vector Store
Update Metadata Index
Ingestion steps
Fetch — HTTP GET each corpus URL; store raw HTML or converted markdown with fetch timestamp
Clean & parse — Remove navigation, footers, and duplicate chrome; retain scheme-specific sections
Section extraction — Map content into logical blocks aligned with FAQ query types:
Section tag
Example content
overview
Category, risk label, AUM, NAV date
expense_ratio
Expense ratio value and definition
exit_load
Load structure and effective dates
minimum_investment
Min SIP, first/second investment
benchmark
Benchmark index name
tax
STCG/LTCG implications (factual only)
fund_management
Manager name, tenure, education, experience, other schemes
investment_objective
Stated objective from scheme description
fund_house
AMC name, website, incorporation date

Chunking — Section-aware chunks (~200–400 tokens) with overlap only within the same section; keep fund manager bios intact in fund_management chunks
Embed — Use a consistent embedding model (e.g. text-embedding-3-small, nomic-embed-text, or equivalent open-source model)
Index — Upsert into vector store; refresh last_fetched_at in metadata index

3.6 Daily Ingestion Scheduler
A dedicated **scheduler component** triggers the **ingestion component** on a fixed daily cadence so the vector store and metadata index stay aligned with the latest Groww scheme pages. The scheduler does not fetch or parse pages itself — it only starts the ingestion job.

Responsibilities:
Trigger the ingestion component at a configured time each day (e.g. 02:00 UTC / off-peak hours)
Invoke the ingestion entrypoint (`ingestion/run.py` or equivalent) as a single atomic job
Log start time, completion status, URLs fetched, and chunk count
On failure, record error details and optionally retry once before alerting
Implementation options:
Option
Use case
Cron (Linux/macOS crontab or container cron)
Simple VM / bare-metal deployment
APScheduler (embedded in a worker process)
Single-process Python deployment
GitHub Actions scheduled workflow
Repo-hosted corpus refresh with no dedicated worker
Cloud scheduler (AWS EventBridge, GCP Cloud Scheduler)
Managed production environments

Scheduler flow (daily):
Daily Scheduler → triggers → Ingestion component → Fetch, parse, chunk, embed → Upsert Vector Store → Refresh Metadata Index → Success / failure status logged
The online chat API is not blocked during ingestion; retrieval continues to serve the previous index until the new index is fully written and swapped in.

4. End-to-End Request Flow
FormatterValidatorLLMRetrieverRAG OrchestratorRefusal HandlerQuery ClassifierChat ControllerWeb UIFormatterValidatorLLMRetrieverRAG OrchestratorRefusal HandlerQuery ClassifierChat ControllerWeb UIalt[Advisory or comparison][Factual]UserAsk questionPOST /api/chatClassify queryBlock RAGRefusal + AMFI/SEBI linkProceedResolve scheme + retrieve chunksTop-k chunks + metadataPrompt with contextDraft answerValidate grounding & complianceApproved text + citation + dateStructured responseAnswer + citation + footerUser

5. Data Model
Chunk record (vector store document)
id: hdfc-mid-cap-fund-direct-growth#fund_management#0
text: |
  Chaitanya Choksi — Fund Manager, Feb 2023 - Present.
  Education: B.Com, CA. Experience: Prior to HDFC AMC...
scheme_name: HDFC Mid Cap Fund Direct Growth
source_url: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
section: fund_management
last_updated: "2026-05-29"
embedding: [ ... ]

Chat request / response (API contract)
Request:
{ "message": "Who manages HDFC Defence Fund?" }

Response (factual):
{
  "answer": "HDFC Defence Fund Direct Growth is managed by Priya Ranjan (since Apr 2025), Dhruv Muchhal (since Jun 2023), and Rahul Baijal (since Apr 2025). Manager profiles and tenure are listed on the scheme page.",
  "citation_url": "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
  "last_updated": "2026-05-29",
  "is_refusal": false,
  "disclaimer": "Facts-only. No investment advice."
}

Response (refusal):
{
  "answer": "I can only answer factual questions about HDFC schemes in my corpus, such as expense ratio, exit load, or fund manager details. I cannot provide investment advice or recommend which fund to choose.",
  "citation_url": "https://www.amfiindia.com/investor/knowledge-center-info?faqs",
  "last_updated": "2026-05-29",
  "is_refusal": true,
  "disclaimer": "Facts-only. No investment advice."
}


6. Query Routing Matrix
User intent
Classifier label
Retrieval
Generation behavior
Expense ratio of a named scheme
Factual
Filter by scheme → expense_ratio section
State ratio from chunk
Exit load
Factual
exit_load section
State load rules
Minimum SIP
Factual
minimum_investment section
State amounts
Benchmark
Factual
benchmark section
State index name
Fund manager / tenure / experience
Factual
fund_management section
List managers and bios factually
Should I invest?
Advisory
None
Refusal + AMFI/SEBI link
Which fund is better?
Comparison
None
Refusal + educational link
Expected returns / past performance comparison
Performance
None or link-only
Refuse calculation; cite scheme page URL only
Unknown scheme (not in corpus)
Out of scope
None
Explain limited corpus; list supported schemes


7. Technology Stack (Recommended)
Layer
Options
Rationale
Frontend
React / Next.js or plain HTML+JS
Minimal chat UI, fast to ship
Backend
Python (FastAPI) or Node (Express)
Strong RAG ecosystem in Python
Embeddings
BGE-small-en-v1.5 (local, sentence-transformers)
Free; sufficient for 51 short factual chunks
Vector DB
ChromaDB (local persistent)
Metadata filtering, upsert, 51-chunk corpus
LLM
GPT-4o-mini, Claude Haiku, or local Llama
Cost-effective for short answers
Ingestion
BeautifulSoup / Playwright + markdown converter
Parse Groww scheme pages
Config
Environment variables for API keys and corpus URLs
No secrets in repo


8. Security, Privacy & Compliance
Blocked / Not Stored
Allowed
Reject input patterns
Reject input patterns
Classifier
Anonymous factual questions
Corpus URLs only
PAN, Aadhaar, account #, OTP
Email, phone
Investment advice generation
RAG Pipeline
No processing
Refusal
Stateless API — No user accounts, chat history persistence, or analytics tied to identity (optional ephemeral in-memory UI history is acceptable)
Input sanitization — Reject or strip patterns resembling PII before LLM call
Allowlist citations — Validator ensures answer citations are corpus URLs (or fixed AMFI/SEBI URLs for refusals)
No training on user data — Queries are not used to fine-tune models in this phase
Rate limiting — Basic per-IP limits to prevent abuse and cost overrun

9. Deployment Topology
Development (local):
[Browser] → [FastAPI :8000] → [Chroma (local disk)] → [LLM API]
                ↑
         [Daily Scheduler] → [Ingestion script (CLI)]

Production (minimal):
[Browser] → [Static UI (CDN/Vercel)] → [API (container/VM)] → [Vector DB volume]
                                              ↓
                                        [LLM provider]

[Daily Scheduler (cron / cloud scheduler / GitHub Actions)]
        ↓
[Ingestion worker] → rebuild index → Vector DB volume

Corpus refresh: The daily scheduler triggers the ingestion component once per day, rebuilding the vector store and metadata index from live Groww URLs
Manual re-run remains available via CLI for ad-hoc refreshes outside the schedule
Environment separation: dev uses cached markdown snapshots; prod refreshes from live Groww URLs

10. Non-Functional Requirements
Attribute
Target
Latency (p95)
< 5 s end-to-end (including LLM)
Availability
Best-effort for demo; no SLA in phase 1
Corpus size
Fixed 12 URLs; ~120–360 chunks total
Ingestion cadence
Daily scheduler trigger (automatic corpus refresh)
Answer length
≤ 3 sentences + 1 link + footer
Observability
Log query class, scheme resolved, retrieval scores, refusal rate (no PII)


11. Known Limitations
Corpus scope — Only twelve HDFC schemes on Groww; no AMFI/SEBI document ingestion in this phase
Source freshness — Answers reflect the last successful daily ingestion run; intra-day Groww updates are picked up on the next scheduled run
Third-party source — Groww is used as reference context, not HDFC AMC primary documents (KIM/SID/factsheets)
No performance analytics — Return comparisons and projections are explicitly out of scope
Scheme disambiguation — Ambiguous queries (e.g. "HDFC fund expense ratio" without naming the scheme) may require clarification or return the most similar scheme
Fund management completeness — Manager data is limited to what appears on each Groww scheme page
Document download guides — Not in current corpus unless added to a future URL list

12. Future Extensions (Out of Current Scope)
Expand corpus to 15–25 official AMC / AMFI / SEBI URLs
Add clarification turn: "Which scheme did you mean?"
Structured extraction cache (JSON facts per scheme) for numeric fields like expense ratio
Multilingual support (Hindi)
Admin dashboard for ingestion status and chunk inspection

13. Project Structure (Suggested)
m2_4/
├── docs/
│   ├── problemStatement.md
│   └── architecture.md          # this document
├── data/
│   ├── raw/                     # fetched HTML/markdown per URL
│   ├── processed/               # parsed sections & chunks
│   └── index/                   # vector store files
├── ingestion/
│   ├── fetch.py
│   ├── parse.py
│   ├── chunk.py
│   ├── index.py
│   └── run.py                   # ingestion entrypoint invoked by scheduler
├── scheduler/
│   └── daily.py                 # daily trigger (cron/APScheduler wrapper)
├── app/
│   ├── main.py                  # FastAPI entry
│   ├── classifier.py
│   ├── retriever.py
│   ├── generator.py
│   ├── validator.py
│   └── formatter.py
├── ui/
│   └── index.html               # minimal chat UI
├── config/
│   └── corpus.yaml              # 12 URLs + scheme metadata
├── tests/
│   ├── test_classifier.py
│   ├── test_retrieval.py
│   └── test_refusal.py
└── README.md


14. Summary
The Mutual Fund FAQ Assistant is a small-corpus, compliance-first RAG system. A query classifier gates advisory and comparison questions before retrieval. Factual questions flow through scheme-aware retrieval over twelve indexed Groww pages, grounded LLM generation, and a strict response formatter that enforces brevity, a single citation, and a last-updated footer. A **daily scheduler** triggers the **ingestion component** to keep embeddings and metadata in sync with the defined corpus. The architecture prioritizes verifiability and refusal correctness over open-ended conversational ability.
