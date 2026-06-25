"""Repository-layer tests for SqlAlchemyUserRepository.

Convention: one test case per repository method (two at most).
All tests use the real async session wired to the test database via the
`db` fixture defined in tests/conftest.py.
"""

import pytest

from src.modules.user.application.enums import Gender
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Email
from src.modules.user.infrastructure.repositories import SqlAlchemyUserRepository
from tests.utils import random_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(email: str | None = None) -> User:
    return User(
        name=Name(first_name="John", last_name="Doe"),
        gender=Gender.MALE,
        birthdate=__import__("datetime").date(1990, 1, 1),
        email=Email(email or random_email()),
        hashed_password="hashed_secret",
    )


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_persists_user(db):
    repo = SqlAlchemyUserRepository(session=db)
    user = make_user()

    await repo.create(user)

    result = await repo.get_by_id(user.id)
    assert result is not None
    assert str(result.email) == str(user.email)


# ---------------------------------------------------------------------------
# exists_by_email
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_exists_by_email_returns_true_when_present(db):
    repo = SqlAlchemyUserRepository(session=db)
    user = make_user()
    await repo.create(user)

    assert await repo.exists_by_email(user.email) is True


@pytest.mark.anyio
async def test_exists_by_email_returns_false_when_absent(db):
    repo = SqlAlchemyUserRepository(session=db)

    assert await repo.exists_by_email(Email(random_email())) is False


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_by_id_returns_none_when_absent(db):
    import uuid

    repo = SqlAlchemyUserRepository(session=db)

    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# get_by_email
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_by_email_returns_user(db):
    repo = SqlAlchemyUserRepository(session=db)
    user = make_user()
    await repo.create(user)

    result = await repo.get_by_email(user.email)
    assert result is not None
    assert str(result.email) == str(user.email)


@pytest.mark.anyio
async def test_get_by_email_returns_none_when_absent(db):
    repo = SqlAlchemyUserRepository(session=db)

    result = await repo.get_by_email(Email(random_email()))
    assert result is None
