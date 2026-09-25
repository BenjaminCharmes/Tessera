"""Le projet bootstrap ne peut pas se lancer lui-même — ticket-152.

`ide-core` affichait « Lancer », et cliquer démarrait un **second** backend —
qui meurt aussitôt, le port étant pris — et un second frontend. Le cas où ce
bouton servirait n'existe pas : il faut que l'IDE tourne pour qu'on voie
l'écran.

C'est ADR-001 qui se mord la queue : le projet bootstrap construit l'IDE, et
l'IDE voudrait le lancer alors qu'il l'exécute déjà.
"""
from pathlib import Path

import pytest

from tessera.services.project_loader import fait_tourner_l_ide


def _projet(racine: Path, git_root: str | None = None) -> Path:
    racine.mkdir(parents=True, exist_ok=True)
    (racine / "CLAUDE.md").write_text("# p\n", encoding="utf-8")
    if git_root is not None:
        import json

        (racine / "agents.json").write_text(
            json.dumps({"git_root": git_root}), encoding="utf-8"
        )
    return racine


def test_le_projet_bootstrap_est_reconnu(tmp_path: Path) -> None:
    # Sa racine autorisée est celle du dépôt qui porte le backend : c'est ce
    # qui le distingue, et non son nom — un projet peut s'appeler autrement.
    depot = tmp_path / "tessera"
    (depot / ".git").mkdir(parents=True)
    projet = _projet(depot / "projects" / "ide-core", git_root="ancestor")

    assert fait_tourner_l_ide(projet, racine_de_l_ide=depot) is True


def test_un_projet_ordinaire_ne_l_est_pas(tmp_path: Path) -> None:
    depot = tmp_path / "tessera"
    (depot / ".git").mkdir(parents=True)
    projet = _projet(depot / "projects" / "client")

    assert fait_tourner_l_ide(projet, racine_de_l_ide=depot) is False


def test_un_ancestor_dans_un_autre_depot_ne_l_est_pas(tmp_path: Path) -> None:
    # `git_root: ancestor` élargit le périmètre au dépôt **qui contient le
    # projet**, pas à celui de l'IDE : un projet client ne doit pas être pris
    # pour le bootstrap parce qu'il déclare la même clef (ADR-028).
    ailleurs = tmp_path / "ailleurs"
    (ailleurs / ".git").mkdir(parents=True)
    projet = _projet(ailleurs / "sous" / "projet", git_root="ancestor")

    assert (
        fait_tourner_l_ide(projet, racine_de_l_ide=tmp_path / "tessera") is False
    )


def test_le_projet_reel_ide_core_est_reconnu() -> None:
    # Le cas concret, sur ce dépôt-ci : c'est lui qui a motivé le ticket.
    racine = Path(__file__).resolve().parents[2]
    ide_core = racine / "projects" / "ide-core"
    if not ide_core.is_dir():
        pytest.skip("ide-core absent de ce clone")

    assert fait_tourner_l_ide(ide_core, racine_de_l_ide=racine) is True
