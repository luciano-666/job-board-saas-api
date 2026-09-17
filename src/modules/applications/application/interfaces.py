from typing import Protocol
from uuid import UUID
from datetime import timedelta

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


class IFileStorageRepository(Protocol):
    async def upload(self, *, key: str, content: bytes, content_type: str) -> None:
        """Upload raw bytes to the given object key."""
        ...

    async def generate_presigned_url(self, *, key: str, expires_in: timedelta) -> str:
        """Generate a time-limited URL to retrieve the object.
        Per spec: TTL 1 hour when returned to employers viewing CVs."""
        ...

    async def delete(self, *, key: str) -> None:
        """Remove an object — used for cleanup on failed application flows."""
        ...
