from datetime import datetime, timezone

import pytest
from sqlalchemy import event, func, inspect, select

from app.core.database import create_database_engine, create_session_factory, initialize
from app.features.todos.models import TodoRecord


class ConnectionRefused(Exception):
    pass


def make_record(title):
    now = datetime(2026, 10, 5, 9, tzinfo=timezone.utc)
    return TodoRecord(title=title, created_at=now, updated_at=now)


def count_rows(engine):
    with engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(TodoRecord))


def test_engine_connects_to_the_configured_server_with_a_ten_second_timeout():
    engine = create_database_engine("postgresql+psycopg://taskly:pw@db.internal:6543/taskly_db")
    attempted = {}

    @event.listens_for(engine, "do_connect")
    def refuse(dialect, connection_record, cargs, cparams):
        attempted.update(cparams)
        raise ConnectionRefused()

    with pytest.raises(ConnectionRefused):
        engine.connect()
    assert {name: attempted[name] for name in ("host", "port", "dbname", "user", "connect_timeout")} == {
        "host": "db.internal", "port": 6543, "dbname": "taskly_db", "user": "taskly", "connect_timeout": 10,
    }


def test_initialize_creates_the_todos_table(sqlite_engine):
    initialize(sqlite_engine)
    assert inspect(sqlite_engine).get_table_names() == ["todos"]


def test_initialize_again_keeps_existing_rows(sqlite_engine):
    initialize(sqlite_engine)
    with create_session_factory(sqlite_engine)() as session:
        session.add(make_record("Existing"))
        session.commit()
    initialize(sqlite_engine)
    assert count_rows(sqlite_engine) == 1


def test_session_factory_sessions_write_to_the_engine_database(sqlite_engine):
    initialize(sqlite_engine)
    with create_session_factory(sqlite_engine)() as session:
        session.add(make_record("Stored"))
        session.commit()
    assert count_rows(sqlite_engine) == 1


def test_session_factory_keeps_committed_objects_readable_after_the_session_closes(sqlite_engine):
    initialize(sqlite_engine)
    record = make_record("Readable")
    with create_session_factory(sqlite_engine)() as session:
        session.add(record)
        session.commit()
    assert record.title == "Readable"
