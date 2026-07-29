"""In-memory fakes for Jobs service-layer tests."""

from typing import Optional
from uuid import UUID

from src.modules.jobs.application.dto import CursorPage, JobFilters, JobCursor
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
        items = list(self._store.values())

        # Apply filters
        if filters.status is not None:
            items = [j for j in items if j.status == filters.status]
        if filters.location is not None:
            needle = filters.location.lower()
            items = [j for j in items if needle in j.location.lower()]
        if filters.job_type is not None:
            items = [j for j in items if j.job_type == filters.job_type]
        if filters.salary_min is not None:
            items = [
                j
                for j in items
                if j.salary.min is not None and j.salary.min >= filters.salary_min
            ]
        if filters.skills:
            wanted = {s.strip().lower() for s in filters.skills}
            items = [j for j in items if wanted.issubset(set(j.skills))]
        if filters.company_id is not None:
            items = [j for j in items if j.employer_id == filters.company_id]
        if filters.search:
            needle = filters.search.lower()
            items = [
                j
                for j in items
                if needle in j.title.lower() or needle in j.description.lower()
            ]

        # Sort: created_at DESC, id DESC (tiebreaker) — matches JobCursor ordering
        items.sort(key=lambda j: (j.created_at, j.id), reverse=True)

        # Apply cursor: keep only items strictly "after" the cursor position
        if cursor is not None:
            decoded = JobCursor.decode(cursor)
            items = [
                j
                for j in items
                if (j.created_at, j.id) < (decoded.created_at, decoded.job_id)
            ]

        page = items[:limit]
        has_more = len(items) > limit

        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = JobCursor(created_at=last.created_at, job_id=last.id).encode()

        return CursorPage(items=page, next_cursor=next_cursor, has_more=has_more)
