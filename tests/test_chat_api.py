from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.chat import handle_chat
from app.generator import GenerationResult
from app.main import app
from app.retriever import Retriever


@dataclass
class MockGenerator:
    answer: str
    model: str = "mock"

    def generate(self, question: str, chunks: tuple) -> GenerationResult:
        return GenerationResult(answer=self.answer, model=self.model)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def retriever():
    instance = Retriever()
    if not instance.is_ready():
        pytest.skip("Vector index not built — run `python -m ingestion.run` first")
    return instance


class TestChatHandler:
    def test_advisory_skips_retrieval(self):
        retriever = MagicMock()
        response, meta = handle_chat("Should I invest in HDFC Mid Cap Fund?", retriever=retriever)
        assert response.is_refusal is True
        assert meta.refusal is True
        assert meta.query_class == "advisory"
        retriever.retrieve.assert_not_called()

    def test_pii_blocked(self, retriever):
        response, meta = handle_chat("My PAN is ABCDE1234F, what is exit load?", retriever=retriever)
        assert response.is_refusal is True
        assert meta.query_class == "pii_blocked"

    def test_factual_with_mock_generator(self, retriever):
        generator = MockGenerator("The expense ratio is 0.76.")
        response, meta = handle_chat(
            "Expense ratio of HDFC Mid Cap Fund Direct Growth?",
            retriever=retriever,
            generator=generator,
        )
        assert response.is_refusal is False
        assert "0.76" in response.answer
        assert meta.query_class == "factual"
        assert meta.resolved_slug == "hdfc-mid-cap-fund-direct-growth"


class TestChatAPI:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["corpus_scheme_count"] == 12

    def test_ready(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        body = response.json()
        assert "ready" in body
        assert "chunk_count" in body

    def test_chat_advisory_refusal(self, client):
        response = client.post("/api/chat", json={"message": "Should I invest in HDFC Mid Cap Fund?"})
        assert response.status_code == 200
        body = response.json()
        assert body["is_refusal"] is True
        assert body["disclaimer"] == "Facts-only. No investment advice."
        assert body["citation_url"]

    def test_chat_empty_message_rejected(self, client):
        response = client.post("/api/chat", json={"message": "   "})
        assert response.status_code == 422

    def test_chat_missing_message_rejected(self, client):
        response = client.post("/api/chat", json={})
        assert response.status_code == 422

    def test_chat_pii_rejected(self, client):
        response = client.post("/api/chat", json={"message": "My PAN is ABCDE1234F"})
        assert response.status_code == 200
        assert response.json()["is_refusal"] is True

    def test_cors_headers_present(self, client):
        response = client.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_ui_index_served(self, client):
        response = client.get("/index.html")
        assert response.status_code == 200
        assert "HDFC Insights Hub" in response.text
        assert "verified facts, no advice" in response.text

    def test_ui_assistant_page_served(self, client):
        response = client.get("/assistant.html")
        assert response.status_code == 200
        assert "Facts Only Assistant" in response.text
        assert 'id="chat-input"' in response.text
