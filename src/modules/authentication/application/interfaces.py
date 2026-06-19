from typing import Protocol

from src.modules.authentication.domain.entities import Session, SessionRequest


class IAuthenticationRepository(Protocol):
    # CREATE
    async def create(self, session: Session) -> None: ...

    # READ
    async def get_by_user_id_agent_and_device(
        self, session: SessionRequest
    ) -> Session | None: ...

    async def get_access_token_by_session(self, session: Session) -> Session | None: ...

    async def get_refresh_token_by_session(
        self, session: Session
    ) -> Session | None: ...

    # UPDATE
    async def update(self, session: Session) -> None: ...

    # DELETE
    async def delete(self, session: Session) -> None: ...
