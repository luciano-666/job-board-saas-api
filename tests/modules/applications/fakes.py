"""In-memory fakes for Applications service-layer tests."""

from typing import Optional
from uuid import UUID

from src.modules.applications.domain.entities import Application


class FakeApplicationRepository:
    """Pure-memory IApplicationRepository implementation."""

    def __init__(self, applications: Optional[list[Application]] = None) -> None:
        self._store: dict[UUID, Application] = {a.id: a for a in (applications or [])}

    async def create(self, application: Application) -> None:
        self._store[application.id] = application

    async def get_by_id(self, id: UUID) -> Optional[Application]:
        return self._store.get(id)

    async def exists_by_candidate_and_job(
        self, candidate_id: UUID, job_id: UUID
    ) -> bool:
        return any(
            a.candidate_id == candidate_id and a.job_id == job_id
            for a in self._store.values()
        )

    async def update(self, application: Application) -> None:
        self._store[application.id] = application
