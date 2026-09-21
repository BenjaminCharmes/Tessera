"""Jusqu'ou un agent va seul, projet par projet — ticket-082."""
import json
from pathlib import Path

import pytest

from tessera.services.autonomie import (
    NiveauAutonomie,
    lire_niveau,
    peut_merger,
    peut_pousser,
)


_compteur = 0


def _projet(tmp_path: Path, **agents_json: object) -> Path:
    # Un dossier par appel : plusieurs projets coexistent dans un meme test.
    global _compteur
    _compteur += 1
    p = tmp_path / f"projet-{_compteur}"
    p.mkdir()
    if agents_json:
        (p / "agents.json").write_text(json.dumps(agents_json), encoding="utf-8")
    return p


def test_par_defaut_un_projet_s_arrete_au_commit(tmp_path: Path) -> None:
    # Le défaut protège : sur un dépôt client, pousser est une décision.
    assert lire_niveau(_projet(tmp_path)) is NiveauAutonomie.commit


def test_un_agents_json_sans_la_cle_reste_au_commit(tmp_path: Path) -> None:
    assert lire_niveau(_projet(tmp_path, project_id="x")) is NiveauAutonomie.commit


def test_une_valeur_inconnue_ne_desarme_rien(tmp_path: Path) -> None:
    # Fail-closed, comme le mode des artefacts et la racine git.
    projet = _projet(tmp_path, autonomy="tout-est-permis")
    assert lire_niveau(projet) is NiveauAutonomie.commit


@pytest.mark.parametrize(
    "declare,attendu",
    [
        ("commit", NiveauAutonomie.commit),
        ("pr", NiveauAutonomie.pr),
        ("merge", NiveauAutonomie.merge),
    ],
)
def test_le_niveau_se_declare(tmp_path: Path, declare: str, attendu) -> None:
    assert lire_niveau(_projet(tmp_path, autonomy=declare)) is attendu


def test_pousser_demande_au_moins_le_niveau_pr(tmp_path: Path) -> None:
    assert peut_pousser(_projet(tmp_path, autonomy="commit")) is False
    assert peut_pousser(_projet(tmp_path, autonomy="pr")) is True
    assert peut_pousser(_projet(tmp_path, autonomy="merge")) is True


def test_merger_demande_le_niveau_merge_ET_une_ci_verte(tmp_path: Path) -> None:
    # ADR-022 ne tombe pas : elle devient conditionnelle. Le merge exige une
    # déclaration **et** le seul signal objectif dont dispose l'IDE.
    merge = _projet(tmp_path, autonomy="merge")

    assert peut_merger(merge, ci_status="passing") is True
    assert peut_merger(merge, ci_status="failing") is False
    assert peut_merger(merge, ci_status="pending") is False
    assert peut_merger(merge, ci_status="none") is False


def test_un_projet_en_pr_ne_merge_jamais(tmp_path: Path) -> None:
    assert peut_merger(_projet(tmp_path, autonomy="pr"), ci_status="passing") is False
