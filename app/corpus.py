from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "config" / "corpus.yaml"

DISCLAIMER = "Facts-only. No investment advice."
AMFI_EDUCATION_URL = "https://www.amfiindia.com/investor/knowledge-center-info?faqs"
SEBI_EDUCATION_URL = "https://investor.sebi.gov.in/"


def corpus_config_path() -> Path:
    return Path(os.getenv("CORPUS_CONFIG_PATH", DEFAULT_CORPUS_PATH))


@lru_cache(maxsize=1)
def load_corpus_urls() -> frozenset[str]:
    with corpus_config_path().open(encoding="utf-8") as handle:
        corpus = yaml.safe_load(handle)
    return frozenset(scheme["source_url"] for scheme in corpus.get("schemes", []))


@lru_cache(maxsize=1)
def load_corpus_scheme_names() -> tuple[str, ...]:
    with corpus_config_path().open(encoding="utf-8") as handle:
        corpus = yaml.safe_load(handle)
    return tuple(scheme["scheme_name"] for scheme in corpus.get("schemes", []))
