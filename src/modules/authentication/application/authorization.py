import structlog
from typing import Optional
import re

from src.modules.shared.application.enums import Role
from src.modules.authentication.presentation.exceptions import StandardException
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def has_access_to_endpoint(
    path: str, method: str, role: Optional[Role] = None
) -> bool:
    try:
        logger.debug(
            f"Checking if user has access to endpoint '{path}' with method '{method}'."
        )

        if role is None:
            paths = settings.SECURITY_NO_AUTH_PATHS
        elif role == Role.ADMIN:
            paths = settings.SECURITY_ADMIN_ALLOWED_PATHS
        elif role == Role.EMPLOYER:
            paths = settings.SECURITY_EMPLOYER_ALLOWED_PATHS
        else:
            paths = settings.SECURITY_USER_ALLOWED_PATHS

        for allowed_path in paths:
            if allowed_path["method"] != method:
                continue

            pattern = allowed_path["endpoint"]
            pattern = pattern.replace("{", "(?P<").replace("}", ">[^/]+)")
            pattern = f"^{pattern}$"

            if re.match(pattern, path):
                logger.debug(
                    f"User has access to endpoint '{path}' with method '{method}'."
                )
                return True

        logger.debug(
            f"User does not have access to endpoint '{path}' with method '{method}'."
        )
        return False
    except StandardException:
        return False
    except Exception as e:
        logger.error(
            "An error occurred during has access to endpoint process.", exc_info=e
        )
        return False
