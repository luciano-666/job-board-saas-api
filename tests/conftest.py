import pytest
from collections.abc import AsyncGenerator
from datetime import date

from httpx import ASGITransport, AsyncClient

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


from src.core.config import settings
from src.main import app
from src.modules.shared.infrastructure.models import Base
from src.core.database import get_async_session

from src.modules.user.application.use_cases import UserUseCases
from src.modules.user.infrastructure.repositories import SqlAlchemyUserRepository
from src.modules.shared.application.use_cases import SharedUseCases
from src.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository
from src.modules.shared.application.enums import Role
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Email
from src.modules.user.application.enums import Gender

from tests.utils import random_email


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

    app.dependency_overrides[get_async_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_async_session, None)


async def _create_user_with_role(
    db: AsyncSession, role: Role, password: str = "P@ssword1!"
) -> User:
    user_repo = SqlAlchemyUserRepository(session=db)
    job_repo = SqlAlchemyJobRepository(session=db)
    shared = SharedUseCases(user_repository=user_repo, job_repository=job_repo)
    use_cases = UserUseCases(repository=user_repo, shared_service=shared)

    user = User(
        name=Name(first_name="Test", last_name="User"),
        gender=Gender.MALE,
        birthdate=date(1990, 1, 1),
        email=Email(random_email()),
        password=password,
        role=role,
    )
    created = await use_cases.create(user)
    await db.flush()
    return created


@pytest.fixture
async def employer_client(
    client: AsyncClient, db: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """An AsyncClient already logged in as an EMPLOYER (cookies set)."""
    password = "P@ssword1!"
    user = await _create_user_with_role(db, Role.EMPLOYER, password=password)

    client.cookies.set("device_id", "test-employer-device")
    response = await client.post(
        "/api/v1/authentication/login/",
        data={
            "grant_type": "password",
            "username": str(user.email),
            "password": password,
        },
    )
    print(response.headers.get_list("set-cookie"))
    assert response.status_code == 200, response.text

    yield client


@pytest.fixture
async def candidate_client(
    client: AsyncClient, db: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """An AsyncClient logged in as a CANDIDATE — used to verify 403 on employer-only routes."""
    password = "P@ssword1!"
    user = await _create_user_with_role(db, Role.CANDIDATE, password=password)

    client.cookies.set("device_id", "test-candidate-device")
    response = await client.post(
        "/api/v1/authentication/login/",
        data={
            "grant_type": "password",
            "username": str(user.email),
            "password": password,
        },
    )
    print(response.headers.get_list("set-cookie"))
    assert response.status_code == 200, response.text

    yield client
