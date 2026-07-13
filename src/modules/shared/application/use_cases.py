import structlog
from uuid import UUID

from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import (
    StandardException,
    DomainException,
)
from src.modules.user.application.interfaces import IUserRepository
from src.modules.user.domain.entities import User
from src.modules.user.presentation.exceptions import (
    UserException,
    UserEmailNotFoundException,
)

logger = structlog.get_logger(__name__)


class SharedUseCases:
    def __init__(
        self,
        user_repository: IUserRepository,
    ) -> None:
        self.user_repository = user_repository
        self._raise_exceptions = True

    @property
    def raise_exceptions(self) -> bool:
        return self._raise_exceptions

    def enable_exceptions(self) -> None:
        self._raise_exceptions = True

    def disable_exceptions(self) -> None:
        self._raise_exceptions = False

    async def get_user_by_id(self, id: UUID) -> User | None:
        try:
            logger.debug(f"Initializing get user by id use case for id: {id}.")

            db_user = await self.user_repository.get_by_id(id)

            if db_user is None and self._raise_exceptions:
                logger.info(f"User with id {id} not found. Raising exception.")
                raise UserEmailNotFoundException(email=str(id))

            logger.debug(f"User {id} retrieved from database successfully.")
            return db_user
        except StandardException:
            if self._raise_exceptions:
                raise
            return None
        except DomainError as e:
            if self._raise_exceptions:
                raise DomainException(e)
            return None
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the get user by id use case.",
                exc_info=e,
            )
            if self._raise_exceptions:
                raise UserException()
            return None

    async def get_user_by_email(self, email: str) -> User:
        """Retrieve an active user by email, raising if not found."""
        logger.debug(f"Initializing get user by email use case for user: {email}.")

        db_user = await self.user_repository.get_by_email(email)

        if db_user is None:
            logger.info(f"User with email {email} not found. Raising exception.")
            raise UserEmailNotFoundException(email=email.__str__())

        logger.debug(f"User {email} retrieved from database successfully.")
        return db_user
