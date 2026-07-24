from typing import Protocol
from uuid import UUID

from src.modules.jobs.application.dto import CursorPage, JobFilters
from src.modules.jobs.domain.entities import Job


class IJobRepository(Protocol):
    # CREATE
    async def create(self, job: Job) -> None: ...

    # UPDATE
    async def update(self, job: Job) -> None: ...

    # READ
    async def get_by_id(self, id: UUID) -> Job | None: ...

    async def get_by_id_any_status(self, id: UUID) -> Job | None: ...

    async def list_by_filters(
        self,
        filters: JobFilters,
        *,
        cursor: str | None,
        limit: int = 20,
    ) -> CursorPage[Job]: ...
