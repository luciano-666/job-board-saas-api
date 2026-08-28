"""Service-layer tests for ApplicationUseCases.apply — duplicate-apply guard."""

from datetime import date
from uuid import uuid4

import pytest

from src.modules.applications.application.use_cases import ApplicationUseCases
from src.modules.applications.presentation.exceptions import (
    ApplicationAlreadyExistsException,
    JobNotOpenForApplicationsException,
)
from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from tests.modules.applications.fakes import FakeApplicationRepository


def make_job(*, status: JobStatus = JobStatus.OPEN, **overrides) -> Job:
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
    job = Job(**defaults)
    if status == JobStatus.OPEN:
        job.publish()
    job.status = status  # allow forcing DRAFT/CLOSED for negative tests
    return job


class FakeSharedUseCasesForApplications:
    """Minimal ISharedUseCases stand-in — only get_job_by_id is needed here."""

    def __init__(self, jobs: list[Job] | None = None) -> None:
        self._jobs = {j.id: j for j in (jobs or [])}

    async def get_job_by_id(self, id):
        return self._jobs.get(id)


def make_use_cases(
    *, applications=None, jobs=None
) -> tuple[ApplicationUseCases, FakeApplicationRepository]:
    repo = FakeApplicationRepository(applications)
    shared = FakeSharedUseCasesForApplications(jobs)
    return ApplicationUseCases(repository=repo, shared_service=shared), repo  # ty:ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# apply — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_creates_application():
    job = make_job()
    use_cases, repo = make_use_cases(jobs=[job])
    candidate_id = uuid4()

    result = await use_cases.apply(
        candidate_id=candidate_id,
        job_id=job.id,
        cv_url="https://s3.example.com/cv/abc.pdf",
    )

    stored = await repo.get_by_id(result.id)
    assert stored is not None
    assert stored.candidate_id == candidate_id
    assert stored.job_id == job.id


# ---------------------------------------------------------------------------
# apply — duplicate application guard
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_raises_when_candidate_already_applied_to_job():
    job = make_job()
    candidate_id = uuid4()
    use_cases, repo = make_use_cases(jobs=[job])

    await use_cases.apply(
        candidate_id=candidate_id,
        job_id=job.id,
        cv_url="https://s3.example.com/cv/first.pdf",
    )

    with pytest.raises(ApplicationAlreadyExistsException):
        await use_cases.apply(
            candidate_id=candidate_id,
            job_id=job.id,
            cv_url="https://s3.example.com/cv/second.pdf",
        )


@pytest.mark.anyio
async def test_apply_allows_same_candidate_different_jobs():
    job_a = make_job()
    job_b = make_job()
    candidate_id = uuid4()
    use_cases, repo = make_use_cases(jobs=[job_a, job_b])

    await use_cases.apply(
        candidate_id=candidate_id,
        job_id=job_a.id,
        cv_url="https://s3.example.com/a.pdf",
    )
    result = await use_cases.apply(
        candidate_id=candidate_id,
        job_id=job_b.id,
        cv_url="https://s3.example.com/b.pdf",
    )

    assert result.job_id == job_b.id


@pytest.mark.anyio
async def test_apply_allows_different_candidates_same_job():
    job = make_job()
    use_cases, repo = make_use_cases(jobs=[job])

    await use_cases.apply(
        candidate_id=uuid4(), job_id=job.id, cv_url="https://s3.example.com/a.pdf"
    )
    result = await use_cases.apply(
        candidate_id=uuid4(), job_id=job.id, cv_url="https://s3.example.com/b.pdf"
    )

    assert result.job_id == job.id


# ---------------------------------------------------------------------------
# apply — job must be OPEN
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_raises_when_job_is_not_open():
    job = make_job(status=JobStatus.DRAFT)
    use_cases, _ = make_use_cases(jobs=[job])

    with pytest.raises(JobNotOpenForApplicationsException):
        await use_cases.apply(
            candidate_id=uuid4(), job_id=job.id, cv_url="https://s3.example.com/a.pdf"
        )


@pytest.mark.anyio
async def test_apply_raises_not_found_when_job_missing():
    from src.modules.jobs.presentation.exceptions import JobNotFoundException

    use_cases, _ = make_use_cases()

    with pytest.raises(JobNotFoundException):
        await use_cases.apply(
            candidate_id=uuid4(), job_id=uuid4(), cv_url="https://s3.example.com/a.pdf"
        )
