from uuid import UUID

from fastapi import APIRouter, Depends
import structlog

from src.modules.authentication.presentation.dependencies import authenticate_employer
from src.modules.jobs.application.use_cases import JobUseCases
from src.modules.jobs.presentation.dependencies import get_job_use_cases
from src.modules.jobs.presentation.docs import (
    router_docs,
    create_job_docs,
    update_job_docs,
)
from src.modules.jobs.presentation.exceptions import JobException
from src.modules.jobs.presentation.schemas import (
    CreateJobRequest,
    CreateJobResponse,
    UpdateJobRequest,
    UpdateJobResponse,
    JobResponse,
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
