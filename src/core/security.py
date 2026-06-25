import structlog
from pwdlib import PasswordHash

from src.modules.authentication.presentation.exceptions import HashingException
from src.modules.shared.presentation.exceptions import StandardException

logger = structlog.get_logger(__name__)

# PASSWORD HASHING
password_hasher = PasswordHash.recommended()


async def hash_password(password: str) -> str:
    try:
        return password_hasher.hash(password)
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during password hashing.", exc_info=e)
        raise HashingException()


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(plain_password, hashed_password)
    except StandardException:
        raise
    except Exception as e:
        logger.error("An error occurred during password verification.", exc_info=e)
        raise HashingException()
