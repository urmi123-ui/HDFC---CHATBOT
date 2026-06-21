from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def retriever_ready():
    from app.retriever import Retriever

    instance = Retriever()
    if not instance.is_ready():
        pytest.skip("Vector index not built — run `python -m ingestion.run` first")
    return instance


class TestMarketOverviewAPI:
    def test_market_overview_returns_corpus_data(self, client, retriever_ready):
        response = client.get("/api/market-overview")
        assert response.status_code == 200
        body = response.json()

        assert body["scheme_count"] == 12
        assert body["category_groups"]
        assert len(body["index_cards"]) >= 1
        assert len(body["commodity_cards"]) == 2
        assert body["suggested_questions"]
        assert "Facts-only" in body["disclaimer"]

        nifty = next(card for card in body["index_cards"] if card["id"] == "nifty50")
        assert "Nifty" in nifty["label"] or "NIFTY" in nifty["fact"] or "Nifty" in nifty["fact"]
        assert nifty["source_url"].startswith("https://")

    def test_market_overview_sector_cards_include_thematic_schemes(self, client, retriever_ready):
        body = client.get("/api/market-overview").json()
        titles = " ".join(card["title"] for card in body["sector_cards"])
        assert "Defence" in titles or "Pharma" in titles
