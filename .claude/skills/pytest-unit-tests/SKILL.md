---
name: pytest-unit-tests
description: Conventions for writing Taskly backend unit tests with pytest (FastAPI routers, SQLAlchemy repository, dependencies, configuration). Use before creating or editing any file under backend/tests.
---

# Backend unit tests (pytest)

## Before writing

Read `backend/tests/conftest.py` and `backend/tests/mocks.py`. Reuse their fixtures (`client`, `repository_mock`, `todo`, `todo_values`, `model_factory`) before adding new ones. A fixture two or more test modules need goes into `conftest.py`; a fixture one module needs stays in that module.

## Layout

- `backend/app/<package>/<module>.py` is tested in `backend/tests/<package>/test_<module>.py`.
- Every test directory is a package: create an empty `__init__.py` with a new directory.

## Seams

Test each layer at its public boundary and replace only what crosses a process boundary.

- **HTTP routes**: call the API through `client`, which mounts the todos router with `repository_mock` injected. Assert the status code, the JSON body (`todo.model_dump(mode="json")`) and the repository call (`repository_mock.update.assert_called_once_with(7, TodoUpdate(...))`). For invalid input assert `422` and that the repository was never called.
- **Repository**: pass `Mock(spec=Session)` and assert the domain objects returned plus the session calls that form the contract: `add` and `commit` before `refresh` on writes, nothing committed when the record is missing. Compare queries with `statement.compare(expected)`.
- **Dependencies, lifespan, factory, health**: build the smallest real collaborator. A `SimpleNamespace` app state, a `Mock` session factory, or an in-memory SQLite engine (`create_engine("sqlite://")`) when the code needs a database that really executes SQL. PostgreSQL and the network are never part of a unit test.
- **Configuration**: set variables with `monkeypatch.setenv` / `monkeypatch.delenv`, and replace `app.core.config.load_dotenv` with a no-op so a developer's `.env` file cannot leak into the result.
- **Time**: code calls `datetime.now(timezone.utc)`. Either assert relations that hold at any instant (timezone-aware, `created_at == updated_at` on create, `updated_at` moved forward on update) or monkeypatch the module's `datetime` with a fixed clock.

## Writing cases

- Plain functions named `test_<observable behaviour>`; no test classes.
- One behaviour per test. Tables of inputs with the same expectation use `pytest.mark.parametrize`.
- Expected values are literals or fixture values, written independently of the code under test.
- Assert the whole observable result where it is small (`assert response.json() == {...}`), not a single field of it.
- No comments, no docstrings.
- Tests are independent: no shared mutable state, no ordering assumptions, no sleeps.
