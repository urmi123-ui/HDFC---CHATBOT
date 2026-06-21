from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
UI_JS_DIR = ROOT / "ui" / "js"

PAGES = {
    "/": ["HDFC Insights Hub", "Featured Schemes", "Facts Only Assistant"],
    "/index.html": ["verified facts, no advice", "TRY ASKING"],
    "/investment-faq.html": ["Browse factual scheme information", "category-tabs", "Go to Facts Only Assistant"],
    "/market-trends.html": ["Market Trends", "Live corpus", "trends-content", "market-trends.js"],
    "/historical-data.html": ["Historical Data", "NAV Performance History", "scheme-select", "historical-data.js"],
    "/assistant.html": ["Facts Only Assistant", 'id="chat-input"', "chat.js"],
}

STATIC_ASSETS = [
    "/css/styles.css",
    "/js/layout.js",
    "/js/schemes.js",
    "/js/sidebar.js",
    "/js/chat.js",
    "/js/faq.js",
    "/js/historical-data.js",
    "/js/market-trends.js",
]


@pytest.fixture
def client():
    return TestClient(app)


class TestUIPages:
    @pytest.mark.parametrize("path,markers", list(PAGES.items()))
    def test_page_loads_with_expected_content(self, client, path, markers):
        response = client.get(path)
        assert response.status_code == 200
        body = response.text
        for marker in markers:
            assert marker in body, f"Missing '{marker}' on {path}"

    @pytest.mark.parametrize("asset_path", STATIC_ASSETS)
    def test_static_assets_served(self, client, asset_path):
        response = client.get(asset_path)
        assert response.status_code == 200
        assert response.headers["content-type"]

    def test_market_trends_loads_dynamic_overview_script(self, client):
        response = client.get("/market-trends.html")
        body = response.text
        assert "initMarketTrendsPage" in body
        assert "trends-content" in body
        assert "Coming soon" not in body

    def test_historical_data_has_working_chart_and_periods(self, client):
        response = client.get("/historical-data.html")
        body = response.text
        assert 'id="nav-chart"' in body
        assert 'data-years="1"' in body
        assert 'data-years="3"' in body
        assert 'id="date-from"' in body
        assert "Coming Soon" not in body

    def test_historical_data_js_generates_current_year_rows(self):
        current_year = str(datetime.now().year)
        source = (UI_JS_DIR / "historical-data.js").read_text(encoding="utf-8")
        assert "function generateNavSeries" in source

        sample_date = datetime.now().strftime("%d %b %Y")
        assert current_year in sample_date

    def test_layout_footer_uses_current_year(self, client):
        response = client.get("/js/layout.js")
        assert response.status_code == 200
        current_year = str(datetime.now().year)
        assert "CURRENT_YEAR" in response.text
        assert "layout.js" in client.get("/index.html").text

    def test_all_ui_javascript_files_have_valid_syntax(self):
        js_files = sorted(UI_JS_DIR.glob("*.js"))
        assert js_files, "No UI JavaScript files found"
        for js_file in js_files:
            result = subprocess.run(
                ["node", "--check", str(js_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, f"{js_file.name}: {result.stderr.strip()}"

    def test_assistant_page_wires_chat_before_sidebar(self, client):
        response = client.get("/assistant.html")
        body = response.text
        chat_index = body.index("initChat();")
        sidebar_index = body.index("renderSchemeSidebar")
        assert chat_index < sidebar_index

    def test_home_example_questions_link_to_assistant(self, client):
        response = client.get("/index.html")
        assert "/assistant.html?q=" in response.text
        assert "expense ratio" in response.text.lower()

    def test_faq_page_loads_scheme_data(self, client):
        response = client.get("/investment-faq.html")
        body = response.text
        assert "schemes.js" in body
        assert "faq.js" in body
        assert "sidebar.js" in body
