"""Tests for DocUpdaterService (ticket-034)."""

import json
from pathlib import Path

import pytest

from tests.test_providers_base import FakeProvider
from vibe_ide.services.doc_updater import DocUpdateResult, DocUpdaterService


@pytest.fixture
def project_path(tmp_path: Path) -> Path:
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n\n## API\n\nGET /health\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md\n\nStack: Python\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def service() -> DocUpdaterService:
    return DocUpdaterService(FakeProvider(), Path("agents/prompts"))


class TestDocUpdaterService:
    async def test_no_changes_when_llm_says_no_changes(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        service._provider = FakeProvider(content='{"no_changes": true}')

        result = await service.update_docs(project_path, diff="minor fix", ticket_title="fix: typo")

        assert result.no_changes is True
        assert result.files_updated == []

    async def test_updates_readme_when_llm_returns_files(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        new_content = "# My Project\n\n## API\n\nGET /health\nPOST /users\n"
        service._provider = FakeProvider(
            content=json.dumps({"files": [{"path": "README.md", "content": new_content}]})
        )

        result = await service.update_docs(project_path, diff="added POST /users", ticket_title="feat: users")

        assert result.no_changes is False
        assert "README.md" in result.files_updated
        assert (project_path / "README.md").read_text(encoding="utf-8") == new_content

    async def test_updates_multiple_files(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        service._provider = FakeProvider(
            content='{"files": [{"path": "README.md", "content": "# updated"}, {"path": "CLAUDE.md", "content": "# updated claude"}]}'
        )

        result = await service.update_docs(project_path, diff="big refactor", ticket_title="refactor: core")

        assert len(result.files_updated) == 2
        assert "README.md" in result.files_updated
        assert "CLAUDE.md" in result.files_updated

    async def test_skips_files_outside_project(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        """Files with path traversal or outside project_path must be ignored."""
        service._provider = FakeProvider(
            content='{"files": [{"path": "../../../etc/passwd", "content": "hacked"}]}'
        )

        result = await service.update_docs(project_path, diff="evil", ticket_title="hack")

        assert result.files_updated == []

    async def test_returns_no_changes_on_invalid_json(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        service._provider = FakeProvider(content="I cannot help with that.")

        result = await service.update_docs(project_path, diff="x", ticket_title="feat: x")

        assert result.no_changes is True
        assert result.files_updated == []

    async def test_docs_truncated_to_8k(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        big_readme = "x" * 20_000
        (project_path / "README.md").write_text(big_readme, encoding="utf-8")
        service._provider = FakeProvider(content='{"no_changes": true}')

        await service.update_docs(project_path, diff="y", ticket_title="feat: y")

        user_content = service._provider.calls[0]["user"]
        assert len(user_content) <= 8000 * 5  # rough upper bound across all docs

    async def test_empty_diff_produces_no_changes(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        service._provider = FakeProvider(content='{"no_changes": true}')

        result = await service.update_docs(project_path, diff="", ticket_title="chore: bump")

        assert result.no_changes is True

    async def test_no_changes_on_llm_failure(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        """Regression — ticket-044 review, finding 6: doc_updater's except
        Exception degradation path had no unit test, unlike validator's and
        security_auditor's equivalents."""

        class _FailingProvider(FakeProvider):
            async def complete(self, **kwargs):  # type: ignore[override]
                raise Exception("Network error")

        service._provider = _FailingProvider()

        result = await service.update_docs(project_path, diff="x", ticket_title="feat: x")

        assert result.no_changes is True
        assert result.files_updated == []


class TestDocUpdateResult:
    def test_default_values(self) -> None:
        result = DocUpdateResult(no_changes=True, files_updated=[])
        assert result.no_changes is True
        assert result.files_updated == []

    def test_with_files(self) -> None:
        result = DocUpdateResult(no_changes=False, files_updated=["README.md"])
        assert result.no_changes is False
        assert "README.md" in result.files_updated
