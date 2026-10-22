import json
from collections.abc import Iterable

from pydantic import BaseModel, ValidationError

from .models import AgentReport, AgentRun


class TranscriptSummary(BaseModel):
    report: AgentReport | None
    session_id: str | None
    run: AgentRun


def _events(lines: Iterable[str]) -> list[dict]:
    events = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _observed_skills(events: list[dict]) -> list[str]:
    skills: list[str] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for item in event.get("message", {}).get("content", []):
            if not isinstance(item, dict) or item.get("type") != "tool_use" or item.get("name") != "Skill":
                continue
            skill = (item.get("input") or {}).get("skill")
            if skill and skill not in skills:
                skills.append(skill)
    return skills


def _describe_denial(denial: dict) -> str:
    tool_input = denial.get("tool_input") or {}
    target = tool_input.get("command") or tool_input.get("file_path") or tool_input.get("url") or ""
    return f"{denial.get('tool_name', 'unknown')}: {target}".strip()


def _report(result: dict | None, skills: list[str]) -> AgentReport | None:
    output = (result or {}).get("structured_output")
    if not isinstance(output, dict):
        return None
    try:
        return AgentReport.model_validate({**output, "skills_used": skills})
    except ValidationError:
        return None


def _outcome(result: dict | None, report: AgentReport | None) -> str:
    if result is None:
        return "no_result"
    if report is None and isinstance(result.get("structured_output"), dict):
        return "invalid_report"
    return result.get("subtype", "unknown")


def summarize_transcript(lines: Iterable[str]) -> TranscriptSummary:
    events = _events(lines)
    init = next((event for event in events if event.get("type") == "system" and event.get("subtype") == "init"), {})
    results = [event for event in events if event.get("type") == "result"]
    result = results[-1] if results else None
    report = _report(result, _observed_skills(events))
    return TranscriptSummary(
        report=report,
        session_id=init.get("session_id"),
        run=AgentRun(
            model=init.get("model"),
            outcome=_outcome(result, report),
            passes=len(results),
            turns=sum(item.get("num_turns") or 0 for item in results) if results else None,
            cost_usd=round(sum(item.get("total_cost_usd") or 0 for item in results), 2),
            denied_tool_calls=[
                _describe_denial(denial) for item in results for denial in item.get("permission_denials") or []
            ],
        ),
    )
