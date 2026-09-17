from datetime import timedelta

import aioboto3
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from src.core.config import settings
from src.modules.applications.presentation.exceptions import ApplicationException

logger = structlog.get_logger(__name__)


class GarageFileStorageRepository:
    """S3-compatible object storage backed by Garage.

    Uses aioboto3 pointed at STORAGE_ENDPOINT_URL — the same boto3 S3 API
    works unmodified against Garage because it implements the S3 protocol.
    No asyncio.to_thread needed here (unlike the sync boto3 pattern used
    elsewhere) since aioboto3 wraps the client natively as async.
    """

    def __init__(self) -> None:
        self._session = aioboto3.Session()

    def _client_kwargs(self) -> dict:
        return dict(
            endpoint_url=settings.STORAGE_ENDPOINT_URL,
            region_name=settings.STORAGE_REGION,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY_ID,
            aws_secret_access_key=settings.STORAGE_SECRET_ACCESS_KEY,
        )

    async def upload(self, *, key: str, content: bytes, content_type: str) -> None:
        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                await s3.put_object(
                    Bucket=settings.STORAGE_BUCKET_NAME,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                )
            logger.info(f"Uploaded object '{key}' to Garage bucket successfully.")
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to upload object '{key}' to Garage.", exc_info=e)
            raise ApplicationException()

    async def generate_presigned_url(self, *, key: str, expires_in: timedelta) -> str:
        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": settings.STORAGE_BUCKET_NAME, "Key": key},
                    ExpiresIn=int(expires_in.total_seconds()),
                )
            return url
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to presign URL for object '{key}'.", exc_info=e)
            raise ApplicationException()

    async def delete(self, *, key: str) -> None:
        try:
            async with self._session.client("s3", **self._client_kwargs()) as s3:
                await s3.delete_object(Bucket=settings.STORAGE_BUCKET_NAME, Key=key)
            logger.info(f"Deleted object '{key}' from Garage bucket successfully.")
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to delete object '{key}' from Garage.", exc_info=e)
            raise ApplicationException()
