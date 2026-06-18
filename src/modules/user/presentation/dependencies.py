from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.modules.shared.application.use_cases import SharedUseCases
from src.modules.shared.presentation.dependencies import get_shared_use_cases
from src.modules.user.application.interfaces import IUserRepository
from src.modules.user.application.use_cases import UserUseCases
from src.modules.user.infrastructure.repositories import SqlAlchemyUserRepository


def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IUserRepository:
    return SqlAlchemyUserRepository(session=session)


def get_user_use_cases(
    repository: IUserRepository = Depends(get_user_repository),
    shared_service: SharedUseCases = Depends(get_shared_use_cases),
) -> UserUseCases:
    return UserUseCases(repository=repository, shared_service=shared_service)
