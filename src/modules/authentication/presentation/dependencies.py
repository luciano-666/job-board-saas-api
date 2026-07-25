from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from typing import Optional

from fastapi.security import OAuth2PasswordBearer
from fastapi.requests import Request

from src.core.redis import get_redis_client
from redis.asyncio import Redis

from src.core.database import get_async_session
from src.modules.authentication.application.interfaces import (
    IAuthenticationRepository,
    IPasswordResetRepository,
)
from src.modules.authentication.application.use_cases import AuthenticationUseCases
from src.modules.authentication.infrastructure.repositories import (
    SqlAlchemySessionRepository,
    RedisPasswordResetRepository,
)
from src.modules.shared.application.use_cases import SharedUseCases
from src.modules.shared.presentation.dependencies import get_shared_use_cases
from src.modules.authentication.presentation.exceptions import (
    StandardException,
    AuthenticationException,
    AuthenticationCookiesNotProvidedException,
    UserHasNotPermissionException,
    AuthenticationTokenInvalidException,
    ModifiedTokenException,
    RefreshTokenNotProvidedException,
    RefreshTokenException,
    RefreshTokenInvalidEndpoint,
)
from src.modules.user.domain.entities import User
from src.modules.authentication.domain.entities import Session, SessionLookup
from src.core.config import settings
from src.modules.authentication.application.authorization import has_access_to_endpoint
from src.modules.authentication.infrastructure.security import (
    decode_nested_access_token,
    hash_tokens,
    decode_nested_refresh_token,
)
from src.modules.shared.application.enums import Role
# from src.modules.shared.application.interfaces import ISharedUseCases

logger = structlog.get_logger(__name__)


def get_authentication_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IAuthenticationRepository:
    return SqlAlchemySessionRepository(session=session)


def get_password_reset_repository(
    redis: Redis = Depends(get_redis_client),
) -> IPasswordResetRepository:
    return RedisPasswordResetRepository(redis=redis)


def get_authentication_use_cases(
    repository: IAuthenticationRepository = Depends(get_authentication_repository),
    shared_service: SharedUseCases = Depends(get_shared_use_cases),
    reset_repository: IPasswordResetRepository = Depends(get_password_reset_repository),
) -> AuthenticationUseCases:
    return AuthenticationUseCases(
        repository=repository,
        shared_service=shared_service,
        reset_repository=reset_repository,
    )


# BEARER TOKEN AUTHENTICATION
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/authentication/login/",
    refreshUrl="/api/v1/authentication/refresh/",
    scheme_name=settings.AUTH_BEARER_TOKEN_SCHEME_NAME,
    description=settings.AUTH_BEARER_TOKEN_SCHEME_DESCRIPTION,
    auto_error=False,
)


async def no_authentication(request: Request) -> None:
    try:
        logger.debug(
            f"No authentication required for this endpoint '{request.url.path}'."
        )

        if not await has_access_to_endpoint(request.url.path, request.method):
            logger.info(
                f"Access attempt to endpoint '{request.url.path}' with method '{request.method}' that is not in the no authentication paths. Raising authentication exception."
            )
            raise UserHasNotPermissionException()

        logger.debug(f"No authentication required for endpoint '{request.url.path}'.")
        return None
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during no authentication process.", exc_info=e)
        raise AuthenticationException()


async def authenticate_user(
    request: Request,
    repository: IAuthenticationRepository = Depends(get_authentication_repository),
    shared_service: SharedUseCases = Depends(get_shared_use_cases),
) -> User:
    try:
        logger.debug(
            f"Authenticating user for endpoint '{request.url.path}' with method '{request.method}'."
        )

        token = request.cookies.get(settings.COOKIES_ACCESS_TOKEN_KEY, None)
        device = request.cookies.get(settings.COOKIES_DEVICE_KEY, None)

        if not token or not device:
            raise AuthenticationCookiesNotProvidedException()

        session: Session = await decode_nested_access_token(token)
        session: Session = await hash_tokens(session)

        session.device = device
        session.user_agent = (request.headers.get("user-agent") or "").lower().strip()

        db_session: Optional[Session] = await repository.get_access_token_by_session(
            SessionLookup.from_access_session(session)
        )

        if (
            db_session is None
            or db_session.refresh_token is None
            or db_session.refresh_token.access_token is None
        ):
            logger.info(
                f"Access token with hashed jti '{session.refresh_token.access_token.hashed_jti}' not found in database. Raising authentication token exception."
            )
            raise AuthenticationTokenInvalidException()

        session: Session = db_session

        if not session.user.role == session.refresh_token.access_token.permission:
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' with method '{request.method}' with modified role. Raising authentication exception."
            )
            raise ModifiedTokenException()

        if not await has_access_to_endpoint(
            request.url.path, request.method, session.user.role
        ):
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' with method '{request.method}' that is not in the allowed paths. Raising authentication exception."
            )
            raise UserHasNotPermissionException()

        logger.debug(f"User '{session.user.email}' authenticated successfully.")
        user: User | None = await shared_service.get_user_by_id(session.user.id)
        if user is None:
            logger.info(
                f"User with id '{session.user.id}' not found during authentication. Raising exception."
            )
            raise AuthenticationTokenInvalidException()
        return user
    except StandardException:
        raise
    except Exception as e:
        logger.error(
            "An error occurred during user authentication process.", exc_info=e
        )
        raise AuthenticationException()


async def authenticate_employer(
    request: Request,
    repository: IAuthenticationRepository = Depends(get_authentication_repository),
    shared_service: SharedUseCases = Depends(get_shared_use_cases),
) -> User:
    try:
        logger.debug(
            f"Authenticating employer for endpoint '{request.url.path}' with method '{request.method}'."
        )

        token = request.cookies.get(settings.COOKIES_ACCESS_TOKEN_KEY, None)
        device = request.cookies.get(settings.COOKIES_DEVICE_KEY, None)

        if not token or not device:
            raise AuthenticationCookiesNotProvidedException()

        session: Session = await decode_nested_access_token(token)
        session: Session = await hash_tokens(session)

        session.device = device
        session.user_agent = (request.headers.get("user-agent") or "").lower().strip()

        db_session: Optional[Session] = await repository.get_access_token_by_session(
            SessionLookup.from_access_session(session)
        )

        if (
            db_session is None
            or db_session.refresh_token is None
            or db_session.refresh_token.access_token is None
        ):
            raise AuthenticationTokenInvalidException()

        session: Session = db_session

        if not session.user.role == session.refresh_token.access_token.permission:
            raise ModifiedTokenException()

        if not session.refresh_token.access_token.permission == Role.EMPLOYER:
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' "
                f"with method '{request.method}' with insufficient permissions (not employer)."
            )
            raise UserHasNotPermissionException()

        if not await has_access_to_endpoint(
            request.url.path,
            request.method,
            session.refresh_token.access_token.permission,
        ):
            raise UserHasNotPermissionException()

        logger.debug(f"Employer '{session.user.email}' authenticated successfully.")
        user: User | None = await shared_service.get_user_by_id(session.user.id)
        if user is None:
            raise AuthenticationTokenInvalidException()

        return user
    except StandardException:
        raise
    except Exception as e:
        logger.error(
            "An error occurred during employer authentication process.", exc_info=e
        )
        raise AuthenticationException()


async def authenticate_admin(
    request: Request,
    repository: IAuthenticationRepository = Depends(get_authentication_repository),
    shared_service: SharedUseCases = Depends(get_shared_use_cases),
) -> User:
    try:
        logger.debug(
            f"Authenticating admin for endpoint '{request.url.path}' with method '{request.method}'."
        )

        token = request.cookies.get(settings.COOKIES_ACCESS_TOKEN_KEY, None)
        device = request.cookies.get(settings.COOKIES_DEVICE_KEY, None)

        if not token or not device:
            raise AuthenticationCookiesNotProvidedException()

        session: Session = await decode_nested_access_token(token)
        session: Session = await hash_tokens(session)

        session.device = device
        session.user_agent = (request.headers.get("user-agent") or "").lower().strip()

        db_session: Optional[Session] = await repository.get_access_token_by_session(
            SessionLookup.from_access_session(session)
        )

        if (
            db_session is None
            or db_session.refresh_token is None
            or db_session.refresh_token.access_token is None
        ):
            logger.info(
                f"Access token with hashed jti '{session.refresh_token.access_token.hashed_jti}' not found in database. Raising authentication token exception."
            )
            raise AuthenticationTokenInvalidException()

        session: Session = db_session

        if not session.user.role == session.refresh_token.access_token.permission:
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' with method '{request.method}' with modified role. Raising authentication exception."
            )
            raise ModifiedTokenException()

        if not session.refresh_token.access_token.permission == Role.ADMIN:
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' with method '{request.method}' with insufficient permissions. Raising authentication exception."
            )
            raise UserHasNotPermissionException()

        if not await has_access_to_endpoint(
            request.url.path,
            request.method,
            session.refresh_token.access_token.permission,
        ):
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' with method '{request.method}' that is not in the allowed paths. Raising authentication exception."
            )
            raise UserHasNotPermissionException()

        logger.debug(f"Admin '{session.user.email}' authenticated successfully.")
        user: User | None = await shared_service.get_user_by_id(session.user.id)
        if user is None:
            logger.info(
                f"User with id '{session.user.id}' not found during authentication. Raising exception."
            )
            raise AuthenticationTokenInvalidException()

        return user
    except StandardException:
        raise
    except Exception as e:
        logger.error(
            "An error occurred during admin authentication process.", exc_info=e
        )
        raise AuthenticationException()


async def authenticate_refresh(
    request: Request,
    repository: IAuthenticationRepository = Depends(get_authentication_repository),
) -> Session:
    try:
        logger.debug("Authenticating access for refresh token endpoint.")

        if not request.url.path.endswith("/api/v1/authentication/refresh/"):
            logger.info(
                f"Access attempt to endpoint '{request.url.path}' with method '{request.method}' that is not the refresh token endpoint. Raising authentication exception."
            )
            raise RefreshTokenInvalidEndpoint()

        token = request.cookies.get(settings.COOKIES_REFRESH_TOKEN_KEY, None)
        device = request.cookies.get(settings.COOKIES_DEVICE_KEY, None)

        if not token or not device:
            raise RefreshTokenNotProvidedException()

        session: Session = await decode_nested_refresh_token(token)
        session: Session = await hash_tokens(session)

        session.device = device
        session.user_agent = (request.headers.get("user-agent") or "").lower().strip()

        db_session: Optional[Session] = await repository.get_refresh_token_by_session(
            SessionLookup.from_refresh_session(session)
        )

        if (
            db_session is None
            or db_session.refresh_token is None
            or db_session.refresh_token.access_token is None
        ):
            logger.info(
                f"Refresh token with hashed jti '{session.refresh_token.access_token.hashed_jti}' not found in database. Raising authentication token exception."
            )
            raise AuthenticationTokenInvalidException()

        logger.debug(
            f"Refresh token authenticated successfully for user '{session.user.email}'."
        )
        return db_session
    except StandardException:
        raise
    except Exception as e:
        logger.error(
            "An error occurred during admin authentication process.", exc_info=e
        )
        raise RefreshTokenException()


async def authenticate_logout(
    request: Request,
    repository: IAuthenticationRepository = Depends(get_authentication_repository),
) -> Session:
    try:
        logger.debug("Authenticating access for logout endpoint.")

        if not request.url.path.endswith("/api/v1/authentication/logout/"):
            logger.info(
                f"Access attempt to endpoint '{request.url.path}' with method '{request.method}' that is not the refresh token endpoint. Raising authentication exception."
            )
            raise RefreshTokenInvalidEndpoint()

        token = request.cookies.get(settings.COOKIES_ACCESS_TOKEN_KEY, None)
        device = request.cookies.get(settings.COOKIES_DEVICE_KEY, None)

        if not token or not device:
            raise AuthenticationCookiesNotProvidedException()

        session: Session = await decode_nested_access_token(token)
        session: Session = await hash_tokens(session)

        session.device = device
        session.user_agent = (request.headers.get("user-agent") or "").lower().strip()

        db_session: Optional[Session] = await repository.get_access_token_by_session(
            SessionLookup.from_access_session(session)
        )

        if (
            db_session is None
            or db_session.refresh_token is None
            or db_session.refresh_token.access_token is None
        ):
            logger.info(
                f"Access token with hashed jti '{session.refresh_token.access_token.hashed_jti}' not found in database. Raising authentication token exception."
            )
            raise AuthenticationTokenInvalidException()

        session: Session = db_session

        if not session.user.role == session.refresh_token.access_token.permission:
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' with method '{request.method}' with modified role. Raising authentication exception."
            )
            raise ModifiedTokenException()

        if not await has_access_to_endpoint(
            request.url.path, request.method, session.user.role
        ):
            logger.info(
                f"User '{session.user.email}' attempted to access endpoint '{request.url.path}' with method '{request.method}' that is not in the allowed paths. Raising authentication exception."
            )
            raise UserHasNotPermissionException()

        logger.debug(f"User '{session.user.email}' authenticated successfully.")
        return session
    except StandardException:
        raise
    except Exception as e:
        logger.error(
            "An error occurred during admin authentication process.", exc_info=e
        )
        raise RefreshTokenException()
