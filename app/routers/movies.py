import math

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.schemas import MovieCreate, MovieUpdate, MovieOut, MoviesResponse
from app.services import movie_service
from app.services.auth_service import get_current_user
from app.models import User
from typing import Optional

router = APIRouter(prefix="/movies", tags=["movies"])

@router.get("/", response_model=MoviesResponse)
def list_movies(
    search: Optional[str] = None,
    year_from: Optional[int] = None,
    rating_min: Optional[float] = None,
    sort_by: Optional[str] = None,
    page: int = 1,
    limit: int = 3,
    session: Session = Depends(get_session)
):
    skip = (page - 1) * limit
    movies = movie_service.get_all(session, search, year_from, rating_min, sort_by, skip, limit)
    total = movie_service.count_all(session, search, year_from, rating_min)
    total_pages = math.ceil(total / limit)
    return MoviesResponse(movies=movies, total=total, page=page, total_pages=total_pages)


@router.get("/{movie_id}", response_model=MovieOut)
def get_movie(movie_id: int, session: Session = Depends(get_session)):
    movie = movie_service.get_by_id(session, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.post("/", response_model=MovieOut, status_code=201)
def create_movie(
        data: MovieCreate,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
    ):
    return movie_service.create(session, data)


@router.patch("/{movie_id}", response_model=MovieOut)
def update_movie(
        movie_id: int,
        data: MovieUpdate,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)):
    movie = movie_service.update(session, movie_id, data)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.delete("/{movie_id}", status_code=204)
def delete_movie(
        movie_id: int,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    movie = movie_service.delete(session, movie_id)
    if not movie_service.delete(session, movie_id):
        raise HTTPException(status_code=404, detail="Movie not found")