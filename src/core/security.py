import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from typing import Any, Tuple
from datetime import datetime, timedelta, timezone

import structlog

import hashlib
import secrets

from src.core.config import settings
from src.modules.shared.presentation.exceptions import StandardException
from src.modules.authentication.presentation.exceptions import (
    HashingException,
)

logger = structlog.get_logger(__name__)

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)


def hash_password(password: str) -> str:
    try:
        return password_hash.hash(password)
    except StandardException:
        raise
    except Exception as e:
        logger.opt(exception=e).error("An error occurred during password hashing.")
        raise HashingException()


def create_refresh_token() -> Tuple[str, str]:
    """
    Returns (raw_token, token_hash).
    raw_token → gửi cho client (cookie/body).
    token_hash → lưu vào DB.
    """
    raw = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return (raw, token_hash)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
