from typing import Optional
from uuid import UUID
from redis.asyncio import Redis

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.modules.authentication.application.interfaces import IAuthenticationRepository
from src.modules.authentication.domain.entities import (
    Session,
    SessionRequest,
    SessionLookup,
)

from src.modules.authentication.infrastructure.models import (
    SessionModel,
    RefreshTokenModel,
    AccessTokenModel,
)
from src.modules.authentication.presentation.exceptions import AuthenticationException
from src.modules.shared.presentation.exceptions import StandardException

logger = structlog.get_logger(__name__)


class SqlAlchemySessionRepository(IAuthenticationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # CREATE
    async def create(self, session: Session) -> None:
        try:
            logger.info(
                f"Creating session for user {session.user.email.__str__()} with device {session.device} and user agent {session.user_agent} in database."
            )

            session_model = SessionModel.from_entity(session)

            self.session.add(session_model)
            await self.session.flush()

            logger.info(
                f"Session created successfully for user {session.user.email.__str__()} with device {session.device} and user agent {session.user_agent} in database."
            )
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the create session repository.", exc_info=e
            )
            raise AuthenticationException()

    # READ
    async def get_by_user_id_agent_and_device(
        self, session: SessionRequest
    ) -> Optional[Session]:
        try:
            logger.info(
                f"Getting session by user id, agent and device for user {session.user.email} with device {session.device} and user agent {session.user_agent} from database."
            )

            statement = (
                select(SessionModel)
                .options(
                    joinedload(SessionModel.user),
                    joinedload(SessionModel.refresh_token).joinedload(
                        RefreshTokenModel.access_token
                    ),
                )
                .where(
                    SessionModel.user_id == session.user.id,
                    SessionModel.user_agent == session.user_agent,
                    SessionModel.device == session.device,
                    SessionModel.blacklisted.is_(False),
                )
            )

            result = await self.session.execute(statement)
            session_model: Optional[SessionModel] = result.scalar_one_or_none()

            if session_model is None:
                logger.info(
                    f"No session found for user {session.user.email} with the given user agent and device."
                )
                return None

            found_session = session_model.to_entity()

            logger.info(
                f"Session retrieved successfully for user {session.user.email} with device {session.device} and user agent {session.user_agent} from database."
            )
            return found_session
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the get session by user agent and device repository.",
                exc_info=e,
            )
            raise

    async def get_access_token_by_session(
        self,
        lookup: SessionLookup,
    ) -> Optional[Session]:
        try:
            logger.info(
                "Getting session by access token hashed_jti and device from database."
            )

            conditions = [
                AccessTokenModel.hashed_jti == lookup.hashed_jti,
                SessionModel.user_agent == lookup.user_agent,
                SessionModel.user_id == lookup.user_id,
                AccessTokenModel.revoked.is_(False),
                RefreshTokenModel.revoked.is_(False),
                SessionModel.blacklisted.is_(False),
            ]

            if lookup.device is not None:
                conditions.append(SessionModel.device == lookup.device)

            statement = (
                select(SessionModel)
                .join(SessionModel.refresh_token)
                .join(RefreshTokenModel.access_token)
                .options(
                    joinedload(SessionModel.user),
                    joinedload(SessionModel.refresh_token).joinedload(
                        RefreshTokenModel.access_token
                    ),
                )
                .where(*conditions)
            )

            result = await self.session.execute(statement)
            session_model: Optional[SessionModel] = result.scalar_one_or_none()

            if session_model is None:
                logger.info(
                    "No session found for the given access token hashed_jti and device."
                )
                return None

            found_session = session_model.to_entity()

            logger.info(
                f"Session retrieved successfully for access token with ID {found_session.refresh_token.access_token.id} and device {found_session.device}."
            )
            return found_session
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the get access token by hashed_jti repository.",
                exc_info=e,
            )
            raise

    async def get_refresh_token_by_session(
        self,
        lookup: SessionLookup,
    ) -> Optional[Session]:
        try:
            logger.info(
                "Getting session by refresh token hashed_jti and device from database."
            )

            conditions = [
                RefreshTokenModel.hashed_jti == lookup.hashed_jti,
                SessionModel.user_agent == lookup.user_agent,
                SessionModel.user_id == lookup.user_id,
                RefreshTokenModel.revoked.is_(False),
                SessionModel.blacklisted.is_(False),
            ]

            if lookup.device is not None:
                conditions.append(SessionModel.device == lookup.device)

            statement = (
                select(SessionModel)
                .join(SessionModel.refresh_token)
                .options(
                    joinedload(SessionModel.user),
                    joinedload(SessionModel.refresh_token).joinedload(
                        RefreshTokenModel.access_token
                    ),
                )
                .where(*conditions)
            )

            result = await self.session.execute(statement)
            session_model: Optional[SessionModel] = result.scalar_one_or_none()

            if session_model is None:
                logger.info(
                    "No session found for the given refresh token hashed_jti and device."
                )
                return None

            found_session = session_model.to_entity()

            logger.info(
                f"Session retrieved successfully for refresh token with ID {found_session.id} and device {found_session.device}."
            )
            return found_session
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the get access token by hashed_jti repository.",
                exc_info=e,
            )
            raise

    # UPDATE
    async def update(self, session: Session) -> None:
        try:
            logger.info(
                f"Updating session {session.id} for user {session.user.email.__str__()} "
                f"with device {session.device} and user agent {session.user_agent} in database."
            )

            session_model = SessionModel.from_entity(session)

            await self.session.merge(session_model)
            await self.session.flush()

            logger.info(
                f"Session {session.id} updated successfully for user {session.user.email.__str__()} "
                f"with device {session.device} and user agent {session.user_agent} in database."
            )
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the update session repository.", exc_info=e
            )
            raise AuthenticationException()

    # DELETE
    async def delete(self, session: Session) -> None:
        try:
            logger.info(
                f"Revoking session {session.id} for user {session.user.email.__str__()} "
                f"with device {session.device} and user agent {session.user_agent} in database."
            )

            session.refresh_token.revoke()
            session.refresh_token.access_token.revoke()

            session_model = SessionModel.from_entity(session)

            await self.session.merge(session_model)
            await self.session.flush()

            logger.info(
                f"Session {session.id} revoked successfully for user {session.user.email.__str__()} "
                f"with device {session.device} and user agent {session.user_agent} in database."
            )
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "An error occurred in the update session repository.", exc_info=e
            )
            raise AuthenticationException()


class RedisPasswordResetRepository:
    """Stores password-reset tokens in Redis, keyed by hashed token value."""

    _KEY_PREFIX = "password_reset:"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def store_reset_token(
        self, hashed_token: str, user_id: UUID, ttl_seconds: int
    ) -> None:
        try:
            await self.redis.set(
                f"{self._KEY_PREFIX}{hashed_token}", str(user_id), ex=ttl_seconds
            )
        except Exception as e:
            logger.error(
                "An error occurred while storing the password reset token.",
                exc_info=e,
            )
            raise AuthenticationException()

    async def get_user_id_by_reset_token(self, hashed_token: str) -> UUID | None:
        try:
            value = await self.redis.get(f"{self._KEY_PREFIX}{hashed_token}")
            if value is None:
                return None

            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return UUID(value)
        except Exception as e:
            logger.error(
                "An error occurred while retrieving the password reset token.",
                exc_info=e,
            )
            raise AuthenticationException()

    async def delete_reset_token(self, hashed_token: str) -> None:
        try:
            await self.redis.delete(f"{self._KEY_PREFIX}{hashed_token}")
        except Exception as e:
            logger.error(
                "An error occurred while deleting the password reset token.",
                exc_info=e,
            )
            raise AuthenticationException()
