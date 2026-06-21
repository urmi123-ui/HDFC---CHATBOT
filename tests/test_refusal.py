from __future__ import annotations

import re

import pytest

from app.classifier import QueryClass
from app.corpus import AMFI_EDUCATION_URL, DISCLAIMER, SEBI_EDUCATION_URL
from app.refusal import build_pii_refusal, build_refusal


@pytest.mark.parametrize(
    "query_class",
    [
        QueryClass.ADVISORY,
        QueryClass.COMPARISON,
        QueryClass.PERFORMANCE,
        QueryClass.OUT_OF_SCOPE,
        QueryClass.GREETING,
    ],
)
def test_refusal_shape(query_class: QueryClass):
    response = build_refusal(query_class)
    assert response.is_refusal is True
    assert response.disclaimer == DISCLAIMER
    assert response.citation_url in {AMFI_EDUCATION_URL, SEBI_EDUCATION_URL}
    assert response.answer
    assert re.match(r"\d{4}-\d{2}-\d{2}", response.last_updated)


def test_pii_refusal_uses_sebi_link():
    response = build_pii_refusal()
    assert response.is_refusal is True
    assert response.citation_url == SEBI_EDUCATION_URL
