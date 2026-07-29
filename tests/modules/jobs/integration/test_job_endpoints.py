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


@pytest.mark.anyio
async def test_get_job_public_returns_404_for_nonexistent_job(client):
    response = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000/")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.anyio
async def test_publish_job_without_auth_returns_401(client):
    response = await client.patch(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/publish/"
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_close_job_without_auth_returns_401(client):
    response = await client.patch(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/close/"
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_archive_job_without_auth_returns_401(client):
    response = await client.patch(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/archive/"
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_list_jobs_public_returns_200_with_empty_data(client):
    response = await client.get("/api/v1/jobs/")
    assert response.status_code == HTTPStatus.OK
    body = response.json()

    # ResponseFormattingMiddleware wraps the entire JobListResponse body
    # under details.data, so the job list itself is nested one level deeper.
    payload = body["details"]["data"]
    assert payload["data"] == []
    assert payload["has_more"] is False
    assert payload["next_cursor"] is None


@pytest.mark.anyio
async def test_list_jobs_rejects_invalid_limit(client):
    response = await client.get("/api/v1/jobs/", params={"limit": 0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


@pytest.mark.anyio
async def test_list_jobs_rejects_negative_salary_min(client):
    response = await client.get("/api/v1/jobs/", params={"salary_min": -100})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


@pytest.mark.anyio
async def test_list_jobs_accepts_multiple_skills_query_params(client):
    response = await client.get(
        "/api/v1/jobs/", params={"skills": ["python", "fastapi"]}
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.anyio
async def test_list_jobs_accepts_location_filter(client):
    response = await client.get(
        "/api/v1/jobs/", params={"location": "Ho Chi Minh City"}
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.anyio
async def test_list_jobs_accepts_job_type_filter(client):
    response = await client.get("/api/v1/jobs/", params={"job_type": "full_time"})
    assert response.status_code == HTTPStatus.OK


@pytest.mark.anyio
async def test_list_jobs_rejects_invalid_job_type(client):
    response = await client.get("/api/v1/jobs/", params={"job_type": "not_a_type"})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
