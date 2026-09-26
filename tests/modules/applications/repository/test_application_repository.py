"""Repository-layer tests for SqlAlchemyApplicationRepository.

Convention: one test case per repository method (two at most).
Uses the real async session wired to the test database via the `db` fixture.
"""

from datetime import date
from uuid import uuid4

import pytest

from src.modules.applications.domain.entities import Application
from src.modules.applications.application.enums import ApplicationStatus
from src.modules.applications.infrastructure.repositories import (
    SqlAlchemyApplicationRepository,
)
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.application.enums import JobType
from src.modules.jobs.domain.value_objects import SalaryRange
from src.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository
from src.modules.shared.application.enums import Role
from src.modules.user.application.enums import Gender
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Email
from src.modules.user.infrastructure.repositories import SqlAlchemyUserRepository
from tests.utils import random_email


# ---------------------------------------------------------------------------
# Helpers — applications.job_id / candidate_id have FKs to real rows,
# so we need real persisted User (candidate + employer) and Job first.
# ---------------------------------------------------------------------------


async def make_candidate(db) -> User:
    repo = SqlAlchemyUserRepository(session=db)
    user = User(
        name=Name(first_name="Jane", last_name="Doe"),
        gender=Gender.FEMALE,
        birthdate=date(1995, 1, 1),
        email=Email(random_email()),
        hashed_password="hashed_secret",
        role=Role.CANDIDATE,
    )
    await repo.create(user)
    await db.flush()
    return user


async def make_employer(db) -> User:
    repo = SqlAlchemyUserRepository(session=db)
    user = User(
        name=Name(first_name="John", last_name="Doe"),
        gender=Gender.MALE,
        birthdate=date(1990, 1, 1),
        email=Email(random_email()),
        hashed_password="hashed_secret",
        role=Role.EMPLOYER,
    )
    await repo.create(user)
    await db.flush()
    return user


async def make_open_job(db, employer_id) -> Job:
    repo = SqlAlchemyJobRepository(session=db)
    job = Job(
        title="Backend Engineer",
        description="Build backend services.",
        location="Ho Chi Minh City",
        job_type=JobType.FULL_TIME,
        skills=["python"],
        employer_id=employer_id,
        salary=SalaryRange(min=2000, max=4000),
    )
    job.publish()
    await repo.create(job)
    await db.flush()
    return job


def make_application(*, candidate_id, job_id, cv_url: str | None = None) -> Application:
    return Application(
        candidate_id=candidate_id,
        job_id=job_id,
        cv_url=cv_url or f"applications/{candidate_id}/{uuid4()}.pdf",
    )


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_persists_application(db):
    candidate = await make_candidate(db)
    employer = await make_employer(db)
    job = await make_open_job(db, employer.id)
    repo = SqlAlchemyApplicationRepository(session=db)
    application = make_application(candidate_id=candidate.id, job_id=job.id)

    await repo.create(application)

    result = await repo.get_by_id(application.id)
    assert result is not None
    assert result.candidate_id == candidate.id
    assert result.job_id == job.id
    assert result.status == ApplicationStatus.SUBMITTED


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_by_id_returns_none_when_absent(db):
    repo = SqlAlchemyApplicationRepository(session=db)

    result = await repo.get_by_id(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# exists_by_candidate_and_job
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_exists_by_candidate_and_job_returns_true_when_present(db):
    candidate = await make_candidate(db)
    employer = await make_employer(db)
    job = await make_open_job(db, employer.id)
    repo = SqlAlchemyApplicationRepository(session=db)
    application = make_application(candidate_id=candidate.id, job_id=job.id)
    await repo.create(application)

    assert await repo.exists_by_candidate_and_job(candidate.id, job.id) is True


@pytest.mark.anyio
async def test_exists_by_candidate_and_job_returns_false_when_absent(db):
    repo = SqlAlchemyApplicationRepository(session=db)

    assert await repo.exists_by_candidate_and_job(uuid4(), uuid4()) is False


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_persists_status_transition(db):
    candidate = await make_candidate(db)
    employer = await make_employer(db)
    job = await make_open_job(db, employer.id)
    repo = SqlAlchemyApplicationRepository(session=db)
    application = make_application(candidate_id=candidate.id, job_id=job.id)
    await repo.create(application)

    application.move_to_reviewing()
    await repo.update(application)

    result = await repo.get_by_id(application.id)
    assert result is not None
    assert result.status == ApplicationStatus.REVIEWING
