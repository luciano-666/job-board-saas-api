"""Integration tests against a real Garage instance (via compose.yaml).
Requires STORAGE_* env vars pointing at the running Garage service and
a bucket already created (garage bucket create / garage bucket allow).
"""

from datetime import timedelta
import pytest

from src.modules.applications.infrastructure.storage import GarageFileStorageRepository
from tests.utils import random_lower_string


@pytest.mark.anyio
async def test_upload_and_presign_roundtrip():
    storage = GarageFileStorageRepository()
    key = f"test/{random_lower_string()}.pdf"

    await storage.upload(
        key=key, content=b"%PDF-1.4...", content_type="application/pdf"
    )
    url = await storage.generate_presigned_url(key=key, expires_in=timedelta(hours=1))

    assert key in url

    await storage.delete(key=key)  # cleanup
