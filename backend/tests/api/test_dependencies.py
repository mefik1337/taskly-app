from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.api.dependencies import Repository
from app.factory import create_app
from app.features.todos.models import TodoRecord
from app.features.todos.schemas import TodoCreate


@pytest.fixture
def pooled_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'taskly.db'}", connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture
def app_client(pooled_engine, serve_engine):
    serve_engine(pooled_engine)
    app = create_app("sqlite://")

    @app.post("/api/failing-write")
    def failing_write(repo: Repository):
        now = datetime.now(timezone.utc)
        repo.session.add(TodoRecord(title="Half written", created_at=now, updated_at=now))
        repo.session.flush()
        raise RuntimeError("handler failed")

    @app.post("/api/held-write", status_code=201)
    def held_write(repo: Repository):
        return repo.create(TodoCreate(title="Task"))

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_request_that_fails_mid_write_returns_500_and_persists_nothing(app_client):
    assert app_client.post("/api/failing-write").status_code == 500
    assert app_client.get("/api/todos").json() == []


def test_request_that_fails_mid_write_releases_its_connection(app_client, pooled_engine):
    app_client.post("/api/failing-write")
    assert pooled_engine.pool.checkedout() == 0


def test_successful_request_releases_its_connection(app_client, pooled_engine):
    assert app_client.post("/api/held-write").status_code == 201
    assert pooled_engine.pool.checkedout() == 0


def test_each_request_sees_writes_committed_by_earlier_requests(app_client):
    created = app_client.post("/api/todos", json={"title": "Task"}).json()
    assert app_client.get("/api/todos").json() == [created]
