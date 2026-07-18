from typing import Protocol
from uuid import UUID

from src.modules.authentication.domain.entities import (
    Session,
    SessionRequest,
    SessionLookup,
)


class IAuthenticationRepository(Protocol):
    # CREATE
    async def create(self, session: Session) -> None: ...

    # READ
    async def get_by_user_id_agent_and_device(
        self, session: SessionRequest
    ) -> Session | None: ...

    async def get_access_token_by_session(
        self, lookup: SessionLookup
    ) -> Session | None: ...

    async def get_refresh_token_by_session(
        self, lookup: SessionLookup
    ) -> Session | None: ...

    # UPDATE
    async def update(self, session: Session) -> None: ...

    # DELETE
    async def delete(self, session: Session) -> None: ...


class IPasswordResetRepository(Protocol):
    async def store_reset_token(
        self, hashed_token: str, user_id: UUID, ttl_seconds: int
    ) -> None: ...

    async def get_user_id_by_reset_token(self, hashed_token: str) -> UUID | None: ...

    async def delete_reset_token(self, hashed_token: str) -> None: ...
