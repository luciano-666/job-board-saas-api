from typing import Protocol
from uuid import UUID

from src.modules.user.domain.entities import User
from src.modules.jobs.domain.entities import Job


class ISharedUseCases(Protocol):
    async def get_user_by_id(self, id: UUID) -> User | None: ...

    async def get_user_by_email(self, email: str) -> User: ...

    async def update_user_password(self, user: User) -> None: ...

    async def get_job_by_id(self, id: UUID) -> Job | None: ...
