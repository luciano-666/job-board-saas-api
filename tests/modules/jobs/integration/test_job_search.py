"""Integration tests for full-text search — verifies tsvector + GIN index
work correctly against a real PostgreSQL database."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.jobs.application.enums import JobType
from src.modules.jobs.application.dto import JobFilters
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from src.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository
from src.modules.shared.application.enums import Role
from src.modules.user.application.enums import Gender
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Email
from src.modules.user.infrastructure.repositories import SqlAlchemyUserRepository
from tests.utils import random_email


async def make_employer(db: AsyncSession) -> User:
    """Persist a real EMPLOYER user — jobs.employer_id has an FK to users.id."""
    user_repo = SqlAlchemyUserRepository(session=db)
    employer = User(
        name=Name(first_name="John", last_name="Doe"),
        gender=Gender.MALE,
        birthdate=date(1990, 1, 1),
        email=Email(random_email()),
        hashed_password="hashed_secret",
        role=Role.EMPLOYER,
    )
    await user_repo.create(employer)
    await db.flush()
    return employer


def make_job(*, employer_id, **overrides) -> Job:
    defaults: dict = dict(
        title="Backend Engineer",
        description="Standard job responsibilities apply to this role.",
        location="Ho Chi Minh City",
        job_type=JobType.FULL_TIME,
        skills=["python"],
        employer_id=employer_id,
        salary=SalaryRange(min=2000, max=4000),
    )
    defaults.update(overrides)
    job = Job(**defaults)
    job.publish()
    return job


# ---------------------------------------------------------------------------
# GIN index existence
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_gin_index_exists_on_search_vector(db):
    result = await db.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'job_board_jobs' "
            "AND indexname = 'ix_jobs_search_vector_gin'"
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert "gin" in row.lower()


# ---------------------------------------------------------------------------
# search matches title
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_matches_job_by_title(db):
    employer = await make_employer(db)
    repo = SqlAlchemyJobRepository(session=db)
    matching = make_job(employer_id=employer.id, title="Senior Backend Engineer")
    other = make_job(
        employer_id=employer.id,
        title="Frontend Developer",
        description="Build user interfaces with React and TypeScript.",
    )
    await repo.create(matching)
    await repo.create(other)
    await db.flush()

    page = await repo.list_by_filters(
        JobFilters(search="backend"), cursor=None, limit=10
    )

    ids = {j.id for j in page.items}
    assert matching.id in ids
    assert other.id not in ids


# ---------------------------------------------------------------------------
# search matches description
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_matches_job_by_description(db):
    employer = await make_employer(db)
    repo = SqlAlchemyJobRepository(session=db)
    matching = make_job(
        employer_id=employer.id,
        title="Engineer",
        description="Experience with distributed systems required.",
    )
    other = make_job(
        employer_id=employer.id,
        title="Engineer",
        description="Experience with UI design required.",
    )
    await repo.create(matching)
    await repo.create(other)
    await db.flush()

    page = await repo.list_by_filters(
        JobFilters(search="distributed systems"), cursor=None, limit=10
    )

    ids = {j.id for j in page.items}
    assert matching.id in ids
    assert other.id not in ids


# ---------------------------------------------------------------------------
# search is stemming-aware (english config)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_matches_stemmed_variants(db):
    """tsvector('english', ...) stems 'engineering' -> 'engin', matching
    a search for 'engineer' -> 'engin' too, verifying the english config
    is actually applied (not just literal substring matching)."""
    employer = await make_employer(db)
    repo = SqlAlchemyJobRepository(session=db)
    job = make_job(
        employer_id=employer.id,
        title="Software Engineering Role",
        description="General role description for the position.",
    )
    await repo.create(job)
    await db.flush()

    page = await repo.list_by_filters(
        JobFilters(search="engineer"), cursor=None, limit=10
    )

    ids = {j.id for j in page.items}
    assert job.id in ids


# ---------------------------------------------------------------------------
# no match returns empty
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_returns_empty_when_no_match(db):
    employer = await make_employer(db)
    repo = SqlAlchemyJobRepository(session=db)
    job = make_job(
        employer_id=employer.id, title="Backend Engineer", description="Python role."
    )
    await repo.create(job)
    await db.flush()

    page = await repo.list_by_filters(
        JobFilters(search="nonexistent_keyword_xyz"), cursor=None, limit=10
    )

    assert page.items == []
