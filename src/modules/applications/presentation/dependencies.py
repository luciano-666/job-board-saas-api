from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.modules.applications.application.interfaces import (
    IApplicationRepository,
    IFileStorageRepository,
    IFileTypeSniffer,
)
from src.modules.applications.application.use_cases import ApplicationUseCases
from src.modules.applications.infrastructure.repositories import (
    SqlAlchemyApplicationRepository,  # implement này nếu chưa có (APP-4)
)
from src.modules.applications.infrastructure.storage import GarageFileStorageRepository
from src.modules.applications.infrastructure.validators import (
    PythonMagicFileTypeSniffer,
)
from src.modules.shared.application.use_cases import SharedUseCases
from src.modules.shared.presentation.dependencies import get_shared_use_cases


def get_application_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IApplicationRepository:
    return SqlAlchemyApplicationRepository(session=session)


def get_file_storage_repository() -> IFileStorageRepository:
    return GarageFileStorageRepository()


def get_file_type_sniffer() -> IFileTypeSniffer:
    return PythonMagicFileTypeSniffer()


def get_application_use_cases(
    repository: IApplicationRepository = Depends(get_application_repository),
    shared_service: SharedUseCases = Depends(get_shared_use_cases),
    file_storage: IFileStorageRepository = Depends(get_file_storage_repository),
    sniffer: IFileTypeSniffer = Depends(get_file_type_sniffer),
) -> ApplicationUseCases:
    return ApplicationUseCases(
        repository=repository,
        shared_service=shared_service,
        file_storage=file_storage,
        sniffer=sniffer,
    )