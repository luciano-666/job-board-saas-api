from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session

from src.modules.authentication.application.interfaces import IAuthenticationRepository
from src.modules.authentication.infrastructure.repositories import (
    SqlAlchemySessionRepository,
)
from src.modules.shared.application.use_cases import SharedUseCases
from src.modules.user.application.interfaces import IUserRepository
from src.modules.user.infrastructure.repositories import SqlAlchemyUserRepository
from src.modules.jobs.application.interfaces import IJobRepository
from src.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository

from src.modules.shared.application.interfaces import IUnitOfWork
from src.modules.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def get_authentication_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IAuthenticationRepository:
    return SqlAlchemySessionRepository(session=session)


def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IUserRepository:
    return SqlAlchemyUserRepository(session=session)


def get_job_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IJobRepository:
    return SqlAlchemyJobRepository(session=session)


def get_shared_use_cases(
    user_repository: IUserRepository = Depends(get_user_repository),
    job_repository: IJobRepository = Depends(get_job_repository),
) -> SharedUseCases:
    return SharedUseCases(
        user_repository=user_repository, job_repository=job_repository
    )


def get_unit_of_work(
    session: AsyncSession = Depends(get_async_session),
) -> IUnitOfWork:
    return SqlAlchemyUnitOfWork(session=session)
