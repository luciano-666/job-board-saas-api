from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends
import structlog

from src.modules.authentication.presentation.dependencies import authenticate_employer
from src.modules.jobs.application.use_cases import JobUseCases
from src.modules.jobs.presentation.dependencies import get_job_use_cases
from src.modules.jobs.presentation.docs import (
    router_docs,
    create_job_docs,
    update_job_docs,
    publish_job_docs,
    close_job_docs,
    archive_job_docs,
    get_job_docs,
    list_jobs_docs,
)
from src.modules.jobs.presentation.exceptions import JobException
from src.modules.jobs.presentation.schemas import (
    CreateJobRequest,
    CreateJobResponse,
    UpdateJobRequest,
    UpdateJobResponse,
    PublishJobResponse,
    CloseJobResponse,
    ArchiveJobResponse,
    JobResponse,
    GetJobResponse,
    JobListQuery,
    JobListResponse,
)
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainException,
)
from src.modules.user.domain.entities import User

logger = structlog.get_logger(__name__)

router = APIRouter(**router_docs)


# CREATE — employer only
@router.post("/", **create_job_docs)
@router.post("", include_in_schema=False)
async def create_job(
    payload: CreateJobRequest,
    user: User = Depends(authenticate_employer),
    use_case: JobUseCases = Depends(get_job_use_cases),
) -> CreateJobResponse:
    try:
        job = payload.to_entity(employer_id=user.id)
        result = await use_case.create_job(job)
        return CreateJobResponse(data=JobResponse.from_entity(result))
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the create job endpoint.", exc_info=e)
        raise JobException()


# READ — public listing (must be registered before GET /{job_id}/)
@router.get("/", **list_jobs_docs)
@router.get("", include_in_schema=False)
async def list_jobs(
    query: Annotated[JobListQuery, Depends()],
    use_case: JobUseCases = Depends(get_job_use_cases),
) -> JobListResponse:
    try:
        page = await use_case.list_public_jobs(
            query.to_filters(), cursor=query.cursor, limit=query.limit
        )
        return JobListResponse(
            data=[JobResponse.from_entity(j) for j in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the list jobs endpoint.", exc_info=e)
        raise JobException()


# UPDATE — employer, owner only
@router.patch("/{job_id}/", **update_job_docs)
@router.patch("/{job_id}", include_in_schema=False)
async def update_job(
    job_id: UUID,
    payload: UpdateJobRequest,
    user: User = Depends(authenticate_employer),
    use_case: JobUseCases = Depends(get_job_use_cases),
) -> UpdateJobResponse:
    try:
        from src.modules.jobs.domain.value_objects import SalaryRange

        result = await use_case.update_job(
            job_id=job_id,
            employer_id=user.id,
            title=payload.title,
            description=payload.description,
            location=payload.location,
            job_type=payload.job_type,
            skills=payload.skills,
            salary=SalaryRange(
                min=payload.salary.min if payload.salary else None,
                max=payload.salary.max if payload.salary else None,
            ),
        )
        return UpdateJobResponse(data=JobResponse.from_entity(result))
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the update job endpoint.", exc_info=e)
        raise JobException()


# UPDATE — publish (draft -> open), owner only
@router.patch("/{job_id}/publish/", **publish_job_docs)
@router.patch("/{job_id}/publish", include_in_schema=False)
async def publish_job(
    job_id: UUID,
    user: User = Depends(authenticate_employer),
    use_case: JobUseCases = Depends(get_job_use_cases),
) -> PublishJobResponse:
    try:
        result = await use_case.publish_job(job_id=job_id, employer_id=user.id)
        return PublishJobResponse(data=JobResponse.from_entity(result))
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the publish job endpoint.", exc_info=e)
        raise JobException()


# UPDATE — close (open -> closed), owner only
@router.patch("/{job_id}/close/", **close_job_docs)
@router.patch("/{job_id}/close", include_in_schema=False)
async def close_job(
    job_id: UUID,
    user: User = Depends(authenticate_employer),
    use_case: JobUseCases = Depends(get_job_use_cases),
) -> CloseJobResponse:
    try:
        result = await use_case.close_job(job_id=job_id, employer_id=user.id)
        return CloseJobResponse(data=JobResponse.from_entity(result))
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the close job endpoint.", exc_info=e)
        raise JobException()


# UPDATE — archive (open|closed -> archived, 90+ days), owner only
@router.patch("/{job_id}/archive/", **archive_job_docs)
@router.patch("/{job_id}/archive", include_in_schema=False)
async def archive_job(
    job_id: UUID,
    user: User = Depends(authenticate_employer),
    use_case: JobUseCases = Depends(get_job_use_cases),
) -> ArchiveJobResponse:
    try:
        result = await use_case.archive_job(job_id=job_id, employer_id=user.id)
        return ArchiveJobResponse(data=JobResponse.from_entity(result))
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the archive job endpoint.", exc_info=e)
        raise JobException()


# READ — public
@router.get("/{job_id}/", **get_job_docs)
@router.get("/{job_id}", include_in_schema=False)
async def get_job(
    job_id: UUID,
    use_case: JobUseCases = Depends(get_job_use_cases),
) -> GetJobResponse:
    try:
        result = await use_case.get_public_job_by_id(job_id)
        return GetJobResponse(data=JobResponse.from_entity(result))
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred in the get job endpoint.", exc_info=e)
        raise JobException()
