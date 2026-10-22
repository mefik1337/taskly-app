import os

import dotenv
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
URL_FROM_PARTS = "postgresql+psycopg://taskly:s3cr%40t%2Fpw@db.internal:6543/taskly_db"


@pytest.fixture
def postgres_parts(monkeypatch):
    for name, value in PARTS.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def dotenv_file(tmp_path, monkeypatch):
    snapshot = dict(os.environ)
    env_file = tmp_path / ".env"
    requested_paths = []

    def load_from_temporary_file(path, override):
        requested_paths.append(path)
        return dotenv.load_dotenv(env_file, override=override)

    monkeypatch.setattr(config, "load_dotenv", load_from_temporary_file)
    yield env_file, requested_paths
    os.environ.clear()
    os.environ.update(snapshot)


def test_explicit_url_wins_over_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert resolve_database_url("sqlite://") == "sqlite://"


def test_uses_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert resolve_database_url() == "postgresql+psycopg://env/db"


def test_empty_explicit_url_falls_back_to_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert resolve_database_url("") == "postgresql+psycopg://env/db"


def test_builds_url_from_postgres_parts_with_visible_escaped_password(postgres_parts):
    assert resolve_database_url() == URL_FROM_PARTS


def test_empty_database_url_falls_back_to_postgres_parts(postgres_parts, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    assert resolve_database_url() == URL_FROM_PARTS


@pytest.mark.parametrize("missing", list(PARTS))
def test_missing_postgres_part_raises_key_error_naming_it(postgres_parts, monkeypatch, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(KeyError, match=missing):
        resolve_database_url()


def test_non_numeric_port_is_rejected(postgres_parts, monkeypatch):
    monkeypatch.setenv("DB_PORT", "abc")
    with pytest.raises(ValueError):
        resolve_database_url()


def test_dotenv_supplies_database_url_missing_from_environment(dotenv_file):
    env_file, _ = dotenv_file
    env_file.write_text("DATABASE_URL=postgresql+psycopg://dotenv/db\n")
    assert resolve_database_url() == "postgresql+psycopg://dotenv/db"


def test_environment_wins_over_dotenv(dotenv_file, monkeypatch):
    env_file, _ = dotenv_file
    env_file.write_text("DATABASE_URL=postgresql+psycopg://dotenv/db\n")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    assert resolve_database_url() == "postgresql+psycopg://env/db"


def test_dotenv_is_read_from_the_repository_root_next_to_env_example(dotenv_file):
    _, requested_paths = dotenv_file
    resolve_database_url("sqlite://")
    [path] = requested_paths
    assert (path.name, path.with_name(".env.example").is_file()) == (".env", True)
