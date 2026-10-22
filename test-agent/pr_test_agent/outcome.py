def _suites_pass(suites: dict) -> bool:
    return bool(suites) and all(
        summary["tests"] > 0 and summary["failures"] == 0 and summary["errors"] == 0
        for summary in suites.values()
    )


def resolve_status(
    *,
    has_targets: bool,
    agent_report: dict | None,
    violations: list[str],
    suites: dict,
    patch_changed: bool,
) -> str:
    if not has_targets:
        return "no_targets"
    if agent_report is None:
        return "agent_failed"
    if violations:
        return "rejected"
    if not _suites_pass(suites):
        return "verification_failed"
    if not patch_changed:
        return "no_changes"
    return "verified"
