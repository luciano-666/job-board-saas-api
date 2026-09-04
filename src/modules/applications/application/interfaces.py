from typing import Protocol
from uuid import UUID

from src.modules.applications.domain.entities import Application


class IApplicationRepository(Protocol):
    async def create(self, application: Application) -> None: ...

    async def get_by_id(self, id: UUID) -> Application | None: ...

    async def exists_by_candidate_and_job(
        self, candidate_id: UUID, job_id: UUID
    ) -> bool: ...

    # UPDATE
    async def update(self, application: Application) -> None: ...


class IFileTypeSniffer(Protocol):
    async def sniff(self, content: bytes) -> str:
        """Return the real MIME type detected from file bytes (magic number),
        never trusting client-supplied Content-Type or filename extension."""
        ...
