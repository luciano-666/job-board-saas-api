from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from src.modules.shared.application.enums import ResponseMessages

T = TypeVar("T")


class StandardDetailsResponse(BaseModel, Generic[T]):
    message: str = Field(
        title="Response message",
        description="A brief, human-readable summary of the response.",
        min_length=1,
        examples=[
            "Process completed successfully.",
            "Unable to process the request.",
        ],
    )

    data: T | None = Field(
        default=None,
        title="Additional data",
        description="Additional payload returned by the API.",
        examples=[
            {"field": "value"},
            {},
            {"key": "value", "another_key": 123},
        ],
    )

    model_config = ConfigDict(
        title="StandardDetailsResponse",
        str_strip_whitespace=True,
        extra="forbid",
        validate_assignment=True,
        json_schema_extra={
            "description": (
                "Standard details response schema containing "
                "a message and optional payload."
            ),
            "example": {
                "message": ResponseMessages.SUCCESS.value,
                "data": {"key": "value"},
            },
        },
    )


class StandardResponse(BaseModel, Generic[T]):
    code: int = Field(
        title="HTTP status code",
        description="HTTP response status code.",
        ge=100,
        le=599,
        examples=[200, 400, 404, 500],
    )

    method: str = Field(
        title="HTTP method",
        description="HTTP method used by the request.",
        pattern="^(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)$",
        examples=["GET", "POST"],
    )

    path: str = Field(
        title="Request path",
        description="API endpoint path.",
        min_length=1,
        pattern=r"^/.*$",
        examples=["/api/v1/resource"],
    )

    timestamp: str = Field(
        title="Timestamp",
        description="ISO-8601 timestamp when the response was generated.",
        examples=["2026-06-18T10:30:00Z"],
    )

    details: StandardDetailsResponse[T] = Field(
        title="Response details",
        description="Response payload and message.",
        examples=[
            {
                "message": ResponseMessages.SUCCESS.value,
                "data": {"key": "value"},
            },
            {
                "message": ResponseMessages.VALIDATION_ERROR.value,
                "data": {"field": "Invalid value"},
            },
        ],
    )

    model_config = ConfigDict(
        title="StandardResponse",
        str_strip_whitespace=True,
        extra="forbid",
        validate_assignment=True,
        json_schema_extra={
            "description": ("Standard API response schema."),
            "example": {
                "code": 200,
                "method": "GET",
                "path": "/api/v1/resource",
                "timestamp": "2026-06-18T10:30:00Z",
                "details": {
                    "message": ResponseMessages.SUCCESS.value,
                    "data": {"key": "value"},
                },
            },
        },
    )
