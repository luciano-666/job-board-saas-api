from uuid import UUID
from datetime import date
from typing import Optional
import re

from fastapi import Request
from fastapi.security import OAuth2PasswordRequestFormStrict
from pydantic import BaseModel, ConfigDict, field_validator, Field

from src.modules.shared.application.enums import ResponseMessages
from src.modules.authentication.domain.entities import SessionLookup
from src.modules.authentication.domain.value_objects import Credentials
from src.modules.authentication.domain.entities import RequestMetadata

from src.modules.shared.application.enums import Role
from src.modules.user.application.enums import Gender
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Email, Phone


# REQUEST
class LoginRequest(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(str_strip_whitespace=True)

    @staticmethod
    def to_credentials(form_data: OAuth2PasswordRequestFormStrict) -> Credentials:
        return Credentials(email=form_data.username, password=form_data.password)

    @staticmethod
    def extract_metadata(request: Request) -> "RequestMetadata":
        """Build request metadata used to construct SessionRequest at login."""
        from src.modules.authentication.presentation.schemas import RequestMetadata

        ip_address = request.headers.get("x-forwarded-for") or request.headers.get(
            "x-real-ip"
        )

        if ip_address is None:
            if request.client is None:
                raise ValueError(
                    "Unable to determine client IP address for login request."
                )
            ip_address = request.client.host

        return RequestMetadata(
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


class RegisterRequest(BaseModel):
    """Public self-registration request.

    Restricts role to non-privileged values (EMPLOYER, CANDIDATE).
    ADMIN accounts can only be created via the user module's admin-only endpoint.
    """

    first_name: str = Field(
        title="First Name (Required)",
        min_length=3,
        max_length=100,
        examples=["John", "Jane"],
    )
    last_name: str = Field(
        title="Last Name (Required)",
        min_length=3,
        max_length=100,
        examples=["Doe", "Smith"],
    )
    preferred_name: Optional[str] = Field(
        default=None,
        title="Preferred Name (Optional)",
        max_length=100,
        examples=["Joe", "Jan"],
    )
    gender: Gender = Field(
        title="Gender (Required)",
        examples=[Gender.MALE.value, Gender.FEMALE.value],
    )
    birthdate: date = Field(
        title="Birthdate (Required)",
        examples=["1995-01-01"],
    )
    email: str = Field(
        title="Email (Required)",
        min_length=3,
        max_length=100,
        examples=["johndoe@domain.com"],
    )
    phone: Optional[str] = Field(
        default=None,
        title="Phone (Optional)",
        examples=["+555472664275"],
    )
    password: str = Field(
        title="Password (Required)",
        min_length=8,
        max_length=64,
        examples=["MyP@ssword123"],
    )
    role: Role = Field(
        default=Role.CANDIDATE,
        title="Role (Optional)",
        description="The role to register as. ADMIN is not permitted here.",
        examples=[Role.EMPLOYER.value, Role.CANDIDATE.value],
    )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s'-]+$", value):
            raise ValueError(
                "Name must contain only letters, spaces, apostrophes, and hyphens."
            )
        return value

    @field_validator("preferred_name")
    @classmethod
    def validate_preferred_name(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value: date) -> date:
        today = date.today()
        if value > today:
            raise ValueError("Birthdate cannot be a future date.")
        if value < date(1900, 1, 1):
            raise ValueError("Birthdate cannot be before January 1, 1900.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", value):
            raise ValueError("Invalid email address.")
        return value.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if isinstance(value, str) and value.strip() == "":
            return None
        stripped = re.sub(r"[\+\-\(\)]", "", value)
        if not stripped.isdigit():
            raise ValueError(
                "Phone number must contain only digits, '+', '-', '(' and ')'."
            )
        if not (7 <= len(stripped) <= 15):
            raise ValueError("Phone number must have between 7 and 15 digits.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character.")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, role: Role) -> Role:
        if role == Role.ADMIN:
            raise ValueError("Cannot self-register with the ADMIN role.")
        return role

    model_config = ConfigDict(
        title="RegisterRequest",
        str_strip_whitespace=True,
        extra="forbid",
        validate_default=True,
        validate_assignment=True,
        validate_return=True,
        json_schema_extra={
            "description": "Request model for public self-registration (EMPLOYER or CANDIDATE only).",
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "preferred_name": "Joe",
                "gender": Gender.MALE.value,
                "birthdate": "1995-01-01",
                "email": "johndoe@domain.com",
                "phone": "+555472664275",
                "password": "MyP@ssword123",
                "role": Role.CANDIDATE.value,
            },
        },
    )

    def to_entity(self) -> User:
        return User(
            name=Name(
                first_name=self.first_name,
                last_name=self.last_name,
                preferred_name=self.preferred_name,
            ),
            gender=self.gender,
            birthdate=self.birthdate,
            email=Email(self.email),
            phone=Phone(self.phone) if self.phone else None,
            password=self.password,
            role=self.role,
        )
