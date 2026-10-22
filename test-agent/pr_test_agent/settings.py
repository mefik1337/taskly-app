from .stacks import STACKS, Stack

READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "Skill"]
READ_ONLY_GIT = ["Bash(git diff *)", "Bash(git log *)", "Bash(git show *)", "Bash(git status *)"]
PROTECTED_ROOTS = [".github/**", ".claude/**", "test-agent/**"]
ALWAYS_DENIED = [
    "WebFetch",
    "WebSearch",
    "Read(**/.env)",
    "Read(**/.env.*)",
    "Read(//proc/**)",
    "Bash(env)",
    "Bash(env *)",
    "Bash(printenv)",
    "Bash(printenv *)",
    "Bash(set)",
    "Bash(export *)",
    "Bash(cat /proc/*)",
]


def _edit_and_write(patterns: list[str]) -> list[str]:
    return [f"{tool}({pattern})" for tool in ("Edit", "Write") for pattern in patterns]


def claude_settings(stack: Stack) -> dict:
    other_roots = [f"{other.root}/**" for other in STACKS.values() if other.name != stack.name]
    return {
        "permissions": {
            "defaultMode": "dontAsk",
            "allow": [
                *READ_ONLY_TOOLS,
                *_edit_and_write(list(stack.test_patterns)),
                f"Bash({stack.runner})",
                f"Bash({stack.runner} *)",
                *READ_ONLY_GIT,
            ],
            "deny": [
                *ALWAYS_DENIED,
                *_edit_and_write([*other_roots, *PROTECTED_ROOTS]),
            ],
        },
        "env": {"DISABLE_AUTOUPDATER": "1", "DISABLE_TELEMETRY": "1", "DISABLE_ERROR_REPORTING": "1"},
    }
