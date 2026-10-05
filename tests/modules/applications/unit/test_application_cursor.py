"""Unit tests for ApplicationCursor encode/decode (cursor-based pagination),
mirrors tests/modules/jobs/unit/test_job_cursor.py."""

import base64
import json
from datetime import datetime, UTC
from uuid import uuid4

import pytest

from src.modules.applications.application.dto import ApplicationCursor


def test_encode_produces_url_safe_base64_string():
    cursor = ApplicationCursor(
        created_at=datetime(2026, 1, 1, tzinfo=UTC), application_id=uuid4()
    )

    encoded = cursor.encode()

    assert isinstance(encoded, str)
    assert all(c.isalnum() or c in "-_=" for c in encoded)


def test_decode_reverses_encode():
    original = ApplicationCursor(
        created_at=datetime(2026, 3, 15, 12, 30, tzinfo=UTC), application_id=uuid4()
    )

    encoded = original.encode()
    decoded = ApplicationCursor.decode(encoded)

    assert decoded == original


def test_decode_raises_value_error_on_malformed_input():
    with pytest.raises(ValueError):
        ApplicationCursor.decode("not-a-valid-cursor")


def test_decode_raises_value_error_on_missing_fields():
    payload = base64.urlsafe_b64encode(
        json.dumps({"created_at": "2026-01-01T00:00:00+00:00"}).encode()
    ).decode()

    with pytest.raises(ValueError):
        ApplicationCursor.decode(payload)
