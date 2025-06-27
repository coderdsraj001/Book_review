from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uvicorn
import json
import logging

from database import SessionLocal, Book, Review
from schemas import BookCreate, BookResponse, ReviewCreate, ReviewResponse
from cache import MockRedis, logger

logging.basicConfig(level=logging.INFO)

mock_redis = MockRedis()

app = FastAPI(title="Book Review Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/books", response_model=List[BookResponse])
def get_books(db: Session = Depends(get_db)):
    cache_key = "books_all"
    try:
        cached_books = mock_redis.get(cache_key)
        if cached_books:
            logger.info("Cache hit for books")
            return json.loads(cached_books)
    except Exception as e:
        logger.warning(f"Cache unavailable or error: {str(e)}. Falling back to database.")

    try:
        books = db.query(Book).all()
        books_response = [BookResponse.model_validate(book) for book in books]
        books_json = json.dumps([book.model_dump() for book in books_response])
        mock_redis.set(cache_key, books_json, ex=60)
        return books_response
    except Exception as e:
        logger.error(f"Database query error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = Book(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    try:
        mock_redis.set("books_all", None)
        logger.info("Invalidated books cache after new book creation")
    except Exception as e:
        logger.warning(f"Cache invalidation error: {str(e)}")
    return db_book

@app.get("/books/{book_id}/reviews", response_model=List[ReviewResponse])
def get_book_reviews(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book.reviews

@app.post("/books/{book_id}/reviews", response_model=ReviewResponse, status_code=201)
def create_review(book_id: int, review: ReviewCreate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db_review = Review(**review.model_dump(), book_id=book_id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)