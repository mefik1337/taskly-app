import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import inspect

import app.core.lifespan as lifespan_module
from app.core.lifespan import lifespan


def make_app():
    return SimpleNamespace(state=SimpleNamespace(database_url="postgresql+psycopg://h/db"))


@pytest.fixture
def engine_factory(monkeypatch, sqlite_engine):
    sqlite_engine.dispose = Mock(wraps=sqlite_engine.dispose)
    factory = Mock(return_value=sqlite_engine)
    monkeypatch.setattr(lifespan_module, "create_database_engine", factory)
    return factory


def run_lifespan(app, during=None):
    async def scenario():
        async with lifespan(app):
            if during:
                during()

    asyncio.run(scenario())


def test_startup_builds_engine_from_app_database_url(engine_factory):
    run_lifespan(make_app())
    engine_factory.assert_called_once_with("postgresql+psycopg://h/db")


def test_startup_creates_schema_and_exposes_a_bound_session_factory(engine_factory, sqlite_engine):
    app = make_app()
    observed = {}

    def during():
        observed["tables"] = inspect(sqlite_engine).get_table_names()
        session = app.state.session_factory()
        observed["bind"] = session.get_bind()
        observed["expire_on_commit"] = session.expire_on_commit
        session.close()
        sqlite_engine.dispose.assert_not_called()

    run_lifespan(app, during)
    assert observed == {"tables": ["todos"], "bind": sqlite_engine, "expire_on_commit": False}


def test_shutdown_disposes_the_engine(engine_factory, sqlite_engine):
    run_lifespan(make_app())
    sqlite_engine.dispose.assert_called_once_with()


def test_disposes_engine_and_propagates_when_initialization_fails(engine_factory, sqlite_engine, monkeypatch):
    monkeypatch.setattr(lifespan_module, "initialize", Mock(side_effect=RuntimeError("db down")))
    app = make_app()
    with pytest.raises(RuntimeError, match="db down"):
        run_lifespan(app)
    sqlite_engine.dispose.assert_called_once_with()
    assert not hasattr(app.state, "session_factory")


def test_disposes_engine_when_the_application_fails_while_running(engine_factory, sqlite_engine):
    def during():
        raise RuntimeError("crash")

    with pytest.raises(RuntimeError, match="crash"):
        run_lifespan(make_app(), during)
    sqlite_engine.dispose.assert_called_once_with()
