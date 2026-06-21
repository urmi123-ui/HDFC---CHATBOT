from __future__ import annotations

from collections import defaultdict

from app.retriever import Retriever, load_schemes


def _snippet(text: str, max_len: int = 200) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rsplit(" ", 1)[0] + "…"


def _retrieve_fact(retriever: Retriever, query: str) -> dict | None:
    result = retriever.retrieve(query)
    if not result.chunks:
        return None

    chunk = result.chunks[0]
    return {
        "scheme_name": chunk.scheme_name,
        "slug": result.resolved_slug,
        "fact": _snippet(chunk.text),
        "source_url": chunk.source_url,
        "last_updated": chunk.last_updated,
        "section": chunk.section,
    }


def _scheme_payload(scheme) -> dict:
    return {
        "slug": scheme.slug,
        "scheme_name": scheme.scheme_name,
        "short_name": scheme.scheme_name.replace(" Direct Growth", "").replace(" Direct Plan Growth", ""),
        "category": scheme.category,
        "source_url": scheme.source_url,
        "last_fetched_at": scheme.last_fetched_at,
    }


def build_market_overview(retriever: Retriever) -> dict:
    schemes = load_schemes()
    categories: dict[str, list[dict]] = defaultdict(list)
    for scheme in schemes:
        categories[scheme.category].append(_scheme_payload(scheme))

    category_groups = [
        {
            "category": category,
            "count": len(items),
            "schemes": items,
        }
        for category, items in sorted(categories.items(), key=lambda item: (-len(item[1]), item[0]))
    ]

    nifty_scheme = next((s for s in schemes if "nifty-50" in s.slug), None)
    gold_scheme = next((s for s in schemes if "gold-etf" in s.slug), None)
    silver_scheme = next((s for s in schemes if "silver-etf" in s.slug), None)
    thematic_schemes = [
        s for s in schemes if "Sectoral" in s.category or "Thematic" in s.category
    ]

    index_cards: list[dict] = []
    if nifty_scheme:
        benchmark = _retrieve_fact(
            retriever,
            f"What is the benchmark of {nifty_scheme.scheme_name}?",
        )
        index_cards.append(
            {
                "id": "nifty50",
                "label": "Nifty 50",
                "subtitle": nifty_scheme.scheme_name,
                "fact": benchmark["fact"] if benchmark else "Benchmark details are listed on the scheme page.",
                "source_url": benchmark["source_url"] if benchmark else nifty_scheme.source_url,
                "last_updated": benchmark["last_updated"] if benchmark else nifty_scheme.last_fetched_at,
            }
        )

    index_cards.append(
        {
            "id": "sensex",
            "label": "Sensex",
            "subtitle": "Not in current corpus",
            "fact": (
                "The current 12-scheme corpus includes HDFC Nifty 50 Index Fund for large-cap index exposure. "
                "Ask the assistant about that scheme's benchmark for index-linked facts."
            ),
            "source_url": nifty_scheme.source_url if nifty_scheme else "",
            "last_updated": nifty_scheme.last_fetched_at if nifty_scheme else None,
        }
    )

    commodity_cards: list[dict] = []
    for scheme, label in ((gold_scheme, "Gold"), (silver_scheme, "Silver")):
        if not scheme:
            continue
        objective = _retrieve_fact(
            retriever,
            f"What is the investment objective of {scheme.scheme_name}?",
        )
        commodity_cards.append(
            {
                "id": label.lower(),
                "label": label,
                "subtitle": scheme.scheme_name,
                "fact": objective["fact"] if objective else scheme.category,
                "source_url": objective["source_url"] if objective else scheme.source_url,
                "last_updated": objective["last_updated"] if objective else scheme.last_fetched_at,
            }
        )

    sector_cards: list[dict] = []
    for scheme in thematic_schemes:
        overview = _retrieve_fact(
            retriever,
            f"What is the investment objective of {scheme.scheme_name}?",
        )
        sector_cards.append(
            {
                "slug": scheme.slug,
                "title": scheme.scheme_name.replace(" Direct Growth", ""),
                "category": scheme.category,
                "fact": overview["fact"] if overview else scheme.category,
                "source_url": overview["source_url"] if overview else scheme.source_url,
                "last_updated": overview["last_updated"] if overview else scheme.last_fetched_at,
            }
        )

    refresh_dates = [s.last_fetched_at for s in schemes if s.last_fetched_at]
    last_refresh = max(refresh_dates) if refresh_dates else None

    return {
        "disclaimer": "Facts-only. No investment advice.",
        "corpus_note": (
            "Overview built from indexed HDFC scheme pages — not live exchange prices or return forecasts."
        ),
        "last_corpus_refresh": last_refresh,
        "scheme_count": len(schemes),
        "category_groups": category_groups,
        "index_cards": index_cards,
        "commodity_cards": commodity_cards,
        "sector_cards": sector_cards,
        "suggested_questions": [
            "What is the benchmark of HDFC Nifty 50 Index Fund Direct Growth?",
            "What is the investment objective of HDFC Defence Fund Direct Growth?",
            "What is the investment objective of HDFC Gold ETF Fund of Fund Direct Plan Growth?",
        ],
    }
