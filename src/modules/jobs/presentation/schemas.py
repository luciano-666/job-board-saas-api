from __future__ import annotations

from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from src.modules.jobs.application.dto import JobFilters
from src.modules.shared.application.enums import ResponseMessages


class SalaryRangeSchema(BaseModel):
    min: Optional[int] = Field(default=None, ge=0)
    max: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class CreateJobRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Backend Engineer"])
    description: str = Field(
        min_length=1, examples=["Build and maintain backend services."]
    )
    location: str = Field(min_length=1, max_length=255, examples=["Ho Chi Minh City"])
    job_type: JobType = Field(examples=[JobType.FULL_TIME.value])
    skills: list[str] = Field(min_length=1, examples=[["python", "fastapi"]])
    salary: Optional[SalaryRangeSchema] = Field(default=None)

    @field_validator("skills")
    @classmethod
    def validate_skills_not_empty_strings(cls, value: list[str]) -> list[str]:
        if not any(s.strip() for s in value):
            raise ValueError("At least one non-empty skill is required.")
        return value

    model_config = ConfigDict(
        title="CreateJobRequest",
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "title": "Backend Engineer",
                "description": "Build and maintain backend services.",
                "location": "Ho Chi Minh City",
                "job_type": JobType.FULL_TIME.value,
                "skills": ["python", "fastapi"],
                "salary": {"min": 2000, "max": 4000},
            }
        },
    )

    def to_entity(self, employer_id: UUID) -> Job:
        return Job(
            title=self.title,
            description=self.description,
            location=self.location,
            job_type=self.job_type,
            skills=self.skills,
            employer_id=employer_id,
            salary=SalaryRange(
                min=self.salary.min if self.salary else None,
                max=self.salary.max if self.salary else None,
            ),
        )


class UpdateJobRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=255)
    job_type: JobType
    skills: list[str] = Field(min_length=1)
    salary: Optional[SalaryRangeSchema] = Field(default=None)

    model_config = ConfigDict(
        title="UpdateJobRequest",
        str_strip_whitespace=True,
        extra="forbid",
    )


class JobResponse(BaseModel):
    id: UUID
    title: str
    description: str
    location: str
    job_type: JobType
    status: JobStatus
    skills: list[str]
    employer_id: UUID
    salary: SalaryRangeSchema

    model_config = ConfigDict(title="JobResponse", extra="forbid")

    @classmethod
    def from_entity(cls, job: Job) -> "JobResponse":
        return cls(
            id=job.id,
            title=job.title,
            description=job.description,
            location=job.location,
            job_type=job.job_type,
            status=job.status,
            skills=job.skills,
            employer_id=job.employer_id,
            salary=SalaryRangeSchema(min=job.salary.min, max=job.salary.max),
        )


class CreateJobResponse(BaseModel):
    message: str = ResponseMessages.CREATED.value
    data: JobResponse

    model_config = ConfigDict(title="CreateJobResponse", extra="forbid")


class UpdateJobResponse(BaseModel):
    message: str = ResponseMessages.UPDATED.value
    data: JobResponse

    model_config = ConfigDict(title="UpdateJobResponse", extra="forbid")


class PublishJobResponse(BaseModel):
    message: str = ResponseMessages.UPDATED.value
    data: JobResponse

    model_config = ConfigDict(title="PublishJobResponse", extra="forbid")


class CloseJobResponse(BaseModel):
    message: str = ResponseMessages.UPDATED.value
    data: JobResponse

    model_config = ConfigDict(title="CloseJobResponse", extra="forbid")


class ArchiveJobResponse(BaseModel):
    message: str = ResponseMessages.UPDATED.value
    data: JobResponse

    model_config = ConfigDict(title="ArchiveJobResponse", extra="forbid")


class GetJobResponse(BaseModel):
    message: str = ResponseMessages.RETRIEVED.value
    data: JobResponse

    model_config = ConfigDict(title="GetJobResponse", extra="forbid")


class JobListQuery(BaseModel):
    """Query parameters for public job listing. All fields optional."""

    location: Optional[str] = Field(default=None, max_length=255)
    job_type: Optional[JobType] = Field(default=None)
    salary_min: Optional[int] = Field(default=None, ge=0)
    skills: Optional[list[str]] = Field(default=None)
    company_id: Optional[UUID] = Field(default=None)
    search: Optional[str] = Field(default=None, max_length=255)
    cursor: Optional[str] = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    def to_filters(self) -> JobFilters:
        return JobFilters(
            location=self.location,
            job_type=self.job_type,
            salary_min=self.salary_min,
            skills=self.skills,
            company_id=self.company_id,
            search=self.search,
        )


class JobListResponse(BaseModel):
    message: str = ResponseMessages.RETRIEVED.value
    data: list[JobResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False

    model_config = ConfigDict(title="JobListResponse", extra="forbid")
