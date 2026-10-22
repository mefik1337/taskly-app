import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_repository
from app.api.health import router
from app.features.todos.models import Base
from app.features.todos.repository import TodoRepository


def make_client(engine, **kwargs):
    app = FastAPI()
    app.include_router(router)
    session_factory = sessionmaker(bind=engine)

    def override():
        session = session_factory()
        try:
            yield TodoRepository(session)
        finally:
            session.close()

    app.dependency_overrides[get_repository] = override
    return TestClient(app, **kwargs)


def test_health_reports_ok_when_the_todos_table_is_queryable(sqlite_engine):
    Base.metadata.create_all(sqlite_engine)
    response = make_client(sqlite_engine).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_propagates_database_errors(sqlite_engine):
    with pytest.raises(OperationalError):
        make_client(sqlite_engine).get("/api/health")


def test_health_responds_500_when_the_database_is_unusable(sqlite_engine):
    response = make_client(sqlite_engine, raise_server_exceptions=False).get("/api/health")
    assert response.status_code == 500
