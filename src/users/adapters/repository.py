from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.users.domain.model import User
from src.users.adapters.orm import UserORM


class SqlAlchemyUserRepository:
    """Persist user aggregates with SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: SQLAlchemy session owned by the unit of work.
        """
        self.session = session
        self.seen: list[User] = []

    def add(self, user: User) -> None:
        """Persist a new user."""
        self.session.add(self._to_record(user))
        self.seen.append(user)

    async def get(self, id: UUID) -> User | None:
        """Return a user by identity."""
        return self._remember(await self.session.get(UserORM, id))

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by normalized email address."""
        record = await self.session.scalar(
            select(UserORM).where(UserORM.email == email.strip().lower())
        )
        return self._remember(record=record)

    def _remember(self, record: UserORM | None) -> User | None:
        """Translate and track a loaded aggregate."""
        if record is None:
            return None
        user = self._to_domain(record=record)
        self.seen.append(user)
        return user

    @staticmethod
    def _to_record(user: User) -> UserORM:
        """Translate a domain aggregate into a persistence record."""
        return UserORM(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
        )

    @staticmethod
    def _to_domain(record: UserORM) -> User:
        """Translate a persistence record into a domain aggregate."""
        return User(
            email=record.email,
            hashed_password=record.hashed_password,
            role=record.role,
            id=record.id,
            full_name=record.full_name,
            is_active=record.is_active,
        )
