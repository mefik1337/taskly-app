import re
from dataclasses import dataclass, field

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass
class FileChange:
    path: str
    status: str = "modified"
    added_lines: list[int] = field(default_factory=list)
    previous_path: str | None = None


def _strip_prefix(value: str, prefix: str) -> str:
    return value[len(prefix):] if value.startswith(prefix) else value


def _header_path(line: str) -> str:
    _, _, new_path = line.rpartition(" b/")
    return new_path


def parse_unified_diff(text: str) -> list[FileChange]:
    changes: list[FileChange] = []
    current: FileChange | None = None
    next_line = 0
    in_hunk = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            current = FileChange(path=_header_path(line))
            changes.append(current)
            in_hunk = False
        elif current is None:
            continue
        elif match := HUNK_HEADER.match(line):
            next_line = int(match.group(1))
            in_hunk = True
        elif in_hunk:
            if line.startswith("+"):
                current.added_lines.append(next_line)
                next_line += 1
            elif line.startswith(" "):
                next_line += 1
        elif line.startswith("new file mode"):
            current.status = "added"
        elif line.startswith("deleted file mode"):
            current.status = "deleted"
        elif line.startswith("rename from "):
            current.status = "renamed"
            current.previous_path = _strip_prefix(line, "rename from ")
        elif line.startswith("rename to "):
            current.path = _strip_prefix(line, "rename to ")
        elif line.startswith("+++ b/"):
            current.path = _strip_prefix(line, "+++ b/")
    return changes
