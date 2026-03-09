from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import reset_settings_cache
from app.db import reset_engine


@pytest.fixture()
def app(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "test_chat.db"
    monkeypatch.setenv("CHAT_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("CHAT_AUTO_CREATE_SCHEMA", "true")

    reset_settings_cache()
    reset_engine()

    from app.main import create_app

    application = create_app()
    yield application

    reset_settings_cache()
    reset_engine()


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def register_and_login(
    client: TestClient, username: str, password: str = "password123"
) -> tuple[str, str]:
    register_response = client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    data = login_response.json()
    return data["access_token"], data["refresh_token"]
