from __future__ import annotations

import pytest

from app.retriever import (
    Retriever,
    detect_section,
    load_schemes,
    resolve_scheme,
)


@pytest.fixture(scope="module")
def schemes():
    return load_schemes()


@pytest.fixture(scope="module")
def retriever():
    instance = Retriever()
    if not instance.is_ready():
        pytest.skip("Vector index not built — run `python -m ingestion.run` first")
    return instance


class TestSchemeResolution:
    def test_full_scheme_name(self, schemes):
        match = resolve_scheme("Expense ratio of HDFC Mid Cap Fund Direct Growth?", schemes)
        assert match is not None
        assert match.slug == "hdfc-mid-cap-fund-direct-growth"
        assert match.confidence == 1.0

    def test_alias_defence(self, schemes):
        match = resolve_scheme("Exit load on Defence Fund?", schemes)
        assert match is not None
        assert match.slug == "hdfc-defence-fund-direct-growth"
        assert match.method.startswith("alias:")

    def test_alias_gold_etf(self, schemes):
        match = resolve_scheme("Who manages Gold ETF FoF?", schemes)
        assert match is not None
        assert match.slug == "hdfc-gold-etf-fund-of-fund-direct-plan-growth"

    def test_groww_url(self, schemes):
        match = resolve_scheme(
            "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
            schemes,
        )
        assert match is not None
        assert match.slug == "hdfc-defence-fund-direct-growth"
        assert match.method == "url"

    def test_out_of_corpus_amc(self, schemes):
        match = resolve_scheme("Expense ratio of SBI Bluechip Fund?", schemes)
        assert match is None

    def test_case_insensitive(self, schemes):
        match = resolve_scheme("hdfc MID cap EXPENSE ratio", schemes)
        assert match is not None
        assert match.slug == "hdfc-mid-cap-fund-direct-growth"


class TestSectionDetection:
    def test_expense_ratio(self):
        assert detect_section("What is the expense ratio?") == "expense_ratio"

    def test_fund_management(self):
        assert detect_section("Who manages HDFC Defence Fund?") == "fund_management"

    def test_benchmark(self):
        assert detect_section("Benchmark of Nifty 50 Index Fund?") == "benchmark"

    def test_riskometer(self):
        assert detect_section("Riskometer of Multi Cap?") == "overview"


class TestEndToEndRetrieval:
    def test_named_scheme_expense_ratio(self, retriever):
        result = retriever.retrieve("Expense ratio of HDFC Mid Cap Fund Direct Growth?")
        assert result.chunks
        assert result.resolved_slug == "hdfc-mid-cap-fund-direct-growth"
        assert result.chunks[0].section == "expense_ratio"
        assert "groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth" in result.chunks[0].source_url
        assert result.insufficient_context is False

    def test_defence_exit_load(self, retriever):
        result = retriever.retrieve("Exit load on Defence Fund?")
        assert result.chunks
        assert result.resolved_slug == "hdfc-defence-fund-direct-growth"
        assert result.chunks[0].section == "exit_load"

    def test_fund_management_multi_chunk(self, retriever):
        result = retriever.retrieve("Who manages HDFC Defence Fund?")
        assert result.chunks
        assert all(chunk.section == "fund_management" for chunk in result.chunks)
        assert len(result.chunks) >= 2
        assert result.resolved_slug == "hdfc-defence-fund-direct-growth"

    def test_unknown_amc_empty(self, retriever):
        result = retriever.retrieve("Expense ratio of SBI Bluechip Fund?")
        assert not result.chunks
        assert result.supported_schemes is not None
        assert len(result.supported_schemes) == 12

    def test_ambiguous_section_only(self, retriever):
        result = retriever.retrieve("What is the expense ratio?")
        assert result.chunks
        assert result.ambiguous is True
        assert result.detected_section == "expense_ratio"
        assert result.chunks[0].section == "expense_ratio"

    def test_no_cross_scheme_leakage(self, retriever):
        result = retriever.retrieve("Expense ratio of HDFC Mid Cap Fund Direct Growth?")
        assert all("mid-cap" in chunk.source_url for chunk in result.chunks[:1])
