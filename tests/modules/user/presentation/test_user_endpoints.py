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


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_suspend_without_admin_auth_returns_401(client):
    response = await client.patch(
        "/api/v1/user/00000000-0000-0000-0000-000000000000/suspend/"
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_activate_without_admin_auth_returns_401(client):
    response = await client.patch(
        "/api/v1/user/00000000-0000-0000-0000-000000000000/activate/"
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_update_me_without_auth_returns_401(client):
    response = await client.patch("/api/v1/user/me/", json={"first_name": "New"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
