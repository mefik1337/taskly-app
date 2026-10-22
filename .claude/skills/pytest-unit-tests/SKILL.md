---
name: pytest-unit-tests
description: Conventions for writing Taskly backend unit tests with pytest (FastAPI routes, SQLAlchemy repository, dependencies, lifespan, configuration). Use before creating or editing any file under backend/tests.
---

# Backend unit tests (pytest)

A backend test is a **specification**: it drives the code through the interface its callers use and asserts what they observe. It survives any refactor that keeps that behaviour.

## Before writing

Read `backend/tests/conftest.py` first and reuse its fixtures. A fixture two or more test modules need goes into `conftest.py`; a fixture one module needs stays in that module.

## Layout

- `backend/app/<package>/<module>.py` is tested in `backend/tests/<package>/test_<module>.py`.
- Every test directory is a package: create an empty `__init__.py` with a new directory.

## Seams

The application runs for real in every test. Substitute only what leaves the process, each in one shared `conftest.py` fixture.

| Code under test | Drive it through | Real collaborators | Substituted |
| --- | --- | --- | --- |
| Routes | `TestClient` requests | the router, validation and a real `TodoRepository` on in-memory SQLite | the database URL (`sqlite://` with `StaticPool`) |
| Repository | its public methods | a real `Session` on in-memory SQLite | nothing |
| Request-scoped dependencies, lifespan, factory | `TestClient` around `create_app(...)` | engine, session factory, middleware | the PostgreSQL engine factory when the code would open one |
| Configuration | the public resolver function | `os.environ` through `monkeypatch.setenv` / `delenv` | `load_dotenv`, so a developer's `.env` cannot leak in |

Assert the **observable result**: the status code and JSON body, the rows a later read returns, the value a resolver returns. To prove a write persisted, read it back through the same interface (`GET` after `POST`, `repository.get` after `repository.update`).

Pydantic, SQLAlchemy and FastAPI are trusted. Their rules matter only where Taskly configures them: a schema constraint is pinned as a `422` whose `detail[*].loc` names the offending field; a mapper is pinned by the values a route returns.

## Time

Code stamps `datetime.now(timezone.utc)`. Assert relations that hold at any instant (`created_at == updated_at` on create, `updated_at` moves forward on update, ordering by creation) or freeze the clock with a monkeypatched module-level `datetime`.

## Writing cases

- Plain functions named as the behaviour they pin: `test_patch_with_unknown_id_returns_404`, `test_list_orders_newest_first`.
- One behaviour per test. Tables of inputs with one expectation use `pytest.mark.parametrize` with readable `ids`.
- Expected values are literals or fixture values written independently of the code under test.
- Assert the whole observable result when it is small (`assert response.json() == {...}`).
- Each test builds its own data through the interface; tests share no mutable state and assume no order.
- Each contract lives at **one layer**: HTTP status, body and validation in route tests; timestamps, ordering ties and persistence details in repository tests.
- A test for an edge case or a bug uses data that **fails against the naive implementation**; when it would pass anyway, choose other data.
- No comments, no docstrings.

## Rejected patterns

Each of these passes while the behaviour is broken or fails while it is intact; replace it with the seam above.

- `Mock(spec=Session)`, `Mock()` repositories, `assert_called_*`, call-order lists: assert stored and returned state instead.
- Calling `_private` helpers, `is` identity checks, comparing compiled SQL.
- A test whose expected value is what the mock was told to return.
- Re-testing a framework feature (URL parsing, `model_validate`, default `create_engine` arguments).
