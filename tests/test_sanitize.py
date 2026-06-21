from __future__ import annotations

import pytest

from app.sanitize import SanitizeReason, sanitize_message


def test_empty_message():
    result = sanitize_message("   ")
    assert result.reason == SanitizeReason.EMPTY


def test_pan_blocked():
    result = sanitize_message("My PAN is ABCDE1234F and I want exit load info")
    assert result.blocked is True
    assert result.pii_type == "pan"


def test_email_blocked():
    result = sanitize_message("Contact me at user@example.com about expense ratio")
    assert result.blocked is True
    assert result.pii_type == "email"


def test_clean_factual_message():
    result = sanitize_message("What is the expense ratio of HDFC Mid Cap Fund?")
    assert result.reason == SanitizeReason.OK
    assert not result.blocked
