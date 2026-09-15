"""Endpoints filesystem — ticket-058.

Le confinement au workspace **est** la fonctionnalité : sans lui, l'endpoint
lit et écrit n'importe quel fichier de la machine.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vibe_ide.config import settings
from vibe_ide.main import app
from vibe_ide.services.database import init_db


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "tickets" / "todo").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    (project / "tickets" / "todo" / "ticket-001.md").write_text(
        "# ticket-001 — Un ticket\n\nContenu du ticket.\n", encoding="utf-8"
    )

    # Un secret hors workspace : c'est ce qu'un endpoint non confiné lirait.
    (tmp_path / "secret.txt").write_text("clef-privee", encoding="utf-8")

    db_path = tmp_path / "vibe.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    return ws


def _client() -> TestClient:
    return TestClient(app)


# ------------------------------------------------------------------
# Lecture
# ------------------------------------------------------------------


def test_lit_un_fichier_du_workspace(workspace: Path) -> None:
    target = workspace / "mon-projet" / "tickets" / "todo" / "ticket-001.md"

    resp = _client().get("/api/v1/fs/read", params={"path": str(target)})

    assert resp.status_code == 200
    assert "Contenu du ticket" in resp.text


def test_lecture_hors_workspace_est_refusee(workspace: Path, tmp_path: Path) -> None:
    # Le scénario que le confinement existe pour empêcher.
    resp = _client().get("/api/v1/fs/read", params={"path": str(tmp_path / "secret.txt")})

    assert resp.status_code == 403
    assert "clef-privee" not in resp.text


def test_traversee_par_points_est_refusee(workspace: Path) -> None:
    traversal = workspace / "mon-projet" / ".." / ".." / "secret.txt"

    resp = _client().get("/api/v1/fs/read", params={"path": str(traversal)})

    assert resp.status_code == 403


def test_fichier_absent_renvoie_404(workspace: Path) -> None:
    resp = _client().get(
        "/api/v1/fs/read", params={"path": str(workspace / "mon-projet" / "jamais.md")}
    )
    assert resp.status_code == 404


def test_un_dossier_n_est_pas_lisible_comme_un_fichier(workspace: Path) -> None:
    resp = _client().get("/api/v1/fs/read", params={"path": str(workspace / "mon-projet")})
    assert resp.status_code == 400


def test_un_fichier_trop_volumineux_est_refuse(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Mieux vaut refuser que saturer la mémoire du backend.
    from vibe_ide.routers import fs as fs_router

    monkeypatch.setattr(fs_router, "_MAX_READ_BYTES", 10)
    big = workspace / "mon-projet" / "gros.md"
    big.write_text("x" * 100, encoding="utf-8")

    resp = _client().get("/api/v1/fs/read", params={"path": str(big)})

    assert resp.status_code == 413


# ------------------------------------------------------------------
# Écriture
# ------------------------------------------------------------------


def test_ecrit_un_fichier_du_workspace(workspace: Path) -> None:
    target = workspace / "mon-projet" / "tickets" / "todo" / "ticket-001.md"

    resp = _client().put(
        "/api/v1/fs/write",
        json={"path": str(target), "content": "# Modifié\n"},
    )

    assert resp.status_code == 204
    assert target.read_text(encoding="utf-8") == "# Modifié\n"


def test_ecriture_hors_workspace_est_refusee(workspace: Path, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"

    resp = _client().put(
        "/api/v1/fs/write", json={"path": str(secret), "content": "compromis"}
    )

    assert resp.status_code == 403
    assert secret.read_text(encoding="utf-8") == "clef-privee"


# ------------------------------------------------------------------
# Listing
# ------------------------------------------------------------------


def test_liste_un_dossier_du_workspace(workspace: Path) -> None:
    resp = _client().get(
        "/api/v1/fs/list", params={"path": str(workspace / "mon-projet" / "tickets" / "todo")}
    )

    assert resp.status_code == 200
    names = [e["name"] for e in resp.json()]
    assert "ticket-001.md" in names


def test_listing_hors_workspace_est_refuse(workspace: Path, tmp_path: Path) -> None:
    resp = _client().get("/api/v1/fs/list", params={"path": str(tmp_path)})
    assert resp.status_code == 403


# ------------------------------------------------------------------
# Projets importés en symlink
# ------------------------------------------------------------------


def test_un_projet_lie_en_symlink_reste_lisible(
    workspace: Path, tmp_path: Path
) -> None:
    # Un import en mode `symlink` pointe hors du workspace par construction :
    # la racine autorisée est la cible résolue du projet, pas le workspace brut.
    source = tmp_path / "source-projet"
    (source / "tickets" / "todo").mkdir(parents=True)
    (source / "tickets" / "todo" / "ticket-009.md").write_text("# lié\n", encoding="utf-8")

    link = workspace / "projet-lie"
    try:
        link.symlink_to(source, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks indisponibles sur cette machine")

    resp = _client().get(
        "/api/v1/fs/read", params={"path": str(link / "tickets" / "todo" / "ticket-009.md")}
    )

    assert resp.status_code == 200
    assert "lié" in resp.text


def test_un_lien_pose_dans_le_workspace_ne_donne_pas_acces_a_l_exterieur(
    workspace: Path, tmp_path: Path
) -> None:
    # Le contrôle doit porter sur le chemin RÉSOLU : sinon un lien déposé dans
    # le workspace contourne tout le confinement.
    evil = workspace / "mon-projet" / "echappatoire"
    try:
        evil.symlink_to(tmp_path / "secret.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks indisponibles sur cette machine")

    resp = _client().get("/api/v1/fs/read", params={"path": str(evil)})

    assert resp.status_code == 403
    assert "clef-privee" not in resp.text
