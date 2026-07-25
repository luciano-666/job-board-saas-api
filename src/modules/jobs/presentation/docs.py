from http import HTTPStatus
from typing import Any

from fastapi import Security

from src.modules.authentication.presentation.dependencies import authenticate_employer
from src.modules.jobs.presentation.schemas import CreateJobResponse, UpdateJobResponse

router_docs: dict[str, Any] = {
    "prefix": "/api/v1/jobs",
    "tags": ["Jobs"],
}

create_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to create a job posting.",
    "description": "Create a new job posting. Requires employer authentication. New jobs start in DRAFT status.",
    "dependencies": [Security(authenticate_employer)],
    "status_code": HTTPStatus.CREATED,
    "response_model": CreateJobResponse,
    "include_in_schema": True,
    "responses": {},
}

update_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to update their own job posting.",
    "description": "Update an existing job posting. Requires employer authentication and ownership of the job.",
    "dependencies": [Security(authenticate_employer)],
    "status_code": HTTPStatus.OK,
    "response_model": UpdateJobResponse,
    "include_in_schema": True,
    "responses": {},
}
