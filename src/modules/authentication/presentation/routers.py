from typing import Annotated
from http import HTTPStatus

from fastapi import APIRouter, Depends, Request, Response, Security
from fastapi.security import OAuth2PasswordRequestFormStrict
import structlog

from src.modules.authentication.presentation.dependencies import (
    no_authentication,
    authenticate_refresh,
    authenticate_logout,
)
from src.core.config import settings
from src.modules.authentication.application.use_cases import AuthenticationUseCases
from src.modules.authentication.domain.entities import Session

from src.modules.authentication.presentation.dependencies import (
    get_authentication_use_cases,
)
from src.modules.authentication.presentation.docs import (
    router_docs,
    login_docs,
    refresh_docs,
    logout_docs,
    register_docs,
)
from src.modules.authentication.presentation.exceptions import AuthenticationException
from src.modules.authentication.presentation.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    LogoutResponse,
    RegisterRequest,
    PasswordResetConfirmSchema,
    PasswordResetConfirmResponse,
    PasswordResetRequestResponse,
    PasswordResetRequestSchema,
)
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainException,
)
from src.modules.user.presentation.exceptions import CookieManagementException
from src.modules.user.application.use_cases import UserUseCases
from src.modules.user.presentation.dependencies import get_user_use_cases
from src.modules.user.presentation.schemas import CreateResponse
from src.modules.user.presentation.exceptions import UserException

logger = structlog.get_logger(__name__)

router = APIRouter(**router_docs)


async def set_cookies(response: Response, session: Session) -> None:
    try:
        if session.refresh_token.access_token.token is None:
            raise ValueError("Access token must be generated before setting cookies.")

        if session.refresh_token.token is None:
            raise ValueError("Refresh token must be generated before setting cookies.")

        response.set_cookie(
            key=settings.COOKIES_TOKEN_TYPE_KEY,
            value=session.token_type,
            max_age=settings.COOKIES_ACCESS_TOKEN_MAX_AGE,
            path=settings.COOKIES_ACCESS_TOKEN_PATH,
            domain=settings.COOKIES_DOMAIN,
            secure=not settings.APPLICATION_ENVIRONMENT_DEBUG,
            httponly=True,
            samesite="lax",
        )

        response.set_cookie(
            key=settings.COOKIES_ACCESS_TOKEN_KEY,
            value=session.refresh_token.access_token.token,
            max_age=settings.COOKIES_ACCESS_TOKEN_MAX_AGE,
            path=settings.COOKIES_ACCESS_TOKEN_PATH,
            domain=settings.COOKIES_DOMAIN,
            secure=not settings.APPLICATION_ENVIRONMENT_DEBUG,
            httponly=True,
            samesite="lax",
        )

        response.set_cookie(
            key=settings.COOKIES_REFRESH_TOKEN_KEY,
            value=session.refresh_token.token,
            max_age=settings.COOKIES_REFRESH_TOKEN_MAX_AGE,
            path=settings.COOKIES_REFRESH_TOKEN_PATH,
            domain=settings.COOKIES_DOMAIN,
            secure=not settings.APPLICATION_ENVIRONMENT_DEBUG,
            httponly=True,
            samesite="strict",
        )
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred in the set_cookies function.", exc_info=e)
        raise CookieManagementException()


async def delete_cookies(response: Response) -> None:
    try:
        response.delete_cookie(
            key=settings.COOKIES_TOKEN_TYPE_KEY,
            path=settings.COOKIES_ACCESS_TOKEN_PATH,
            domain=settings.COOKIES_DOMAIN,
            secure=not settings.APPLICATION_ENVIRONMENT_DEBUG,
            httponly=True,
            samesite="lax",
        )

        response.delete_cookie(
            key=settings.COOKIES_ACCESS_TOKEN_KEY,
            path=settings.COOKIES_ACCESS_TOKEN_PATH,
            domain=settings.COOKIES_DOMAIN,
            secure=not settings.APPLICATION_ENVIRONMENT_DEBUG,
            httponly=True,
            samesite="lax",
        )

        response.delete_cookie(
            key=settings.COOKIES_REFRESH_TOKEN_KEY,
            path=settings.COOKIES_REFRESH_TOKEN_PATH,
            domain=settings.COOKIES_DOMAIN,
            secure=not settings.APPLICATION_ENVIRONMENT_DEBUG,
            httponly=True,
            samesite="lax",
        )
    except Exception as e:
        logger.error("An error occurred in the delete_cookies function.", exc_info=e)
        raise CookieManagementException()


# CREATE
@router.post("/login/", **login_docs)
@router.post("/login", include_in_schema=False)
async def login(
    request: Request,
    response: Response,
    _: Annotated[None, Depends(no_authentication)],
    form_data: OAuth2PasswordRequestFormStrict = Depends(),
    use_case: AuthenticationUseCases = Depends(get_authentication_use_cases),
) -> LoginResponse:
    try:
        credentials = LoginRequest.to_credentials(form_data)
        metadata = LoginRequest.extract_metadata(request)

        session = await use_case.login(credentials, metadata)

        await set_cookies(response, session)

        return LoginResponse()
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the login endpoint.", exc_info=e)
        raise AuthenticationException()


# UPDATE
@router.patch("/refresh/", **refresh_docs)
@router.patch("/refresh", include_in_schema=False)
async def refresh(
    response: Response,
    session: Session = Depends(authenticate_refresh),
    use_case: AuthenticationUseCases = Depends(get_authentication_use_cases),
) -> RefreshResponse:
    try:
        refreshed_session = await use_case.refresh(session)

        await set_cookies(response, refreshed_session)

        return RefreshResponse()
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the refresh endpoint.", exc_info=e)
        raise AuthenticationException()


# DELETE
@router.delete("/logout/", **logout_docs)
@router.delete("/logout", include_in_schema=False)
async def logout(
    response: Response,
    session: Session = Depends(authenticate_logout),
    use_case: AuthenticationUseCases = Depends(get_authentication_use_cases),
) -> LogoutResponse:
    try:
        await use_case.logout(session)
        await delete_cookies(response)

        return LogoutResponse()
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error("An error occurred in the logout endpoint.", exc_info=e)
        raise AuthenticationException()


# CREATE — public registration
@router.post("/register/", **register_docs)
@router.post("/register", include_in_schema=False)
async def register(
    payload: RegisterRequest,
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
        logger.error("An error occurred in the register endpoint.", exc_info=e)
        raise UserException()


@router.post(
    "/password-reset/request/",
    status_code=HTTPStatus.OK,
    dependencies=[Security(no_authentication)],
)
@router.post("/password-reset/request", include_in_schema=False)
async def request_password_reset(
    payload: PasswordResetRequestSchema,
    use_case: AuthenticationUseCases = Depends(get_authentication_use_cases),
) -> PasswordResetRequestResponse:
    try:
        await use_case.request_password_reset(payload.email)
        return PasswordResetRequestResponse()
    except StandardException:
        raise
    except Exception as e:
        logger.error(
            "An error occurred in the password reset request endpoint.", exc_info=e
        )
        raise AuthenticationException()


@router.post(
    "/password-reset/confirm/",
    status_code=HTTPStatus.OK,
    dependencies=[Security(no_authentication)],
)
@router.post("/password-reset/confirm", include_in_schema=False)
async def confirm_password_reset(
    payload: PasswordResetConfirmSchema,
    use_case: AuthenticationUseCases = Depends(get_authentication_use_cases),
) -> PasswordResetConfirmResponse:
    try:
        await use_case.confirm_password_reset(payload.token, payload.new_password)
        return PasswordResetConfirmResponse()
    except StandardException:
        raise
    except DomainError as e:
        raise DomainException(e)
    except Exception as e:
        logger.error(
            "An error occurred in the password reset confirm endpoint.", exc_info=e
        )
        raise AuthenticationException()
