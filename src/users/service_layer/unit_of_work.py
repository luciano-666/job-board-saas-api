from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from src.shared.service_layer.unit_of_work import AbstractUnitOfWork, IntegrityConflict
from src.users.adapters.repository import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """Manage a SQLAlchemy session as one atomic unit."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize the unit of work.

        Args:
            session_factory: Factory used to create a SQLAlchemy session.
        """
        self.session_factory = session_factory

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        """Open a session and repositories."""
        self.session = self.session_factory()
        self.users = SqlAlchemyUserRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Roll back unfinished work and close the session."""
        await super().__aexit__(exc_type, exc, tb)
        await self.session.close()

    @property
    def repositories(self):
        return [self.users]

    async def commit(self):
        try:
            await self.session.commit()
        except IntegrityError as error:
            raise IntegrityConflict from error

    async def rollback(self):
        """Roll back the SQLAlchemy transaction."""
        await self.session.rollback()
