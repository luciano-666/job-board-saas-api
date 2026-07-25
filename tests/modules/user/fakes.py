"""In-memory fakes for User service-layer tests.

These replace SqlAlchemyUserRepository and SharedUseCases so service tests
run without a real database.
"""

from typing import Optional
from uuid import UUID

from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Email
from src.modules.jobs.domain.entities import Job


class FakeUserRepository:
    """Pure-memory IUserRepository implementation."""

    def __init__(self, users: Optional[list[User]] = None) -> None:
        self._store: dict[UUID, User] = {u.id: u for u in (users or [])}

    # CREATE
    async def create(self, user: User) -> None:
        self._store[user.id] = user

    # READ
    async def get_by_id(self, id: UUID) -> Optional[User]:
        return self._store.get(id)

    async def get_by_email(self, email: Email | str) -> Optional[User]:
        target = str(email).lower()
        return next(
            (u for u in self._store.values() if str(u.email).lower() == target),
            None,
        )

    async def exists_by_email(self, email: Email | str) -> bool:
        target = str(email).lower()
        return any(str(u.email).lower() == target for u in self._store.values())

    async def update(self, user: User) -> None:
        self._store[user.id] = user

    async def get_by_id_any_status(self, id: UUID) -> Optional[User]:
        return self._store.get(id)


class FakeSharedUseCases:
    """Minimal SharedUseCases stand-in for UserUseCases tests."""

    def __init__(self, repository: FakeUserRepository) -> None:
        self._repo = repository

    async def get_user_by_id(self, id: UUID) -> Optional[User]:
        return await self._repo.get_by_id(id)

    async def get_user_by_email(self, email: str) -> User:
        from src.modules.user.presentation.exceptions import UserEmailNotFoundException

        result = await self._repo.get_by_email(email)
        if result is None:
            raise UserEmailNotFoundException(email=email)
        return result

    async def get_job_by_id(self, id: UUID) -> Optional[Job]:
        return None
