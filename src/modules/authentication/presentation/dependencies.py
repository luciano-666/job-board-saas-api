from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.modules.authentication.application.interfaces import IAuthenticationRepository
from src.modules.authentication.application.use_cases import AuthenticationUseCases
from src.modules.authentication.infrastructure.repositories import (
    SqlAlchemySessionRepository,
)
from src.modules.shared.application.use_cases import SharedUseCases
from src.modules.shared.presentation.dependencies import get_shared_use_cases


def get_authentication_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IAuthenticationRepository:
    return SqlAlchemySessionRepository(session=session)


def get_authentication_use_cases(
    repository: IAuthenticationRepository = Depends(get_authentication_repository),
    shared_service: SharedUseCases = Depends(get_shared_use_cases),
) -> AuthenticationUseCases:
    return AuthenticationUseCases(repository=repository, shared_service=shared_service)
