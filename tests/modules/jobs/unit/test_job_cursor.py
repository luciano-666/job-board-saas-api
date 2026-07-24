"""Unit tests for JobCursor encode/decode (cursor-based pagination)."""

import base64
import json
from datetime import datetime, UTC
from uuid import uuid4

import pytest

from src.modules.jobs.application.dto import JobCursor


def test_encode_produces_url_safe_base64_string():
    cursor = JobCursor(created_at=datetime(2026, 1, 1, tzinfo=UTC), job_id=uuid4())

    encoded = cursor.encode()

    assert isinstance(encoded, str)
    # url-safe base64 alphabet only
    assert all(c.isalnum() or c in "-_=" for c in encoded)


def test_decode_reverses_encode():
    original = JobCursor(
        created_at=datetime(2026, 3, 15, 12, 30, tzinfo=UTC), job_id=uuid4()
    )

    encoded = original.encode()
    decoded = JobCursor.decode(encoded)

    assert decoded == original


def test_decode_raises_value_error_on_malformed_input():
    with pytest.raises(ValueError):
        JobCursor.decode("not-a-valid-cursor")


def test_decode_raises_value_error_on_missing_fields():
    payload = base64.urlsafe_b64encode(
        json.dumps({"created_at": "2026-01-01T00:00:00+00:00"}).encode()
    ).decode()

    with pytest.raises(ValueError):
        JobCursor.decode(payload)


def test_encode_decode_roundtrip_preserves_microseconds():
    original = JobCursor(
        created_at=datetime(2026, 6, 10, 8, 15, 30, 123456, tzinfo=UTC),
        job_id=uuid4(),
    )

    decoded = JobCursor.decode(original.encode())

    assert decoded.created_at == original.created_at
