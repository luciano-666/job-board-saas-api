from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from src.logging_config import configure_logging
from src.middleware.logging import RequestLoggingMiddleware


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(generate_unique_id_function=custom_generate_unique_id, lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
