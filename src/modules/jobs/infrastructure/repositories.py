from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.jobs.application.dto import CursorPage, JobFilters
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

    # NOTE: full filter/cursor implementation belongs to JOBS-listing ticket.
    # Minimal stub here to satisfy IJobRepository until that ticket lands.
    async def list_by_filters(
        self,
        filters: JobFilters,
        *,
        cursor: str | None,
        limit: int = 20,
    ) -> CursorPage[Job]:
        raise NotImplementedError(
            "list_by_filters is implemented in a separate ticket."
        )
