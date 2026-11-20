"""Les noms protégés se comparent après normalisation Windows — ticket-747.

Windows ouvre le même fichier sous `settings.json`, `Settings.JSON`,
`settings.json.`, `settings.json ` et `settings.json::$DATA`. Les cibles de ces
tests n'existent pas : `resolve()` ne normalise alors rien, et c'est le garde
qui doit le faire.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.noyau.database import init_db
from tessera.services.providers.chemins_proteges import motif_de_protection
from tessera.utils.noms_windows import normaliser_segment

VARIANTES_REFUSEES = [
    ".claude/settings.json.",
    ".claude/settings.json::$DATA",
    ".claude/settings.local.json ",
    ".Claude/Settings.json",
    "sub/CLAUDE.md.",
    "sub/claude.MD",
    "CLAUDE.local.md::$DATA",
    ".GitHub/Workflows/x.yml",
    ".GIT/hooks/pre-commit",
    "agents.json.",
]

VARIANTES_DES_REGLAGES = [
    ".claude/settings.json.",
    ".claude/settings.json::$DATA",
    ".claude/settings.local.json ",
    ".Claude/Settings.json",
]


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [
        ("settings.json", "settings.json"),
        ("Settings.JSON", "settings.json"),
        ("settings.json.", "settings.json"),
        ("settings.json ", "settings.json"),
        ("settings.json. .", "settings.json"),
        ("settings.json::$DATA", "settings.json"),
        (".claude", ".claude"),
    ],
)
def test_normaliser_segment_returns_the_win32_form(brut: str, attendu: str) -> None:
    assert normaliser_segment(brut) == attendu


@pytest.mark.parametrize("relatif", VARIANTES_REFUSEES)
def test_motif_de_protection_refuses_win32_spellings_of_absent_files(
    tmp_path: Path, relatif: str
) -> None:
    projet = tmp_path / "projects" / "client"
    projet.mkdir(parents=True)

    assert motif_de_protection(relatif, projet, projet) is not None, relatif
    assert motif_de_protection(str(projet / relatif), projet, projet) is not None, relatif


@pytest.mark.parametrize(
    "relatif",
    [
        "settings.md",
        "notes/claude-notes.md",
        "docs/CLAUDE-notes.md",
        "config/settings.json",
        ".github/CODEOWNERS",
        "tests/fixtures/agents.json.",
    ],
)
def test_motif_de_protection_lets_legitimate_neighbours_pass(
    tmp_path: Path, relatif: str
) -> None:
    projet = tmp_path / "projects" / "client"
    projet.mkdir(parents=True)

    assert motif_de_protection(relatif, projet, projet) is None, relatif


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    (ws / "mon-projet").mkdir(parents=True)
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    return ws


@pytest.mark.parametrize("relatif", VARIANTES_DES_REGLAGES)
def test_fs_write_refuses_win32_spellings_of_cli_settings(
    workspace: Path, relatif: str
) -> None:
    cible = workspace / "mon-projet" / relatif

    resp = TestClient(app).put("/api/v1/fs/write", json={"path": str(cible), "content": "{}"})

    # 403 normalement ; 400 si l'OS refuse de lire le nom : jamais 204.
    assert resp.status_code in (400, 403), relatif
    assert not (workspace / "mon-projet" / ".claude").exists() or not any(
        (workspace / "mon-projet" / ".claude").iterdir()
    )


def test_fs_write_still_accepts_settings_md(workspace: Path) -> None:
    cible = workspace / "mon-projet" / "notes" / "settings.md"

    resp = TestClient(app).put("/api/v1/fs/write", json={"path": str(cible), "content": "x"})

    assert resp.status_code == 204
