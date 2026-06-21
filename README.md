# Mutual Fund FAQ Assistant

Facts-only RAG chatbot for HDFC mutual fund schemes on Groww. Answers objective queries (expense ratio, exit load, fund managers, etc.) with source-backed responses. No investment advice.

> **Facts-only. No investment advice.**

## Documentation

- [Problem Statement](docs/problemstatement.md)
- [Architecture](architecture.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Edge Cases](docs/edgecase.md)

## Corpus

**AMC:** HDFC Asset Management Company  
**Sources:** 12 HDFC scheme pages on Groww (see `config/corpus.yaml`)

## Setup

### Prerequisites

- Python 3.11+
- pip

### Install

```bash
cd "rag chatbot"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add API keys when implementing Phase 4+
```

### Run API (Phase 0)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok","corpus_scheme_count":12}
```

### Run ingestion (Phase 1)

```bash
# Full pipeline: fetch → parse → chunk → embed → index
python -m ingestion.run

# Re-index from existing parsed data (skip network fetch)
python -m ingestion.run --skip-fetch

# Individual steps
python -m ingestion.fetch
python -m ingestion.parse
python -m ingestion.chunk
python -m ingestion.index
```

Outputs:
- `data/raw/{slug}/` — fetched HTML + metadata
- `data/processed/{slug}/sections.json` — parsed sections
- `data/processed/{slug}/chunks.json` — chunked text (debug)
- `data/index/` — ChromaDB vector store
- `data/index/scheme_metadata.json` — scheme lookup index
- `data/ingestion_log.json` — last run summary

## Project Structure

```
├── app/              # FastAPI application
├── config/           # corpus.yaml (12 scheme URLs)
├── data/             # raw, processed, index (gitignored)
├── docs/             # problem statement, plans, edge cases
├── ingestion/        # fetch, parse, chunk, index (Phase 1+)
├── scheduler/        # daily ingestion trigger (Phase 7+)
├── tests/
├── ui/               # chat UI (Phase 6+)
├── architecture.md
└── requirements.txt
```

## Implementation Status

| Phase | Status |
|-------|--------|
| 0 — Project foundation | Done |
| 1 — Ingestion pipeline | Done |
| 2 — Retrieval | Pending |
| 3 — Classifier & refusal | Pending |
| 4 — RAG generation | Pending |
| 5 — Chat API | Pending |
| 6 — UI | Pending |
| 7 — Daily scheduler | Pending |
| 8 — Hardening & launch | Pending |

## Known Limitations

- Corpus limited to 12 Groww scheme pages (not AMC KIM/SID documents)
- No investment advice, comparisons, or return calculations
- No PII collection (PAN, Aadhaar, account numbers, OTP, email, phone)
