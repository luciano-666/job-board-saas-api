import structlog
from uuid import UUID

from src.modules.applications.application.interfaces import IApplicationRepository
from src.modules.applications.domain.entities import Application
from src.modules.jobs.application.enums import JobStatus
from src.modules.jobs.presentation.exceptions import JobNotFoundException
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainException,
)
from src.modules.applications.presentation.exceptions import (
    ApplicationException,
    ApplicationAlreadyExistsException,
    JobNotOpenForApplicationsException,
)
from src.modules.shared.application.interfaces import ISharedUseCases

logger = structlog.get_logger(__name__)


class ApplicationUseCases:
    def __init__(
        self,
        repository: IApplicationRepository,
        shared_service: ISharedUseCases,
    ) -> None:
        self.repository = repository
        self.shared_service = shared_service

    # CREATE
    async def apply(self, candidate_id: UUID, job_id: UUID, cv_url: str) -> Application:
        try:
            logger.debug(
                f"Initializing apply use case for candidate {candidate_id} "
                f"to job {job_id}."
            )

            job = await self.shared_service.get_job_by_id(job_id)
            if job is None:
                raise JobNotFoundException(job_id=str(job_id))

            if job.status != JobStatus.OPEN:
                logger.info(
                    f"Candidate {candidate_id} attempted to apply to job "
                    f"{job_id} which is not open (status={job.status})."
                )
                raise JobNotOpenForApplicationsException()

            # Domain-rule guard: candidate cannot apply to the same job twice.
            # This is a best-effort check (TOCTOU race is still possible
            # under concurrent requests) — the DB-level unique constraint
            # on (candidate_id, job_id) is the actual source of truth and
            # must be added in the Alembic migration for the applications
            # table (see APP-4).
            if await self.repository.exists_by_candidate_and_job(candidate_id, job_id):
                logger.info(
                    f"Candidate {candidate_id} already applied to job {job_id}. "
                    f"Raising conflict exception."
                )
                raise ApplicationAlreadyExistsException(
                    candidate_id=str(candidate_id), job_id=str(job_id)
                )

            application = Application(
                candidate_id=candidate_id, job_id=job_id, cv_url=cv_url
            )
            await self.repository.create(application)

            logger.debug(
                f"Application {application.id} created successfully for "
                f"candidate {candidate_id} to job {job_id}."
            )
            return application
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the apply use case.",
                exc_info=e,
            )
            raise ApplicationException()
