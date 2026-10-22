from fastapi.testclient import TestClient

from app.factory import create_app
from app.features.todos.models import Base


def test_health_reports_ok_when_the_todos_table_is_queryable(client):
    response = client.get("/api/health")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


def test_health_responds_500_when_the_todos_table_is_missing(sqlite_engine, serve_engine):
    serve_engine(sqlite_engine)
    with TestClient(create_app("sqlite://"), raise_server_exceptions=False) as client:
        Base.metadata.drop_all(sqlite_engine)
        assert client.get("/api/health").status_code == 500
