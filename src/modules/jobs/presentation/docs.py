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


publish_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to publish a draft job posting.",
    "description": "Transition a job from draft to open. Requires employer authentication and ownership.",
    "dependencies": [Security(authenticate_employer)],
    "status_code": HTTPStatus.OK,
    "response_model": PublishJobResponse,
    "include_in_schema": True,
    "responses": {},
}

close_job_docs: dict[str, Any] = {
    "summary": "Endpoint for an employer to close an open job posting.",
    "description": "Transition a job from open to closed. Requires employer authentication and ownership.",
    "dependencies": [Security(authenticate_employer)],
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
    "status_code": HTTPStatus.OK,
    "response_model": ArchiveJobResponse,
    "include_in_schema": True,
    "responses": {},
}

get_job_docs: dict[str, Any] = {
    "summary": "Public endpoint to view a job posting.",
    "description": "Retrieve a job posting by id. Only jobs with OPEN status are visible.",
    "dependencies": [Security(no_authentication)],
    "status_code": HTTPStatus.OK,
    "response_model": GetJobResponse,
    "include_in_schema": True,
    "responses": {},
}


list_jobs_docs: dict[str, Any] = {
    "summary": "Public endpoint to list job postings.",
    "description": (
        "List job postings with optional filters. Cursor-based pagination "
        "(no offset). Only jobs with OPEN status are visible."
    ),
    "dependencies": [Security(no_authentication)],
    "status_code": HTTPStatus.OK,
    "response_model": JobListResponse,
    "include_in_schema": True,
    "responses": {},
}
