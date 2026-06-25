"""Presentation-layer (integration) tests for User endpoints.

Uses the `client` fixture from tests/conftest.py which wires a real
async DB session and overrides `get_async_session`.

Coverage goal: happy path for every endpoint + the most critical error paths.
"""

import pytest
from http import HTTPStatus

from tests.utils import random_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def valid_create_payload(email: str | None = None) -> dict:
    return {
        "first_name": "John",
        "last_name": "Doe",
        "preferred_name": "Johnny",
        "gender": "male",
        "birthdate": "1990-06-15",
        "email": email or random_email(),
        "phone": "+15554726642",
        "password": "Str0ng@Pass!",
    }


# ---------------------------------------------------------------------------
# POST /api/v1/user/ — create user
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_user_returns_201(client):
    payload = valid_create_payload()

    response = await client.post("/api/v1/user/", json=payload)

    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.anyio
async def test_create_user_response_has_standard_envelope(client):
    payload = valid_create_payload()

    response = await client.post("/api/v1/user/", json=payload)
    body = response.json()

    assert "code" in body
    assert "details" in body
    assert body["code"] == HTTPStatus.CREATED


@pytest.mark.anyio
async def test_create_user_duplicate_email_returns_409(client):
    payload = valid_create_payload()

    await client.post("/api/v1/user/", json=payload)
    response = await client.post("/api/v1/user/", json=payload)

    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.anyio
async def test_create_user_missing_required_field_returns_422(client):
    payload = valid_create_payload()
    payload.pop("email")

    response = await client.post("/api/v1/user/", json=payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_create_user_invalid_email_format_returns_422(client):
    payload = valid_create_payload()
    payload["email"] = "not-an-email"

    response = await client.post("/api/v1/user/", json=payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_create_user_weak_password_returns_422(client):
    payload = valid_create_payload()
    payload["password"] = "weak"

    response = await client.post("/api/v1/user/", json=payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_create_user_underage_birthdate_returns_422(client):
    import datetime

    payload = valid_create_payload()
    payload["birthdate"] = str(
        datetime.date.today().replace(year=datetime.date.today().year - 16)
    )

    response = await client.post("/api/v1/user/", json=payload)

    # Pydantic birthdate validator only checks future/1900 bounds;
    # the domain entity raises DomainError caught as 400.
    assert response.status_code in (
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/user/me/ — requires authentication
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_me_without_auth_cookies_returns_401(client):
    response = await client.get("/api/v1/user/me/")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_me_with_invalid_access_token_returns_401(client):
    client.cookies.set("access_token", "totally.invalid.token")
    client.cookies.set("device_id", "test-device-001")

    response = await client.get("/api/v1/user/me/")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
