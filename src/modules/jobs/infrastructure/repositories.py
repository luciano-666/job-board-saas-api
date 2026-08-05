from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select, and_, tuple_, literal, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.jobs.application.dto import CursorPage, JobFilters, JobCursor
from src.modules.jobs.application.interfaces import IJobRepository
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.infrastructure.models import JobModel
from src.modules.jobs.presentation.exceptions import JobException
from src.modules.shared.presentation.exceptions import StandardException

logger = structlog.get_logger(__name__)


class SqlAlchemyJobRepository(IJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # CREATE
    async def create(self, job: Job) -> None:
        try:
            logger.info(f"Creating job '{job.title}' for employer {job.employer_id}.")

            db_job = JobModel.from_entity(job)
            self.session.add(db_job)
            await self.session.flush()

            logger.info(f"Job {job.id} created successfully.")
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error("An error occurred in the create job repository.", exc_info=e)
            raise JobException()

    # UPDATE
    async def update(self, job: Job) -> None:
        try:
            logger.info(f"Updating job {job.id}.")

            db_job = JobModel.from_entity(job)
            await self.session.merge(db_job)
            await self.session.flush()

            logger.info(f"Job {job.id} updated successfully.")
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error("An error occurred in the update job repository.", exc_info=e)
            raise JobException()

    # READ
    async def get_by_id(self, id: UUID) -> Optional[Job]:
        try:
            statement = select(JobModel).where(
                JobModel.id == id, JobModel.is_active.is_(True)
            )
            result = await self.session.execute(statement)
            job_model: Optional[JobModel] = result.scalar_one_or_none()

            if job_model is None:
                return None
            return job_model.to_entity()
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the get job by id repository.", exc_info=e
            )
            raise JobException()

    async def get_by_id_any_status(self, id: UUID) -> Optional[Job]:
        try:
            statement = select(JobModel).where(JobModel.id == id)
            result = await self.session.execute(statement)
            job_model: Optional[JobModel] = result.scalar_one_or_none()

            if job_model is None:
                return None
            return job_model.to_entity()
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the get job by id (any status) repository.",
                exc_info=e,
            )
            raise JobException()

    # READ — cursor-based listing with filters
    async def list_by_filters(
        self,
        filters: JobFilters,
        *,
        cursor: str | None,
        limit: int = 20,
    ) -> CursorPage[Job]:
        try:
            logger.info("Listing jobs by filters with cursor pagination.")

            conditions = [JobModel.is_active.is_(True)]

            if filters.status is not None:
                conditions.append(JobModel.status == filters.status)
            if filters.location is not None:
                conditions.append(JobModel.location.ilike(f"%{filters.location}%"))
            if filters.job_type is not None:
                conditions.append(JobModel.job_type == filters.job_type)
            if filters.salary_min is not None:
                conditions.append(JobModel.salary_min >= filters.salary_min)
            if filters.skills:
                # Postgres ARRAY contains — job must have all requested skills.
                # Skills are stored lowercase (see Job._normalize()), so
                # normalize the filter input the same way before querying.
                normalized_skills = [s.strip().lower() for s in filters.skills]
                conditions.append(JobModel.skills.contains(normalized_skills))
            if filters.company_id is not None:
                conditions.append(JobModel.employer_id == filters.company_id)
            if filters.search:
                conditions.append(
                    JobModel.search_vector.op("@@")(
                        func.websearch_to_tsquery("english", filters.search)
                    )
                )

            if cursor is not None:
                decoded = JobCursor.decode(cursor)
                # Keyset pagination: (created_at, id) < (cursor.created_at, cursor.job_id)
                # using row-comparison, consistent with DESC, DESC ordering.
                conditions.append(
                    tuple_(JobModel.created_at, JobModel.id)
                    < tuple_(literal(decoded.created_at), literal(decoded.job_id))
                )

            statement = (
                select(JobModel)
                .where(and_(*conditions))
                .order_by(JobModel.created_at.desc(), JobModel.id.desc())
                .limit(limit + 1)  # fetch one extra to detect has_more
            )

            result = await self.session.execute(statement)
            job_models = list(result.scalars().all())

            has_more = len(job_models) > limit
            page_models = job_models[:limit]

            items = [m.to_entity() for m in page_models]

            next_cursor = None
            if has_more and items:
                last = items[-1]
                next_cursor = JobCursor(
                    created_at=last.created_at, job_id=last.id
                ).encode()

            logger.info(f"Listed {len(items)} jobs successfully.")
            return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
        except StandardException:
            raise
        except ValueError:
            # Malformed cursor from JobCursor.decode — let caller/use case handle
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the list jobs by filters repository.", exc_info=e
            )
            raise JobException()
