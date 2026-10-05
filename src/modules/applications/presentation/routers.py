from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
import structlog

from src.modules.authentication.presentation.dependencies import (
    authenticate_employer,
    authenticate_user,
)
from src.modules.applications.application.use_cases import ApplicationUseCases
from src.modules.applications.presentation.dependencies import (
    get_application_use_cases,
)
from src.modules.applications.presentation.exceptions import ApplicationException
from src.modules.applications.presentation.schemas import (
    ApplicationListQuery,
    ApplicationListResponse,
    ApplicationResponse,
)
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainException,
)
from src.modules.user.domain.entities import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/applications", tags=["Applications"])


# READ — employer, ownership enforced in use case
@router.get("/jobs/{job_id}/")
@router.get("/jobs/{job_id}", include_in_schema=False)
async def list_applications_for_job(
    job_id: UUID,
    query: Annotated[ApplicationListQuery, Depends()],
    user: User = Depends(authenticate_employer),
    use_case: ApplicationUseCases = Depends(get_application_use_cases),
) -> ApplicationListResponse:
    try:
        page = await use_case.list_applications_for_job(
            job_id=job_id,
            employer_id=user.id,
            cursor=query.cursor,
            limit=query.limit,
        )
        return ApplicationListResponse(
            data=[ApplicationResponse.from_view(v) for v in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error(
            "An error occurred in the list applications for job endpoint.", exc_info=e
        )
        raise ApplicationException()


# READ — candidate, always own applications
@router.get("/me/")
@router.get("/me", include_in_schema=False)
async def list_my_applications(
    query: Annotated[ApplicationListQuery, Depends()],
    user: User = Depends(authenticate_user),
    use_case: ApplicationUseCases = Depends(get_application_use_cases),
) -> ApplicationListResponse:
    try:
        page = await use_case.list_my_applications(
            candidate_id=user.id, cursor=query.cursor, limit=query.limit
        )
        return ApplicationListResponse(
            data=[ApplicationResponse.from_view(v) for v in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error(
            "An error occurred in the list my applications endpoint.", exc_info=e
        )
        raise ApplicationException()
