"""Service-layer tests for ApplicationUseCases.apply_to_job — full orchestration:
job lookup → duplicate guard → CV validation → upload → persist."""

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
from src.modules.jobs.presentation.exceptions import JobNotFoundException
from src.modules.shared.presentation.exceptions import DomainException
from tests.modules.applications.fakes import (
    FakeApplicationRepository,
    FakeFileStorageRepository,
    FakeSharedUseCases,
)

REAL_PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


class FakeSniffer:
    """Deterministic MIME sniffer — avoids depending on python-magic in
    service-layer tests, mirrors the fake used in APP-7's test_cv_validation.py."""

    def __init__(self, mime: str = "application/pdf") -> None:
        self._mime = mime

    async def sniff(self, content: bytes) -> str:
        return self._mime


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
    job.status = status
    return job


def make_use_cases(*, applications=None, jobs=None, mime: str = "application/pdf"):
    app_repo = FakeApplicationRepository(applications)
    shared = FakeSharedUseCases(jobs)
    storage = FakeFileStorageRepository()
    sniffer = FakeSniffer(mime)
    use_cases = ApplicationUseCases(
        repository=app_repo,
        shared_service=shared,
        file_storage=storage,
        sniffer=sniffer,
    )
    return use_cases, app_repo, storage


# ---------------------------------------------------------------------------
# apply_to_job — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_to_job_uploads_file_and_persists_application():
    job = make_job()
    use_cases, app_repo, storage = make_use_cases(jobs=[job])
    candidate_id = uuid4()

    result = await use_cases.apply_to_job(
        candidate_id=candidate_id,
        job_id=job.id,
        filename="resume.pdf",
        content=REAL_PDF_BYTES,
    )

    stored = await app_repo.get_by_id(result.id)
    assert stored is not None
    assert stored.candidate_id == candidate_id
    assert stored.job_id == job.id
    assert stored.cv_url == f"applications/{candidate_id}/{result.id}.pdf"


@pytest.mark.anyio
async def test_apply_to_job_uploads_content_to_storage_with_correct_key():
    job = make_job()
    use_cases, _, storage = make_use_cases(jobs=[job])
    candidate_id = uuid4()

    result = await use_cases.apply_to_job(
        candidate_id=candidate_id,
        job_id=job.id,
        filename="resume.pdf",
        content=REAL_PDF_BYTES,
    )

    expected_key = f"applications/{candidate_id}/{result.id}.pdf"
    assert expected_key in storage.uploaded_keys


# ---------------------------------------------------------------------------
# apply_to_job — CV validation failures (APP-7 rules enforced here too)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_to_job_rejects_non_pdf_content():
    job = make_job()
    use_cases, app_repo, storage = make_use_cases(
        jobs=[job], mime="application/x-dosexec"
    )

    with pytest.raises(DomainException):
        await use_cases.apply_to_job(
            candidate_id=uuid4(),
            job_id=job.id,
            filename="resume.pdf",
            content=b"MZ\x90\x00...",
        )

    # Nothing should be persisted or uploaded on validation failure.
    assert storage.uploaded_keys == []


@pytest.mark.anyio
async def test_apply_to_job_rejects_oversized_file():
    job = make_job()
    use_cases, _, storage = make_use_cases(jobs=[job])
    oversized = b"0" * (5 * 1024 * 1024 + 1)

    with pytest.raises(DomainException):
        await use_cases.apply_to_job(
            candidate_id=uuid4(),
            job_id=job.id,
            filename="resume.pdf",
            content=oversized,
        )

    assert storage.uploaded_keys == []


# ---------------------------------------------------------------------------
# apply_to_job — job state guards (existing rules, now exercised end-to-end)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_to_job_raises_not_found_when_job_missing():
    use_cases, _, _ = make_use_cases()

    with pytest.raises(JobNotFoundException):
        await use_cases.apply_to_job(
            candidate_id=uuid4(),
            job_id=uuid4(),
            filename="resume.pdf",
            content=REAL_PDF_BYTES,
        )


@pytest.mark.anyio
async def test_apply_to_job_raises_when_job_not_open():
    job = make_job(status=JobStatus.DRAFT)
    use_cases, _, storage = make_use_cases(jobs=[job])

    with pytest.raises(JobNotOpenForApplicationsException):
        await use_cases.apply_to_job(
            candidate_id=uuid4(),
            job_id=job.id,
            filename="resume.pdf",
            content=REAL_PDF_BYTES,
        )

    # Job check happens before file validation/upload — no upload attempted.
    assert storage.uploaded_keys == []


# ---------------------------------------------------------------------------
# apply_to_job — duplicate application guard
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_to_job_raises_when_already_applied():
    job = make_job()
    candidate_id = uuid4()
    use_cases, _, storage = make_use_cases(jobs=[job])

    await use_cases.apply_to_job(
        candidate_id=candidate_id,
        job_id=job.id,
        filename="resume.pdf",
        content=REAL_PDF_BYTES,
    )

    with pytest.raises(ApplicationAlreadyExistsException):
        await use_cases.apply_to_job(
            candidate_id=candidate_id,
            job_id=job.id,
            filename="resume_v2.pdf",
            content=REAL_PDF_BYTES,
        )

    # Only the first, successful upload happened.
    assert len(storage.uploaded_keys) == 1
