from fastapi.testclient import TestClient

from app.factory import create_app


def test_created_app_answers_health_and_todo_requests_against_its_database(sqlite_engine, serve_engine):
    serve_engine(sqlite_engine)
    with TestClient(create_app("sqlite://")) as client:
        health = client.get("/api/health")
        created = client.post("/api/todos", json={"title": "Write tests"})
        listed = client.get("/api/todos")
    assert (health.status_code, health.json()) == (200, {"status": "ok"})
    assert created.status_code == 201
    assert listed.json() == [created.json()]
