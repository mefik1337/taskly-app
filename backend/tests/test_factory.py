from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app.core.config as config
import app.core.lifespan as lifespan_module
from app.factory import create_app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", Mock())
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_create_app_describes_the_taskly_api():
    app = create_app("sqlite://")
    assert (app.title, app.version) == ("Taskly API", "1.0.0")


def test_create_app_stores_the_explicit_database_url():
    assert create_app("postgresql+psycopg://h/db").state.database_url == "postgresql+psycopg://h/db"


def test_create_app_resolves_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert create_app().state.database_url == "postgresql+psycopg://env/db"


def test_create_app_registers_health_and_todo_routes():
    paths = create_app("sqlite://").openapi()["paths"]
    assert {path: set(operations) for path, operations in paths.items()} == {
        "/api/health": {"get"},
        "/api/todos": {"get", "post"},
        "/api/todos/{todo_id}": {"get", "patch", "delete"},
    }


def test_created_app_serves_requests_against_its_database(monkeypatch, sqlite_engine):
    engine_factory = Mock(return_value=sqlite_engine)
    monkeypatch.setattr(lifespan_module, "create_database_engine", engine_factory)
    with TestClient(create_app("sqlite://")) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        created = client.post("/api/todos", json={"title": "Write tests"})
        assert created.status_code == 201
        listed = client.get("/api/todos").json()
    engine_factory.assert_called_once_with("sqlite://")
    assert [todo["title"] for todo in listed] == ["Write tests"]
    assert listed[0]["id"] == created.json()["id"]
