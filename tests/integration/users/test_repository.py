import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from src.users.domain.model import User, UserRole
from src.users.adapters.repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.anyio


def make_user(
    email: str = "john@example.com",
) -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password="hashed-password",
        role=UserRole.candidate,
        is_active=True,
    )


async def test_add_user(db: AsyncSession):
    user = make_user(email="candidate@example.com")
    user_repo = SqlAlchemyUserRepository(db)
    user_repo.add(user)
    await db.flush()

    fetched_user = await user_repo.get(user.id)
    assert fetched_user is not None
    assert fetched_user.id == user.id
    assert fetched_user.email == "candidate@example.com"


async def test_get_user_by_id(db: AsyncSession):
    repo = SqlAlchemyUserRepository(db)
    user = make_user()

    repo.add(user)
    await db.flush()

    fetched = await repo.get(user.id)
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.email == user.email


async def test_get_user_by_id_not_found(db: AsyncSession):
    repo = SqlAlchemyUserRepository(db)

    result = await repo.get(uuid4())

    assert result is None


async def test_get_user_by_email(db: AsyncSession):
    repo = SqlAlchemyUserRepository(db)
    user = make_user(email="target@example.com")

    repo.add(user)
    await db.flush()

    fetched = await repo.get_by_email("target@example.com")
    assert fetched is not None
    assert fetched.email == "target@example.com"


async def test_get_user_by_email_not_found(db: AsyncSession):
    repo = SqlAlchemyUserRepository(db)
    result = await repo.get_by_email("ghost@example.com")
    assert result is None
