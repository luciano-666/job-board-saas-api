import pytest
from src.modules.applications.infrastructure.validators import (
    PythonMagicFileTypeSniffer,
)

REAL_PDF_MINIMAL = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@pytest.mark.anyio
async def test_sniffer_detects_real_pdf():
    sniffer = PythonMagicFileTypeSniffer()
    mime = await sniffer.sniff(REAL_PDF_MINIMAL)
    assert mime == "application/pdf"


@pytest.mark.anyio
async def test_sniffer_detects_spoofed_pdf_as_its_real_type():
    """Content is plain text but named/declared as PDF — must not be fooled."""
    sniffer = PythonMagicFileTypeSniffer()
    mime = await sniffer.sniff(b"just plain text content, not a pdf at all")
    assert mime != "application/pdf"
