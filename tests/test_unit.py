import pytest
from unittest.mock import patch, Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Book, Review
from cache import MockRedis
from main import get_books, create_book
from schemas import BookCreate, BookResponse
import json

# Setup test database
TEST_DATABASE_URL = "sqlite:///./test_book_reviews.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_create_book(db_session):
    book_data = BookCreate(title="Test Book", author="Test Author")
    book = create_book(book_data, db_session)
    
    assert book.title == "Test Book"
    assert book.author == "Test Author"
    assert book.id is not None
    
    # Verify book in database
    db_book = db_session.query(Book).filter(Book.id == book.id).first()
    assert db_book is not None
    assert db_book.title == "Test Book"

def test_get_books_from_database(db_session):
    # Add a book to the database
    book = Book(title="Test Book", author="Test Author")
    db_session.add(book)
    db_session.commit()
    
    # Mock cache to simulate miss
    with patch('main.mock_redis.get', return_value=None) as mock_get:
        with patch('main.mock_redis.set') as mock_set:
            books = get_books(db=db_session)
            
            assert len(books) == 1
            assert isinstance(books[0], BookResponse)
            assert books[0].title == "Test Book"
            assert books[0].author == "Test Author"
            mock_get.assert_called_once_with("books_all")
            mock_set.assert_called_once()

def test_get_books_cache_hit():
    # Mock cache hit
    cached_data = [
        {"id": 1, "title": "Cached Book", "author": "Cached Author"}
    ]
    with patch('main.mock_redis.get', return_value=json.dumps(cached_data)):
        books = get_books(db=Mock())
        
        assert len(books) == 1
        assert books[0]["id"] == 1
        assert books[0]["title"] == "Cached Book"
        assert books[0]["author"] == "Cached Author"

def test_create_review(db_session):
    # Add a book
    book = Book(title="Test Book", author="Test Author")
    db_session.add(book)
    db_session.commit()
    
    # Add a review
    review = Review(book_id=book.id, rating=4.5, comment="Great book!")
    db_session.add(review)
    db_session.commit()
    
    # Verify review in database
    db_review = db_session.query(Review).filter(Review.book_id == book.id).first()
    assert db_review is not None
    assert db_review.rating == 4.5
    assert db_review.comment == "Great book!"