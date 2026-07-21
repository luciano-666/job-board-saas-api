import structlog
from uuid import UUID
from datetime import date

from src.modules.user.application.interfaces import IUserRepository
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Phone
from src.core.security import hash_password
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainException,
)
from src.modules.user.presentation.exceptions import (
    UserEmailAlreadyExistsException,
    UserException,
    UserEmailNotFoundException,
)
from src.modules.shared.application.interfaces import ISharedUseCases
from src.modules.user.application.enums import Gender

logger = structlog.get_logger(__name__)


class UserUseCases:
    def __init__(
        self, repository: IUserRepository, shared_service: ISharedUseCases
    ) -> None:
        self.repository = repository
        self.shared_service = shared_service

    # CREATE
    async def create(self, user: User) -> User:
        try:
            logger.debug(f"Initializing create user use case with user: {user.email}.")

            if await self.repository.exists_by_email(user.email):
                logger.info(
                    f"User with email {user.email} already exists. Raising exception."
                )
                raise UserEmailAlreadyExistsException(email=user.email.__str__())

            user.hashed_password = (
                await hash_password(user.password) if user.password else None
            )
            await self.repository.create(user)

            logger.debug(f"User {user.email} created successfully.")
            return user
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the create user use case.",
                exc_info=e,
            )
            raise UserException()

    # UPDATE
    async def suspend(self, id: UUID) -> User:
        try:
            logger.debug(f"Initializing suspend user use case for id: {id}.")

            user = await self.repository.get_by_id_any_status(id)
            if user is None:
                raise UserEmailNotFoundException(email=str(id))

            user.suspend()
            await self.repository.update(user)

            logger.debug(f"User {id} suspended successfully.")
            return user
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An error occurred during the suspend user use case.", exc_info=e
            )
            raise UserException()

    async def activate(self, id: UUID) -> User:
        try:
            logger.debug(f"Initializing activate user use case for id: {id}.")

            user = await self.repository.get_by_id_any_status(id)
            if user is None:
                raise UserEmailNotFoundException(email=str(id))

            user.activate()
            await self.repository.update(user)

            logger.debug(f"User {id} activated successfully.")
            return user
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An error occurred during the activate user use case.", exc_info=e
            )
            raise UserException()

    # READ
    async def me(self, user: User) -> User:
        try:
            logger.debug(
                f"Initializing get user use case for user: {user.email.__str__()}."
            )

            db_user: User | None = await self.shared_service.get_user_by_id(user.id)

            if db_user is None:
                logger.info(
                    f"User with email {user.email} not found. Raising exception."
                )
                raise UserEmailNotFoundException(email=user.email.__str__())

            logger.debug(f"User {user.email.__str__()} retrieved successfully.")
            return db_user
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error("An error occurred in the me use case.", exc_info=e)
            raise UserException()

    # ------------------------------------------------------------------
    # UPDATE — profile user
    # ------------------------------------------------------------------
    async def update_profile(
        self,
        id: UUID,
        *,
        name: Name,
        gender: Gender | None,
        birthdate: date | None,
        phone: Phone | None,
    ) -> User:
        try:
            logger.debug(f"Initializing update profile use case for id: {id}.")
            user = await self.repository.get_by_id(id)
            if user is None:
                raise UserEmailNotFoundException(email=str(id))

            user.update_profile(
                name=name, gender=gender, birthdate=birthdate, phone=phone
            )
            await self.repository.update(user)

            logger.debug(f"Profile for user {id} updated successfully.")
            return user
        except StandardException:
            raise
        except DomainError as e:
            raise DomainException(e)
        except Exception as e:
            logger.error(
                "An error occurred during the update profile use case.", exc_info=e
            )
            raise UserException()
