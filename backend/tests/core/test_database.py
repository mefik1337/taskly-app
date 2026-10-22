from unittest.mock import Mock

from sqlalchemy import inspect
from sqlalchemy.orm import Session

import app.core.database as database
from app.core.database import create_database_engine, create_session_factory, initialize


def test_engine_uses_the_postgresql_psycopg_driver():
    url = "postgresql+psycopg://taskly:taskly@localhost:5432/taskly"
    engine = create_database_engine(url)
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.url.database == "taskly"
    finally:
        engine.dispose()


def test_engine_pings_connections_and_limits_connect_time(monkeypatch):
    create_engine = Mock()
    monkeypatch.setattr(database, "create_engine", create_engine)
    assert create_database_engine("postgresql+psycopg://h/db") is create_engine.return_value
    create_engine.assert_called_once_with(
        "postgresql+psycopg://h/db",
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


def test_session_factory_binds_sessions_to_engine_without_expiring_on_commit(sqlite_engine):
    session = create_session_factory(sqlite_engine)()
    try:
        assert isinstance(session, Session)
        assert session.get_bind() is sqlite_engine
        assert session.expire_on_commit is False
    finally:
        session.close()


def test_initialize_creates_the_todos_table(sqlite_engine):
    initialize(sqlite_engine)
    columns = {column["name"] for column in inspect(sqlite_engine).get_columns("todos")}
    assert columns == {
        "id", "title", "description", "priority", "due_date",
        "completed", "created_at", "updated_at",
    }


def test_initialize_is_idempotent(sqlite_engine):
    initialize(sqlite_engine)
    initialize(sqlite_engine)
    assert inspect(sqlite_engine).get_table_names() == ["todos"]
