from dataclasses import dataclass
from src.modules.shared.presentation.exceptions import DomainError


@dataclass(frozen=True, slots=True, kw_only=True)
class SalaryRange:
    """Salary range for a job posting. Either bound may be omitted
    (e.g. 'undisclosed' or open-ended), but if both are present,
    min must not exceed max."""

    min: int | None = None
    max: int | None = None

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if self.min is not None and self.min < 0:
            raise DomainError("Salary min must not be negative.")

        if self.max is not None and self.max < 0:
            raise DomainError("Salary max must not be negative.")

        if self.min is not None and self.max is not None and self.min > self.max:
            raise DomainError("Salary min must not be greater than salary max.")

    def __str__(self) -> str:
        if self.min is not None and self.max is not None:
            return f"{self.min}-{self.max}"
        if self.min is not None:
            return f"{self.min}+"
        if self.max is not None:
            return f"up to {self.max}"
        return "undisclosed"
