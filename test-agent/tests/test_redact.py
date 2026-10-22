from pr_test_agent.redact import redact


def test_every_occurrence_of_each_secret_is_replaced():
    text = '{"output": "token=abc123def456 and again abc123def456", "key": "sk-ant-xyz"}'
    assert redact(text, ["abc123def456", "sk-ant-xyz"]) == (
        '{"output": "token=[REDACTED] and again [REDACTED]", "key": "[REDACTED]"}'
    )


def test_empty_or_short_values_are_ignored_to_avoid_mangling_the_transcript():
    assert redact("a 1 b", ["", "1", None]) == "a 1 b"


def test_longer_secrets_are_redacted_before_their_prefixes():
    assert redact("secret-long", ["secret", "secret-long"]) == "[REDACTED]"
