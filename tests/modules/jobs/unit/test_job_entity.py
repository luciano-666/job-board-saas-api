"""Unit tests for the Job domain entity."""

import pytest
from uuid import uuid4, UUID

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
    job = make_job(skills=["python", "Python", "FastAPI"])
    assert job.skills == ["python", "fastapi"]


def test_job_rejects_empty_title():
    with pytest.raises(DomainError, match="title"):
        make_job(title="   ")


def test_job_rejects_empty_skills_list():
    with pytest.raises(DomainError, match="skill"):
        make_job(skills=[])


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
# archive (closed -> archived)
# ---------------------------------------------------------------------------


def test_archive_moves_closed_to_archived():
    job = make_job()
    job.publish()
    job.close()
    job.archive()
    assert job.status == JobStatus.ARCHIVED


def test_archive_raises_when_not_closed():
    job = make_job()
    job.publish()
    with pytest.raises(DomainError, match="closed"):
        job.archive()
