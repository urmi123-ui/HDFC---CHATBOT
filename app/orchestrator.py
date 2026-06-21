from __future__ import annotations

import argparse
import json
import logging
from typing import Protocol

from dotenv import load_dotenv

from app.formatter import ChatResponse, format_factual_response, link_only_fallback
from app.generator import GenerationResult, GroqGenerator, get_generator
from app.retriever import RetrievalResult, Retriever, get_retriever
from app.validator import validate_answer

logger = logging.getLogger(__name__)

MAX_GENERATION_ATTEMPTS = 2


class GeneratorProtocol(Protocol):
    def generate(self, question: str, chunks: tuple) -> GenerationResult: ...


def answer_factual_query(
    message: str,
    *,
    retriever: Retriever | None = None,
    generator: GeneratorProtocol | None = None,
    retrieval: RetrievalResult | None = None,
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
) -> ChatResponse:
    retriever = retriever or get_retriever()
    generator = generator or get_generator()

    retrieval = retrieval or retriever.retrieve(message)
    if not retrieval.chunks or retrieval.insufficient_context:
        logger.info("Retrieval insufficient for query — returning link-only fallback")
        return link_only_fallback(retrieval)

    citation_url = retrieval.resolved_source_url or retrieval.chunks[0].source_url
    draft = ""

    for attempt in range(1, max_attempts + 1):
        generation = generator.generate(message, retrieval.chunks)
        draft = generation.answer
        validation = validate_answer(
            draft,
            retrieval.chunks,
            detected_section=retrieval.detected_section,
            citation_url=citation_url,
        )
        if validation.ok:
            return format_factual_response(validation.answer, retrieval)

        logger.warning(
            "Validation failed on attempt %s: %s",
            attempt,
            ", ".join(validation.issues),
        )
        draft = validation.answer

    if draft:
        partial = validate_answer(
            draft,
            retrieval.chunks,
            detected_section=retrieval.detected_section,
            citation_url=citation_url,
        )
        if partial.ok:
            return format_factual_response(partial.answer, retrieval)

    return link_only_fallback(retrieval)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run factual RAG for a user query")
    parser.add_argument("query", help="Factual user question")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv()
    args = _build_parser().parse_args()
    response = answer_factual_query(args.query)
    print(json.dumps(response.to_dict(), indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
