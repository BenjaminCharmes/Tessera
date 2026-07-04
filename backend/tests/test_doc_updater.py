"""Tests for DocUpdaterService (ticket-034)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.services.doc_updater import DocUpdateResult, DocUpdaterService


@pytest.fixture
def project_path(tmp_path: Path) -> Path:
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n\n## API\n\nGET /health\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("# Architecture\n")
    (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md\n\nStack: Python\n")
    return tmp_path


@pytest.fixture
def service() -> DocUpdaterService:
    mock_client = MagicMock()
    return DocUpdaterService(mock_client, Path("agents/prompts"))


class TestDocUpdaterService:
    async def test_no_changes_when_llm_says_no_changes(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"no_changes": true}')]
        service._client.messages.create = AsyncMock(return_value=mock_msg)

        result = await service.update_docs(project_path, diff="minor fix", ticket_title="fix: typo")

        assert result.no_changes is True
        assert result.files_updated == []

    async def test_updates_readme_when_llm_returns_files(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        new_content = "# My Project\n\n## API\n\nGET /health\nPOST /users\n"
        mock_msg = MagicMock()
        mock_msg.content = [
            MagicMock(
                text=json.dumps({"files": [{"path": "README.md", "content": new_content}]})
            )
        ]
        service._client.messages.create = AsyncMock(return_value=mock_msg)

        result = await service.update_docs(project_path, diff="added POST /users", ticket_title="feat: users")

        assert result.no_changes is False
        assert "README.md" in result.files_updated
        assert (project_path / "README.md").read_text() == new_content

    async def test_updates_multiple_files(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        mock_msg = MagicMock()
        mock_msg.content = [
            MagicMock(
                text='{"files": [{"path": "README.md", "content": "# updated"}, {"path": "CLAUDE.md", "content": "# updated claude"}]}'
            )
        ]
        service._client.messages.create = AsyncMock(return_value=mock_msg)

        result = await service.update_docs(project_path, diff="big refactor", ticket_title="refactor: core")

        assert len(result.files_updated) == 2
        assert "README.md" in result.files_updated
        assert "CLAUDE.md" in result.files_updated

    async def test_skips_files_outside_project(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        """Files with path traversal or outside project_path must be ignored."""
        mock_msg = MagicMock()
        mock_msg.content = [
            MagicMock(
                text='{"files": [{"path": "../../../etc/passwd", "content": "hacked"}]}'
            )
        ]
        service._client.messages.create = AsyncMock(return_value=mock_msg)

        result = await service.update_docs(project_path, diff="evil", ticket_title="hack")

        assert result.files_updated == []

    async def test_returns_no_changes_on_invalid_json(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="I cannot help with that.")]
        service._client.messages.create = AsyncMock(return_value=mock_msg)

        result = await service.update_docs(project_path, diff="x", ticket_title="feat: x")

        assert result.no_changes is True
        assert result.files_updated == []

    async def test_docs_truncated_to_8k(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        big_readme = "x" * 20_000
        (project_path / "README.md").write_text(big_readme)
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"no_changes": true}')]
        service._client.messages.create = AsyncMock(return_value=mock_msg)

        await service.update_docs(project_path, diff="y", ticket_title="feat: y")

        call_args = service._client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]
        assert len(user_content) <= 8000 * 5  # rough upper bound across all docs

    async def test_empty_diff_produces_no_changes(
        self, service: DocUpdaterService, project_path: Path
    ) -> None:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"no_changes": true}')]
        service._client.messages.create = AsyncMock(return_value=mock_msg)

        result = await service.update_docs(project_path, diff="", ticket_title="chore: bump")

        assert result.no_changes is True


class TestDocUpdateResult:
    def test_default_values(self) -> None:
        result = DocUpdateResult(no_changes=True, files_updated=[])
        assert result.no_changes is True
        assert result.files_updated == []

    def test_with_files(self) -> None:
        result = DocUpdateResult(no_changes=False, files_updated=["README.md"])
        assert result.no_changes is False
        assert "README.md" in result.files_updated
