import random
import string
import uuid

# from sqlalchemy.ext.asyncio import AsyncSession

# from httpx import AsyncClient
# from app.core.config import settings


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def random_id() -> uuid.UUID:
    return uuid.uuid4()


def extract_payload(response_json: dict) -> dict:
    """Unwrap the double-nested `data` produced by ResponseFormattingMiddleware
    for response models that themselves have a `data` field."""
    return response_json["details"]["data"]
