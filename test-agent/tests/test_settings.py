from pr_test_agent.settings import claude_settings
from pr_test_agent.stacks import get_stack


def _permissions(stack: str) -> dict:
    return claude_settings(get_stack(stack))["permissions"]


def test_the_agent_may_edit_and_write_only_the_test_files_of_its_stack():
    allow = _permissions("frontend")["allow"]
    edits = sorted(rule for rule in allow if rule.startswith(("Edit(", "Write(")))
    assert edits == [
        "Edit(frontend/src/**/*.test.ts)",
        "Edit(frontend/src/**/*.test.tsx)",
        "Edit(frontend/src/test/**)",
        "Write(frontend/src/**/*.test.ts)",
        "Write(frontend/src/**/*.test.tsx)",
        "Write(frontend/src/test/**)",
    ]


def test_the_agent_may_run_only_the_test_runner_of_its_stack_and_read_only_git():
    bash = sorted(rule for rule in _permissions("backend")["allow"] if rule.startswith("Bash("))
    assert bash == [
        "Bash(git diff *)",
        "Bash(git log *)",
        "Bash(git show *)",
        "Bash(git status *)",
        "Bash(test-agent/bin/run-backend-tests *)",
        "Bash(test-agent/bin/run-backend-tests)",
    ]


def test_production_code_of_the_stack_and_the_whole_other_stack_are_denied():
    deny = _permissions("backend")["deny"]
    for rule in ("Edit(backend/app/**)", "Write(backend/app/**)", "Edit(frontend/**)", "Write(frontend/**)"):
        assert rule in deny


def test_secrets_and_the_network_are_denied_and_unlisted_tools_are_refused():
    permissions = _permissions("frontend")
    for rule in ("WebFetch", "WebSearch", "Read(**/.env)", "Bash(printenv)", "Bash(env *)", "Read(//proc/**)"):
        assert rule in permissions["deny"]
    assert permissions["defaultMode"] == "dontAsk"
