from pathlib import Path
from unittest.mock import Mock

import pytest

import app.core.config as config
from app.core.config import resolve_database_url

PARTS = {
    "POSTGRES_USER": "taskly",
    "POSTGRES_PASSWORD": "s3cr@t/pw",
    "POSTGRES_HOST": "db.internal",
    "DB_PORT": "6543",
    "POSTGRES_DB": "taskly_db",
}


@pytest.fixture
def load_dotenv(monkeypatch):
    stub = Mock()
    monkeypatch.setattr(config, "load_dotenv", stub)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name in PARTS:
        monkeypatch.delenv(name, raising=False)
    return stub


def test_explicit_url_wins_over_environment(load_dotenv, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert resolve_database_url("sqlite://") == "sqlite://"


def test_uses_database_url_from_environment(load_dotenv, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert resolve_database_url() == "postgresql+psycopg://env/db"


def test_empty_explicit_url_falls_back_to_environment(load_dotenv, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert resolve_database_url("") == "postgresql+psycopg://env/db"


def test_builds_url_from_postgres_parts_with_visible_escaped_password(load_dotenv, monkeypatch):
    for name, value in PARTS.items():
        monkeypatch.setenv(name, value)
    assert resolve_database_url() == (
        "postgresql+psycopg://taskly:s3cr%40t%2Fpw@db.internal:6543/taskly_db"
    )


def test_empty_database_url_falls_back_to_postgres_parts(load_dotenv, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    for name, value in PARTS.items():
        monkeypatch.setenv(name, value)
    assert resolve_database_url().startswith("postgresql+psycopg://taskly:")


@pytest.mark.parametrize("missing", list(PARTS))
def test_missing_postgres_part_raises_key_error(load_dotenv, monkeypatch, missing):
    for name, value in PARTS.items():
        if name != missing:
            monkeypatch.setenv(name, value)
    with pytest.raises(KeyError, match=missing):
        resolve_database_url()


def test_non_numeric_port_is_rejected(load_dotenv, monkeypatch):
    for name, value in {**PARTS, "DB_PORT": "abc"}.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        resolve_database_url()


def test_loads_repository_dotenv_without_overriding_environment(load_dotenv):
    resolve_database_url("sqlite://")
    repository_root = Path(config.__file__).resolve().parent.parent.parent.parent
    load_dotenv.assert_called_once_with(repository_root / ".env", override=False)
