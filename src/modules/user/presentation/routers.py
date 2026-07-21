from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
import structlog

from src.modules.authentication.presentation.dependencies import (
    authenticate_user,
    authenticate_admin,
)
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainError,
    DomainException,
)
from src.modules.user.application.use_cases import UserUseCases
from src.modules.user.domain.entities import User
from src.modules.user.presentation.dependencies import get_user_use_cases
from src.modules.user.presentation.docs import (
    router_docs,
    create_docs,
    me_docs,
    suspend_docs,
    activate_docs,
    update_me_docs,
)
from src.modules.user.presentation.exceptions import UserException
from src.modules.user.presentation.schemas import (
    CreateRequest,
    CreateResponse,
    MeResponse,
    SuspendResponse,
    ActivateResponse,
    UpdateProfileRequest,
)
from src.modules.user.domain.value_objects import Phone

logger = structlog.get_logger(__name__)

router = APIRouter(**router_docs)


# CREATE — admin only
@router.post("/", **create_docs)
@router.post("", include_in_schema=False)
async def create(
    payload: CreateRequest,
    _: Annotated[None, Depends(authenticate_admin)],
    use_case: UserUseCases = Depends(get_user_use_cases),
) -> CreateResponse:
    try:
        user = payload.to_entity()
        await use_case.create(user)
        return CreateResponse()
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the create user endpoint.", exc_info=e)
        raise UserException()


# READ
@router.get("/me/", **me_docs)
@router.get("/me", include_in_schema=False)
async def me(
    user: User = Depends(authenticate_user),
    use_case: UserUseCases = Depends(get_user_use_cases),
) -> MeResponse:
    try:
        result = await use_case.me(user)
        return MeResponse.from_entity(result)
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the me endpoint.", exc_info=e)
        raise UserException()


@router.patch("/me/", **update_me_docs)
@router.patch("/me", include_in_schema=False)
async def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(authenticate_user),
    use_case: UserUseCases = Depends(get_user_use_cases),
) -> MeResponse:
    try:
        payload.apply_to(
            user
        )  # validates + builds merged value objects on `user` in-memory
        phone = user.phone if isinstance(user.phone, Phone) else None
        result = await use_case.update_profile(
            user.id,
            name=user.name,
            gender=user.gender,
            birthdate=user.birthdate,
            phone=phone,
        )
        return MeResponse.from_entity(result)
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the update_me endpoint.", exc_info=e)
        raise UserException()


@router.patch("/{user_id}/suspend/", **suspend_docs)
@router.patch("/{user_id}/suspend", include_in_schema=False)
async def suspend(
    user_id: UUID,
    _: Annotated[None, Depends(authenticate_admin)],
    use_case: UserUseCases = Depends(get_user_use_cases),
) -> SuspendResponse:
    try:
        await use_case.suspend(user_id)
        return SuspendResponse()
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the suspend user endpoint.", exc_info=e)
        raise UserException()


@router.patch("/{user_id}/activate/", **activate_docs)
@router.patch("/{user_id}/activate", include_in_schema=False)
async def activate(
    user_id: UUID,
    _: Annotated[None, Depends(authenticate_admin)],
    use_case: UserUseCases = Depends(get_user_use_cases),
) -> ActivateResponse:
    try:
        await use_case.activate(user_id)
        return ActivateResponse()
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the activate endpoint.", exc_info=e)
        raise UserException()
