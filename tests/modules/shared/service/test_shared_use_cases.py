"""Service-layer tests for SharedUseCases — cross-bounded-context accessors."""

from uuid import uuid4

import pytest

from src.modules.shared.application.use_cases import SharedUseCases
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.application.enums import JobType
from src.modules.jobs.domain.value_objects import SalaryRange
from tests.modules.jobs.fakes import FakeJobRepository
from tests.modules.user.fakes import FakeUserRepository


def make_job(**overrides) -> Job:
    defaults = dict(
        title="Backend Engineer",
        description="Build backend services.",
        location="Ho Chi Minh City",
        job_type=JobType.FULL_TIME,
        skills=["python"],
        employer_id=uuid4(),
        salary=SalaryRange(min=2000, max=4000),
    )
    defaults.update(overrides)
    return Job(**defaults)


def make_shared_use_cases(jobs: list[Job] | None = None) -> SharedUseCases:
    user_repo = FakeUserRepository()
    job_repo = FakeJobRepository(jobs)
    return SharedUseCases(user_repository=user_repo, job_repository=job_repo)

# ---------------------------------------------------------------------------
# get_job_by_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_job_by_id_returns_job_when_exists():
    job = make_job()
    shared = make_shared_use_cases(jobs=[job])

    result = await shared.get_job_by_id(job.id)

    assert result is not None
    assert result.id == job.id
    assert result.employer_id == job.employer_id


@pytest.mark.anyio
async def test_get_job_by_id_returns_none_when_missing():
    shared = make_shared_use_cases()

    result = await shared.get_job_by_id(uuid4())

    assert result is None


@pytest.mark.anyio
async def test_get_job_by_id_exposes_status():
    job = make_job()
    job.publish()  # -> OPEN
    shared = make_shared_use_cases(jobs=[job])

    result = await shared.get_job_by_id(job.id)

    assert result is not None
    assert result.status == job.status
