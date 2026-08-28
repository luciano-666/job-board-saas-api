from http import HTTPStatus

from src.modules.shared.application.enums import ResponseMessages
from src.modules.shared.presentation.exceptions import StandardException


class ApplicationException(StandardException):
    def __init__(self) -> None:
        message = ResponseMessages.INTERNAL_ERROR.value
        errors = "An unexpected error occurred while processing the request at the applications module."

        super().__init__(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            message=message,
            data={"errors": errors},
        )


class ApplicationNotFoundException(StandardException):
    def __init__(self, application_id: str) -> None:
        message = ResponseMessages.RESOURCE_NOT_FOUND.value
        errors = f"Application '{application_id}' not found."

        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            message=message,
            data={"errors": errors},
        )


class ApplicationAlreadyExistsException(StandardException):
    def __init__(self, candidate_id: str, job_id: str) -> None:
        message = ResponseMessages.CONFLICT.value
        errors = f"Candidate '{candidate_id}' has already applied to job '{job_id}'."

        super().__init__(
            status_code=HTTPStatus.CONFLICT,
            message=message,
            data={"errors": errors},
        )


class JobNotOpenForApplicationsException(StandardException):
    def __init__(self) -> None:
        message = ResponseMessages.VALIDATION_ERROR.value
        errors = "This job is not open for applications."

        super().__init__(
            status_code=HTTPStatus.BAD_REQUEST,
            message=message,
            data={"errors": errors},
        )
