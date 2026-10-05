"""Service-layer tests for ApplicationUseCases.list_applications_for_job
and list_my_applications — cursor pagination + presigned URL assembly."""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest

from src.modules.applications.application.dto import ApplicationFilters
from src.modules.applications.application.use_cases import ApplicationUseCases
from src.modules.applications.domain.entities import Application
from src.modules.applications.presentation.exceptions import ApplicationException
from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from src.modules.jobs.presentation.exceptions import (
    JobNotFoundException,
    JobNotOwnedException,
)
from tests.modules.applications.fakes import (
    FakeApplicationRepository,
    FakeFileStorageRepository,
    FakeSharedUseCases,
)


class FakeSniffer:
    async def sniff(self, content: bytes) -> str:
        return "application/pdf"


def make_job(*, employer_id=None, status: JobStatus = JobStatus.OPEN) -> Job:
    job = Job(
        title="Backend Engineer",
        description="Build backend services.",
        location="Ho Chi Minh City",
        job_type=JobType.FULL_TIME,
        skills=["python"],
        employer_id=employer_id or uuid4(),
        salary=SalaryRange(min=2000, max=4000),
    )
    if status == JobStatus.OPEN:
        job.publish()
    job.status = status
    return job


def make_application(*, job_id, candidate_id=None, created_at=None) -> Application:
    application = Application(
        candidate_id=candidate_id or uuid4(),
        job_id=job_id,
        cv_url=f"applications/{uuid4()}/{uuid4()}.pdf",
    )
    if created_at is not None:
        application.created_at = created_at
    return application


def make_use_cases(*, applications=None, jobs=None):
    app_repo = FakeApplicationRepository(applications)
    shared = FakeSharedUseCases(jobs)
    storage = FakeFileStorageRepository()
    # storage needs the objects to "exist" for presign to succeed
    for a in applications or []:
        storage._store[a.cv_url] = (b"data", "application/pdf")
    use_cases = ApplicationUseCases(
        repository=app_repo,
        shared_service=shared,
        file_storage=storage,
        sniffer=FakeSniffer(),
    )
    return use_cases, app_repo, storage


# ---------------------------------------------------------------------------
# list_applications_for_job — employer, ownership enforced
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_applications_for_job_returns_presigned_urls():
    employer_id = uuid4()
    job = make_job(employer_id=employer_id)
    applications = [make_application(job_id=job.id) for _ in range(3)]
    use_cases, _, storage = make_use_cases(applications=applications, jobs=[job])

    page = await use_cases.list_applications_for_job(
        job_id=job.id, employer_id=employer_id, cursor=None, limit=10
    )

    assert len(page.items) == 3
    for view in page.items:
        assert view.cv_download_url.startswith("https://fake-storage.local/") 
        assert view.application.cv_url in view.cv_download_url


@pytest.mark.anyio
async def test_list_applications_for_job_raises_not_found_when_job_missing():
    use_cases, _, _ = make_use_cases()

    with pytest.raises(JobNotFoundException):
        await use_cases.list_applications_for_job(
            job_id=uuid4(), employer_id=uuid4(), cursor=None, limit=10
        )


@pytest.mark.anyio
async def test_list_applications_for_job_raises_forbidden_when_not_owner():
    owner_id = uuid4()
    other_id = uuid4()
    job = make_job(employer_id=owner_id)
    use_cases, _, _ = make_use_cases(jobs=[job])

    with pytest.raises(JobNotOwnedException):
        await use_cases.list_applications_for_job(
            job_id=job.id, employer_id=other_id, cursor=None, limit=10
        )


@pytest.mark.anyio
async def test_list_applications_for_job_paginates_with_cursor():
    employer_id = uuid4()
    job = make_job(employer_id=employer_id)
    base = datetime.now(UTC)
    applications = [
        make_application(job_id=job.id, created_at=base - timedelta(minutes=i))
        for i in range(5)
    ]
    use_cases, _, _ = make_use_cases(applications=applications, jobs=[job])

    first_page = await use_cases.list_applications_for_job(
        job_id=job.id, employer_id=employer_id, cursor=None, limit=3
    )
    second_page = await use_cases.list_applications_for_job(
        job_id=job.id,
        employer_id=employer_id,
        cursor=first_page.next_cursor,
        limit=3,
    )

    first_ids = {v.application.id for v in first_page.items}
    second_ids = {v.application.id for v in second_page.items}
    assert first_ids.isdisjoint(second_ids)
    assert first_page.has_more is True
    assert second_page.has_more is False


@pytest.mark.anyio
async def test_list_applications_for_job_only_includes_that_jobs_applications():
    employer_id = uuid4()
    job_a = make_job(employer_id=employer_id)
    job_b = make_job(employer_id=employer_id)
    app_a = make_application(job_id=job_a.id)
    app_b = make_application(job_id=job_b.id)
    use_cases, _, _ = make_use_cases(applications=[app_a, app_b], jobs=[job_a, job_b])

    page = await use_cases.list_applications_for_job(
        job_id=job_a.id, employer_id=employer_id, cursor=None, limit=10
    )

    ids = {v.application.id for v in page.items}
    assert ids == {app_a.id}


# ---------------------------------------------------------------------------
# list_my_applications — candidate, no ownership check needed
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_my_applications_returns_only_own_applications():
    candidate_id = uuid4()
    other_candidate_id = uuid4()
    job = make_job()
    mine = make_application(job_id=job.id, candidate_id=candidate_id)
    not_mine = make_application(job_id=job.id, candidate_id=other_candidate_id)
    use_cases, _, _ = make_use_cases(applications=[mine, not_mine], jobs=[job])

    page = await use_cases.list_my_applications(
        candidate_id=candidate_id, cursor=None, limit=10
    )

    ids = {v.application.id for v in page.items}
    assert ids == {mine.id}


@pytest.mark.anyio
async def test_list_my_applications_returns_empty_when_none():
    use_cases, _, _ = make_use_cases()

    page = await use_cases.list_my_applications(
        candidate_id=uuid4(), cursor=None, limit=10
    )

    assert page.items == []
    assert page.has_more is False
