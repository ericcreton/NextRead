import os
from pathlib import Path
from sqlalchemy import JSON, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
(ROOT / 'data').mkdir(exist_ok=True)
engine = create_engine(os.getenv('DATABASE_URL', f'sqlite:///{ROOT / "data/nextread.db"}'))
Session = sessionmaker(engine)

class Base(DeclarativeBase):
    pass

class Book(Base):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    authors: Mapped[str] = mapped_column(String)
    year: Mapped[str] = mapped_column(String)
    average_rating: Mapped[float] = mapped_column(Float)
    ratings_count: Mapped[int] = mapped_column(Integer)
    genres: Mapped[list] = mapped_column(JSON)

def serialize(book):
    return {key: getattr(book, key) for key in ('id', 'title', 'authors', 'year', 'average_rating', 'ratings_count', 'genres')}
