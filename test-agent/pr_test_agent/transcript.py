import json
from collections.abc import Iterable


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


def _tool_uses(event: dict) -> list[dict]:
    if event.get("type") != "assistant":
        return []
    content = event.get("message", {}).get("content", [])
    return [item for item in content if isinstance(item, dict) and item.get("type") == "tool_use"]


def _describe_denial(denial: dict) -> str:
    tool_input = denial.get("tool_input") or {}
    target = tool_input.get("command") or tool_input.get("file_path") or tool_input.get("url") or ""
    return f"{denial.get('tool_name', 'unknown')}: {target}".strip()


def summarize_transcript(lines: Iterable[str]) -> dict:
    events = _events(lines)
    init = next((event for event in events if event.get("type") == "system" and event.get("subtype") == "init"), {})
    result = next((event for event in reversed(events) if event.get("type") == "result"), None)
    skills: list[str] = []
    for event in events:
        for tool_use in _tool_uses(event):
            skill = (tool_use.get("input") or {}).get("skill")
            if tool_use.get("name") == "Skill" and skill and skill not in skills:
                skills.append(skill)
    report = (result or {}).get("structured_output")
    if isinstance(report, dict):
        report = {**report, "skills_used": skills}
    else:
        report = None
    return {
        "report": report,
        "run": {
            "model": init.get("model"),
            "outcome": result.get("subtype", "unknown") if result else "no_result",
            "turns": (result or {}).get("num_turns"),
            "cost_usd": round((result or {}).get("total_cost_usd") or 0, 2),
            "denied_tool_calls": [_describe_denial(denial) for denial in (result or {}).get("permission_denials") or []],
        },
    }
