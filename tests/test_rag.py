from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

from app.corpus import DISCLAIMER, load_corpus_urls
from app.formatter import format_factual_response, link_only_fallback
from app.generator import GenerationResult
from app.orchestrator import answer_factual_query
from app.retriever import RetrievedChunk, Retriever, RetrievalResult
from app.validator import (
    count_sentences,
    truncate_to_sentences,
    validate_answer,
)


def _chunk(
    *,
    section: str = "expense_ratio",
    text: str = "Scheme: HDFC Mid Cap Fund Direct Growth\nSection: expense_ratio\nExpense ratio: 0.76",
    source_url: str = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    scheme_name: str = "HDFC Mid Cap Fund Direct Growth",
) -> RetrievedChunk:
    return RetrievedChunk(
        id="hdfc-mid-cap-fund-direct-growth#expense_ratio#0",
        text=text,
        section=section,
        scheme_name=scheme_name,
        source_url=source_url,
        last_updated="2026-06-21",
        distance=0.1,
    )


def _retrieval(chunks: tuple[RetrievedChunk, ...], **kwargs) -> RetrievalResult:
    defaults = {
        "resolved_slug": "hdfc-mid-cap-fund-direct-growth",
        "resolved_scheme_name": "HDFC Mid Cap Fund Direct Growth",
        "resolved_source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "detected_section": "expense_ratio",
        "confidence": 1.0,
        "ambiguous": False,
        "insufficient_context": False,
        "supported_schemes": None,
    }
    defaults.update(kwargs)
    return RetrievalResult(chunks=chunks, **defaults)


@dataclass
class MockGenerator:
    answer: str
    model: str = "mock"

    def generate(self, question: str, chunks: tuple[RetrievedChunk, ...]) -> GenerationResult:
        return GenerationResult(answer=self.answer, model=self.model)


class TestValidator:
    def test_accepts_grounded_expense_ratio(self):
        chunks = (_chunk(),)
        result = validate_answer(
            "The expense ratio is 0.76.",
            chunks,
            detected_section="expense_ratio",
            citation_url=chunks[0].source_url,
        )
        assert result.ok
        assert "0.76" in result.answer

    def test_rejects_advisory_language(self):
        chunks = (_chunk(),)
        result = validate_answer(
            "You should invest in this fund because it is a good fund.",
            chunks,
            detected_section="expense_ratio",
            citation_url=chunks[0].source_url,
        )
        assert not result.ok
        assert "advisory_language" in result.issues

    def test_rejects_ungrounded_numbers(self):
        chunks = (_chunk(),)
        result = validate_answer(
            "The expense ratio is 9.99.",
            chunks,
            detected_section="expense_ratio",
            citation_url=chunks[0].source_url,
        )
        assert not result.ok
        assert "ungrounded_numbers" in result.issues

    def test_truncates_to_three_sentences(self):
        text = "One. Two. Three. Four."
        truncated = truncate_to_sentences(text, 3)
        assert count_sentences(truncated) == 3

    def test_truncated_answer_passes_validation(self):
        chunks = (_chunk(),)
        result = validate_answer(
            "One. Two. Three. Four.",
            chunks,
            detected_section="expense_ratio",
            citation_url=chunks[0].source_url,
        )
        assert result.ok
        assert count_sentences(result.answer) == 3
        assert "too_many_sentences" not in result.issues

    def test_rejects_invalid_citation(self):
        chunks = (_chunk(),)
        result = validate_answer(
            "The expense ratio is 0.76.",
            chunks,
            detected_section="expense_ratio",
            citation_url="https://example.com/not-allowed",
        )
        assert not result.ok
        assert "invalid_citation" in result.issues

    def test_rejects_performance_language(self):
        chunks = (_chunk(),)
        result = validate_answer(
            "The fund delivered 15% CAGR over 3 years.",
            chunks,
            detected_section="overview",
            citation_url=chunks[0].source_url,
        )
        assert not result.ok
        assert "performance_language" in result.issues


class TestFormatter:
    def test_format_factual_response(self):
        chunks = (_chunk(),)
        retrieval = _retrieval(chunks)
        response = format_factual_response("The expense ratio is 0.76.", retrieval)
        assert response.citation_url in load_corpus_urls()
        assert response.last_updated == "2026-06-21"
        assert response.is_refusal is False
        assert response.disclaimer == DISCLAIMER

    def test_link_only_fallback(self):
        retrieval = _retrieval((), insufficient_context=True, resolved_source_url=None)
        response = link_only_fallback(retrieval)
        assert "couldn't verify" in response.answer.lower()
        assert response.citation_url == ""


@pytest.fixture(scope="module")
def retriever():
    instance = Retriever()
    if not instance.is_ready():
        pytest.skip("Vector index not built — run `python -m ingestion.run` first")
    return instance


class TestOrchestrator:
    def test_orchestrator_uses_mock_generator(self, retriever):
        generator = MockGenerator("The expense ratio is 0.76.")
        response = answer_factual_query(
            "Expense ratio of HDFC Mid Cap Fund Direct Growth?",
            retriever=retriever,
            generator=generator,
        )
        assert "0.76" in response.answer
        assert response.citation_url in load_corpus_urls()
        assert response.is_refusal is False
        assert count_sentences(response.answer) <= 3

    def test_orchestrator_link_only_on_bad_generation(self, retriever):
        generator = MockGenerator("You should buy this fund for 99.99% returns.")
        response = answer_factual_query(
            "Expense ratio of HDFC Mid Cap Fund Direct Growth?",
            retriever=retriever,
            generator=generator,
        )
        assert "couldn't verify" in response.answer.lower()
        assert response.citation_url in load_corpus_urls()

    def test_orchestrator_fund_management_mock(self, retriever):
        generator = MockGenerator(
            "HDFC Defence Fund Direct Growth is managed by Priya Ranjan (since 2025-04-17), "
            "Dhruv Muchhal (since 2023-06-21), and Rahul Baijal (since 2025-04-17)."
        )
        response = answer_factual_query(
            "Who manages HDFC Defence Fund?",
            retriever=retriever,
            generator=generator,
        )
        assert "Priya Ranjan" in response.answer
        assert "defence-fund" in response.citation_url
        assert count_sentences(response.answer) <= 3


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
class TestGroqIntegration:
    def test_live_groq_expense_ratio(self, retriever):
        response = answer_factual_query(
            "Expense ratio of HDFC Mid Cap Fund Direct Growth?",
            retriever=retriever,
        )
        assert response.citation_url in load_corpus_urls()
        assert response.last_updated
        assert count_sentences(response.answer) <= 3
        assert response.is_refusal is False
