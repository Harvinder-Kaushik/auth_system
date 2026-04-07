import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

# Use SQLite in-memory database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Create all tables in test database
Base.metadata.create_all(bind=engine)

# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db():
    """Database session for tests."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    # Use a shorter password to avoid bcrypt issues
    password = "Test1234"
    user = User(
        email="test@example.com",
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_inactive(db: Session):
    """Create an inactive test user."""
    password = "Test1234"
    user = User(
        email="inactive@example.com",
        hashed_password=hash_password(password),
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_tokens(client: TestClient, test_user: User):
    """Get valid access and refresh tokens."""
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test1234",
        },
    )
    assert response.status_code == 200
    data = response.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }
