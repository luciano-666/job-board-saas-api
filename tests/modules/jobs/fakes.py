"""In-memory fakes for Jobs service-layer tests."""

from typing import Optional
from uuid import UUID

from src.modules.jobs.application.dto import CursorPage, JobFilters
from src.modules.jobs.domain.entities import Job


class FakeJobRepository:
    """Pure-memory IJobRepository implementation."""

    def __init__(self, jobs: Optional[list[Job]] = None) -> None:
        self._store: dict[UUID, Job] = {j.id: j for j in (jobs or [])}

    async def create(self, job: Job) -> None:
        self._store[job.id] = job

    async def update(self, job: Job) -> None:
        self._store[job.id] = job

    async def get_by_id(self, id: UUID) -> Optional[Job]:
        return self._store.get(id)

    async def get_by_id_any_status(self, id: UUID) -> Optional[Job]:
        return self._store.get(id)

    async def list_by_filters(
        self,
        filters: JobFilters,
        *,
        cursor: str | None,
        limit: int = 20,
    ) -> CursorPage[Job]:
        return CursorPage(
            items=list(self._store.values()), next_cursor=None, has_more=False
        )
