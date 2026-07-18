from redis.asyncio import Redis, ConnectionPool

from src.core.config import settings

_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True,
)


def get_redis_client() -> Redis:
    return Redis(connection_pool=_pool)
