from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

from groq import Groq

from app.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Facts-only HDFC mutual fund assistant.
Use only the provided context. Max 3 short sentences.
No advice, comparisons, buy/sell/hold, or ungrounded returns.
If context is insufficient, say you cannot answer from indexed data.
No URLs or markdown."""

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_TOKENS = 120
DEFAULT_MAX_CHUNKS = 2
DEFAULT_FUND_MANAGEMENT_MAX_CHUNKS = 3

_CHUNK_PREFIX_PATTERN = re.compile(
    r"^Scheme:\s*.+\nSection:\s*.+\n",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GenerationResult:
    answer: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _strip_chunk_prefix(text: str) -> str:
    """Drop embedding prefix already captured in chunk metadata."""
    stripped = _CHUNK_PREFIX_PATTERN.sub("", text.strip(), count=1)
    return stripped or text.strip()


def _max_chunks_for_section(section: str | None) -> int:
    if section == "fund_management":
        return _env_int("GROQ_MAX_FUND_MANAGEMENT_CHUNKS", DEFAULT_FUND_MANAGEMENT_MAX_CHUNKS)
    return _env_int("GROQ_MAX_CHUNKS", DEFAULT_MAX_CHUNKS)


def _select_chunks(chunks: tuple[RetrievedChunk, ...]) -> tuple[RetrievedChunk, ...]:
    if not chunks:
        return chunks
    section = chunks[0].section
    limit = _max_chunks_for_section(section)
    return chunks[:limit]


def _format_context(chunks: tuple[RetrievedChunk, ...]) -> str:
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        body = _strip_chunk_prefix(chunk.text)
        blocks.append(f"[{index}] {body}")
    return "\n\n".join(blocks)


def _build_user_prompt(question: str, chunks: tuple[RetrievedChunk, ...]) -> str:
    selected = _select_chunks(chunks)
    return (
        f"Context:\n{_format_context(selected)}\n\n"
        f"Q: {question.strip()}\n"
        "A:"
    )


class GroqGenerator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.max_tokens = max_tokens if max_tokens is not None else _env_int("GROQ_MAX_TOKENS", DEFAULT_MAX_TOKENS)
        self.temperature = temperature
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        if self._client is None:
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate(self, question: str, chunks: tuple[RetrievedChunk, ...]) -> GenerationResult:
        if not chunks:
            raise ValueError("At least one retrieved chunk is required for generation")

        user_prompt = _build_user_prompt(question, chunks)
        logger.info(
            "Generating answer with Groq model=%s max_tokens=%s prompt_chars=%s",
            self.model,
            self.max_tokens,
            len(SYSTEM_PROMPT) + len(user_prompt),
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        answer = (response.choices[0].message.content or "").strip()
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        if prompt_tokens is not None:
            logger.info(
                "Groq usage prompt_tokens=%s completion_tokens=%s total=%s",
                prompt_tokens,
                completion_tokens,
                usage.total_tokens if usage else None,
            )
        return GenerationResult(
            answer=answer,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


_default_generator: GroqGenerator | None = None


def get_generator() -> GroqGenerator:
    global _default_generator
    if _default_generator is None:
        _default_generator = GroqGenerator()
    return _default_generator
