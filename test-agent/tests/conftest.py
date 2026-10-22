import pytest

from pr_test_agent.workspace import Workspace
from tests.support import make_repository, open_pull_request


@pytest.fixture
def repo(tmp_path):
    return make_repository(tmp_path)


@pytest.fixture
def pull_request(repo):
    return open_pull_request(repo)


@pytest.fixture
def workspace(tmp_path):
    return Workspace(tmp_path / ".test-agent")
