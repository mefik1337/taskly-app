from collections.abc import Iterable

MIN_SECRET_LENGTH = 8
PLACEHOLDER = "[REDACTED]"


def redact(text: str, secrets: Iterable[str | None]) -> str:
    values = sorted({secret for secret in secrets if secret and len(secret) >= MIN_SECRET_LENGTH}, key=len, reverse=True)
    for value in values:
        text = text.replace(value, PLACEHOLDER)
    return text
