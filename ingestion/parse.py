from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from ingestion.corpus import Scheme, load_corpus

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

SECTION_NAMES = (
    "overview",
    "expense_ratio",
    "exit_load",
    "minimum_investment",
    "benchmark",
    "tax",
    "fund_management",
    "investment_objective",
    "fund_house",
)


@dataclass(frozen=True)
class ParsedScheme:
    slug: str
    scheme_name: str
    source_url: str
    last_updated: str
    fetched_at: str | None
    sections: dict[str, str]
    output_path: str


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", text).strip()


def _format_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.date().isoformat()
        return datetime.fromisoformat(value[:10]).date().isoformat()
    except ValueError:
        return value.strip()


def _format_manager_entry(manager: dict[str, Any]) -> str:
    name = manager.get("person_name") or manager.get("fund_manager") or "Unknown"
    date_from = _format_date(manager.get("date_from"))
    tenure = f"since {date_from}" if date_from else "tenure not specified"
    education = _strip_html(manager.get("education"))
    experience = _strip_html(manager.get("experience"))
    other_schemes = [
        fund.get("scheme_name", "")
        for fund in (manager.get("funds_managed") or [])
        if fund.get("scheme_name")
    ]
    parts = [f"{name} — Fund Manager, {tenure}."]
    if education:
        parts.append(f"Education: {education}")
    if experience:
        parts.append(f"Experience: {experience}")
    if other_schemes:
        parts.append(f"Other schemes managed: {', '.join(other_schemes[:5])}.")
    return " ".join(parts)


def _extract_mf_data(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        raise ValueError("Could not find __NEXT_DATA__ payload in HTML")

    payload = json.loads(script.string)
    mf_data = payload.get("props", {}).get("pageProps", {}).get("mfServerSideData")
    if not mf_data:
        raise ValueError("Could not find mfServerSideData in __NEXT_DATA__")
    return mf_data


def _build_sections(mf: dict[str, Any], scheme: Scheme) -> dict[str, str]:
    category_info = mf.get("category_info") or {}
    amc_info = mf.get("amc_info") or {}
    manager_details = mf.get("fund_manager_details") or []

    overview_lines = [
        f"Scheme: {mf.get('scheme_name') or scheme.scheme_name}",
        f"Category: {mf.get('category') or scheme.category}",
        f"Sub-category: {mf.get('sub_category') or ''}".strip(),
        f"Super category: {mf.get('super_category') or ''}".strip(),
        f"Risk label: {mf.get('nfo_risk') or 'Not specified'}",
        f"AUM: {mf.get('aum')}" if mf.get("aum") is not None else "",
        f"NAV: {mf.get('nav')} (as of {mf.get('nav_date') or 'unknown'})"
        if mf.get("nav") is not None
        else "",
        f"Launch date: {mf.get('launch_date') or ''}".strip(),
        f"Plan type: {mf.get('plan_type') or ''}".strip(),
        f"Scheme type: {mf.get('scheme_type') or ''}".strip(),
    ]
    overview = "\n".join(line for line in overview_lines if line and not line.endswith(": "))

    expense_lines = []
    if mf.get("expense_ratio"):
        expense_lines.append(f"Expense ratio: {mf['expense_ratio']}")
    historic_expense = mf.get("historic_fund_expense") or []
    if historic_expense:
        expense_lines.append("Historic expense ratio:")
        for item in historic_expense[:5]:
            expense_lines.append(
                f"- {item.get('date') or item.get('effective_date')}: {item.get('expense_ratio')}"
            )
    expense_ratio = "\n".join(expense_lines).strip()

    exit_lines = []
    if mf.get("exit_load"):
        exit_lines.append(f"Exit load: {mf['exit_load']}")
    historic_exit = mf.get("historic_exit_loads") or []
    if historic_exit:
        exit_lines.append("Historic exit load:")
        for item in historic_exit[:5]:
            exit_lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
    exit_load = "\n".join(exit_lines).strip()

    minimum_lines = [
        f"Minimum lumpsum investment: Rs {mf['min_investment_amount']}"
        if mf.get("min_investment_amount") is not None
        else "",
        f"Minimum SIP: Rs {mf['min_sip_investment']}"
        if mf.get("min_sip_investment") is not None
        else "",
        f"Maximum SIP: Rs {mf['max_sip_investment']}"
        if mf.get("max_sip_investment") is not None
        else "",
        f"Additional investment minimum: Rs {mf['mini_additional_investment']}"
        if mf.get("mini_additional_investment") is not None
        else "",
        f"SIP multiplier: {mf['sip_multiplier']}" if mf.get("sip_multiplier") is not None else "",
        f"SIP allowed: {mf.get('sip_allowed')}",
        f"Lumpsum allowed: {mf.get('lumpsum_allowed')}",
    ]
    minimum_investment = "\n".join(line for line in minimum_lines if line).strip()

    benchmark_lines = []
    if mf.get("benchmark_name"):
        benchmark_lines.append(f"Benchmark: {mf['benchmark_name']}")
    elif mf.get("benchmark"):
        benchmark_lines.append(f"Benchmark: {mf['benchmark']}")
    benchmark = "\n".join(benchmark_lines).strip()

    tax_lines = []
    tax_impact = category_info.get("tax_impact")
    if tax_impact:
        tax_lines.append(f"Tax impact: {tax_impact}")
    if mf.get("lock_in"):
        tax_lines.append(f"Lock-in period: {mf['lock_in']}")
    tax = "\n".join(tax_lines).strip()

    manager_blocks = [_format_manager_entry(m) for m in manager_details if m]
    if not manager_blocks and mf.get("fund_manager"):
        manager_blocks.append(f"Fund manager: {mf['fund_manager']}")
    fund_management = "\n\n".join(manager_blocks).strip()

    investment_objective = _strip_html(mf.get("description"))
    if category_info.get("description"):
        investment_objective = "\n".join(
            part for part in [investment_objective, category_info["description"]] if part
        ).strip()

    fund_house_lines = [
        f"Fund house: {mf.get('fund_house') or amc_info.get('name') or ''}".strip(),
        f"AMC website: {amc_info.get('vro_website') or mf.get('amc_page_url') or ''}".strip(),
        f"AMC launch date: {_format_date(amc_info.get('launch_date'))}".strip(),
        f"AMC address: {amc_info.get('address') or ''}".strip(),
        f"Registrar: {mf.get('registrar_agent') or ''}".strip(),
    ]
    if amc_info.get("description"):
        fund_house_lines.append(f"AMC description: {_strip_html(amc_info['description'])}")
    fund_house = "\n".join(line for line in fund_house_lines if line and not line.endswith(": "))

    sections = {
        "overview": overview,
        "expense_ratio": expense_ratio,
        "exit_load": exit_load,
        "minimum_investment": minimum_investment,
        "benchmark": benchmark,
        "tax": tax,
        "fund_management": fund_management,
        "investment_objective": investment_objective,
        "fund_house": fund_house,
    }
    return {name: text for name, text in sections.items() if text}


def _resolve_html_path(raw_dir: Path, slug: str, html_path: Path | None) -> Path:
    if html_path:
        return html_path
    latest = raw_dir / slug / "latest.html"
    if latest.exists():
        return latest
    scheme_dir = raw_dir / slug
    html_files = sorted(scheme_dir.glob("*.html"), reverse=True)
    if not html_files:
        raise FileNotFoundError(f"No fetched HTML found for slug '{slug}' in {scheme_dir}")
    return html_files[0]


def _load_fetch_timestamp(raw_dir: Path, slug: str) -> str | None:
    meta_path = raw_dir / slug / "latest.meta.json"
    if not meta_path.exists():
        meta_files = sorted((raw_dir / slug).glob("*.meta.json"), reverse=True)
        if not meta_files:
            return None
        meta_path = meta_files[0]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta.get("fetched_at")


def parse_scheme_html(
    scheme: Scheme,
    html: str,
    *,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    mf = _extract_mf_data(html)
    sections = _build_sections(mf, scheme)
    last_updated = (fetched_at or datetime.now(UTC).replace(microsecond=0).isoformat())[:10]
    return {
        "slug": scheme.slug,
        "scheme_name": mf.get("scheme_name") or scheme.scheme_name,
        "source_url": scheme.source_url,
        "category": scheme.category,
        "last_updated": last_updated,
        "fetched_at": fetched_at,
        "sections": sections,
    }


def parse_scheme(
    scheme: Scheme,
    raw_dir: Path = DEFAULT_RAW_DIR,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    *,
    html_path: Path | None = None,
) -> ParsedScheme:
    """Parse fetched HTML for one scheme and write structured sections to data/processed/."""
    resolved_html_path = _resolve_html_path(raw_dir, scheme.slug, html_path)
    html = resolved_html_path.read_text(encoding="utf-8")
    fetched_at = _load_fetch_timestamp(raw_dir, scheme.slug)
    parsed = parse_scheme_html(scheme, html, fetched_at=fetched_at)

    output_dir = processed_dir / scheme.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sections.json"
    output_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")

    missing = [name for name in SECTION_NAMES if name not in parsed["sections"]]
    if missing:
        logger.warning("%s missing sections: %s", scheme.slug, ", ".join(missing))

    logger.info(
        "Parsed %s — %s sections written to %s",
        scheme.slug,
        len(parsed["sections"]),
        output_path,
    )
    return ParsedScheme(
        slug=scheme.slug,
        scheme_name=parsed["scheme_name"],
        source_url=scheme.source_url,
        last_updated=parsed["last_updated"],
        fetched_at=fetched_at,
        sections=parsed["sections"],
        output_path=str(output_path),
    )


def parse_all(
    raw_dir: Path = DEFAULT_RAW_DIR,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    *,
    slugs: list[str] | None = None,
) -> list[ParsedScheme]:
    corpus = load_corpus()
    schemes = corpus.schemes
    if slugs:
        slug_set = set(slugs)
        schemes = tuple(s for s in schemes if s.slug in slug_set)

    processed_dir.mkdir(parents=True, exist_ok=True)
    results: list[ParsedScheme] = []
    errors: list[str] = []

    for scheme in schemes:
        try:
            results.append(parse_scheme(scheme, raw_dir, processed_dir))
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            logger.error("Failed to parse %s: %s", scheme.slug, exc)
            errors.append(f"{scheme.slug}: {exc}")

    if errors:
        raise RuntimeError("Parse failures:\n" + "\n".join(errors))
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse fetched Groww HTML into structured sections")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Directory containing fetched HTML",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help="Directory for parsed section JSON",
    )
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Parse only specific scheme slug(s); repeatable",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args()
    try:
        results = parse_all(args.raw_dir, args.processed_dir, slugs=args.slugs)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    summary = {
        "total": len(results),
        "sections_per_scheme": {
            r.slug: list(r.sections.keys()) for r in results
        },
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
