import re
from xml.etree import ElementTree

MAX_MESSAGE_LENGTH = 300
ANSI_SEQUENCE = re.compile(r"(?:\x1b|#x1B)\[[0-9;]*[A-Za-z]")


def _outcome(case: ElementTree.Element) -> tuple[str, ElementTree.Element | None]:
    for outcome in ("failure", "error", "skipped"):
        element = case.find(outcome)
        if element is not None:
            return outcome, element
    return "passed", None


def summarize_junit(xml_text: str) -> dict:
    root = ElementTree.fromstring(xml_text)
    counts = {"passed": 0, "failure": 0, "error": 0, "skipped": 0}
    failed_cases = []
    cases = list(root.iter("testcase"))
    for case in cases:
        outcome, element = _outcome(case)
        counts[outcome] += 1
        if outcome in ("failure", "error"):
            message = ANSI_SEQUENCE.sub("", element.get("message") or (element.text or "").strip())
            failed_cases.append({
                "name": f"{case.get('classname', '')}::{case.get('name', '')}",
                "message": message[:MAX_MESSAGE_LENGTH],
            })
    return {
        "tests": len(cases),
        "passed": counts["passed"],
        "failures": counts["failure"],
        "errors": counts["error"],
        "skipped": counts["skipped"],
        "failed_cases": failed_cases,
    }
