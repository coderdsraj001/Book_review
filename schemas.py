from pydantic import BaseModel, ConfigDict

class BookCreate(BaseModel):
    title: str
    author: str
    model_config = ConfigDict()

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    model_config = ConfigDict(from_attributes=True)

class ReviewCreate(BaseModel):
    rating: float
    comment: str
    model_config = ConfigDict()

class ReviewResponse(BaseModel):
    id: int
    book_id: int
    rating: float
    comment: str
    model_config = ConfigDict(from_attributes=True)