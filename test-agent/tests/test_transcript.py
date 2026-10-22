import json

from pr_test_agent.models import AgentReport
from pr_test_agent.transcript import summarize_transcript

REPORT = {
    "summary": "Added tests.",
    "decisions": [{"path": "backend/app/x.py", "action": "created_tests", "reason": "New route.", "test_file": "backend/tests/test_x.py"}],
    "skills_used": ["change-analysis", "invented-skill"],
    "test_files": [{"path": "backend/tests/test_x.py", "change": "created", "cases": ["test_x_returns_200"]}],
    "suspected_bugs": [],
    "verification": [{"stack": "backend", "command": "test-agent/bin/run-backend-tests", "passed": True}],
}


def _init(session_id: str = "s-1") -> str:
    return json.dumps({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5", "session_id": session_id})


def _assistant(*tool_uses) -> str:
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": f"toolu_{index}", "name": name, "input": tool_input}
        for index, (name, tool_input) in enumerate(tool_uses)
    ]}})


def _result(**overrides) -> str:
    event = {
        "type": "result", "subtype": "success", "is_error": False, "num_turns": 12, "total_cost_usd": 0.4213,
        "structured_output": REPORT, "permission_denials": [],
    }
    return json.dumps({**event, **overrides})


def test_the_report_comes_from_the_result_and_skills_from_observed_invocations():
    lines = [
        "Warning: no stdin data received in 3s, proceeding without it.",
        _init(),
        _assistant(("Skill", {"skill": "change-analysis"}), ("Read", {"file_path": "backend/app/factory.py"})),
        _assistant(("Skill", {"skill": "pytest-unit-tests"})),
        _assistant(("Skill", {"skill": "change-analysis"}), ("Skill", {"skill": "test-verification"})),
        _result(),
    ]
    summary = summarize_transcript(lines)
    assert summary.report == AgentReport.model_validate(
        {**REPORT, "skills_used": ["change-analysis", "pytest-unit-tests", "test-verification"]}
    )
    assert summary.run.model_dump() == {
        "model": "claude-sonnet-5-5", "outcome": "success", "passes": 1, "turns": 12, "cost_usd": 0.42,
        "denied_tool_calls": [],
    }


def test_denied_tool_calls_are_listed_for_the_audit_trail():
    denials = [
        {"tool_name": "Bash", "tool_use_id": "toolu_1", "tool_input": {"command": "curl -s https://evil.test"}},
        {"tool_name": "Write", "tool_use_id": "toolu_2", "tool_input": {"file_path": "backend/app/x.py", "content": "x"}},
    ]
    summary = summarize_transcript([_result(permission_denials=denials)])
    assert summary.run.denied_tool_calls == ["Bash: curl -s https://evil.test", "Write: backend/app/x.py"]


def test_a_run_without_structured_output_has_no_report():
    summary = summarize_transcript([_result(subtype="error_max_turns", is_error=True, structured_output=None)])
    assert summary.report is None
    assert summary.run.outcome == "error_max_turns"


def test_structured_output_that_breaks_the_contract_is_not_trusted():
    broken = {**REPORT, "decisions": [{**REPORT["decisions"][0], "action": "rewrote_production_code"}]}
    summary = summarize_transcript([_result(structured_output=broken)])
    assert summary.report is None
    assert summary.run.outcome == "invalid_report"


def test_a_truncated_transcript_without_a_result_event_has_no_report():
    summary = summarize_transcript([_init(), _assistant(("Skill", {"skill": "change-analysis"}))])
    assert summary.report is None
    assert summary.run.outcome == "no_result"
    assert summary.session_id == "s-1"


def test_a_resumed_repair_pass_adds_its_turns_cost_and_skills_and_supersedes_the_report():
    first = [_init(), _assistant(("Skill", {"skill": "change-analysis"})),
             _result(num_turns=30, total_cost_usd=0.3, structured_output={**REPORT, "summary": "First pass."})]
    repair = [_init(), _assistant(("Skill", {"skill": "test-verification"})),
              _result(num_turns=8, total_cost_usd=0.12, structured_output={**REPORT, "summary": "Repaired."})]
    summary = summarize_transcript(first + repair)
    assert summary.report.summary == "Repaired."
    assert summary.report.skills_used == ["change-analysis", "test-verification"]
    assert (summary.run.turns, summary.run.cost_usd, summary.run.passes) == (38, 0.42, 2)


def test_the_schema_given_to_the_agent_forbids_fields_outside_the_contract():
    schema = AgentReport.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(REPORT)
    decision = schema["$defs"]["Decision"]
    assert decision["properties"]["action"]["enum"] == ["created_tests", "updated_tests", "skipped"]
