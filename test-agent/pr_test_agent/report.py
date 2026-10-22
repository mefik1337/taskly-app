import html
import re

MARKER = "<!-- taskly-test-agent -->"
MENTION = re.compile(r"@(?=[\w-])")
SUMMARY_LIMIT = 600
CELL_LIMIT = 300

HEADLINES = {
    "committed": "✅ Tests were generated, verified and committed in {commit}.",
    "verification_failed": "❌ The generated tests failed independent verification, so nothing was committed.",
    "rejected": "⛔ The agent's changes were rejected by the path guard and discarded.",
    "no_targets": "ℹ️ No changed production code needs unit tests, so the agent was not started.",
    "agent_failed": "⚠️ The agent did not finish with a valid report, so nothing was committed.",
    "no_changes": "✅ The agent reviewed the changes and decided that no new tests are needed.",
    "verified_not_committed": (
        "☑️ Tests were generated and verified but not committed. "
        "Download the `test-agent-patch` artifact and apply it with `git apply`."
    ),
}

ACTION_LABELS = {
    "created_tests": "created tests",
    "updated_tests": "updated tests",
    "skipped": "skipped",
}


def _text(value: str, limit: int = CELL_LIMIT) -> str:
    collapsed = " ".join(str(value).split())
    if len(collapsed) > limit:
        collapsed = collapsed[: limit - 1] + "…"
    escaped = html.escape(collapsed, quote=False)
    return MENTION.sub("@​", escaped).replace("|", "\\|")


def _code(value: str) -> str:
    return f"`{_text(value).replace('`', '')}`"


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def _decisions(agent: dict) -> list[str]:
    lines = ["### Agent decisions", "", "| Changed file | Decision | Reason |", "| --- | --- | --- |"]
    for decision in agent["decisions"]:
        lines.append(
            f"| {_code(decision['path'])} | {ACTION_LABELS.get(decision['action'], 'unknown')} "
            f"| {_text(decision['reason'])} |"
        )
    return lines


def _test_files(agent: dict) -> list[str]:
    lines = ["### Tests written by the agent", "", "| Test file | Change | Test cases |", "| --- | --- | --- |"]
    for test_file in agent["test_files"]:
        lines.append(f"| {_code(test_file['path'])} | {_text(test_file['change'])} | {len(test_file['cases'])} |")
    return lines


def _verification(verification: dict) -> list[str]:
    lines = [
        "### Verification",
        "",
        "| Suite | Tests | Passed | Failed | Skipped |",
        "| --- | --- | --- | --- | --- |",
    ]
    for suite, summary in verification["suites"].items():
        failed = summary["failures"] + summary["errors"]
        lines.append(f"| {suite} | {summary['tests']} | {summary['passed']} | {failed} | {summary['skipped']} |")
    failed_cases = [case for summary in verification["suites"].values() for case in summary["failed_cases"]]
    if failed_cases:
        lines += ["", "**Failing tests:**", ""]
        lines += [f"- {_code(case['name'])}: {_text(case['message'])}" for case in failed_cases]
    if verification["violations"]:
        lines += ["", "**Guard violations:**", ""]
        lines += [f"- {_text(violation)}" for violation in verification["violations"]]
    return lines


def _suspected_bugs(agent: dict) -> list[str]:
    bugs = agent.get("suspected_bugs") or []
    if not bugs:
        return []
    return ["### Possible bugs in production code", ""] + [
        f"- {_code(bug['path'])}: {_text(bug['description'])}" for bug in bugs
    ]


def _ranges(lines: list[int]) -> str:
    spans: list[list[int]] = []
    for line in sorted(lines):
        if spans and line == spans[-1][1] + 1:
            spans[-1][1] = line
        else:
            spans.append([line, line])
    return ", ".join(str(start) if start == end else f"{start}–{end}" for start, end in spans) or "—"


def _coverage(coverage: dict) -> list[str]:
    before = {item["path"]: item for item in coverage["before"]["files"]}
    lines = [
        "### Coverage of changed lines",
        "",
        f"**Changed lines covered:** {_percent(coverage['before']['total']['percent'])} → "
        f"{_percent(coverage['after']['total']['percent'])}",
        "",
        "| File | Before | After | Uncovered lines after |",
        "| --- | --- | --- | --- |",
    ]
    for item in coverage["after"]["files"]:
        previous = before.get(item["path"], {}).get("percent")
        lines.append(
            f"| `{item['path']}` | {_percent(previous)} | {_percent(item['percent'])} "
            f"| {_ranges(item['uncovered_lines'])} |"
        )
    return lines


def _agent_sections(agent: dict | None) -> list[list[str]]:
    if not agent:
        return []
    return [
        [f"> {_text(agent['summary'], SUMMARY_LIMIT)}"],
        _decisions(agent),
        _test_files(agent) if agent["test_files"] else [],
    ]


def _agent_run(run: dict | None) -> list[str]:
    if not run:
        return []
    denied = run.get("denied_tool_calls") or []
    noun = "call" if len(denied) == 1 else "calls"
    lines = [
        f"**Agent run:** {_code(run.get('model') or 'unknown')}, {run.get('turns') or 0} turns, "
        f"${run.get('cost_usd') or 0:.2f}, {len(denied)} denied tool {noun}"
    ]
    if denied:
        lines += ["", *(f"- {_text(call)}" for call in denied)]
    return lines


def render_comment(data: dict) -> str:
    agent = data["agent"]
    headline = HEADLINES[data["status"]].format(commit=(data.get("commit_sha") or "")[:7])
    sections = [
        [MARKER, "## 🧪 Test agent report", "", headline],
        *_agent_sections(agent),
        _verification(data["verification"]) if data["verification"] else [],
        _suspected_bugs(agent) if agent else [],
        _coverage(data["coverage"]) if data["coverage"] else [],
        ["### Skills used", "", ", ".join(_code(skill) for skill in agent["skills_used"])] if agent else [],
        _agent_run(data.get("run")),
        [f"[Workflow run]({data['run_url']})"],
    ]
    return "\n\n".join("\n".join(section) for section in sections if section) + "\n"
