import pytest
import asyncio
import uuid
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.main import app
from src.infrastructure.database.models import Base
from src.infrastructure.database.models_user import User
from src.infrastructure.database.connection import get_db
from src.api.auth.jwt import create_access_token, get_password_hash

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Test user credentials
TEST_USER_ID = str(uuid.uuid4())
TEST_USERNAME = "testuser"
TEST_EMAIL = "test@mattilda.com"
TEST_PASSWORD = "testpassword123"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for authentication."""
    user = User(
        id=uuid.UUID(TEST_USER_ID),
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Generate a valid JWT token for the test user."""
    return create_access_token(
        data={"sub": test_user.username, "user_id": str(test_user.id)}
    )


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Return authorization headers with the test token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def auth_client(auth_token: str) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated HTTP client for testing protected endpoints."""
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {auth_token}"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
