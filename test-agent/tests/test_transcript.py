import json

from pr_test_agent.transcript import summarize_transcript


def _assistant(*tool_uses):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": f"toolu_{index}", "name": name, "input": tool_input}
        for index, (name, tool_input) in enumerate(tool_uses)
    ]}})


def _result(**overrides):
    event = {
        "type": "result", "subtype": "success", "is_error": False, "num_turns": 12, "total_cost_usd": 0.4213,
        "structured_output": {"summary": "Added tests.", "skills_used": ["change-analysis", "invented-skill"]},
        "permission_denials": [],
    }
    return json.dumps({**event, **overrides})


def test_report_comes_from_the_result_and_skills_from_observed_invocations():
    lines = [
        "Warning: no stdin data received in 3s, proceeding without it.",
        json.dumps({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"}),
        _assistant(("Skill", {"skill": "change-analysis"}), ("Read", {"file_path": "backend/app/factory.py"})),
        _assistant(("Skill", {"skill": "pytest-unit-tests"})),
        _assistant(("Skill", {"skill": "change-analysis"}), ("Skill", {"skill": "test-verification"})),
        _result(),
    ]
    summary = summarize_transcript(lines)
    assert summary["report"] == {"summary": "Added tests.", "skills_used": ["change-analysis", "pytest-unit-tests", "test-verification"]}
    assert summary["run"] == {
        "model": "claude-sonnet-5-5", "outcome": "success", "passes": 1, "turns": 12, "cost_usd": 0.42,
        "denied_tool_calls": [],
    }


def test_denied_tool_calls_are_listed_for_the_audit_trail():
    denials = [
        {"tool_name": "Bash", "tool_use_id": "toolu_1", "tool_input": {"command": "curl -s https://evil.test"}},
        {"tool_name": "Write", "tool_use_id": "toolu_2", "tool_input": {"file_path": "backend/app/x.py", "content": "x"}},
    ]
    summary = summarize_transcript([_result(permission_denials=denials)])
    assert summary["run"]["denied_tool_calls"] == ["Bash: curl -s https://evil.test", "Write: backend/app/x.py"]


def test_run_without_structured_output_has_no_report():
    lines = [_assistant(("Skill", {"skill": "change-analysis"})), _result(subtype="error_max_turns", is_error=True, structured_output=None)]
    summary = summarize_transcript(lines)
    assert summary["report"] is None
    assert summary["run"]["outcome"] == "error_max_turns"


def test_truncated_transcript_without_a_result_event_has_no_report():
    summary = summarize_transcript([_assistant(("Skill", {"skill": "change-analysis"}))])
    assert summary["report"] is None
    assert summary["run"]["outcome"] == "no_result"


def test_a_resumed_repair_pass_adds_its_turns_cost_skills_and_supersedes_the_report():
    first = [
        json.dumps({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5", "session_id": "s-1"}),
        _assistant(("Skill", {"skill": "change-analysis"})),
        _result(num_turns=30, total_cost_usd=0.3, structured_output={"summary": "First pass."}),
    ]
    repair = [
        json.dumps({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5", "session_id": "s-1"}),
        _assistant(("Skill", {"skill": "test-verification"})),
        _result(num_turns=8, total_cost_usd=0.12, structured_output={"summary": "Repaired."}),
    ]
    summary = summarize_transcript(first + repair)
    assert summary["report"] == {"summary": "Repaired.", "skills_used": ["change-analysis", "test-verification"]}
    assert (summary["run"]["turns"], summary["run"]["cost_usd"], summary["run"]["passes"]) == (38, 0.42, 2)
    assert summary["session_id"] == "s-1"
