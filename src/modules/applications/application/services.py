import structlog

from src.modules.applications.application.interfaces import IFileTypeSniffer
from src.modules.applications.domain.value_objects import CvFile
from src.modules.shared.domain.entities import DomainError
from src.modules.shared.presentation.exceptions import DomainException

logger = structlog.get_logger(__name__)


async def validate_cv_upload(
    *, filename: str, content: bytes, sniffer: IFileTypeSniffer
) -> CvFile:
    """Orchestrates MIME sniffing + domain validation. Called from the
    presentation layer (router) before the use case ever sees the file,
    or from within apply_to_job (APP-9) directly."""
    try:
        detected_mime = await sniffer.sniff(content)
        return CvFile(
            filename=filename,
            content_type=detected_mime,
            size_bytes=len(content),
        )
    except DomainError as e:
        raise DomainException(e)
