from __future__ import annotations

import pytest

from app.classifier import QueryClass, classify_query


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Should I invest in HDFC Mid Cap Fund?", QueryClass.ADVISORY),
        ("Recommend a good HDFC fund", QueryClass.ADVISORY),
        ("Is HDFC Gold FoF a safe fund?", QueryClass.ADVISORY),
        ("Which is better: Mid Cap or Small Cap?", QueryClass.COMPARISON),
        ("Compare exit load of Mid Cap vs Small Cap", QueryClass.COMPARISON),
        ("What returns will I get in 5 years?", QueryClass.PERFORMANCE),
        ("Compare 3Y returns of Mid Cap vs Defence", QueryClass.COMPARISON),
        ("What is the weather in Mumbai?", QueryClass.OUT_OF_SCOPE),
        ("Expense ratio of SBI Bluechip Fund?", QueryClass.OUT_OF_SCOPE),
        ("Hello", QueryClass.GREETING),
        ("What is the expense ratio of HDFC Defence Fund?", QueryClass.FACTUAL),
        ("Who manages HDFC Focused Fund?", QueryClass.FACTUAL),
        ("Minimum SIP for Balanced Advantage?", QueryClass.FACTUAL),
    ],
)
def test_classify_query(query: str, expected: QueryClass):
    result = classify_query(query)
    assert result.query_class == expected
