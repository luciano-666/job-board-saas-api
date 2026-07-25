from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.modules.jobs.application.interfaces import IJobRepository
from src.modules.jobs.application.use_cases import JobUseCases
from src.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository


def get_job_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IJobRepository:
    return SqlAlchemyJobRepository(session=session)


def get_job_use_cases(
    repository: IJobRepository = Depends(get_job_repository),
) -> JobUseCases:
    return JobUseCases(repository=repository)
