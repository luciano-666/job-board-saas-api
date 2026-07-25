"""Integration tests for job endpoints — happy path per spec."""

import pytest
from http import HTTPStatus


def valid_create_payload(**overrides) -> dict:
    payload = {
        "title": "Backend Engineer",
        "description": "Build and maintain backend services.",
        "location": "Ho Chi Minh City",
        "job_type": "full_time",
        "skills": ["python", "fastapi"],
        "salary": {"min": 2000, "max": 4000},
    }
    payload.update(overrides)
    return payload


@pytest.mark.anyio
async def test_create_job_without_auth_returns_401(client):
    response = await client.post("/api/v1/jobs/", json=valid_create_payload())
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_update_job_without_auth_returns_401(client):
    response = await client.patch(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/",
        json=valid_create_payload(),
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# NOTE: happy-path tests requiring an authenticated employer session need a
# login fixture (create employer user via UserUseCases fixture + login flow).
# Follow the same pattern as tests/modules/user/presentation/test_user_endpoints.py
# once a shared "authenticated_employer_client" fixture exists in conftest.py.
