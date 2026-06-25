from datetime import datetime, timedelta, UTC

import structlog

from src.core.security import verify_password
from src.modules.authentication.infrastructure.security import (
    generate_tokens,
    hash_tokens,
)
from src.core.config import settings
from src.modules.authentication.application.interfaces import IAuthenticationRepository
from src.modules.authentication.domain.entities import (
    AccessToken,
    RefreshToken,
    Session,
    SessionRequest,
)
from src.modules.authentication.presentation.exceptions import (
    AuthenticationException,
    SessionInvalidCredentialsException,
)
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    DomainException,
    StandardException,
)
from src.modules.user.domain.entities import User
from src.modules.shared.application.interfaces import ISharedUseCases

logger = structlog.get_logger(__name__)


class AuthenticationUseCases:
    def __init__(
        self,
        repository: IAuthenticationRepository,
        shared_service: ISharedUseCases,
    ) -> None:
        self.repository = repository
        self.shared_service = shared_service

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_refresh_token(self, refresh_expires_at: datetime) -> RefreshToken:
        """Construct a fresh RefreshToken + AccessToken pair with expiry timestamps."""
        access_expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = AccessToken(expires_at=access_expires_at)
        refresh_token = RefreshToken(
            expires_at=refresh_expires_at,
            access_token=access_token,
        )
        refresh_token.stamp_created_at()
        refresh_token.stamp_updated_at()
        refresh_token.access_token.stamp_created_at()
        return refresh_token

    async def _issue_tokens(self, session: Session) -> Session:
        """Run generate_tokens → hash_tokens and set the permission on the access token."""
        session = await generate_tokens(session)
        session = await hash_tokens(session)
        session.refresh_token.access_token.permission = session.user.role
        return session

    # ------------------------------------------------------------------
    # CREATE — login
    # ------------------------------------------------------------------

    async def login(self, request: SessionRequest) -> Session:
        """Authenticate a user and return a fully populated Session.

        If a session already exists for the same user / device / agent,
        it is refreshed in place; otherwise a new session is created.
        """
        try:
            logger.debug(
                "Initializing login use case.",
                email=str(request.user.email),
                device=request.device,
            )

            db_user: User = await self.shared_service.get_user_by_email(request.user)

            if not request.user.password or not db_user.hashed_password:
                raise SessionInvalidCredentialsException()

            if not await verify_password(
                request.user.password, db_user.hashed_password
            ):
                logger.info("Password mismatch — raising invalid credentials.")
                raise SessionInvalidCredentialsException()

            # Build a temporary Session-like object the repository can query by.
            # We only need user / device / user_agent for the lookup.
            lookup = SessionRequest(
                user=db_user,
                ip_address=request.ip_address,
                user_agent=request.user_agent,
                device=request.device,
                location=request.location,
                accept_language=request.accept_language,
                accept_encoding=request.accept_encoding,
                origin=request.origin,
                referer=request.referer,
            )

            refresh_expires_at = datetime.now(UTC) + timedelta(
                days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
            )

            existing: (
                Session | None
            ) = await self.repository.get_by_user_id_agent_and_device(lookup)

            if existing is not None:
                logger.debug(
                    "Existing session found — refreshing tokens.",
                    email=str(db_user.email),
                    device=request.device,
                )
                existing.touch()

                existing.refresh_token.expires_at = refresh_expires_at
                existing.refresh_token.stamp_updated_at()
                existing.refresh_token.rotate_jti()
                existing.refresh_token.activate()

                access_expires_at = datetime.now(UTC) + timedelta(
                    minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                )
                existing.refresh_token.access_token.expires_at = access_expires_at
                existing.refresh_token.access_token.stamp_created_at()
                existing.refresh_token.access_token.rotate_jti()
                existing.refresh_token.access_token.activate()

                session = await self._issue_tokens(existing)
                await self.repository.update(session)
            else:
                logger.debug(
                    "No existing session — creating new session.",
                    email=str(db_user.email),
                    device=request.device,
                )
                refresh_token = self._build_refresh_token(refresh_expires_at)
                now = datetime.now(UTC)

                # The repository will populate id after persist; we use a
                # temporary sentinel UUID that gets replaced on create().
                from uuid import uuid4

                new_session = Session(
                    id=uuid4(),  # replaced by DB after create()
                    user=db_user,
                    refresh_token=refresh_token,
                    ip_address=request.ip_address,
                    user_agent=request.user_agent,
                    device=request.device,
                    created_at=now,
                    last_updated_at=now,
                    location=request.location,
                    accept_language=request.accept_language,
                    accept_encoding=request.accept_encoding,
                    origin=request.origin,
                    referer=request.referer,
                )

                session = await self._issue_tokens(new_session)
                await self.repository.create(session)

            logger.debug("Login successful.", email=str(db_user.email))
            return session

        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.opt(exception=e).error("Unexpected error during login.")
            raise AuthenticationException()

    # ------------------------------------------------------------------
    # UPDATE — refresh tokens
    # ------------------------------------------------------------------

    async def refresh(self, session: Session) -> Session:
        """Issue a new access token (and rotate the refresh token) for an active session."""
        try:
            logger.debug(
                "Initializing refresh tokens use case.",
                email=str(session.user.email),
                device=session.device,
            )

            access_expires_at = datetime.now(UTC) + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )

            session.refresh_token.stamp_updated_at()
            session.refresh_token.rotate_jti()

            session.refresh_token.access_token.expires_at = access_expires_at
            session.refresh_token.access_token.stamp_created_at()
            session.refresh_token.access_token.rotate_jti()

            session = await self._issue_tokens(session)
            await self.repository.update(session)

            logger.debug("Tokens refreshed.", email=str(session.user.email))
            return session

        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.opt(exception=e).error("Unexpected error during token refresh.")
            raise AuthenticationException()

    # ------------------------------------------------------------------
    # DELETE — logout
    # ------------------------------------------------------------------

    async def logout(self, session: Session) -> None:
        """Invalidate a session and revoke its tokens."""
        try:
            logger.debug(
                "Initializing logout use case.",
                email=str(session.user.email),
                device=session.device,
            )

            session.refresh_token.stamp_updated_at()
            session.refresh_token.revoke()
            session.refresh_token.access_token.revoke()

            await self.repository.delete(session)

            logger.debug("Logout successful.", email=str(session.user.email))

        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.opt(exception=e).error("Unexpected error during logout.")
            raise AuthenticationException()
