from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event, Hint

from src.core.logging_config import configure_logging
from src.core.middleware.logging import RequestLoggingMiddleware
from src.core.config import settings


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


app = FastAPI(generate_unique_id_function=custom_generate_unique_id, lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
