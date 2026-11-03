"""Reviewer prompt asks to search callers of what the diff removes — ticket-608."""
from pathlib import Path

PROMPT = Path(__file__).resolve().parents[2] / "agents" / "prompts" / "reviewer.md"


def _blocking_section() -> str:
    text = PROMPT.read_text(encoding="utf-8")
    start = text.index("### Bloquant")
    end = text.index("### Non bloquant", start)
    return text[start:end]


def test_blocking_section_asks_to_grep_callers_of_removed_paths() -> None:
    section = _blocking_section()
    assert "appelant" in section
    assert "`Grep`" in section


def test_blocking_section_names_the_removed_kinds() -> None:
    section = _blocking_section()
    for word in ("route", "export", "chemin", "supprime"):
        assert word in section
