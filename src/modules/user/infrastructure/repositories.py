from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.presentation.exceptions import StandardException
from src.modules.user.application.interfaces import IUserRepository
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Email
from src.modules.user.infrastructure.models import UserModel
from src.modules.user.presentation.exceptions import UserException

logger = structlog.get_logger(__name__)


class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # CREATE
    async def create(self, user: User) -> None:
        try:
            logger.info(f"Creating user {user.email.__str__()} in database.")

            db_user = UserModel.from_entity(user)

            self.session.add(db_user)
            await self.session.flush()

            logger.info(
                f"User {user.email.__str__()} created successfully in database."
            )
            return None
        except StandardException:
            raise
        except Exception as e:
            logger.error("An error occurred in the create user repository.", exc_info=e)
            raise UserException()

    # READ
    async def exists_by_email(self, email: Email | str) -> bool:
        try:
            logger.info(f"Checking if user {email.__str__()} exists in database.")

            statement = (
                select(UserModel.id)
                .where(
                    UserModel.email == str(email),
                    UserModel.is_active.is_(True),
                )
                .limit(1)
            )

            result = await self.session.scalar(statement)
            exists = result is not None

            logger.info(
                f"Existence check for user {email.__str__()} completed. Exists: {exists}."
            )
            return exists
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during the existence check of a user in the database.",
                exc_info=e,
            )
            raise UserException()

    async def get_by_id(self, id: UUID) -> Optional[User]:
        try:
            logger.info(f"Retrieving user with id {id} from database.")

            statement = select(UserModel).where(
                UserModel.id == id, UserModel.is_active.is_(True)
            )

            result = await self.session.execute(statement)
            user_model: Optional[UserModel] = result.scalar_one_or_none()

            if user_model is None:
                logger.info(f"User with id {id} not found in database.")
                return None

            user = UserModel.to_entity(user_model)

            logger.info(f"User with id {user.id} retrieved successfully from database.")
            return user
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during the get user by id repository.", exc_info=e
            )
            raise UserException()

    async def get_by_email(self, email: Email | str) -> Optional[User]:
        try:
            logger.info(f"Getting user {email.__str__()} from database.")

            statement = select(UserModel).where(
                UserModel.email == str(email), UserModel.is_active
            )

            result = await self.session.execute(statement)
            user_model: Optional[UserModel] = result.scalar_one_or_none()

            if user_model is None:
                logger.info(
                    f"User with email {email.__str__()} not found in database. Returning None."
                )
                return None

            user = UserModel.to_entity(user_model)

            logger.info(f"User {user.email} retrieved successfully.")
            return user
        except StandardException:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during the get by email of a user in the database.",
                exc_info=e,
            )
            raise UserException()
