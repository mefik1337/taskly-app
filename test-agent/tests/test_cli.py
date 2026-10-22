import json

from pr_test_agent.cli import main
from pr_test_agent.comment import marker
from tests.support import FAILING, FakeRunner, agent_patch


def run(argv: list[str], repo=None, runner=None) -> int:
    return main(argv, repo=repo, runner_factory=(lambda _: runner) if runner else None)


def test_the_whole_pull_request_flow_produces_a_committable_status_and_a_comment(repo, pull_request, workspace, capsys):
    runner = FakeRunner(repo, hits={1: 1, 2: 1, 3: 1, 4: 1})
    stack = ["--stack", "backend", "--workspace", str(workspace.root)]
    assert run(["analyze", *stack, "--base", pull_request], repo, runner) == 0
    workspace.patch_path.write_text(agent_patch(repo, "backend/tests/test_new.py", "def test_new():\n    pass\n"))
    (workspace.root / "agent-report.json").write_text(json.dumps({
        "summary": "Added a test.", "decisions": [], "skills_used": [], "test_files": [], "suspected_bugs": [],
        "verification": [],
    }))
    assert run(["verify", *stack], repo, runner) == 0
    capsys.readouterr()
    assert run(["status", "--workspace", str(workspace.root)]) == 0
    assert capsys.readouterr().out.strip() == "verified"
    out = workspace.root / "comment.md"
    assert run(["comment", *stack, "--status", "committed", "--commit-sha", "abcdef1234",
                "--run-url", "https://example.test/run", "--out", str(out)]) == 0
    comment = out.read_text(encoding="utf-8")
    assert comment.startswith(marker("backend"))
    assert "committed in abcdef1" in comment


def test_selfcheck_exits_non_zero_when_the_suite_is_red(repo, workspace):
    runner = FakeRunner(repo, hits={1: 1}, junit=FAILING)
    assert run(["selfcheck", "--stack", "backend", "--workspace", str(workspace.root)], repo, runner) == 1


def test_selfcheck_exits_zero_when_the_suite_is_green(repo, workspace):
    runner = FakeRunner(repo, hits={1: 1})
    assert run(["selfcheck", "--stack", "backend", "--workspace", str(workspace.root)], repo, runner) == 0


def test_status_without_an_analysis_means_nothing_was_measured(workspace, capsys):
    assert run(["status", "--workspace", str(workspace.root)]) == 0
    assert capsys.readouterr().out.strip() == "not_measured"


def test_the_transcript_command_writes_the_report_the_run_and_the_session_to_resume(workspace):
    workspace.root.mkdir(parents=True)
    workspace.transcript_path.write_text("\n".join([
        json.dumps({"type": "system", "subtype": "init", "model": "m", "session_id": "abc-123"}),
        json.dumps({"type": "result", "subtype": "success", "num_turns": 3, "total_cost_usd": 0.1,
                    "structured_output": {"summary": "s", "decisions": [], "skills_used": [], "test_files": [],
                                          "suspected_bugs": [], "verification": []}}),
    ]), encoding="utf-8")
    assert run(["transcript", "--workspace", str(workspace.root)]) == 0
    assert json.loads((workspace.root / "agent-report.json").read_text())["summary"] == "s"
    assert json.loads((workspace.root / "agent-run.json").read_text())["turns"] == 3
    assert workspace.session_path.read_text(encoding="utf-8") == "abc-123"


def test_the_transcript_command_removes_a_stale_report_when_the_agent_produced_none(workspace):
    workspace.root.mkdir(parents=True)
    (workspace.root / "agent-report.json").write_text("{}")
    workspace.transcript_path.write_text(json.dumps({"type": "result", "subtype": "error_max_turns"}))
    assert run(["transcript", "--workspace", str(workspace.root)]) == 0
    assert not (workspace.root / "agent-report.json").exists()


def test_the_redact_command_scrubs_secrets_named_by_environment_variable(tmp_path, monkeypatch):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"token": "sk-ant-oat01-secret-value"}', encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-secret-value")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert run(["redact", "--file", str(transcript), "--env", "CLAUDE_CODE_OAUTH_TOKEN", "--env", "ANTHROPIC_API_KEY"]) == 0
    assert transcript.read_text(encoding="utf-8") == '{"token": "[REDACTED]"}'


def test_the_schema_command_prints_the_report_contract_for_the_agent(capsys):
    assert run(["schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["additionalProperties"] is False


def test_the_settings_command_prints_the_sandbox_of_one_stack(capsys):
    assert run(["claude-settings", "--stack", "frontend"]) == 0
    allow = json.loads(capsys.readouterr().out)["permissions"]["allow"]
    assert "Bash(test-agent/bin/run-frontend-tests)" in allow
    assert not any("backend" in rule for rule in allow)


def test_the_guard_command_fails_on_a_patch_outside_the_test_tree(repo, workspace, capsys):
    workspace.root.mkdir(parents=True)
    workspace.patch_path.write_text(agent_patch(repo, "backend/app/router.py", "hacked\n"), encoding="utf-8")
    assert run(["guard", "--stack", "backend", "--workspace", str(workspace.root)]) == 1
    assert "backend/app/router.py: only backend test files may be changed" in capsys.readouterr().err


def test_the_guard_command_passes_a_patch_of_test_files(repo, workspace):
    workspace.root.mkdir(parents=True)
    workspace.patch_path.write_text(agent_patch(repo, "backend/tests/test_new.py", "x = 1\n"), encoding="utf-8")
    assert run(["guard", "--stack", "backend", "--workspace", str(workspace.root)]) == 0
