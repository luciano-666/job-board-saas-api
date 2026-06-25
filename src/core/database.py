from typing import AsyncIterator
import structlog

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import settings
from src.modules.shared.presentation.exceptions import StandardException

logger = structlog.get_logger(__name__)


engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

pg_async_engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
    echo=settings.APPLICATION_ENVIRONMENT_DEBUG,
    future=True,
)

PGAsyncSession = async_sessionmaker(
    bind=pg_async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with PGAsyncSession() as session:
        try:
            yield session
            await session.commit()
        except StandardException:
            await session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(
                "An asynchronous database error occurred during the session.",
                exc_info=e,
            )
            await session.rollback()
            raise
        except Exception as e:
            logger.error(
                "An unexpected error occurred during the asynchronous database session.",
                exc_info=e,
            )
            await session.rollback()
            raise
        finally:
            await session.close()
