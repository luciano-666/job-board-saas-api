from typing import Annotated

from fastapi import APIRouter, Depends
import structlog

from src.modules.authentication.presentation.dependencies import (
    authenticate_user,
    no_authentication,
)
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainError,
    DomainException,
)
from src.modules.user.application.use_cases import UserUseCases
from src.modules.user.domain.entities import User
from src.modules.user.presentation.dependencies import get_user_use_cases
from src.modules.user.presentation.docs import router_docs, create_docs, me_docs
from src.modules.user.presentation.exceptions import UserException
from src.modules.user.presentation.schemas import (
    CreateRequest,
    CreateResponse,
    MeResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(**router_docs)


# CREATE
@router.post("/", **create_docs)
@router.post("", include_in_schema=False)
async def create(
    payload: CreateRequest,
    _: Annotated[None, Depends(no_authentication)],
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
        logger.opt(exception=e).error("An error occurred in the create user endpoint.")
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
        logger.opt(exception=e).error("An error occurred in the me endpoint.")
        raise UserException()
