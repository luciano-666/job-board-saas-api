from dataclasses import dataclass
from src.modules.shared.presentation.exceptions import DomainError


@dataclass(frozen=True, slots=True, kw_only=True)
class CvFile:
    """Validated CV file metadata. content_type must come from actual byte
    sniffing (python-magic), NOT from the client-declared Content-Type
    header or the filename extension — both are trivially spoofable."""

    ALLOWED_CONTENT_TYPE = "application/pdf"
    MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

    filename: str
    content_type: str
    size_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "filename", self.filename.strip())
        self._validate()

    def _validate(self) -> None:
        if not self.filename:
            raise DomainError("CV filename is required.")
        if self.content_type != self.ALLOWED_CONTENT_TYPE:
            raise DomainError(
                f"Only PDF files are allowed (detected: '{self.content_type}')."
            )
        if self.size_bytes <= 0:
            raise DomainError("CV file must not be empty.")
        if self.size_bytes > self.MAX_SIZE_BYTES:
            raise DomainError("CV file must not exceed 5MB.")
