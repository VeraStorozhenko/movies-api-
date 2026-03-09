import pytest


# --- helpers ---

def create_movie(client, title="Inception", director="Nolan", year=2010, rating=8.8):
    response = client.post("/movies/", json={
        "title": title,
        "description": "A mind-bending thriller",
        "director": director,
        "year": year,
        "rating": rating
    })
    assert response.status_code == 201
    return response.json()


# --- tests ---

def test_create_movie(client):
    movie = create_movie(client)

    assert movie["title"] == "Inception"
    assert movie["director"] == "Nolan"
    assert movie["year"] == 2010
    assert movie["rating"] == 8.8
    assert "id" in movie


def test_get_movies(client):
    create_movie(client, title="Inception")
    create_movie(client, title="Matrix")

    response = client.get("/movies/")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["movies"]) == 2


def test_get_movie_by_id(client):
    movie = create_movie(client)

    response = client.get(f"/movies/{movie['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Inception"


def test_get_movie_not_found(client):
    response = client.get("/movies/999")
    assert response.status_code == 404


def test_update_movie(client):
    movie = create_movie(client)

    response = client.patch(f"/movies/{movie['id']}", json={"title": "Inception 2"})
    assert response.status_code == 200
    assert response.json()["title"] == "Inception 2"


def test_delete_movie(client):
    movie = create_movie(client)

    response = client.delete(f"/movies/{movie['id']}")
    assert response.status_code == 204

    # проверяем что удалился
    response = client.get(f"/movies/{movie['id']}")
    assert response.status_code == 404


def test_search_movies(client):
    create_movie(client, title="Inception")
    create_movie(client, title="Matrix")

    response = client.get("/movies/?search=inception")
    data = response.json()
    assert data["total"] == 1
    assert data["movies"][0]["title"] == "Inception"


def test_filter_by_year(client):
    create_movie(client, title="Old Movie", year=1990)
    create_movie(client, title="New Movie", year=2020)

    response = client.get("/movies/?year_from=2000")
    data = response.json()
    assert data["total"] == 1
    assert data["movies"][0]["title"] == "New Movie"


def test_filter_by_rating(client):
    create_movie(client, title="Bad Movie", rating=4.0)
    create_movie(client, title="Good Movie", rating=9.0)

    response = client.get("/movies/?rating_min=8")
    data = response.json()
    assert data["total"] == 1
    assert data["movies"][0]["title"] == "Good Movie"