from typing import Protocol
from uuid import UUID

from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Email


class IUserRepository(Protocol):
    async def create(self, user: User) -> None: ...

    async def get_by_id(self, id: UUID) -> User | None: ...

    async def get_by_email(self, email: Email | str) -> User | None: ...

    async def exists_by_email(self, email: Email | str) -> bool: ...
