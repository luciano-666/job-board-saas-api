import pytest
from src.modules.applications.application.services import validate_cv_upload
from src.modules.shared.presentation.exceptions import DomainException


class FakeSniffer:
    def __init__(self, mime: str) -> None:
        self._mime = mime

    async def sniff(self, content: bytes) -> str:
        return self._mime


@pytest.mark.anyio
async def test_validate_cv_upload_accepts_real_pdf_bytes():
    cv = await validate_cv_upload(
        filename="cv.pdf",
        content=b"fake pdf bytes",
        sniffer=FakeSniffer("application/pdf"),
    )
    assert cv.content_type == "application/pdf"


@pytest.mark.anyio
async def test_validate_cv_upload_rejects_renamed_file():
    """Client renames a .exe to .pdf — sniffed MIME must still win."""
    with pytest.raises(DomainException):
        await validate_cv_upload(
            filename="cv.pdf",
            content=b"MZ\x90\x00...",  # PE header, not PDF
            sniffer=FakeSniffer("application/x-dosexec"),
        )


@pytest.mark.anyio
async def test_validate_cv_upload_rejects_oversized_file():
    oversized = b"0" * (5 * 1024 * 1024 + 1)
    with pytest.raises(DomainException):
        await validate_cv_upload(
            filename="cv.pdf", content=oversized, sniffer=FakeSniffer("application/pdf")
        )
