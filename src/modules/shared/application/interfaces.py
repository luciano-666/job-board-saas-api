from typing import Protocol

from src.modules.user.domain.entities import User


class ISharedUseCases(Protocol):
    async def get_user_by_id(self, user: User) -> User | None: ...

    async def get_user_by_email(self, email: str) -> User: ...
