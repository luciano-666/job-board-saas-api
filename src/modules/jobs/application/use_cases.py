import structlog
from uuid import UUID

from src.modules.jobs.application.interfaces import IJobRepository
from src.modules.jobs.application.enums import JobType
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainException,
)
from src.modules.jobs.presentation.exceptions import (
    JobException,
    JobNotFoundException,
    JobNotOwnedException,
)

logger = structlog.get_logger(__name__)


class JobUseCases:
    def __init__(self, repository: IJobRepository) -> None:
        self.repository = repository

    # CREATE
    async def create_job(self, job: Job) -> Job:
        try:
            logger.debug(
                f"Initializing create job use case for employer: {job.employer_id}."
            )

            await self.repository.create(job)

            logger.debug(f"Job {job.id} created successfully.")
            return job
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the create job use case.",
                exc_info=e,
            )
            raise JobException()

    # UPDATE — owner only
    async def update_job(
        self,
        job_id: UUID,
        employer_id: UUID,
        *,
        title: str,
        description: str,
        location: str,
        job_type: JobType,
        skills: list[str],
        salary: SalaryRange,
    ) -> Job:
        try:
            logger.debug(f"Initializing update job use case for job: {job_id}.")

            job = await self.repository.get_by_id_any_status(job_id)
            if job is None:
                raise JobNotFoundException(job_id=str(job_id))

            if job.employer_id != employer_id:
                logger.info(
                    f"Employer {employer_id} attempted to update job {job_id} owned by {job.employer_id}."
                )
                raise JobNotOwnedException()

            job.update_details(
                title=title,
                description=description,
                location=location,
                job_type=job_type,
                skills=skills,
                salary=salary,
            )
            job.__post_init__()  # re-run normalize/validate on mutated fields
            job._touch()

            await self.repository.update(job)

            logger.debug(f"Job {job_id} updated successfully.")
            return job
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the update job use case.",
                exc_info=e,
            )
            raise JobException()

    # UPDATE — status transitions (owner only)
    async def _get_owned_job(self, job_id: UUID, employer_id: UUID) -> Job:
        job = await self.repository.get_by_id_any_status(job_id)
        if job is None:
            raise JobNotFoundException(job_id=str(job_id))

        if job.employer_id != employer_id:
            logger.info(
                f"Employer {employer_id} attempted to act on job {job_id} owned by {job.employer_id}."
            )
            raise JobNotOwnedException()

        return job

    async def publish_job(self, job_id: UUID, employer_id: UUID) -> Job:
        try:
            logger.debug(f"Initializing publish job use case for job: {job_id}.")

            job = await self._get_owned_job(job_id, employer_id)
            job.publish()
            await self.repository.update(job)

            logger.debug(f"Job {job_id} published successfully.")
            return job
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the publish job use case.",
                exc_info=e,
            )
            raise JobException()

    async def close_job(self, job_id: UUID, employer_id: UUID) -> Job:
        try:
            logger.debug(f"Initializing close job use case for job: {job_id}.")
            job = await self._get_owned_job(job_id, employer_id)
            job.close()
            await self.repository.update(job)

            logger.debug(f"Job {job_id} closed successfully.")
            return job
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the close job use case.",
                exc_info=e,
            )
            raise JobException()

    async def archive_job(self, job_id: UUID, employer_id: UUID) -> Job:
        try:
            logger.debug(f"Initializing archive job use case for job: {job_id}.")

            job = await self._get_owned_job(job_id, employer_id)
            job.archive()
            await self.repository.update(job)

            logger.debug(f"Job {job_id} archived successfully.")
            return job
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the archive job use case.",
                exc_info=e,
            )
            raise JobException()
