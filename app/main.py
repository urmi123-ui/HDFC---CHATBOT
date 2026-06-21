from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.chat import handle_chat
from app.formatter import ChatResponse
from app.market_overview import build_market_overview
from app.orchestrator import answer_factual_query
from app.rate_limit import client_ip, get_rate_limiter
from app.retriever import RetrievalResult, Retriever, get_retriever

load_dotenv()

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

_retriever: Retriever | None = None


def _resolve_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = get_retriever()
    return _retriever


def load_corpus_scheme_count() -> int:
    corpus_path = Path(__file__).resolve().parent.parent / "config" / "corpus.yaml"
    with corpus_path.open(encoding="utf-8") as handle:
        corpus = yaml.safe_load(handle)
    return len(corpus.get("schemes", []))


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    retriever = _resolve_retriever()
    if retriever.is_ready():
        print(f"Retriever ready — {retriever.chunk_count} chunks indexed")
    else:
        print("Retriever not ready — run `python -m ingestion.run` to build the index")
    yield


app = FastAPI(
    title="Mutual Fund FAQ Assistant",
    description="Facts-only RAG assistant for HDFC mutual fund schemes.",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    corpus_scheme_count: int


class ReadyResponse(BaseModel):
    ready: bool
    chunk_count: int
    embedding_model: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be empty")
        return value


class RetrievedChunkResponse(BaseModel):
    id: str
    text: str
    section: str
    scheme_name: str
    source_url: str
    last_updated: str
    distance: float


class RetrievalResponse(BaseModel):
    chunks: list[RetrievedChunkResponse]
    resolved_slug: str | None
    resolved_scheme_name: str | None
    resolved_source_url: str | None
    detected_section: str | None
    confidence: float
    ambiguous: bool
    insufficient_context: bool
    supported_schemes: list[str] | None = None


class ChatResponseModel(BaseModel):
    answer: str
    citation_url: str
    last_updated: str
    is_refusal: bool
    disclaimer: str


def _to_retrieval_response(result: RetrievalResult) -> RetrievalResponse:
    return RetrievalResponse(
        chunks=[
            RetrievedChunkResponse(
                id=chunk.id,
                text=chunk.text,
                section=chunk.section,
                scheme_name=chunk.scheme_name,
                source_url=chunk.source_url,
                last_updated=chunk.last_updated,
                distance=chunk.distance,
            )
            for chunk in result.chunks
        ],
        resolved_slug=result.resolved_slug,
        resolved_scheme_name=result.resolved_scheme_name,
        resolved_source_url=result.resolved_source_url,
        detected_section=result.detected_section,
        confidence=result.confidence,
        ambiguous=result.ambiguous,
        insufficient_context=result.insufficient_context,
        supported_schemes=list(result.supported_schemes) if result.supported_schemes else None,
    )


def _to_chat_response(result: ChatResponse) -> ChatResponseModel:
    return ChatResponseModel(
        answer=result.answer,
        citation_url=result.citation_url,
        last_updated=result.last_updated,
        is_refusal=result.is_refusal,
        disclaimer=result.disclaimer,
    )


def _ensure_dev_environment() -> None:
    if os.getenv("ENV", "development").lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")


def _ensure_retriever_ready() -> Retriever:
    retriever = _resolve_retriever()
    if not retriever.is_ready():
        raise HTTPException(status_code=503, detail="Vector index not loaded. Run ingestion first.")
    return retriever


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", corpus_scheme_count=load_corpus_scheme_count())


@app.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    retriever = _resolve_retriever()
    chunk_count = retriever.chunk_count if retriever.is_ready() else 0
    return ReadyResponse(
        ready=retriever.is_ready(),
        chunk_count=chunk_count,
        embedding_model=retriever.model_name,
    )


@app.post("/api/chat", response_model=ChatResponseModel)
def chat(request_body: ChatRequest, request: Request) -> ChatResponseModel:
    get_rate_limiter().check(client_ip(request))

    try:
        response, _meta = handle_chat(request_body.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate an answer right now. Please try again shortly.",
        ) from exc

    if not response.is_refusal and not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured.")

    return _to_chat_response(response)


@app.get("/api/market-overview")
def market_overview() -> dict:
    retriever = _ensure_retriever_ready()
    return build_market_overview(retriever)


@app.get("/dev/retrieve", response_model=RetrievalResponse)
def dev_retrieve(q: str = Query(..., min_length=1, description="Factual query to retrieve against")) -> RetrievalResponse:
    _ensure_dev_environment()
    retriever = _ensure_retriever_ready()
    return _to_retrieval_response(retriever.retrieve(q))


@app.get("/dev/chat", response_model=ChatResponseModel)
def dev_chat(q: str = Query(..., min_length=1, description="Factual query for end-to-end RAG")) -> ChatResponseModel:
    _ensure_dev_environment()
    _ensure_retriever_ready()
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured.")
    return _to_chat_response(answer_factual_query(q))


if UI_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")
