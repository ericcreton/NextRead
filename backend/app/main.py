from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import select
from .db import Base, Book, Session, engine, serialize
from .hybrid import load_recommender
from backend.ml.ranking import diversify

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with Session() as session:
        app.state.model = load_recommender([serialize(b) for b in session.scalars(select(Book))])
    yield

app = FastAPI(title='NextRead API', version='0.1.0', lifespan=lifespan)

class Rating(BaseModel):
    book_id: StrictInt
    rating: int = Field(ge=1, le=5, strict=True)

class RecommendationRequest(BaseModel):
    ratings: list[Rating] = Field(default_factory=list, max_length=1000)
    limit: int = Field(default=12, ge=1, le=50)
    diverse: bool = False

@app.get('/api/health')
def health():
    return {'status': 'ok', 'books': len(app.state.model.books), 'model': getattr(app.state.model, 'version', 'content-baseline')}

@app.get('/api/books')
def books(q: str = Query(default='', max_length=200), offset: int = Query(default=0, ge=0), limit: int = Query(default=24, ge=1, le=100)):
    query = q.casefold().strip()
    matches = [b for b in app.state.model.books.values() if query in (b['title'] + ' ' + b['authors']).casefold()]
    matches.sort(key=lambda b: -b['ratings_count'])
    return {'books': matches[offset:offset+limit], 'total': len(matches)}

@app.post('/api/recommendations')
def recommendations(body: RecommendationRequest):
    ratings = {r.book_id: r.rating for r in body.ratings}
    if len(ratings) != len(body.ratings):
        raise HTTPException(422, 'Duplicate book IDs are not allowed.')
    if any(bid not in app.state.model.books for bid in ratings):
        raise HTTPException(422, 'Unknown book ID. Refresh the catalog and try again.')
    result = app.state.model.recommend(ratings, len(app.state.model.books) if body.diverse else body.limit)
    if body.diverse:
        result['books'] = diversify(result['books'], body.limit)
    result['ranking_policy'] = 'discovery-v1' if body.diverse else 'score-only'
    return result
