"""Unit tests for the Job domain entity."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

from src.modules.shared.domain.entities import DomainError
from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_job(
    *,
    title: str = "Backend Engineer",
    description: str = "Build and maintain backend services.",
    location: str = "Ho Chi Minh City",
    salary: SalaryRange = SalaryRange(min=2000, max=4000),
    job_type: JobType = JobType.FULL_TIME,
    skills: list[str] | None = None,
    employer_id: UUID | None = None,
) -> Job:
    return Job(
        title=title,
        description=description,
        location=location,
        salary=salary,
        job_type=job_type,
        skills=skills if skills is not None else ["python", "fastapi"],
        employer_id=employer_id if employer_id is not None else uuid4(),
    )


# ---------------------------------------------------------------------------
# creation
# ---------------------------------------------------------------------------


def test_job_defaults_to_draft_status():
    job = make_job()
    assert job.status == JobStatus.DRAFT


def test_job_normalizes_and_dedupes_skills():
    job = make_job(skills=["Python", " python ", "FastAPI"])
    assert job.skills == ["python", "fastapi"]


def test_job_rejects_empty_title():
    with pytest.raises(DomainError, match="title"):
        make_job(title="   ")


def test_job_rejects_empty_skills_list():
    with pytest.raises(DomainError, match="skill"):
        make_job(skills=[])


def test_job_salary_defaults_to_undisclosed_when_omitted():
    job = Job(
        title="Engineer",
        description="Some description.",
        location="Remote",
        job_type=JobType.CONTRACT,
        skills=["go"],
        employer_id=uuid4(),
    )
    assert job.salary == SalaryRange()


# ---------------------------------------------------------------------------
# publish (draft -> open)
# ---------------------------------------------------------------------------


def test_publish_moves_draft_to_open():
    job = make_job()
    job.publish()
    assert job.status == JobStatus.OPEN


def test_publish_raises_when_not_draft():
    job = make_job()
    job.publish()
    with pytest.raises(DomainError, match="draft"):
        job.publish()


# ---------------------------------------------------------------------------
# close (open -> closed)
# ---------------------------------------------------------------------------


def test_close_moves_open_to_closed():
    job = make_job()
    job.publish()
    job.close()
    assert job.status == JobStatus.CLOSED


def test_close_raises_when_not_open():
    job = make_job()  # still draft
    with pytest.raises(DomainError, match="open"):
        job.close()


# ---------------------------------------------------------------------------
# archive (open|closed -> archived, only after 90 days since created_at)
# ---------------------------------------------------------------------------


def _age_job(job: Job, days: int) -> None:
    """Backdate created_at to simulate a job that has aged `days` days."""
    job.created_at = datetime.now(UTC) - timedelta(days=days)


def test_archive_raises_when_status_is_draft():
    job = make_job()
    _age_job(job, days=100)
    with pytest.raises(DomainError, match="open or closed"):
        job.archive()


def test_archive_raises_when_not_yet_90_days_from_open():
    job = make_job()
    job.publish()
    _age_job(job, days=10)
    with pytest.raises(DomainError, match="90 days"):
        job.archive()


def test_archive_raises_when_not_yet_90_days_from_closed():
    job = make_job()
    job.publish()
    job.close()
    _age_job(job, days=89)
    with pytest.raises(DomainError, match="90 days"):
        job.archive()


def test_archive_succeeds_from_open_after_90_days():
    job = make_job()
    job.publish()
    _age_job(job, days=90)
    job.archive()
    assert job.status == JobStatus.ARCHIVED


def test_archive_succeeds_from_closed_after_90_days():
    job = make_job()
    job.publish()
    job.close()
    _age_job(job, days=91)
    job.archive()
    assert job.status == JobStatus.ARCHIVED


def test_archive_raises_when_already_archived():
    job = make_job()
    job.publish()
    _age_job(job, days=90)
    job.archive()
    with pytest.raises(DomainError, match="open or closed"):
        job.archive()
