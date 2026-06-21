"""Tests pour ProjectImporter (ticket-025)."""

from pathlib import Path

import pytest

from vibe_ide.services.project_importer import ImportError, ProjectImporter, _sanitize_id


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_source(tmp_path: Path, name: str = "mon-projet") -> Path:
    """Crée un dossier source minimal avec quelques fichiers."""
    src = tmp_path / "sources" / name
    src.mkdir(parents=True)
    (src / "main.py").write_text("print('hello')", encoding="utf-8")
    (src / "README.md").write_text("# Mon projet\n", encoding="utf-8")
    return src


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


# ------------------------------------------------------------------
# _sanitize_id
# ------------------------------------------------------------------


def test_sanitize_id_basic() -> None:
    assert _sanitize_id("Mon Projet") == "mon-projet"


def test_sanitize_id_special_chars() -> None:
    assert _sanitize_id("my_project.v2!") == "my-project-v2-"


def test_sanitize_id_truncates_at_50() -> None:
    long_name = "a" * 60
    result = _sanitize_id(long_name)
    assert len(result) == 50


def test_sanitize_id_already_valid() -> None:
    assert _sanitize_id("my-project-123") == "my-project-123"


# ------------------------------------------------------------------
# Validation — source_path
# ------------------------------------------------------------------


async def test_import_rejects_nonexistent_source(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    importer = ProjectImporter(ws)

    with pytest.raises(ImportError, match="n'existe pas"):
        await importer.import_project(tmp_path / "ghost", mode="symlink")


async def test_import_rejects_file_as_source(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")
    importer = ProjectImporter(ws)

    with pytest.raises(ImportError, match="dossier"):
        await importer.import_project(file_path, mode="symlink")


async def test_import_rejects_source_inside_workspace(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    inner = ws / "already-here"
    inner.mkdir()
    importer = ProjectImporter(ws)

    with pytest.raises(ImportError, match="déjà dans le workspace"):
        await importer.import_project(inner, mode="symlink")


async def test_import_rejects_workspace_itself(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    importer = ProjectImporter(ws)

    with pytest.raises(ImportError, match="déjà dans le workspace"):
        await importer.import_project(ws, mode="symlink")


async def test_import_rejects_parent_of_workspace(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    importer = ProjectImporter(ws)

    with pytest.raises(ImportError, match="parent du workspace"):
        await importer.import_project(tmp_path, mode="symlink")


# ------------------------------------------------------------------
# Mode symlink
# ------------------------------------------------------------------


async def test_import_symlink_creates_link(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    project = await importer.import_project(src, mode="symlink")

    dest = ws / "mon-projet"
    assert dest.is_symlink()
    assert dest.resolve() == src.resolve()
    assert project.id == "mon-projet"


async def test_import_symlink_source_files_accessible(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="symlink")

    assert (ws / "mon-projet" / "main.py").read_text() == "print('hello')"


async def test_import_symlink_with_explicit_project_id(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    project = await importer.import_project(src, mode="symlink", project_id="custom-id")

    assert project.id == "custom-id"
    assert (ws / "custom-id").is_symlink()


async def test_import_symlink_scaffolds_vibe_dirs(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="symlink")

    dest = ws / "mon-projet"
    assert (dest / "tickets" / "todo").is_dir()
    assert (dest / "tickets" / "done").is_dir()
    assert (dest / "memory").is_dir()
    assert (dest / "workspace").is_dir()


async def test_import_symlink_creates_claude_md_if_missing(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="symlink")

    claude_md = ws / "mon-projet" / "CLAUDE.md"
    assert claude_md.exists()
    assert "mon-projet" in claude_md.read_text()


async def test_import_symlink_preserves_existing_claude_md(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    existing_content = "# Projet existant\n\nDéjà documenté.\n"
    (src / "CLAUDE.md").write_text(existing_content, encoding="utf-8")
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="symlink")

    assert (ws / "mon-projet" / "CLAUDE.md").read_text() == existing_content


async def test_import_symlink_duplicate_raises(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="symlink")

    with pytest.raises(ImportError, match="existe déjà"):
        await importer.import_project(src, mode="symlink")


# ------------------------------------------------------------------
# Mode copy
# ------------------------------------------------------------------


async def test_import_copy_copies_files(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    project = await importer.import_project(src, mode="copy")

    dest = ws / "mon-projet"
    assert dest.is_dir() and not dest.is_symlink()
    assert (dest / "main.py").read_text() == "print('hello')"
    assert project.id == "mon-projet"


async def test_import_copy_excludes_dot_git(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    (src / ".git").mkdir()
    (src / ".git" / "config").write_text("[core]\n")
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    assert not (ws / "mon-projet" / ".git").exists()


async def test_import_copy_excludes_node_modules(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    (src / "node_modules").mkdir()
    (src / "node_modules" / "lodash").mkdir()
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    assert not (ws / "mon-projet" / "node_modules").exists()


async def test_import_copy_excludes_venv(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    (src / ".venv").mkdir()
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    assert not (ws / "mon-projet" / ".venv").exists()


async def test_import_copy_excludes_env_files(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    (src / ".env").write_text("SECRET=abc123")
    (src / ".env.local").write_text("SECRET=local")
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    assert not (ws / "mon-projet" / ".env").exists()
    assert not (ws / "mon-projet" / ".env.local").exists()


async def test_import_copy_excludes_pyc(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    (src / "app.pyc").write_bytes(b"\x00\x00")
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    assert not (ws / "mon-projet" / "app.pyc").exists()


async def test_import_copy_scaffolds_vibe_dirs(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    dest = ws / "mon-projet"
    assert (dest / "tickets" / "todo").is_dir()
    assert (dest / "memory").is_dir()


async def test_import_copy_duplicate_raises(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    with pytest.raises(ImportError, match="existe déjà"):
        await importer.import_project(src, mode="copy")


async def test_import_copy_preserves_existing_tickets(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    (src / "tickets").mkdir()
    (src / "tickets" / "todo").mkdir()
    (src / "tickets" / "todo" / "ticket-001.md").write_text("---\nid: ticket-001\n---\n")
    importer = ProjectImporter(ws)

    await importer.import_project(src, mode="copy")

    ticket = ws / "mon-projet" / "tickets" / "todo" / "ticket-001.md"
    assert ticket.exists()


# ------------------------------------------------------------------
# Retour Project
# ------------------------------------------------------------------


async def test_import_returns_project_model(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    src = _make_source(tmp_path)
    (src / "CLAUDE.md").write_text("# Super Projet\n\nDescription.\n", encoding="utf-8")
    importer = ProjectImporter(ws)

    project = await importer.import_project(src, mode="symlink")

    assert project.id == "mon-projet"
    assert project.name == "Super Projet"
    assert project.description == "Description."
