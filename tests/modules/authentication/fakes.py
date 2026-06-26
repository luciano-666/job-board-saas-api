"""In-memory fakes for Authentication service-layer tests."""

from uuid import UUID
from typing import Optional


from src.modules.authentication.domain.entities import (
    Session,
    SessionRequest,
    SessionLookup,
)

from src.modules.user.domain.entities import User
from src.modules.user.presentation.exceptions import UserEmailNotFoundException


class FakeAuthenticationRepository:
    """Pure-memory IAuthenticationRepository implementation."""

    def __init__(self, sessions: Optional[list[Session]] = None) -> None:
        self._store: dict[UUID, Session] = {s.id: s for s in (sessions or [])}
        self.created: list[Session] = []
        self.updated: list[Session] = []
        self.deleted: list[Session] = []

    async def create(self, session: Session) -> None:
        self._store[session.id] = session
        self.created.append(session)

    async def get_by_user_id_agent_and_device(
        self, session: SessionRequest
    ) -> Session | None:
        return next(
            (
                s
                for s in self._store.values()
                if s.user.id == session.user.id
                and s.user_agent == session.user_agent
                and s.device == session.device
                and not s.blacklisted
            ),
            None,
        )

    async def get_access_token_by_session(
        self, lookup: SessionLookup
    ) -> Session | None:
        return next(
            (
                s
                for s in self._store.values()
                if s.user.id == lookup.user_id
                and s.user_agent == lookup.user_agent
                and s.device == lookup.device
                and s.refresh_token.access_token.hashed_jti == lookup.hashed_jti
                and not s.refresh_token.access_token.revoked
                and not s.refresh_token.revoked
                and not s.blacklisted
            ),
            None,
        )

    async def get_refresh_token_by_session(
        self, lookup: SessionLookup
    ) -> Session | None:
        return next(
            (
                s
                for s in self._store.values()
                if s.user.id == lookup.user_id
                and s.user_agent == lookup.user_agent
                and s.device == lookup.device
                and s.refresh_token.hashed_jti == lookup.hashed_jti
                and not s.refresh_token.revoked
                and not s.blacklisted
            ),
            None,
        )

    async def update(self, session: Session) -> None:
        self._store[session.id] = session
        self.updated.append(session)

    async def delete(self, session: Session) -> None:
        self._store[session.id] = session  # keep in store, tokens are revoked
        self.deleted.append(session)


class FakeSharedUseCases:
    """Minimal ISharedUseCases stand-in for AuthenticationUseCases tests."""

    def __init__(self, users: Optional[list[User]] = None) -> None:
        self._store: dict[str, User] = {str(u.email): u for u in (users or [])}

    async def get_user_by_email(self, user: User) -> User:
        result = self._store.get(str(user.email))
        if result is None:
            raise UserEmailNotFoundException(email=str(user.email))
        return result

    async def get_user_by_id(self, user: User) -> User | None:
        return next(
            (u for u in self._store.values() if u.id == user.id),
            None,
        )
