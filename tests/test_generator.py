from __future__ import annotations

from app.generator import (
    DEFAULT_MAX_CHUNKS,
    GroqGenerator,
    _build_user_prompt,
    _select_chunks,
    _strip_chunk_prefix,
)
from app.retriever import RetrievedChunk


def _chunk(
    *,
    section: str = "expense_ratio",
    text: str = "Scheme: HDFC Mid Cap Fund Direct Growth\nSection: expense_ratio\nExpense ratio: 0.76",
    chunk_index: int = 0,
) -> RetrievedChunk:
    return RetrievedChunk(
        id=f"hdfc-mid-cap-fund-direct-growth#{section}#{chunk_index}",
        text=text,
        section=section,
        scheme_name="HDFC Mid Cap Fund Direct Growth",
        source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        last_updated="2026-06-21",
        distance=0.1 + chunk_index,
    )


class TestGeneratorPrompt:
    def test_strip_chunk_prefix(self):
        text = "Scheme: HDFC Mid Cap Fund Direct Growth\nSection: expense_ratio\nExpense ratio: 0.76"
        assert _strip_chunk_prefix(text) == "Expense ratio: 0.76"

    def test_user_prompt_omits_redundant_prefix(self):
        prompt = _build_user_prompt("What is the expense ratio?", (_chunk(),))
        assert "Scheme:" not in prompt
        assert "Expense ratio: 0.76" in prompt
        assert "Q: What is the expense ratio?" in prompt

    def test_select_chunks_limits_fund_management(self, monkeypatch):
        monkeypatch.setenv("GROQ_MAX_FUND_MANAGEMENT_CHUNKS", "2")
        chunks = tuple(_chunk(section="fund_management", chunk_index=i) for i in range(4))
        selected = _select_chunks(chunks)
        assert len(selected) == 2

    def test_select_chunks_default_limit(self, monkeypatch):
        monkeypatch.delenv("GROQ_MAX_CHUNKS", raising=False)
        chunks = tuple(_chunk(chunk_index=i) for i in range(4))
        selected = _select_chunks(chunks)
        assert len(selected) == DEFAULT_MAX_CHUNKS

    def test_groq_max_tokens_from_env(self, monkeypatch):
        monkeypatch.setenv("GROQ_MAX_TOKENS", "96")
        generator = GroqGenerator(api_key="test-key")
        assert generator.max_tokens == 96
