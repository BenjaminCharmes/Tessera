"""Tests for pure-text pipeline helpers — ticket-214.

Focuses on `_extract_criteria`, which must reassemble multi-line criteria
before handing them to the validator.
"""
from tessera.services.pipeline_text import _extract_criteria


class TestExtractCriteria:
    """Acceptance-criteria extraction from ticket markdown bodies."""

    _HEADER = "## Critères d'acceptation\n"

    def _body(self, content: str) -> str:
        return self._HEADER + content

    # --- ticket-214 acceptance criteria ---

    def test_multiline_criterion_joined(self) -> None:
        """A criterion split across two lines (second indented) yields one entry."""
        body = self._body(
            "- [ ] First line of the criterion\n"
            "      that continues here\n"
        )
        result = _extract_criteria(body)
        assert result == ["First line of the criterion that continues here"]

    def test_two_single_line_criteria(self) -> None:
        """Two single-line criteria yield two separate entries (non-regression)."""
        body = self._body(
            "- [ ] First criterion\n"
            "- [ ] Second criterion\n"
        )
        result = _extract_criteria(body)
        assert result == ["First criterion", "Second criterion"]

    def test_blank_line_does_not_extend_criterion(self) -> None:
        """A blank line after a criterion does not become part of it."""
        body = self._body(
            "- [ ] Only line\n"
            "\n"
            "- [ ] Next criterion\n"
        )
        result = _extract_criteria(body)
        assert result == ["Only line", "Next criterion"]

    def test_indented_line_after_blank_line_is_not_a_continuation(self) -> None:
        """An indented paragraph separated by a blank line stays out of the criterion."""
        body = self._body(
            "- [ ] Only line\n"
            "\n"
            "    an unrelated indented paragraph\n"
            "- [ ] Next criterion\n"
        )
        result = _extract_criteria(body)
        assert result == ["Only line", "Next criterion"]

    def test_checked_criteria_read_same_way(self) -> None:
        """Checked boxes `- [x]` are extracted the same as unchecked ones."""
        body = self._body(
            "- [x] Done criterion on one line\n"
            "- [x] Done multiline criterion\n"
            "      second part here\n"
        )
        result = _extract_criteria(body)
        assert result == [
            "Done criterion on one line",
            "Done multiline criterion second part here",
        ]

    # --- additional edge cases ---

    def test_continuation_with_tab_indent(self) -> None:
        """Tab-indented continuation lines are also joined."""
        body = self._body(
            "- [ ] Main text\n"
            "\tcontinuation with tab\n"
        )
        result = _extract_criteria(body)
        assert result == ["Main text continuation with tab"]

    def test_multiple_continuation_lines(self) -> None:
        """More than one continuation line is fully joined."""
        body = self._body(
            "- [ ] Line one\n"
            "      line two\n"
            "      line three\n"
        )
        result = _extract_criteria(body)
        assert result == ["Line one line two line three"]

    def test_next_section_terminates_extraction(self) -> None:
        """A second `##` heading ends the criteria section."""
        body = self._body(
            "- [ ] Only criterion\n"
            "## Other section\n"
            "- [ ] Not a criterion\n"
        )
        result = _extract_criteria(body)
        assert result == ["Only criterion"]

    def test_english_heading_accepted(self) -> None:
        """An English `## Acceptance criteria` heading is recognised."""
        body = "## Acceptance criteria\n- [ ] Works fine\n"
        result = _extract_criteria(body)
        assert result == ["Works fine"]

    def test_no_criteria_section_returns_empty(self) -> None:
        """A body without a criteria heading yields an empty list."""
        body = "## Context\nSome prose.\n"
        result = _extract_criteria(body)
        assert result == []

    def test_uppercase_x_treated_as_checked(self) -> None:
        """Uppercase `- [X]` is extracted like `- [x]`."""
        body = self._body("- [X] Uppercase checked\n")
        result = _extract_criteria(body)
        assert result == ["Uppercase checked"]

    # --- ticket-362 acceptance criteria ---

    def test_heading_title_in_prose_does_not_open_section(self) -> None:
        """A criteria heading cited in prose (e.g. backticks) must not open the section."""
        body = (
            "## Contexte\n"
            "See `## Critères d'acceptation` below.\n"
            "## Solution proposée\n"
            "Some text.\n"
            "## Critères d'acceptation\n"
            "- [ ] First real criterion\n"
            "- [ ] Second real criterion\n"
        )
        result = _extract_criteria(body)
        assert result == ["First real criterion", "Second real criterion"]

    def test_criterion_whose_text_cites_heading_is_included(self) -> None:
        """A criterion whose text contains the heading title is still extracted."""
        body = self._body(
            "- [ ] Verify that `## Critères d'acceptation` is matched only at line start\n"
            "- [ ] Another criterion\n"
        )
        result = _extract_criteria(body)
        assert result == [
            "Verify that `## Critères d'acceptation` is matched only at line start",
            "Another criterion",
        ]
