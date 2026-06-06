import random
import string
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

# from httpx import AsyncClient
from src.auth.schemas import UserCreate, UserPublic
from src.auth.models import UserRole
from src.auth.repositories import UserRepository
# from app.core.config import settings


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def random_id() -> uuid.UUID:
    return uuid.uuid4()


async def create_random_user(db: AsyncSession, email: str | None = None) -> UserPublic:
    if not email:
        email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.employer)
    repo = UserRepository(db)
    user = await repo.create(payload=user_in, hashed_password=random_lower_string())
    return user
