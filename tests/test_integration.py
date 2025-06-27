import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db
from database import Base
from cache import MockRedis

# Setup test database
TEST_DATABASE_URL = "sqlite:///./test_book_reviews.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override dependency for test database
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture
async def async_client():
    with TestClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_redis(monkeypatch):
    redis = MockRedis()
    monkeypatch.setattr("main.mock_redis", redis)
    return redis

@pytest.mark.asyncio
async def test_get_books_empty(async_client, db_session):
    response = async_client.get("/books")
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_create_and_get_books(async_client, db_session, mock_redis):
    # Create a book
    book_data = {"title": "Test Book", "author": "Test Author"}
    response = async_client.post("/books", json=book_data)
    assert response.status_code == 201
    book = response.json()
    assert book["title"] == "Test Book"
    assert book["author"] == "Test Author"
    assert "id" in book

    # Get books (should hit database first, then cache)
    response = async_client.get("/books")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test Book"

    # Verify cache was set
    cached = mock_redis.get("books_all")
    assert cached is not None

    # Get books again (should hit cache)
    response = async_client.get("/books")
    assert response.status_code == 200
    assert len(response.json()) == 1

@pytest.mark.asyncio
async def test_create_and_get_reviews(async_client, db_session):
    # Create a book
    book_data = {"title": "Test Book", "author": "Test Author"}
    response = async_client.post("/books", json=book_data)
    book_id = response.json()["id"]

    # Create a review
    review_data = {"rating": 4.5, "comment": "Great book!"}
    response = async_client.post(f"/books/{book_id}/reviews", json=review_data)
    assert response.status_code == 201
    review = response.json()
    assert review["rating"] == 4.5
    assert review["comment"] == "Great book!"
    assert review["book_id"] == book_id

    # Get reviews
    response = async_client.get(f"/books/{book_id}/reviews")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["rating"] == 4.5

@pytest.mark.asyncio
async def test_get_reviews_invalid_book(async_client, db_session):
    response = async_client.get("/books/999/reviews")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"

@pytest.mark.asyncio
async def test_create_review_invalid_book(async_client, db_session):
    review_data = {"rating": 4.5, "comment": "Great book!"}
    response = async_client.post("/books/999/reviews", json=review_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"