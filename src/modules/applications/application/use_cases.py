import structlog
from uuid import UUID, uuid4
from datetime import timedelta

from src.core.config import settings
from src.modules.applications.application.interfaces import (
    IApplicationRepository,
    IFileStorageRepository,
    IFileTypeSniffer,
)
from src.modules.applications.application.services import validate_cv_upload
from src.modules.applications.domain.entities import Application
from src.modules.applications.domain.value_objects import CvStorageKey
from src.modules.applications.application.dto import (
    ApplicationFilters,
    ApplicationView,
)
from src.modules.jobs.application.dto import CursorPage
from src.modules.jobs.application.enums import JobStatus
from src.modules.jobs.presentation.exceptions import JobNotFoundException
from src.modules.jobs.presentation.exceptions import (
    JobNotFoundException,
    JobNotOwnedException,
)
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
    MAX_PAGE_LIMIT = 100

    def __init__(
        self,
        repository: IApplicationRepository,
        shared_service: ISharedUseCases,
        file_storage: IFileStorageRepository,
        sniffer: IFileTypeSniffer,
    ) -> None:
        self.repository = repository
        self.shared_service = shared_service
        self.file_storage = file_storage
        self.sniffer = sniffer

    # ------------------------------------------------------------------
    # CREATE — apply to a job with a CV upload
    # ------------------------------------------------------------------
    async def apply_to_job(
        self,
        *,
        candidate_id: UUID,
        job_id: UUID,
        filename: str,
        content: bytes,
    ) -> Application:
        try:
            logger.debug(
                f"Initializing apply_to_job use case for candidate {candidate_id} "
                f"to job {job_id}."
            )

            # 1. Job must exist and be OPEN.
            job = await self.shared_service.get_job_by_id(job_id)
            if job is None:
                raise JobNotFoundException(job_id=str(job_id))

            if job.status != JobStatus.OPEN:
                logger.info(
                    f"Candidate {candidate_id} attempted to apply to job "
                    f"{job_id} which is not open (status={job.status})."
                )
                raise JobNotOpenForApplicationsException()

            # 2. No duplicate applications for the same candidate/job pair.
            # Best-effort check — the DB unique constraint on
            # (candidate_id, job_id) is the real source of truth under
            # concurrency (see APP-4).
            if await self.repository.exists_by_candidate_and_job(candidate_id, job_id):
                logger.info(
                    f"Candidate {candidate_id} already applied to job {job_id}. "
                    f"Raising conflict exception."
                )
                raise ApplicationAlreadyExistsException(
                    candidate_id=str(candidate_id), job_id=str(job_id)
                )

            # 3. CV must be a real PDF, <= 5MB (APP-7). Raises DomainException
            # on failure — nothing has been created or uploaded yet.
            cv_file = await validate_cv_upload(
                filename=filename, content=content, sniffer=self.sniffer
            )

            # 4. Pre-generate the application id so the storage key can be
            # derived before the entity exists — the Application entity's
            # invariant requires a non-empty cv_url at construction time,
            # so we can't build it with a placeholder.
            application_id = uuid4()

            storage_key = CvStorageKey(
                candidate_id=candidate_id, application_id=application_id
            )

            # 5. Upload before persisting (see rationale above).
            await self.file_storage.upload(
                key=str(storage_key),
                content=content,
                content_type=cv_file.content_type,
            )

            application = Application(
                id=application_id,
                candidate_id=candidate_id,
                job_id=job_id,
                cv_url=str(storage_key),
            )

            try:
                await self.repository.create(application)
            except Exception:
                logger.error(
                    f"Failed to persist application {application.id} after "
                    f"upload — cleaning up storage key '{storage_key}'."
                )
                await self.file_storage.delete(key=str(storage_key))
                raise

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
                "An unexpected error occurred during the apply_to_job use case.",
                exc_info=e,
            )
            raise ApplicationException()

    async def _to_view(self, application: Application) -> ApplicationView:
        """Attach a freshly generated presigned URL to a domain entity.
        Never cache the result — TTL is short and per-request by design."""
        url = await self.file_storage.generate_presigned_url(
            key=application.cv_url,
            expires_in=timedelta(seconds=settings.STORAGE_PRESIGN_TTL_SECONDS),
        )
        return ApplicationView(application=application, cv_download_url=url)

    # ------------------------------------------------------------------
    # READ — employer view, owner-only, cursor pagination
    # ------------------------------------------------------------------
    async def list_applications_for_job(
        self,
        *,
        job_id: UUID,
        employer_id: UUID,
        cursor: str | None,
        limit: int = 20,
    ) -> CursorPage[ApplicationView]:
        try:
            logger.debug(
                f"Initializing list applications for job use case: job={job_id}."
            )

            job = await self.shared_service.get_job_by_id(job_id)
            if job is None:
                raise JobNotFoundException(job_id=str(job_id))

            if job.employer_id != employer_id:
                logger.info(
                    f"Employer {employer_id} attempted to list applications for "
                    f"job {job_id} owned by {job.employer_id}."
                )
                raise JobNotOwnedException()

            capped_limit = min(max(limit, 1), self.MAX_PAGE_LIMIT)

            page = await self.repository.list_by_filters(
                ApplicationFilters(job_id=job_id),
                cursor=cursor,
                limit=capped_limit,
            )

            views = [await self._to_view(a) for a in page.items]

            logger.debug(f"Listed {len(views)} applications for job {job_id}.")
            return CursorPage(
                items=views, next_cursor=page.next_cursor, has_more=page.has_more
            )
        except StandardException:
            raise
        except ValueError as e:
            logger.info("Invalid pagination cursor provided.", exc_info=e)
            raise DomainException(DomainError(str(e)))
        except Exception as e:
            logger.error(
                "An unexpected error occurred during list_applications_for_job.",
                exc_info=e,
            )
            raise ApplicationException()

    # ------------------------------------------------------------------
    # READ — candidate view, always "my own", cursor pagination
    # ------------------------------------------------------------------
    async def list_my_applications(
        self,
        *,
        candidate_id: UUID,
        cursor: str | None,
        limit: int = 20,
    ) -> CursorPage[ApplicationView]:
        try:
            logger.debug(
                f"Initializing list my applications use case: candidate={candidate_id}."
            )

            capped_limit = min(max(limit, 1), self.MAX_PAGE_LIMIT)

            page = await self.repository.list_by_filters(
                ApplicationFilters(candidate_id=candidate_id),
                cursor=cursor,
                limit=capped_limit,
            )

            views = [await self._to_view(a) for a in page.items]

            logger.debug(
                f"Listed {len(views)} applications for candidate {candidate_id}."
            )
            return CursorPage(
                items=views, next_cursor=page.next_cursor, has_more=page.has_more
            )
        except StandardException:
            raise
        except ValueError as e:
            logger.info("Invalid pagination cursor provided.", exc_info=e)
            raise DomainException(DomainError(str(e)))
        except Exception as e:
            logger.error(
                "An unexpected error occurred during list_my_applications.",
                exc_info=e,
            )
            raise ApplicationException()
