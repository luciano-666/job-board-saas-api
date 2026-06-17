import pytest
from collections.abc import AsyncGenerator

from httpx import ASGITransport, AsyncClient

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


from src.core.config import settings
from src.main import app
from src.shared.adapters.models import Base
from src.core.dependencies import get_db


pytest_plugins = ["anyio"]


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        str(settings.TEST_DATABASE_URI),
        poolclass=NullPool,
    )

    yield engine

    await engine.dispose()


@pytest.fixture(scope="session")
async def setup_database(
    test_engine,
) -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db(
    test_engine,
    setup_database,
) -> AsyncGenerator[AsyncSession, None]:
    conn = await test_engine.connect()
    trans = await conn.begin()

    session_factory = async_sessionmaker(
        bind=conn,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        async with session_factory() as session:
            yield session
    finally:
        await trans.rollback()
        await conn.close()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)
