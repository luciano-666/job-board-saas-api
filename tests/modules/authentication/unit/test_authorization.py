"""Unit tests for has_access_to_endpoint — role-based path resolution."""

import pytest

from src.modules.authentication.application.authorization import has_access_to_endpoint
from src.modules.shared.application.enums import Role


# ---------------------------------------------------------------------------
# EMPLOYER role
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_employer_can_access_create_job():
    result = await has_access_to_endpoint("/api/v1/jobs/", "POST", Role.EMPLOYER)
    assert result is True


@pytest.mark.anyio
async def test_employer_can_access_publish_job():
    result = await has_access_to_endpoint(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/publish/",
        "PATCH",
        Role.EMPLOYER,
    )
    assert result is True


@pytest.mark.anyio
async def test_employer_can_access_own_profile():
    """Employer inherits USER-level paths (e.g. /user/me/)."""
    result = await has_access_to_endpoint("/api/v1/user/me/", "GET", Role.EMPLOYER)
    assert result is True


@pytest.mark.anyio
async def test_employer_cannot_access_admin_only_create_user():
    result = await has_access_to_endpoint("/api/v1/user/", "POST", Role.EMPLOYER)
    assert result is False


@pytest.mark.anyio
async def test_employer_cannot_suspend_user():
    result = await has_access_to_endpoint(
        "/api/v1/user/00000000-0000-0000-0000-000000000000/suspend/",
        "PATCH",
        Role.EMPLOYER,
    )
    assert result is False


# ---------------------------------------------------------------------------
# CANDIDATE role — must NOT have employer job-management access
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_candidate_cannot_create_job():
    result = await has_access_to_endpoint("/api/v1/jobs/", "POST", Role.CANDIDATE)
    assert result is False


@pytest.mark.anyio
async def test_candidate_cannot_publish_job():
    result = await has_access_to_endpoint(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/publish/",
        "PATCH",
        Role.CANDIDATE,
    )
    assert result is False


# ---------------------------------------------------------------------------
# ADMIN role — must inherit EMPLOYER job-management access
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_can_create_job():
    result = await has_access_to_endpoint("/api/v1/jobs/", "POST", Role.ADMIN)
    assert result is True


@pytest.mark.anyio
async def test_admin_can_archive_job():
    result = await has_access_to_endpoint(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/archive/",
        "PATCH",
        Role.ADMIN,
    )
    assert result is True


@pytest.mark.anyio
async def test_admin_can_still_suspend_user():
    """Regression: admin's own path list must not be lost after spreading employer paths."""
    result = await has_access_to_endpoint(
        "/api/v1/user/00000000-0000-0000-0000-000000000000/suspend/",
        "PATCH",
        Role.ADMIN,
    )
    assert result is True


# ---------------------------------------------------------------------------
# Public / no-auth paths — always accessible regardless of role
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_public_job_listing_accessible_with_no_role():
    result = await has_access_to_endpoint("/api/v1/jobs/", "GET", None)
    assert result is True


@pytest.mark.anyio
async def test_public_job_detail_accessible_with_no_role():
    result = await has_access_to_endpoint(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/", "GET", None
    )
    assert result is True
