import asyncio
import structlog
import magic

from src.modules.applications.presentation.exceptions import ApplicationException

logger = structlog.get_logger(__name__)


class PythonMagicFileTypeSniffer:
    """Sniffs MIME type from magic bytes, not from filename/Content-Type.
    libmagic is a blocking C call — run in a worker thread to keep the
    event loop free, same pattern as boto3 calls (constraint #2)."""

    async def sniff(self, content: bytes) -> str:
        try:
            return await asyncio.to_thread(magic.from_buffer, content, mime=True)
        except Exception as e:
            logger.error("An error occurred while sniffing file MIME type.", exc_info=e)
            raise ApplicationException()
