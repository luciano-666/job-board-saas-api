"""Service-layer tests for JobUseCases.create_job."""

from uuid import uuid4

import pytest

from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.application.use_cases import JobUseCases
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from tests.modules.jobs.fakes import FakeJobRepository, FakeUnitOfWork


def make_job(employer_id=None, **overrides) -> Job:
    defaults = dict(
        title="Backend Engineer",
        description="Build backend services.",
        location="Ho Chi Minh City",
        job_type=JobType.FULL_TIME,
        skills=["python"],
        employer_id=employer_id or uuid4(),
        salary=SalaryRange(min=2000, max=4000),
    )
    defaults.update(overrides)
    return Job(**defaults)  # ty:ignore[invalid-argument-type]


def make_use_cases(existing: list[Job] | None = None):
    repo = FakeJobRepository(existing)
    uow = FakeUnitOfWork()
    return JobUseCases(repository=repo, uow=uow), repo


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_job_persists_job_as_draft():
    use_cases, repo = make_use_cases()
    employer_id = uuid4()
    job = make_job(employer_id=employer_id)

    result = await use_cases.create_job(job)

    stored = await repo.get_by_id(result.id)
    assert stored is not None
    assert stored.status == JobStatus.DRAFT
    assert stored.employer_id == employer_id


@pytest.mark.anyio
async def test_create_job_returns_the_job():
    use_cases, _ = make_use_cases()
    job = make_job()

    result = await use_cases.create_job(job)

    assert result.title == job.title


# ---------------------------------------------------------------------------
# update_job — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_job_persists_changes_for_owner():
    employer_id = uuid4()
    existing = make_job(employer_id=employer_id)
    use_cases, repo = make_use_cases(existing=[existing])

    result = await use_cases.update_job(
        job_id=existing.id,
        employer_id=employer_id,
        title="Senior Backend Engineer",
        description=existing.description,
        location=existing.location,
        job_type=existing.job_type,
        skills=existing.skills,
        salary=existing.salary,
    )

    stored = await repo.get_by_id(existing.id)
    assert stored is not None
    assert stored.title == "Senior Backend Engineer"
    assert result.title == "Senior Backend Engineer"


# ---------------------------------------------------------------------------
# update_job — not found
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_job_raises_not_found_when_job_missing():
    from src.modules.jobs.presentation.exceptions import JobNotFoundException

    use_cases, _ = make_use_cases()

    with pytest.raises(JobNotFoundException):
        await use_cases.update_job(
            job_id=uuid4(),
            employer_id=uuid4(),
            title="X",
            description="Y",
            location="Z",
            job_type=JobType.FULL_TIME,
            skills=["go"],
            salary=SalaryRange(),
        )


# ---------------------------------------------------------------------------
# update_job — not owner
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_job_raises_forbidden_when_not_owner():
    from src.modules.jobs.presentation.exceptions import JobNotOwnedException

    owner_id = uuid4()
    other_employer_id = uuid4()
    existing = make_job(employer_id=owner_id)
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(JobNotOwnedException):
        await use_cases.update_job(
            job_id=existing.id,
            employer_id=other_employer_id,
            title="Hacked Title",
            description=existing.description,
            location=existing.location,
            job_type=existing.job_type,
            skills=existing.skills,
            salary=existing.salary,
        )


# ---------------------------------------------------------------------------
# publish_job
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_publish_job_transitions_draft_to_open():
    employer_id = uuid4()
    existing = make_job(employer_id=employer_id)
    use_cases, repo = make_use_cases(existing=[existing])

    result = await use_cases.publish_job(job_id=existing.id, employer_id=employer_id)

    stored = await repo.get_by_id(existing.id)
    assert stored is not None
    assert stored.status == JobStatus.OPEN
    assert result.status == JobStatus.OPEN


@pytest.mark.anyio
async def test_publish_job_raises_not_found_when_job_missing():
    from src.modules.jobs.presentation.exceptions import JobNotFoundException

    use_cases, _ = make_use_cases()

    with pytest.raises(JobNotFoundException):
        await use_cases.publish_job(job_id=uuid4(), employer_id=uuid4())


@pytest.mark.anyio
async def test_publish_job_raises_forbidden_when_not_owner():
    from src.modules.jobs.presentation.exceptions import JobNotOwnedException

    owner_id = uuid4()
    other_id = uuid4()
    existing = make_job(employer_id=owner_id)
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(JobNotOwnedException):
        await use_cases.publish_job(job_id=existing.id, employer_id=other_id)


@pytest.mark.anyio
async def test_publish_job_raises_domain_error_when_not_draft():
    from src.modules.shared.presentation.exceptions import DomainException

    employer_id = uuid4()
    existing = make_job(employer_id=employer_id)
    existing.publish()  # now OPEN
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(DomainException):
        await use_cases.publish_job(job_id=existing.id, employer_id=employer_id)


# ---------------------------------------------------------------------------
# close_job
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_close_job_transitions_open_to_closed():
    employer_id = uuid4()
    existing = make_job(employer_id=employer_id)
    existing.publish()
    use_cases, repo = make_use_cases(existing=[existing])

    result = await use_cases.close_job(job_id=existing.id, employer_id=employer_id)

    stored = await repo.get_by_id(existing.id)
    assert stored is not None
    assert stored.status == JobStatus.CLOSED
    assert result.status == JobStatus.CLOSED


@pytest.mark.anyio
async def test_close_job_raises_forbidden_when_not_owner():
    from src.modules.jobs.presentation.exceptions import JobNotOwnedException

    owner_id = uuid4()
    other_id = uuid4()
    existing = make_job(employer_id=owner_id)
    existing.publish()
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(JobNotOwnedException):
        await use_cases.close_job(job_id=existing.id, employer_id=other_id)


@pytest.mark.anyio
async def test_close_job_raises_domain_error_when_not_open():
    from src.modules.shared.presentation.exceptions import DomainException

    employer_id = uuid4()
    existing = make_job(employer_id=employer_id)  # still DRAFT
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(DomainException):
        await use_cases.close_job(job_id=existing.id, employer_id=employer_id)


# ---------------------------------------------------------------------------
# archive_job
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_archive_job_transitions_closed_to_archived():
    from datetime import datetime, timedelta, UTC

    employer_id = uuid4()
    existing = make_job(employer_id=employer_id)
    existing.publish()
    existing.close()
    existing.created_at = datetime.now(UTC) - timedelta(days=91)
    use_cases, repo = make_use_cases(existing=[existing])

    result = await use_cases.archive_job(job_id=existing.id, employer_id=employer_id)

    stored = await repo.get_by_id(existing.id)
    assert stored is not None
    assert stored.status == JobStatus.ARCHIVED
    assert result.status == JobStatus.ARCHIVED


@pytest.mark.anyio
async def test_archive_job_raises_forbidden_when_not_owner():
    from datetime import datetime, timedelta, UTC
    from src.modules.jobs.presentation.exceptions import JobNotOwnedException

    owner_id = uuid4()
    other_id = uuid4()
    existing = make_job(employer_id=owner_id)
    existing.publish()
    existing.created_at = datetime.now(UTC) - timedelta(days=91)
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(JobNotOwnedException):
        await use_cases.archive_job(job_id=existing.id, employer_id=other_id)


@pytest.mark.anyio
async def test_archive_job_raises_domain_error_before_90_days():
    from src.modules.shared.presentation.exceptions import DomainException

    employer_id = uuid4()
    existing = make_job(employer_id=employer_id)
    existing.publish()
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(DomainException):
        await use_cases.archive_job(job_id=existing.id, employer_id=employer_id)


@pytest.mark.anyio
async def test_archive_job_raises_not_found_when_job_missing():
    from src.modules.jobs.presentation.exceptions import JobNotFoundException

    use_cases, _ = make_use_cases()

    with pytest.raises(JobNotFoundException):
        await use_cases.archive_job(job_id=uuid4(), employer_id=uuid4())


# ---------------------------------------------------------------------------
# get_public_job_by_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_public_job_by_id_returns_open_job():
    existing = make_job()
    existing.publish()
    use_cases, _ = make_use_cases(existing=[existing])

    result = await use_cases.get_public_job_by_id(existing.id)

    assert result.id == existing.id
    assert result.status == JobStatus.OPEN


@pytest.mark.anyio
async def test_get_public_job_by_id_raises_not_found_for_draft_job():
    from src.modules.jobs.presentation.exceptions import JobNotFoundException

    existing = make_job()  # still DRAFT
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(JobNotFoundException):
        await use_cases.get_public_job_by_id(existing.id)


@pytest.mark.anyio
async def test_get_public_job_by_id_raises_not_found_for_closed_job():
    from src.modules.jobs.presentation.exceptions import JobNotFoundException

    existing = make_job()
    existing.publish()
    existing.close()
    use_cases, _ = make_use_cases(existing=[existing])

    with pytest.raises(JobNotFoundException):
        await use_cases.get_public_job_by_id(existing.id)


@pytest.mark.anyio
async def test_get_public_job_by_id_raises_not_found_when_missing():
    from src.modules.jobs.presentation.exceptions import JobNotFoundException

    use_cases, _ = make_use_cases()

    with pytest.raises(JobNotFoundException):
        await use_cases.get_public_job_by_id(uuid4())
