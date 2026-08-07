from http import HTTPStatus
from typing import Any

from fastapi import Security

from src.modules.authentication.presentation.dependencies import (
    authenticate_employer,
    no_authentication,
)
from src.modules.jobs.presentation.schemas import (
    CreateJobResponse,
    UpdateJobResponse,
    PublishJobResponse,
    CloseJobResponse,
    ArchiveJobResponse,
    GetJobResponse,
    JobListResponse,
)
from src.modules.shared.application.enums import ResponseMessages
from src.modules.shared.presentation.schemas import StandardResponse

# MODULE DOCS
router_docs: dict[str, Any] = {
    "prefix": "/api/v1/jobs",
    "tags": ["Jobs"],
    "responses": {
        400: {
            "model": StandardResponse,
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "examples": {
                        "Bad Request": {
                            "summary": "The request could not be understood or was missing required parameters.",
                            "value": {
                                "code": 400,
                                "method": "POST",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.VALIDATION_ERROR.value,
                                    "data": {
                                        "error": "The request is missing required parameters."
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        401: {
            "model": StandardResponse,
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "examples": {
                        "Unauthorized": {
                            "summary": "Authentication is required and has failed or has not yet been provided.",
                            "value": {
                                "code": 401,
                                "method": "POST",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.UNAUTHORIZED_ERROR.value,
                                    "data": {
                                        "error": "Authentication credentials were missing or incorrect."
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        403: {
            "model": StandardResponse,
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "examples": {
                        "Forbidden": {
                            "summary": "The request was valid, but the server is refusing action.",
                            "value": {
                                "code": 403,
                                "method": "PATCH",
                                "path": "/api/v1/jobs/{job_id}",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.AUTHORIZATION_ERROR.value,
                                    "data": {
                                        "error": "You do not own this job posting."
                                    },
                                },
                            },
                        },
                    },
                }
            },
        },
        404: {
            "model": StandardResponse,
            "description": "Not Found",
            "content": {
                "application/json": {
                    "examples": {
                        "Not Found": {
                            "summary": "The requested job posting does not exist or is not publicly visible.",
                            "value": {
                                "code": 404,
                                "method": "GET",
                                "path": "/api/v1/jobs/{job_id}",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.RESOURCE_NOT_FOUND.value,
                                    "data": {
                                        "error": "Job '00000000-0000-0000-0000-000000000000' not found."
                                    },
                                },
                            },
                        },
                    },
                }
            },
        },
        405: {
            "model": StandardResponse,
            "description": "Method Not Allowed",
            "content": {
                "application/json": {
                    "examples": {
                        "Method Not Allowed": {
                            "summary": "The method is not allowed for the requested URL.",
                            "value": {
                                "code": 405,
                                "method": "PUT",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.METHOD_NOT_ALLOWED.value,
                                    "data": {
                                        "error": "The method is not allowed for the requested URL."
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        422: {
            "model": StandardResponse,
            "description": "Form Validation Error",
            "content": {
                "application/json": {
                    "examples": {
                        "Form Validation Error": {
                            "summary": "The request was well-formed but was unable to be followed due to semantic errors.",
                            "value": {
                                "code": 422,
                                "method": "POST",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.VALIDATION_ERROR.value,
                                    "data": {
                                        "error": "The request contains semantic errors and cannot be processed."
                                    },
                                },
                            },
                        },
                    },
                }
            },
        },
        500: {
            "model": StandardResponse,
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "examples": {
                        "Internal Server Error": {
                            "summary": "An unexpected error occurred while processing the request.",
                            "value": {
                                "code": 500,
                                "method": "POST",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.INTERNAL_ERROR.value,
                                    "data": {"error": "An unexpected error occurred."},
                                },
                            },
                        },
                    },
                }
            },
        },
        502: {
            "model": StandardResponse,
            "description": "Bad Gateway",
            "content": {
                "application/json": {
                    "examples": {
                        "Bad Gateway": {
                            "summary": "The server received an invalid response from the upstream server while acting as a gateway or proxy.",
                            "value": {
                                "code": 502,
                                "method": "POST",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.BAD_GATEWAY.value,
                                    "data": {
                                        "error": "The server received an invalid response from the upstream server."
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        504: {
            "model": StandardResponse,
            "description": "Gateway Timeout",
            "content": {
                "application/json": {
                    "examples": {
                        "Gateway Timeout": {
                            "summary": "The server, while acting as a gateway or proxy, did not receive a timely response from the upstream server.",
                            "value": {
                                "code": 504,
                                "method": "POST",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-07-15T12:34:56Z",
                                "details": {
                                    "message": ResponseMessages.GATEWAY_TIMEOUT.value,
                                    "data": {
                                        "error": "The server did not receive a timely response from the upstream server."
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}

# ENDPOINT DOCS
create_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to create a job posting.",
    "description": (
        "Create a new job posting. Requires employer authentication. "
        "New jobs start in DRAFT status and must be published separately."
    ),
    "dependencies": [Security(authenticate_employer)],
    "response_description": "The response contains the created job posting.",
    "status_code": HTTPStatus.CREATED,
    "response_model": CreateJobResponse,
    "include_in_schema": True,
    "responses": {
        201: {
            "description": "Successful Response",
            "model": CreateJobResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "Job Created Successfully": {
                            "summary": "Job Created Successfully",
                            "value": {
                                "code": 201,
                                "method": "POST",
                                "path": "/api/v1/jobs",
                                "timestamp": "2025-01-15T10:30:00Z",
                                "details": {
                                    "message": ResponseMessages.CREATED.value,
                                    "data": {
                                        "message": ResponseMessages.CREATED.value,
                                        "data": {
                                            "id": "00000000-0000-0000-0000-000000000000",
                                            "title": "Backend Engineer",
                                            "description": "Build and maintain backend services.",
                                            "location": "Ho Chi Minh City",
                                            "job_type": "full_time",
                                            "status": "draft",
                                            "skills": ["python", "fastapi"],
                                            "employer_id": "00000000-0000-0000-0000-000000000001",
                                            "salary": {"min": 2000, "max": 4000},
                                        },
                                    },
                                },
                            },
                        },
                    }
                }
            },
        },
    },
}


update_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to update their own job posting.",
    "description": (
        "Update an existing job posting. Requires employer authentication "
        "and ownership of the job. Status transitions have dedicated endpoints."
    ),
    "dependencies": [Security(authenticate_employer)],
    "response_description": "The response contains the updated job posting.",
    "status_code": HTTPStatus.OK,
    "response_model": UpdateJobResponse,
    "include_in_schema": True,
    "responses": {},
}


publish_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to publish a draft job posting.",
    "description": (
        "Transition a job from draft to open, making it publicly visible. "
        "Requires employer authentication and ownership."
    ),
    "dependencies": [Security(authenticate_employer)],
    "response_description": "The response contains the published job posting.",
    "status_code": HTTPStatus.OK,
    "response_model": PublishJobResponse,
    "include_in_schema": True,
    "responses": {},
}


close_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to close an open job posting.",
    "description": (
        "Transition a job from open to closed, hiding it from public listings. "
        "Requires employer authentication and ownership."
    ),
    "dependencies": [Security(authenticate_employer)],
    "response_description": "The response contains the closed job posting.",
    "status_code": HTTPStatus.OK,
    "response_model": CloseJobResponse,
    "include_in_schema": True,
    "responses": {},
}


archive_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to archive a job posting.",
    "description": (
        "Transition a job from open or closed to archived. Only allowed 90+ "
        "days after creation. Requires employer authentication and ownership."
    ),
    "dependencies": [Security(authenticate_employer)],
    "response_description": "The response contains the archived job posting.",
    "status_code": HTTPStatus.OK,
    "response_model": ArchiveJobResponse,
    "include_in_schema": True,
    "responses": {},
}


get_job_docs: dict[str, Any] = {
    "summary": "Public endpoint to view a job posting.",
    "description": (
        "Retrieve a job posting by id. Only jobs with OPEN status are visible — "
        "draft, closed, and archived jobs return 404 regardless of existence, "
        "to avoid leaking job lifecycle state to unauthenticated clients."
    ),
    "dependencies": [Security(no_authentication)],
    "response_description": "The response contains the requested job posting.",
    "status_code": HTTPStatus.OK,
    "response_model": GetJobResponse,
    "include_in_schema": True,
    "responses": {
        200: {
            "description": "Successful Response",
            "model": GetJobResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "Job Retrieved Successfully": {
                            "summary": "Job Retrieved Successfully",
                            "value": {
                                "code": 200,
                                "method": "GET",
                                "path": "/api/v1/jobs/{job_id}",
                                "timestamp": "2025-01-15T10:30:00Z",
                                "details": {
                                    "message": ResponseMessages.RETRIEVED.value,
                                    "data": {
                                        "message": ResponseMessages.RETRIEVED.value,
                                        "data": {
                                            "id": "00000000-0000-0000-0000-000000000000",
                                            "title": "Backend Engineer",
                                            "description": "Build and maintain backend services.",
                                            "location": "Ho Chi Minh City",
                                            "job_type": "full_time",
                                            "status": "open",
                                            "skills": ["python", "fastapi"],
                                            "employer_id": "00000000-0000-0000-0000-000000000001",
                                            "salary": {"min": 2000, "max": 4000},
                                        },
                                    },
                                },
                            },
                        },
                    }
                }
            },
        },
    },
}


list_jobs_docs: dict[str, Any] = {
    "summary": "Public endpoint to list job postings.",
    "description": (
        "List job postings with optional filters (location, job_type, "
        "salary_min, skills, company_id, search). Cursor-based pagination "
        "(no offset). Only jobs with OPEN status are visible."
    ),
    "dependencies": [Security(no_authentication)],
    "response_description": "The response contains a page of job postings.",
    "status_code": HTTPStatus.OK,
    "response_model": JobListResponse,
    "include_in_schema": True,
    "responses": {},
}
