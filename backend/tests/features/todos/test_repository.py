from datetime import date, datetime, timezone

import pytest

from app.features.todos.repository import TodoRepository
from app.features.todos.schemas import TodoCreate, TodoUpdate

MONDAY = datetime(2026, 10, 5, 9, tzinfo=timezone.utc)
TUESDAY = datetime(2026, 10, 6, 9, tzinfo=timezone.utc)
WEDNESDAY = datetime(2026, 10, 7, 9, tzinfo=timezone.utc)


@pytest.fixture
def read_back(open_session):
    return lambda: TodoRepository(open_session())


@pytest.fixture
def stored(repository, clock):
    clock.current = MONDAY
    return repository.create(
        TodoCreate(
            title="Plan the sprint", description="Agenda", priority="high",
            due_date=date(2026, 10, 15), completed=False,
        )
    )


def as_utc(moment):
    return moment.replace(tzinfo=timezone.utc)


def fields(todo):
    return todo.model_dump(exclude={"id", "created_at", "updated_at"})


def test_create_returns_the_stored_values(stored):
    assert fields(stored) == {
        "title": "Plan the sprint", "description": "Agenda", "priority": "high",
        "due_date": date(2026, 10, 15), "completed": False,
    }


def test_created_task_can_be_read_back_by_id(stored, read_back):
    assert read_back().get(stored.id) == stored


def test_create_applies_defaults_for_omitted_fields(repository, read_back, clock):
    clock.current = MONDAY
    created = repository.create(TodoCreate(title="Task"))
    assert fields(read_back().get(created.id)) == {
        "title": "Task", "description": "", "priority": "medium",
        "due_date": None, "completed": False,
    }


def test_create_assigns_distinct_ids(repository, clock):
    clock.current = MONDAY
    first = repository.create(TodoCreate(title="First"))
    second = repository.create(TodoCreate(title="Second"))
    assert first.id != second.id


def test_create_stamps_creation_and_update_time_with_the_current_instant(stored, read_back):
    found = read_back().get(stored.id)
    assert (as_utc(found.created_at), as_utc(found.updated_at)) == (MONDAY, MONDAY)


def test_list_without_tasks_is_empty(repository):
    assert repository.list() == []


def test_list_orders_by_creation_time_newest_first_regardless_of_insertion_order(repository, read_back, clock):
    clock.current = MONDAY
    oldest = repository.create(TodoCreate(title="Created on Monday"))
    clock.current = WEDNESDAY
    newest = repository.create(TodoCreate(title="Created on Wednesday"))
    clock.current = TUESDAY
    middle = repository.create(TodoCreate(title="Created on Tuesday"))
    assert [todo.id for todo in read_back().list()] == [newest.id, middle.id, oldest.id]


def test_list_puts_the_higher_id_first_when_created_at_is_equal(repository, read_back, clock):
    clock.current = MONDAY
    first = repository.create(TodoCreate(title="First"))
    second = repository.create(TodoCreate(title="Second"))
    assert [todo.id for todo in read_back().list()] == [second.id, first.id]


def test_get_unknown_id_returns_none(repository):
    assert repository.get(404) is None


def test_update_persists_only_the_patched_fields(stored, repository, read_back, clock):
    clock.current = TUESDAY
    repository.update(stored.id, TodoUpdate(title="Renamed", completed=True))
    assert fields(read_back().get(stored.id)) == {
        "title": "Renamed", "description": "Agenda", "priority": "high",
        "due_date": date(2026, 10, 15), "completed": True,
    }


def test_update_returns_the_updated_task(stored, repository, read_back, clock):
    clock.current = TUESDAY
    updated = repository.update(stored.id, TodoUpdate(priority="low"))
    assert updated == read_back().get(stored.id)


def test_update_moves_updated_at_and_keeps_created_at(stored, repository, read_back, clock):
    clock.current = TUESDAY
    repository.update(stored.id, TodoUpdate(priority="low"))
    found = read_back().get(stored.id)
    assert (as_utc(found.created_at), as_utc(found.updated_at)) == (MONDAY, TUESDAY)


def test_update_unknown_id_returns_none_and_stores_nothing(repository, read_back, clock):
    clock.current = TUESDAY
    assert repository.update(404, TodoUpdate(title="Renamed")) is None
    assert read_back().list() == []


def test_delete_removes_the_task(stored, repository, read_back):
    assert repository.delete(stored.id) is True
    assert read_back().get(stored.id) is None


def test_delete_keeps_other_tasks(stored, repository, read_back, clock):
    clock.current = TUESDAY
    other = repository.create(TodoCreate(title="Keep me"))
    repository.delete(stored.id)
    assert [todo.id for todo in read_back().list()] == [other.id]


def test_delete_unknown_id_returns_false_and_keeps_existing_tasks(stored, repository, read_back):
    assert repository.delete(404) is False
    assert read_back().list() == [stored]


def test_delete_completed_removes_only_completed_tasks_and_counts_them(repository, read_back):
    repository.create(TodoCreate(title="Done", completed=True))
    kept = repository.create(TodoCreate(title="Open", completed=False))
    repository.create(TodoCreate(title="Also done", completed=True))
    assert repository.delete_completed() == 2
    assert [todo.id for todo in read_back().list()] == [kept.id]


def test_delete_completed_without_completed_tasks_keeps_everything(stored, repository, read_back):
    assert repository.delete_completed() == 0
    assert read_back().list() == [stored]
