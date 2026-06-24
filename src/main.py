from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.openapi.utils import get_openapi


import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event, Hint

from src.core.logging_config import configure_logging
from src.core.middleware import (
    RequestLoggingMiddleware,
    DeviceIdMiddleware,
    ResponseFormattingMiddleware,
)
from src.core.config import settings
from src.core.exception_handler import (
    validation_exception_handler,
    http_exception_handler,
    internal_exception_handler,
)

from src.modules.authentication.presentation.routers import (
    router as authentication_router,
)
from src.modules.user.presentation.routers import router as user_router


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


def _before_send(event: Event, hint: Hint) -> Event | None:
    """Enrich every Sentry event with user_id and endpoint context.

    Sentry calls this hook synchronously before uploading the event,
    giving us a last chance to attach or scrub fields.
    Returning None drops the event entirely (useful for filtering noise).
    """
    request_data: dict = event.get("request", {})

    # --- endpoint context ---
    # Sentry's FastAPI integration already populates event["request"]["url"]
    # and event["request"]["method"]; expose them under a flat "endpoint" key
    # so they appear prominently in the Sentry issue UI.
    method = request_data.get("method", "")
    url = request_data.get("url", "")
    if method and url:
        event.setdefault("tags", {})["endpoint"] = f"{method} {url}"

    # --- user_id context ---
    # The auth dependency (added later) sets `request.state.user_id` after
    # validating the JWT.  Sentry's standard "user" interface expects a dict
    # with at least an "id" key; the Sentry UI then groups issues by user.
    user_id = (
        event.get("user", {}).get("id")  # already set by integration
        or request_data.get("user_id")  # fallback from request data
    )
    if user_id:
        event["user"] = {"id": str(user_id)}
    else:
        # Unauthenticated request — keep user dict clean, don't leak IP
        event["user"] = {"id": "anonymous"}

    return event


def _init_sentry() -> None:
    if not settings.SENTRY_DSN:
        return  # no-op in local dev when DSN is unset

    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        environment=settings.ENVIRONMENT,
        # Capture 100 % of errors; tune traces_sample_rate separately
        # once you add performance monitoring.
        traces_sample_rate=0.0,
        # Send 100 % of errors (default); lower in high-traffic prod if needed
        sample_rate=1.0,
        before_send=_before_send,
        integrations=[
            # Order matters: Starlette must come before FastAPI
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        # Don't send raw SQL values — avoids leaking PII / secrets
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    _init_sentry()
    yield


# APPLICATION
app = FastAPI(generate_unique_id_function=custom_generate_unique_id, lifespan=lifespan)

# EXCEPTION HANDLERS
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, internal_exception_handler)

# MIDDLEWARES
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.SECURITY_ALLOW_ORIGINS],
    allow_credentials=True,
    allow_methods=[str(method) for method in settings.SECURITY_ALLOW_METHODS],
    allow_headers=[str(header) for header in settings.SECURITY_ALLOW_HEADERS],
)
app.add_middleware(ResponseFormattingMiddleware)
app.add_middleware(DeviceIdMiddleware)

# ROUTERS
routers = [
    authentication_router,
    user_router,
]

for router in routers:
    app.include_router(router)


# CUSTOM OPENAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APPLICATION_TITLE,
        summary=settings.APPLICATION_SUMMARY,
        description=settings.APPLICATION_DESCRIPTION,
        version=settings.APPLICATION_VERSION,
        tags=[
            {
                "name": "Authentication",
                "description": "Endpoints for user authentication and authorization.",
            },
            {
                "name": "Example",
                "description": "Example module for demonstrating application features.",
            },
            {
                "name": "Health",
                "description": "Endpoints for monitoring the health of the application.",
            },
            {
                "name": "User",
                "description": "Endpoints for managing user resources.",
            },
        ],
        contact={
            "name": settings.APPLICATION_CONTACT_NAME,
            "url": settings.APPLICATION_CONTACT_URL,
            "email": settings.APPLICATION_CONTACT_EMAIL,
            "phone": settings.APPLICATION_CONTACT_PHONE,
        },
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        settings.AUTH_BEARER_TOKEN_SCHEME_NAME: {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        settings.AUTH_API_KEY_SCHEME_NAME: {
            "type": "apiKey",
            "in": "header",
            "name": settings.AUTH_API_KEY_HEADER,
            "description": "API Key necessary to access the API endpoints.",
        },
    }

    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi
