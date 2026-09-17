"""In-memory fakes for Applications service-layer tests."""

from typing import Optional
from uuid import UUID
from datetime import timedelta

from src.modules.applications.domain.entities import Application
from src.modules.jobs.domain.entities import Job
from src.modules.user.domain.entities import User


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


class FakeSharedUseCases:
    """Minimal ISharedUseCases stand-in for ApplicationUseCases tests.

    Only get_job_by_id is exercised by ApplicationUseCases today, but all
    ISharedUseCases methods are implemented (even if unused) so this fake
    stays valid if the Protocol is extended later.
    """

    def __init__(self, jobs: list[Job] | None = None) -> None:
        self._jobs: dict[UUID, Job] = {j.id: j for j in (jobs or [])}

    async def get_job_by_id(self, id: UUID) -> Job | None:
        return self._jobs.get(id)

    async def get_user_by_id(self, id: UUID) -> User | None:
        return None

    async def get_user_by_email(self, email: str) -> User:
        raise NotImplementedError(
            "get_user_by_email is not used by ApplicationUseCases tests."
        )

    async def update_user_password(self, user: User) -> None:
        raise NotImplementedError(
            "update_user_password is not used by ApplicationUseCases tests."
        )


class FakeFileStorageRepository:
    """Pure-memory IFileStorageRepository implementation."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, str]] = {}
        self.uploaded_keys: list[str] = []
        self.deleted_keys: list[str] = []

    async def upload(self, *, key: str, content: bytes, content_type: str) -> None:
        self._store[key] = (content, content_type)
        self.uploaded_keys.append(key)

    async def generate_presigned_url(self, *, key: str, expires_in: timedelta) -> str:
        if key not in self._store:
            raise KeyError(f"Object '{key}' does not exist in fake storage.")
        return f"https://fake-storage.local/{key}?expires_in={int(expires_in.total_seconds())}"

    async def delete(self, *, key: str) -> None:
        self._store.pop(key, None)
        self.deleted_keys.append(key)
