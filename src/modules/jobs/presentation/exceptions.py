from http import HTTPStatus

from src.modules.shared.application.enums import ResponseMessages
from src.modules.shared.presentation.exceptions import StandardException


class JobException(StandardException):
    def __init__(self) -> None:
        message = ResponseMessages.INTERNAL_ERROR.value
        errors = "An unexpected error occurred while processing the request at the jobs module."

        super().__init__(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=message,
            data={"errors": errors},
        )


class JobNotFoundException(StandardException):
    def __init__(self, job_id: str) -> None:
        message = ResponseMessages.RESOURCE_NOT_FOUND.value
        errors = f"Job '{job_id}' not found."

        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            message=message,
            data={"errors": errors},
        )


class JobNotOwnedException(StandardException):
    def __init__(self) -> None:
        message = ResponseMessages.AUTHORIZATION_ERROR.value
        errors = "You do not own this job posting."

        super().__init__(
            status_code=HTTPStatus.FORBIDDEN,
            message=message,
            data={"errors": errors},
        )
