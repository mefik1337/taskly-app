from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.core.config as config
import app.core.lifespan as lifespan
import app.features.todos.repository as repository_module
from app.factory import create_app
from app.features.todos.models import Base
from app.features.todos.repository import TodoRepository

DATABASE_VARIABLES = ("DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "DB_PORT", "POSTGRES_DB")
FROZEN_INSTANT = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


class FrozenClock:
    def __init__(self, current):
        self.current = current

    def now(self, tz=None):
        return self.current


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda path, override: None)
    for name in DATABASE_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield engine
    engine.dispose()


@pytest.fixture
def open_session(sqlite_engine):
    Base.metadata.create_all(sqlite_engine)
    sessions = []

    def open_new():
        session = Session(sqlite_engine)
        sessions.append(session)
        return session

    yield open_new
    for session in sessions:
        session.close()


@pytest.fixture
def repository(open_session):
    return TodoRepository(open_session())


@pytest.fixture
def clock(monkeypatch):
    frozen = FrozenClock(FROZEN_INSTANT)
    monkeypatch.setattr(repository_module, "datetime", frozen)
    return frozen


@pytest.fixture
def serve_engine(monkeypatch):
    opened_urls = []

    def serve(engine):
        def open_engine(database_url):
            opened_urls.append(database_url)
            return engine

        monkeypatch.setattr(lifespan, "create_database_engine", open_engine)
        return opened_urls

    return serve


@pytest.fixture
def client(sqlite_engine, serve_engine):
    serve_engine(sqlite_engine)
    with TestClient(create_app("sqlite://")) as client:
        yield client
