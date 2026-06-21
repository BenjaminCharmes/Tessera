"""Tests TDD pour ProjectAnalyzerService — ticket-026."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.services.project_analyzer import ProjectAnalyzerService


# ------------------------------------------------------------------
# Constants / helpers
# ------------------------------------------------------------------

_VALID_RESPONSE = json.dumps(
    {
        "claude_md": "# My Project\n\nUn projet Python.\n\n## Agents actifs\n\n- `codeur` — implémente\n- `reviewer` — valide\n",
        "detected_stack": ["Python", "FastAPI"],
        "suggested_agents": ["codeur", "reviewer"],
    }
)

_VALID_REACT_RESPONSE = json.dumps(
    {
        "claude_md": "# React App\n\nUne app TypeScript React.\n\n## Agents actifs\n\n- `codeur` — implémente\n",
        "detected_stack": ["TypeScript", "React"],
        "suggested_agents": ["codeur", "reviewer"],
    }
)


def _make_mock_client(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=response_text)]
    mock_resp.usage = MagicMock(input_tokens=100, output_tokens=200)
    mock.messages.create = AsyncMock(return_value=mock_resp)
    return mock


def _make_service(tmp_path: Path, response_text: str) -> ProjectAnalyzerService:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "project-analyzer.md").write_text(
        "Tu es un expert en analyse de projets.", encoding="utf-8"
    )
    return ProjectAnalyzerService(
        client=_make_mock_client(response_text),
        prompts_dir=prompts_dir,
    )


def _make_python_project(tmp_path: Path) -> Path:
    project = tmp_path / "workspace" / "my-project"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname = 'my-project'\n", encoding="utf-8")
    (project / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    (project / "README.md").write_text("# My Project\n", encoding="utf-8")
    return project


def _make_react_project(tmp_path: Path) -> Path:
    project = tmp_path / "workspace" / "react-app"
    project.mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"name": "react-app", "dependencies": {"react": "^18.0.0"}}),
        encoding="utf-8",
    )
    (project / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}', encoding="utf-8")
    (project / "README.md").write_text("# React App\n", encoding="utf-8")
    return project


# ------------------------------------------------------------------
# analyze() — résultat retourné
# ------------------------------------------------------------------


async def test_analyze_returns_detected_stack(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.analyze(project)
    assert result.detected_stack == ["Python", "FastAPI"]


async def test_analyze_returns_suggested_agents(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.analyze(project)
    assert result.suggested_agents == ["codeur", "reviewer"]


async def test_analyze_returns_claude_md_text(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.analyze(project)
    assert "My Project" in result.claude_md


# ------------------------------------------------------------------
# analyze() — écriture de CLAUDE.md
# ------------------------------------------------------------------


async def test_analyze_writes_claude_md_when_absent(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    await svc.analyze(project)
    assert (project / "CLAUDE.md").exists()


async def test_analyze_returns_written_true_when_absent(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.analyze(project)
    assert result.claude_md_written is True


async def test_analyze_preserves_existing_claude_md(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    original = "# Déjà documenté\n\nContenu original.\n"
    (project / "CLAUDE.md").write_text(original, encoding="utf-8")
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    await svc.analyze(project, overwrite=False)
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == original


async def test_analyze_returns_written_false_when_exists(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    (project / "CLAUDE.md").write_text("# Existant\n", encoding="utf-8")
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.analyze(project, overwrite=False)
    assert result.claude_md_written is False


async def test_analyze_overwrites_when_flag_set(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    (project / "CLAUDE.md").write_text("# Ancien\n", encoding="utf-8")
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.analyze(project, overwrite=True)
    assert result.claude_md_written is True
    assert "My Project" in (project / "CLAUDE.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------
# Filtrage des fichiers sensibles
# ------------------------------------------------------------------


def _make_svc_no_client(tmp_path: Path) -> ProjectAnalyzerService:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    return ProjectAnalyzerService(client=MagicMock(), prompts_dir=prompts_dir)


def test_is_sensitive_env_file(tmp_path: Path) -> None:
    svc = _make_svc_no_client(tmp_path)
    assert svc._is_sensitive(tmp_path / ".env") is True


def test_is_sensitive_env_local(tmp_path: Path) -> None:
    svc = _make_svc_no_client(tmp_path)
    assert svc._is_sensitive(tmp_path / ".env.local") is True


def test_is_sensitive_env_production(tmp_path: Path) -> None:
    svc = _make_svc_no_client(tmp_path)
    assert svc._is_sensitive(tmp_path / ".env.production") is True


def test_is_sensitive_key_file(tmp_path: Path) -> None:
    svc = _make_svc_no_client(tmp_path)
    assert svc._is_sensitive(tmp_path / "private.key") is True


def test_is_sensitive_pem_file(tmp_path: Path) -> None:
    svc = _make_svc_no_client(tmp_path)
    assert svc._is_sensitive(tmp_path / "cert.pem") is True


def test_is_sensitive_secrets_file(tmp_path: Path) -> None:
    svc = _make_svc_no_client(tmp_path)
    assert svc._is_sensitive(tmp_path / "secrets.json") is True


def test_is_not_sensitive_regular_py(tmp_path: Path) -> None:
    svc = _make_svc_no_client(tmp_path)
    assert svc._is_sensitive(tmp_path / "main.py") is False


def test_sensitive_files_excluded_from_collection(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("SECRET=abc123", encoding="utf-8")
    (project / "main.py").write_text("print('hello')", encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    contents = svc._collect_file_contents(project)
    paths = [rel for rel, _ in contents]
    assert ".env" not in paths
    assert "main.py" in paths


async def test_env_content_not_sent_to_claude(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    (project / ".env").write_text("SECRET_KEY=super-secret", encoding="utf-8")
    mock_client = _make_mock_client(_VALID_RESPONSE)
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "project-analyzer.md").write_text("system", encoding="utf-8")
    svc = ProjectAnalyzerService(client=mock_client, prompts_dir=prompts_dir)
    await svc.analyze(project)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "super-secret" not in user_content


# ------------------------------------------------------------------
# Filtrage des dossiers exclus
# ------------------------------------------------------------------


def test_excluded_dirs_not_walked(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / ".git" / "config").write_text("[core]", encoding="utf-8")
    (project / "node_modules").mkdir()
    (project / "node_modules" / "lodash").mkdir()
    (project / "src").mkdir()
    (project / "src" / "app.ts").write_text("export {};", encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    files = svc._walk_files(project)
    file_names = [f.name for f in files]
    assert "config" not in file_names  # .git/config excluded
    assert "app.ts" in file_names


def test_venv_excluded(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".venv").mkdir()
    (project / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin", encoding="utf-8")
    (project / "main.py").write_text("pass", encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    files = svc._walk_files(project)
    assert all(".venv" not in str(f) for f in files)


# ------------------------------------------------------------------
# Fichiers binaires
# ------------------------------------------------------------------


def test_binary_files_excluded(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    (project / "main.py").write_text("pass", encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    contents = svc._collect_file_contents(project)
    paths = [rel for rel, _ in contents]
    assert "image.png" not in paths
    assert "main.py" in paths


# ------------------------------------------------------------------
# Priorité des KEY_FILES
# ------------------------------------------------------------------


def test_key_files_appear_before_others(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "zzz_last.py").write_text("pass", encoding="utf-8")
    (project / "README.md").write_text("# README", encoding="utf-8")
    (project / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    contents = svc._collect_file_contents(project)
    paths = [rel for rel, _ in contents]
    readme_idx = paths.index("README.md")
    pkg_idx = paths.index("package.json")
    zzz_idx = paths.index("zzz_last.py")
    assert readme_idx < zzz_idx
    assert pkg_idx < zzz_idx


# ------------------------------------------------------------------
# Limite MAX_FILES
# ------------------------------------------------------------------


def test_max_files_limit(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    for i in range(100):
        (project / f"file_{i:03d}.py").write_text(f"# {i}", encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    contents = svc._collect_file_contents(project)
    assert len(contents) <= svc.MAX_FILES


# ------------------------------------------------------------------
# Troncature des fichiers
# ------------------------------------------------------------------


def test_file_truncated_at_max_bytes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "big.py").write_bytes(b"x" * 20_000)
    svc = _make_svc_no_client(tmp_path)
    content = svc._read_truncated(project / "big.py")
    assert content is not None
    assert len(content.encode("utf-8")) <= svc.MAX_FILE_BYTES


# ------------------------------------------------------------------
# Arbre de fichiers
# ------------------------------------------------------------------


def test_file_tree_excludes_git(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("pass", encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    tree = svc._build_file_tree(project)
    assert ".git" not in tree
    assert "src/" in tree


def test_file_tree_excludes_sensitive(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("SECRET=x", encoding="utf-8")
    (project / "main.py").write_text("pass", encoding="utf-8")
    svc = _make_svc_no_client(tmp_path)
    tree = svc._build_file_tree(project)
    assert ".env" not in tree
    assert "main.py" in tree


# ------------------------------------------------------------------
# Appel Anthropic
# ------------------------------------------------------------------


async def test_calls_anthropic_with_system_prompt(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    await svc.analyze(project)
    svc._client.messages.create.assert_called_once()
    kwargs = svc._client.messages.create.call_args.kwargs
    assert "Tu es un expert en analyse de projets." in kwargs["system"]


async def test_calls_anthropic_with_user_message(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    await svc.analyze(project)
    kwargs = svc._client.messages.create.call_args.kwargs
    assert kwargs["messages"][0]["role"] == "user"
    assert "Arbre de fichiers" in kwargs["messages"][0]["content"]


# ------------------------------------------------------------------
# Fallback sans fichier prompt
# ------------------------------------------------------------------


async def test_fallback_when_no_prompt_file(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    svc = ProjectAnalyzerService(client=_make_mock_client(_VALID_RESPONSE), prompts_dir=prompts_dir)
    result = await svc.analyze(project)
    assert result.detected_stack == ["Python", "FastAPI"]


# ------------------------------------------------------------------
# JSON invalide → ValueError
# ------------------------------------------------------------------


async def test_invalid_json_raises_value_error(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, "Désolé, je ne peux pas analyser ce projet.")
    with pytest.raises(ValueError, match="JSON valide"):
        await svc.analyze(project)


async def test_json_missing_claude_md_raises_value_error(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    bad_response = json.dumps({"detected_stack": ["Python"], "suggested_agents": []})
    svc = _make_service(tmp_path, bad_response)
    with pytest.raises(ValueError, match="JSON valide"):
        await svc.analyze(project)


# ------------------------------------------------------------------
# JSON dans un bloc markdown → extraction correcte
# ------------------------------------------------------------------


async def test_json_in_markdown_code_block(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    wrapped = f"Voici l'analyse :\n\n```json\n{_VALID_RESPONSE}\n```"
    svc = _make_service(tmp_path, wrapped)
    result = await svc.analyze(project)
    assert result.detected_stack == ["Python", "FastAPI"]


# ------------------------------------------------------------------
# Projets variés (critères d'acceptation du ticket)
# ------------------------------------------------------------------


async def test_python_project_writes_correct_stack(tmp_path: Path) -> None:
    project = _make_python_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_RESPONSE)
    result = await svc.analyze(project)
    assert "Python" in result.detected_stack


async def test_react_project_writes_correct_stack(tmp_path: Path) -> None:
    project = _make_react_project(tmp_path)
    svc = _make_service(tmp_path, _VALID_REACT_RESPONSE)
    result = await svc.analyze(project)
    assert "React" in result.detected_stack
