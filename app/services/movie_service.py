from __future__ import annotations

from typing import Optional, Any, Sequence

from sqlmodel import Session, select
from app.models import Movie
from app.schemas import MovieCreate, MovieUpdate

def get_all(
    session: Session,
    search: Optional[str] = None,
    year_from: Optional[int] = None,
    rating_min: Optional[float] = None,
    sort_by: Optional[str] = None,
    skip: int = 0,
    limit: int = 3,
) -> Sequence[Any]:
    query = select(Movie)

    if search:
        query = query.where(
            (Movie.title.ilike(f"%{search}%")) |
            (Movie.director.ilike(f"%{search}%"))
        )

    if year_from:
        query = query.where(Movie.year >= year_from)

    if rating_min:
        query = query.where(Movie.rating >= rating_min)

    if sort_by == "title":
        query = query.order_by(Movie.title)
    elif sort_by == "year_asc":
        query = query.order_by(Movie.year)
    elif sort_by == "year_desc":
        query = query.order_by(Movie.year.desc())
    elif sort_by == "rating_asc":
        query = query.order_by(Movie.rating)
    elif sort_by == "rating_desc":
        query = query.order_by(Movie.rating.desc())

    return session.exec(query.offset(skip).limit(limit)).all()

def get_by_id(session: Session, movie_id: int) -> Movie | None:
    return session.get(Movie, movie_id)

def create(session: Session, data: MovieCreate) -> Movie:
    movie = Movie(**data.model_dump())
    session.add(movie)
    session.commit()
    session.refresh(movie)
    return movie


def update(session: Session, movie_id: int, data: MovieUpdate) -> Movie | None:
    movie = session.get(Movie, movie_id)
    if not movie:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(movie, key, value)
    session.commit()
    session.refresh(movie)
    return movie


def delete(session: Session, movie_id: int) -> bool:
    movie = session.get(Movie, movie_id)
    if not movie:
        return False
    session.delete(movie)
    session.commit()
    return True

def count_all(
    session: Session,
    search: Optional[str] = None,
    year_from: Optional[int] = None,
    rating_min: Optional[float] = None,
) -> int:
    query = select(Movie)
    if search:
        query = query.where(
            (Movie.title.ilike(f"%{search}%")) |
            (Movie.director.ilike(f"%{search}%"))
        )
    if year_from:
        query = query.where(Movie.year >= year_from)
    if rating_min:
        query = query.where(Movie.rating >= rating_min)
    return len(session.exec(query).all())