import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from src.users.domain.model import User, UserRole


def make_user(
    email: str = "john@example.com",
) -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password="hashed-password",
        role=UserRole.candidate,
        is_activated=True,
    )


async def test_add_user(db: AsyncSession):
    pytest.fail("todo")


async def test_get_user_by_email(db: AsyncSession):
    pytest.fail("todo")


async def test_returns_none_when_email_not_found(db: AsyncSession):
    pytest.fail("todo")


async def test_repository_tracks_added_entity_in_seen(db: AsyncSession):
    pytest.fail("todo")


async def test_repository_tracks_loaded_entity_in_seen(db: AsyncSession):
    pytest.fail("todo")


async def test_loaded_user_contains_persisted_role(db: AsyncSession):
    pytest.fail("todo")


async def test_loaded_user_contains_activation_status(db: AsyncSession):
    pytest.fail("todo")
