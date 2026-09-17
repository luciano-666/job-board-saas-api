from datetime import timedelta
import pytest

from tests.modules.applications.fakes import FakeFileStorageRepository


@pytest.mark.anyio
async def test_upload_then_presign_returns_url():
    storage = FakeFileStorageRepository()

    await storage.upload(
        key="cv.pdf", content=b"%PDF-1.4...", content_type="application/pdf"
    )
    url = await storage.generate_presigned_url(
        key="cv.pdf", expires_in=timedelta(hours=1)
    )

    assert "cv.pdf" in url
    assert "expires_in=3600" in url


@pytest.mark.anyio
async def test_presign_raises_when_key_missing():
    storage = FakeFileStorageRepository()

    with pytest.raises(KeyError):
        await storage.generate_presigned_url(
            key="missing.pdf", expires_in=timedelta(hours=1)
        )


@pytest.mark.anyio
async def test_delete_removes_object():
    storage = FakeFileStorageRepository()
    await storage.upload(key="cv.pdf", content=b"data", content_type="application/pdf")

    await storage.delete(key="cv.pdf")

    with pytest.raises(KeyError):
        await storage.generate_presigned_url(
            key="cv.pdf", expires_in=timedelta(hours=1)
        )
