import pytest
from src.modules.shared.domain.entities import DomainError
from src.modules.applications.domain.value_objects import CvFile

VALID_PDF_HEADER = b"%PDF-1.4\n%useless bytes to pad..."


def test_accepts_valid_pdf():
    cv = CvFile(filename="resume.pdf", content_type="application/pdf", size_bytes=1024)
    assert cv.filename == "resume.pdf"


def test_rejects_non_pdf_content_type():
    with pytest.raises(DomainError, match="PDF"):
        CvFile(filename="resume.pdf", content_type="image/png", size_bytes=1024)


def test_rejects_file_over_5mb():
    with pytest.raises(DomainError, match="5"):
        CvFile(
            filename="resume.pdf",
            content_type="application/pdf",
            size_bytes=5 * 1024 * 1024 + 1,
        )


def test_accepts_exactly_5mb():
    cv = CvFile(
        filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=5 * 1024 * 1024,
    )
    assert cv.size_bytes == 5 * 1024 * 1024


def test_rejects_empty_filename():
    with pytest.raises(DomainError, match="filename"):
        CvFile(filename="   ", content_type="application/pdf", size_bytes=1024)
