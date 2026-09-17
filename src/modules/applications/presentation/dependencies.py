from src.modules.applications.application.interfaces import IFileStorageRepository
from src.modules.applications.infrastructure.storage import GarageFileStorageRepository


def get_file_storage_repository() -> IFileStorageRepository:
    return GarageFileStorageRepository()
