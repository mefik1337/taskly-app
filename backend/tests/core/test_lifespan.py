import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError

from app.factory import create_app


def track_closed_connections(engine):
    closed = []
    event.listen(engine, "close", lambda dbapi_connection, record: closed.append(dbapi_connection))
    return closed


@pytest.fixture
def read_only_engine(tmp_path):
    database = tmp_path / "taskly.db"
    database.touch()
    engine = create_engine(
        f"sqlite:///file:{database.as_posix()}?mode=ro&uri=true",
        connect_args={"check_same_thread": False},
    )
    yield engine
    engine.dispose()


def test_startup_prepares_the_database_so_the_first_request_succeeds(sqlite_engine, serve_engine):
    serve_engine(sqlite_engine)
    with TestClient(create_app("sqlite://")) as client:
        response = client.get("/api/todos")
    assert (response.status_code, response.json()) == (200, [])


def test_startup_opens_the_engine_for_the_app_database_url(sqlite_engine, serve_engine):
    opened_urls = serve_engine(sqlite_engine)
    with TestClient(create_app("postgresql+psycopg://taskly@db.internal/taskly")):
        pass
    assert opened_urls == ["postgresql+psycopg://taskly@db.internal/taskly"]


def test_database_connections_stay_open_while_the_app_runs(sqlite_engine, serve_engine):
    serve_engine(sqlite_engine)
    closed = track_closed_connections(sqlite_engine)
    with TestClient(create_app("sqlite://")) as client:
        client.get("/api/todos")
        assert closed == []


def test_shutdown_closes_the_database_connections(sqlite_engine, serve_engine):
    serve_engine(sqlite_engine)
    closed = track_closed_connections(sqlite_engine)
    with TestClient(create_app("sqlite://")) as client:
        client.get("/api/todos")
    assert len(closed) == 1


def test_startup_failure_propagates_and_closes_the_database_connections(read_only_engine, serve_engine):
    serve_engine(read_only_engine)
    closed = track_closed_connections(read_only_engine)
    with pytest.raises(OperationalError, match="readonly database"):
        with TestClient(create_app("sqlite://")):
            pass
    assert len(closed) == 1
