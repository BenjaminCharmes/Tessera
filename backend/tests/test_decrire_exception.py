from tessera.utils.exceptions import decrire_exception


def test_empty_exception_is_described_by_its_type() -> None:
    description = decrire_exception(TimeoutError())

    assert description
    assert "TimeoutError" in description


def test_message_is_kept_and_prefixed_with_the_type() -> None:
    assert decrire_exception(ValueError("bad value")) == "ValueError: bad value"


def test_message_already_naming_the_type_is_not_doubled() -> None:
    assert decrire_exception(ValueError("ValueError: bad")) == "ValueError: bad"


def test_whitespace_only_message_counts_as_empty() -> None:
    assert decrire_exception(OSError("  ")) == "OSError"
