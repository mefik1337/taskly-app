from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.dependencies import get_repository
from app.features.todos.repository import TodoRepository


def make_request(session_factory):
    app = SimpleNamespace(state=SimpleNamespace(session_factory=session_factory))
    return Request({"type": "http", "app": app})


def test_session_creation_failure_propagates_from_repository_dependency():
    session_factory = Mock(side_effect=RuntimeError("Session unavailable"))
    request = make_request(session_factory)
    dependency = get_repository(request)
    with pytest.raises(RuntimeError, match="Session unavailable"):
        next(dependency)
    session_factory.assert_called_once_with()


def test_yields_a_repository_bound_to_a_new_session():
    session = Mock(spec=Session)
    dependency = get_repository(make_request(Mock(return_value=session)))
    repository = next(dependency)
    assert isinstance(repository, TodoRepository)
    assert repository.session is session
    session.close.assert_not_called()


def test_closes_the_session_without_rollback_after_a_successful_request():
    session = Mock(spec=Session)
    dependency = get_repository(make_request(Mock(return_value=session)))
    next(dependency)
    with pytest.raises(StopIteration):
        next(dependency)
    session.close.assert_called_once_with()
    session.rollback.assert_not_called()


def test_rolls_back_closes_and_reraises_when_the_request_fails():
    session = Mock(spec=Session)
    manager = Mock()
    session.rollback = manager.rollback
    session.close = manager.close
    dependency = get_repository(make_request(Mock(return_value=session)))
    next(dependency)
    with pytest.raises(ValueError, match="boom"):
        dependency.throw(ValueError("boom"))
    assert [call[0] for call in manager.mock_calls] == ["rollback", "close"]
