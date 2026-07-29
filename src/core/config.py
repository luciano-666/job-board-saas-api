from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, PostgresDsn, AnyUrl, AnyHttpUrl, model_validator

import json

from src.modules.shared.application.enums import ApplicationEnvironment


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    ENVIRONMENT: str = "local"  # local | staging | production

    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    TEST_DB: str = "test_db"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def TEST_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.TEST_DB,
        )

    # COOKIES
    COOKIES_MAX_AGE_SECONDS: int
    COOKIES_TOKEN_TYPE_KEY: str
    COOKIES_ACCESS_TOKEN_KEY: str
    COOKIES_ACCESS_TOKEN_PATH: str
    COOKIES_REFRESH_TOKEN_KEY: str
    COOKIES_REFRESH_TOKEN_PATH: str
    COOKIES_DEVICE_KEY: str
    COOKIES_DOMAIN: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # Sentry — optional, no-op when unset (local dev)
    SENTRY_DSN: AnyUrl | None = None

    # APPLICATION
    APPLICATION_TITLE: str
    APPLICATION_SUMMARY: str
    APPLICATION_DESCRIPTION: str
    APPLICATION_VERSION: str
    APPLICATION_CONTACT_NAME: str
    APPLICATION_CONTACT_URL: str
    APPLICATION_CONTACT_EMAIL: str
    APPLICATION_CONTACT_PHONE: str
    APPLICATION_ENVIRONMENT: str
    APPLICATION_PORT: int
    APPLICATION_CONNECT_TIMEOUT_SECONDS: int
    APPLICATION_URL: AnyHttpUrl
    APPLICATION_TABLE_PREFIX: str

    # APPLICATION
    @computed_field
    @property
    def APPLICATION_ENVIRONMENT_DEBUG(self) -> bool:  # noqa
        if self.APPLICATION_ENVIRONMENT == ApplicationEnvironment.PRODUCTION.value:
            return False
        else:
            return True

    # JWT
    JWT_ISSUER: str
    JWT_AUDIENCE: str
    JWT_SIGNING_KEY_PASSWORD: str
    JWT_ENCRYPTION_KEY_PASSWORD: str
    JWT_SIGNING_PRIVATE_KEY_PATH: str
    JWT_SIGNING_PUBLIC_KEY_PATH: str
    JWT_ENCRYPTION_PRIVATE_KEY_PATH: str
    JWT_ENCRYPTION_PUBLIC_KEY_PATH: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int
    JWT_HASH_FINGERPRINT: str

    # AUTH
    AUTH_BEARER_TOKEN_SCHEME_NAME: str
    AUTH_BEARER_TOKEN_SCHEME_DESCRIPTION: str
    AUTH_API_KEY_SCHEME_NAME: str
    AUTH_API_KEY_SCHEME_DESCRIPTION: str
    AUTH_API_KEY_HEADER: str
    AUTH_API_KEY_HEADER_DESCRIPTION: str

    # SECURITY SETTINGS
    SECURITY_ALLOW_ORIGINS: list[str] | str = []
    SECURITY_ALLOW_HEADERS: list[str] | str = []
    SECURITY_ALLOW_METHODS: list[str] | str = []
    SECURITY_EMAIL_ALLOWED_DOMAINS: list[str] | str = []
    SECURITY_ADMIN_EMAIL: str
    SECURITY_ADMIN_PASSWORD: str

    @model_validator(mode="before")
    @classmethod
    def parse_list_fields(cls, values: dict) -> dict:
        for field in (
            "SECURITY_ALLOW_ORIGINS",
            "SECURITY_ALLOW_HEADERS",
            "SECURITY_ALLOW_METHODS",
            "SECURITY_EMAIL_ALLOWED_DOMAINS",
        ):
            v = values.get(field)
            if isinstance(v, str):
                v = v.strip()
                if v.startswith("["):
                    try:
                        values[field] = json.loads(v)
                    except json.JSONDecodeError:
                        # strip brackets, split by comma
                        values[field] = [
                            i.strip().strip("\"'") for i in v[1:-1].split(",")
                        ]
                elif "," in v:
                    values[field] = [i.strip() for i in v.split(",")]
        return values

    # COOKIES
    @computed_field
    @property
    def COOKIES_ACCESS_TOKEN_MAX_AGE(self) -> int:  # noqa
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @computed_field
    @property
    def COOKIES_REFRESH_TOKEN_MAX_AGE(self) -> int:  # noqa
        return self.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    # SECURITY
    @computed_field
    @property
    def SECURITY_NO_AUTH_PATHS(self) -> list[dict[str, str]]:  # noqa
        return [
            # AUTHENTICATION
            {"endpoint": "/api/v1/authentication/login/", "method": "POST"},
            {"endpoint": "/api/v1/authentication/login", "method": "POST"},
            {"endpoint": "/api/v1/authentication/logout/", "method": "DELETE"},
            {"endpoint": "/api/v1/authentication/logout", "method": "DELETE"},
            {"endpoint": "/api/v1/authentication/register/", "method": "POST"},
            {"endpoint": "/api/v1/authentication/register", "method": "POST"},
            # EXAMPLE
            {"endpoint": "/api/v1/example/", "method": "POST"},
            {"endpoint": "/api/v1/example", "method": "POST"},
            # HEALTH
            {"endpoint": "/health/", "method": "GET"},
            {"endpoint": "/health", "method": "GET"},
            # PASSWORD RESET
            {
                "endpoint": "/api/v1/authentication/password-reset/request/",
                "method": "POST",
            },
            {
                "endpoint": "/api/v1/authentication/password-reset/request",
                "method": "POST",
            },
            {
                "endpoint": "/api/v1/authentication/password-reset/confirm/",
                "method": "POST",
            },
            {
                "endpoint": "/api/v1/authentication/password-reset/confirm",
                "method": "POST",
            },
            # JOBS — public read
            {"endpoint": "/api/v1/jobs/{job_id}/", "method": "GET"},
            {"endpoint": "/api/v1/jobs/{job_id}", "method": "GET"},
        ]

    @computed_field
    @property
    def SECURITY_USER_ALLOWED_PATHS(self) -> list[dict[str, str]]:  # noqa
        return [
            *self.SECURITY_NO_AUTH_PATHS,
            # AUTHENTICATION
            {"endpoint": "/api/v1/authentication/refresh/", "method": "PATCH"},
            {"endpoint": "/api/v1/authentication/refresh", "method": "PATCH"},
            # USER
            {"endpoint": "/api/v1/user/me", "method": "GET"},
            {"endpoint": "/api/v1/user/me/", "method": "GET"},
            {"endpoint": "/api/v1/user/me/", "method": "PATCH"},
            {"endpoint": "/api/v1/user/me", "method": "PATCH"},
            {"endpoint": "/api/v1/user/me/", "method": "DELETE"},
            {"endpoint": "/api/v1/user/me", "method": "DELETE"},
        ]

    @computed_field
    @property
    def SECURITY_EMPLOYER_ALLOWED_PATHS(self) -> list[dict[str, str]]:
        return [
            *self.SECURITY_USER_ALLOWED_PATHS,
            # JOBS — employer-owned job management (endpoints added in JOBS-8+)
            {"endpoint": "/api/v1/jobs/", "method": "POST"},
            {"endpoint": "/api/v1/jobs", "method": "POST"},
            {"endpoint": "/api/v1/jobs/{job_id}/", "method": "PATCH"},
            {"endpoint": "/api/v1/jobs/{job_id}", "method": "PATCH"},
            {"endpoint": "/api/v1/jobs/{job_id}/publish/", "method": "PATCH"},
            {"endpoint": "/api/v1/jobs/{job_id}/publish", "method": "PATCH"},
            {"endpoint": "/api/v1/jobs/{job_id}/close/", "method": "PATCH"},
            {"endpoint": "/api/v1/jobs/{job_id}/close", "method": "PATCH"},
            {"endpoint": "/api/v1/jobs/{job_id}/archive/", "method": "PATCH"},
            {"endpoint": "/api/v1/jobs/{job_id}/archive", "method": "PATCH"},
        ]

    @computed_field
    @property
    def SECURITY_ADMIN_ALLOWED_PATHS(self) -> list[dict[str, str]]:  # noqa
        return [
            *self.SECURITY_EMPLOYER_ALLOWED_PATHS,
            # HEALTH
            {"endpoint": "/api/v1/alembic-version/", "method": "GET"},
            {"endpoint": "/api/v1/alembic-version", "method": "GET"},
            {"endpoint": "/api/v1/user/", "method": "POST"},
            {"endpoint": "/api/v1/user", "method": "POST"},
            {"endpoint": "/api/v1/user/{user_id}/suspend/", "method": "PATCH"},
            {"endpoint": "/api/v1/user/{user_id}/suspend", "method": "PATCH"},
            {"endpoint": "/api/v1/user/{user_id}/activate/", "method": "PATCH"},
            {"endpoint": "/api/v1/user/{user_id}/activate", "method": "PATCH"},
        ]

    @computed_field
    @property
    def SECURITY_API_KEY_ALLOWED_PATHS(self) -> list[dict[str, str]]:  # noqa
        return []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if ":" in self.POSTGRES_SERVER:
            host_parts = self.POSTGRES_SERVER.split(":")
            object.__setattr__(self, "POSTGRES_SERVER", host_parts[0])
            if len(host_parts) > 1 and not self.POSTGRES_PORT:
                object.__setattr__(self, "POSTGRES_PORT", int(host_parts[1]))

        if self.APPLICATION_ENVIRONMENT not in [
            env.value for env in ApplicationEnvironment
        ]:
            raise ValueError(
                f"Invalid execution environment: {self.APPLICATION_ENVIRONMENT}. "
                f"The environment must be {', '.join([env.value for env in ApplicationEnvironment])} (case-sensitive). "
                f"Please check your .env file."
            )

    PASSWORD_RESET_TOKEN_EXPIRE_SECONDS: int = 900  # 15 minutes


settings = Settings()
