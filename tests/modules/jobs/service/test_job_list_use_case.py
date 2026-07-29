"""Service-layer tests for JobUseCases.list_public_jobs (cursor pagination)."""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest

from src.modules.jobs.application.dto import JobFilters
from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.application.use_cases import JobUseCases
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from tests.modules.jobs.fakes import FakeJobRepository


def make_job(*, created_at=None, status=JobStatus.OPEN, **overrides) -> Job:
    defaults: dict = dict(
        title="Backend Engineer",
        description="Build backend services.",
        location="Ho Chi Minh City",
        job_type=JobType.FULL_TIME,
        skills=["python"],
        employer_id=uuid4(),
        salary=SalaryRange(min=2000, max=4000),
    )
    defaults.update(overrides)
    job = Job(**defaults)
    if created_at is not None:
        job.created_at = created_at
    job.status = status  # bypass transition rules for test data setup
    return job


def make_use_cases(existing: list[Job] | None = None):
    repo = FakeJobRepository(existing)
    return JobUseCases(repository=repo), repo


def make_open_jobs(n: int) -> list[Job]:
    """Create n OPEN jobs with distinct, descending created_at timestamps."""
    base = datetime.now(UTC)
    return [
        make_job(created_at=base - timedelta(minutes=i), status=JobStatus.OPEN)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# list_public_jobs — basic pagination
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_public_jobs_returns_first_page_ordered_by_created_at_desc():
    jobs = make_open_jobs(5)
    use_cases, _ = make_use_cases(existing=jobs)

    page = await use_cases.list_public_jobs(JobFilters(), cursor=None, limit=3)

    assert len(page.items) == 3
    assert page.has_more is True
    assert page.next_cursor is not None
    # newest first
    assert (
        page.items[0].created_at >= page.items[1].created_at >= page.items[2].created_at
    )


@pytest.mark.anyio
async def test_list_public_jobs_second_page_continues_after_cursor():
    jobs = make_open_jobs(5)
    use_cases, _ = make_use_cases(existing=jobs)

    first_page = await use_cases.list_public_jobs(JobFilters(), cursor=None, limit=3)
    second_page = await use_cases.list_public_jobs(
        JobFilters(), cursor=first_page.next_cursor, limit=3
    )

    first_ids = {j.id for j in first_page.items}
    second_ids = {j.id for j in second_page.items}
    assert first_ids.isdisjoint(second_ids)
    assert len(second_page.items) == 2
    assert second_page.has_more is False
    assert second_page.next_cursor is None


@pytest.mark.anyio
async def test_list_public_jobs_returns_empty_when_no_jobs():
    use_cases, _ = make_use_cases()

    page = await use_cases.list_public_jobs(JobFilters(), cursor=None, limit=10)

    assert page.items == []
    assert page.has_more is False
    assert page.next_cursor is None


# ---------------------------------------------------------------------------
# list_public_jobs — only OPEN jobs are visible (public listing)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_public_jobs_excludes_non_open_jobs():
    open_job = make_job(status=JobStatus.OPEN)
    draft_job = make_job(status=JobStatus.DRAFT)
    closed_job = make_job(status=JobStatus.CLOSED)
    use_cases, _ = make_use_cases(existing=[open_job, draft_job, closed_job])

    page = await use_cases.list_public_jobs(JobFilters(), cursor=None, limit=10)

    ids = {j.id for j in page.items}
    assert ids == {open_job.id}


# ---------------------------------------------------------------------------
# list_public_jobs — filters
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_public_jobs_filters_by_location():
    matching = make_job(location="Ho Chi Minh City", status=JobStatus.OPEN)
    other = make_job(location="Hanoi", status=JobStatus.OPEN)
    use_cases, _ = make_use_cases(existing=[matching, other])

    page = await use_cases.list_public_jobs(
        JobFilters(location="ho chi minh"), cursor=None, limit=10
    )

    ids = {j.id for j in page.items}
    assert ids == {matching.id}


@pytest.mark.anyio
async def test_list_public_jobs_filters_by_job_type():
    fulltime = make_job(job_type=JobType.FULL_TIME, status=JobStatus.OPEN)
    contract = make_job(job_type=JobType.CONTRACT, status=JobStatus.OPEN)
    use_cases, _ = make_use_cases(existing=[fulltime, contract])

    page = await use_cases.list_public_jobs(
        JobFilters(job_type=JobType.CONTRACT), cursor=None, limit=10
    )

    ids = {j.id for j in page.items}
    assert ids == {contract.id}


@pytest.mark.anyio
async def test_list_public_jobs_filters_by_salary_min():
    high = make_job(salary=SalaryRange(min=5000, max=8000), status=JobStatus.OPEN)
    low = make_job(salary=SalaryRange(min=1000, max=2000), status=JobStatus.OPEN)
    use_cases, _ = make_use_cases(existing=[high, low])

    page = await use_cases.list_public_jobs(
        JobFilters(salary_min=3000), cursor=None, limit=10
    )

    ids = {j.id for j in page.items}
    assert ids == {high.id}


@pytest.mark.anyio
async def test_list_public_jobs_filters_by_skills():
    matching = make_job(skills=["python", "fastapi"], status=JobStatus.OPEN)
    other = make_job(skills=["go"], status=JobStatus.OPEN)
    use_cases, _ = make_use_cases(existing=[matching, other])

    page = await use_cases.list_public_jobs(
        JobFilters(skills=["python"]), cursor=None, limit=10
    )

    ids = {j.id for j in page.items}
    assert ids == {matching.id}
