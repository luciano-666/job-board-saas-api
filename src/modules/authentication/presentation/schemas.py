from uuid import UUID

from fastapi import Request
from fastapi.security import OAuth2PasswordRequestFormStrict
from pydantic import BaseModel, ConfigDict

from src.modules.shared.application.enums import ResponseMessages
from src.modules.authentication.domain.entities import (
    SessionRequest,
    SessionLookup,
)


# REQUEST
class LoginRequest(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(str_strip_whitespace=True)

    @staticmethod
    def to_entity(
        form_data: OAuth2PasswordRequestFormStrict, request: Request
    ) -> "SessionRequest":
        from src.modules.authentication.domain.entities import SessionRequest
        from src.modules.user.domain.entities import User

        ip_address = request.headers.get("x-forwarded-for") or request.headers.get(
            "x-real-ip"
        )

        if ip_address is None:
            if request.client is None:
                raise ValueError(
                    "Unable to determine client IP address for login request."
                )
            ip_address = request.client.host

        return SessionRequest(
            user=User(email=form_data.username, password=form_data.password),
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent", ""),
            device=getattr(request.state, "device_id", ""),
            accept_language=request.headers.get("accept-language"),
            accept_encoding=request.headers.get("accept-encoding"),
            origin=request.headers.get("origin", ""),
            referer=request.headers.get("referer"),
            location=getattr(request.state, "location", None),
        )


# RESPONSE
class LoginResponse(BaseModel):
    message: str = ResponseMessages.LOGIN_SUCCESS.value

    model_config = ConfigDict(
        title="LoginResponse",
        str_strip_whitespace=True,
        extra="forbid",
        validate_default=True,
        validate_assignment=True,
        validate_return=True,
        json_schema_extra={
            "description": "Response model for successful user login.",
            "example": {"message": ResponseMessages.LOGIN_SUCCESS.value},
        },
    )

    @staticmethod
    def from_claims(claims: dict) -> "SessionLookup":
        """Build a SessionLookup from a decoded access token payload,
        used to query the persisted Session in the repository."""
        from src.modules.authentication.domain.entities import SessionLookup

        return SessionLookup(
            user_id=UUID(claims["sub"])
            if isinstance(claims["sub"], str)
            else claims["sub"],
            user_agent=claims.get("user_agent", ""),
            hashed_jti=claims["jti"],
            device=claims.get("device"),
        )


class RefreshResponse(BaseModel):
    message: str = ResponseMessages.REFRESH_SUCCESS.value

    model_config = ConfigDict(
        title="RefreshResponse",
        str_strip_whitespace=True,
        extra="forbid",
        validate_default=True,
        validate_assignment=True,
        validate_return=True,
        json_schema_extra={
            "description": "Response model for successful user refresh.",
            "example": {"message": ResponseMessages.REFRESH_SUCCESS.value},
        },
    )

    @staticmethod
    def from_claims(claims: dict) -> "SessionLookup":
        """Build a SessionLookup from a decoded refresh token payload,
        used to query the persisted Session in the repository."""
        from src.modules.authentication.domain.entities import SessionLookup

        return SessionLookup(
            user_id=UUID(claims["sub"])
            if isinstance(claims["sub"], str)
            else claims["sub"],
            user_agent=claims.get("user_agent", ""),
            hashed_jti=claims["jti"],
            device=claims.get("device"),
        )


class LogoutResponse(BaseModel):
    message: str = ResponseMessages.LOGOUT_SUCCESS.value

    model_config = ConfigDict(
        title="LogoutResponse",
        str_strip_whitespace=True,
        extra="forbid",
        validate_default=True,
        validate_assignment=True,
        validate_return=True,
        json_schema_extra={
            "description": "Response model for successful user logout.",
            "example": {"message": ResponseMessages.LOGOUT_SUCCESS.value},
        },
    )
