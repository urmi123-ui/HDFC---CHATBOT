from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "config" / "corpus.yaml"


@dataclass(frozen=True)
class Scheme:
    slug: str
    scheme_name: str
    source_url: str
    category: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Corpus:
    amc: str
    amc_short: str
    schemes: tuple[Scheme, ...]


def load_corpus(config_path: Path | None = None) -> Corpus:
    path = config_path or DEFAULT_CORPUS_PATH
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    schemes = tuple(
        Scheme(
            slug=item["slug"],
            scheme_name=item["scheme_name"],
            source_url=item["source_url"],
            category=item.get("category", ""),
            aliases=tuple(item.get("aliases", [])),
        )
        for item in raw["schemes"]
    )
    return Corpus(
        amc=raw.get("amc", ""),
        amc_short=raw.get("amc_short", ""),
        schemes=schemes,
    )
