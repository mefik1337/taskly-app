from datetime import date, datetime, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.features.todos.models import Base, TodoRecord
from app.features.todos.repository import TodoRepository
from app.features.todos.schemas import TodoCreate, TodoUpdate


@pytest.fixture
def stored_record(model_factory, todo_values):
    return model_factory(todo_values)


@pytest.fixture
def session_with(stored_record):
    session = Mock(spec=Session)
    session.get.return_value = stored_record
    return session


def call_names(session):
    return [call[0] for call in session.mock_calls]


def test_list_maps_models_and_orders_tasks_newest_first(model_factory, todo_values, todo):
    session = Mock(spec=Session)
    session.scalars.return_value = [model_factory(todo_values)]
    assert TodoRepository(session).list() == [todo]
    statement = session.scalars.call_args.args[0]
    expected = select(TodoRecord).order_by(TodoRecord.created_at.desc(), TodoRecord.id.desc())
    assert statement.compare(expected)
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "ORDER BY todos.created_at DESC, todos.id DESC" in compiled


def test_list_returns_an_empty_list_when_no_tasks_exist():
    session = Mock(spec=Session)
    session.scalars.return_value = []
    assert TodoRepository(session).list() == []


def test_get_returns_none_for_missing_task():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).get(404) is None
    session.get.assert_called_once_with(TodoRecord, 404)


def test_get_maps_an_existing_task(session_with, todo):
    assert TodoRepository(session_with).get(7) == todo
    session_with.get.assert_called_once_with(TodoRecord, 7)


def test_create_adds_commits_and_refreshes_before_returning_the_stored_task():
    session = Mock(spec=Session)
    session.refresh.side_effect = lambda record: setattr(record, "id", 11)
    payload = TodoCreate(
        title="Plan the sprint", description="Details", priority="high",
        due_date=date(2026, 10, 15), completed=True,
    )
    todo = TodoRepository(session).create(payload)
    record = session.add.call_args.args[0]
    assert call_names(session) == ["add", "commit", "refresh"]
    session.refresh.assert_called_once_with(record)
    assert todo.model_dump(exclude={"created_at", "updated_at"}) == {
        "id": 11, "title": "Plan the sprint", "description": "Details",
        "priority": "high", "due_date": date(2026, 10, 15), "completed": True,
    }


def test_create_stamps_equal_timezone_aware_creation_and_update_times():
    session = Mock(spec=Session)
    session.refresh.side_effect = lambda record: setattr(record, "id", 11)
    before = datetime.now(timezone.utc)
    todo = TodoRepository(session).create(TodoCreate(title="Task"))
    after = datetime.now(timezone.utc)
    assert todo.created_at == todo.updated_at
    assert todo.created_at.tzinfo is not None
    assert before <= todo.created_at <= after


def test_update_returns_none_and_commits_nothing_for_missing_task():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).update(404, TodoUpdate(title="Renamed")) is None
    session.get.assert_called_once_with(TodoRecord, 404)
    session.commit.assert_not_called()
    session.refresh.assert_not_called()


def test_update_changes_only_the_fields_in_the_patch(session_with, stored_record, todo_values):
    todo = TodoRepository(session_with).update(7, TodoUpdate(title="Renamed", completed=True))
    session_with.get.assert_called_once_with(TodoRecord, 7)
    assert todo.model_dump(exclude={"updated_at"}) == {
        **{k: v for k, v in todo_values.items() if k != "updated_at"},
        "title": "Renamed", "completed": True,
    }
    assert stored_record.title == "Renamed"
    assert stored_record.description == "First scenario"


def test_update_clears_the_due_date_when_patched_with_null(model_factory, todo_values):
    record = model_factory({**todo_values, "due_date": date(2026, 10, 15)})
    session = Mock(spec=Session)
    session.get.return_value = record
    todo = TodoRepository(session).update(7, TodoUpdate(due_date=None))
    assert todo.due_date is None
    assert record.due_date is None


def test_update_moves_updated_at_forward_and_keeps_created_at(session_with, todo_values):
    before = datetime.now(timezone.utc)
    todo = TodoRepository(session_with).update(7, TodoUpdate(priority="low"))
    assert todo.created_at == todo_values["created_at"]
    assert todo.updated_at >= before
    assert todo.updated_at.tzinfo is not None


def test_update_commits_then_refreshes_the_record(session_with, stored_record):
    TodoRepository(session_with).update(7, TodoUpdate(title="Renamed"))
    assert call_names(session_with) == ["get", "commit", "refresh"]
    session_with.refresh.assert_called_once_with(stored_record)


def test_delete_returns_false_and_deletes_nothing_for_missing_task():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).delete(404) is False
    session.get.assert_called_once_with(TodoRecord, 404)
    session.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_removes_and_commits_an_existing_task(session_with, stored_record):
    assert TodoRepository(session_with).delete(7) is True
    assert call_names(session_with) == ["get", "delete", "commit"]
    session_with.delete.assert_called_once_with(stored_record)


def test_delete_completed_removes_only_completed_tasks_and_reports_how_many(sqlite_engine):
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as session:
        repository = TodoRepository(session)
        for title, completed in [("Done", True), ("Open", False), ("Also done", True)]:
            repository.create(TodoCreate(title=title, completed=completed))
        assert repository.delete_completed() == 2
        assert [todo.title for todo in repository.list()] == ["Open"]


def test_delete_completed_reports_zero_and_keeps_tasks_when_nothing_is_completed(sqlite_engine):
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as session:
        repository = TodoRepository(session)
        repository.create(TodoCreate(title="Open"))
        assert repository.delete_completed() == 0
        assert [todo.title for todo in repository.list()] == ["Open"]
