"""Un depot sans CI peut merger sur le verdict du pipeline — ticket-176.

Les pull requests servent l'historique et l'execution des tests, pas a faire
cliquer. Sur un depot sans CI, la relecture humaine au merge n'ajoute aucune
verification et coute un aller-retour par ticket.
"""

import json
from pathlib import Path

from tessera.services.autonomie import NiveauAutonomie, niveau_peut_merger
from tessera.services.politique_run import PolitiqueRun


def _manifeste(racine: Path, **champs: object) -> Path:
    (racine / "agents.json").write_text(json.dumps(champs), encoding="utf-8")
    return racine


# --- La declaration ---------------------------------------------------------


def test_la_politique_lit_la_declaration(tmp_path: Path) -> None:
    _manifeste(tmp_path, merge_without_ci=True)

    assert PolitiqueRun.lire(tmp_path).merge_without_ci is True


def test_sans_declaration_le_defaut_protege(tmp_path: Path) -> None:
    _manifeste(tmp_path, autonomy="merge")

    assert PolitiqueRun.lire(tmp_path).merge_without_ci is False


def test_une_valeur_qui_n_est_pas_un_booleen_ne_desarme_rien(tmp_path: Path) -> None:
    _manifeste(tmp_path, merge_without_ci="oui")

    assert PolitiqueRun.lire(tmp_path).merge_without_ci is False


def test_un_manifeste_illisible_ne_desarme_rien(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text("{ pas du json", encoding="utf-8")

    assert PolitiqueRun.lire(tmp_path).merge_without_ci is False


# --- La regle ---------------------------------------------------------------


def test_sans_ci_observable_la_declaration_ouvre_le_merge() -> None:
    assert niveau_peut_merger(NiveauAutonomie.merge, "none", sans_ci=True) is True


def test_une_ci_rouge_refuse_malgre_la_declaration() -> None:
    """« Ce depot n'a pas de CI » ne veut pas dire « ignore la CI »."""
    assert niveau_peut_merger(NiveauAutonomie.merge, "failing", sans_ci=True) is False


def test_une_ci_en_attente_refuse_malgre_la_declaration() -> None:
    """Merger pendant qu'elle tourne serait merger sans son verdict."""
    assert niveau_peut_merger(NiveauAutonomie.merge, "pending", sans_ci=True) is False


def test_une_ci_verte_merge_avec_ou_sans_declaration() -> None:
    assert niveau_peut_merger(NiveauAutonomie.merge, "passing", sans_ci=True) is True
    assert niveau_peut_merger(NiveauAutonomie.merge, "passing") is True


def test_sans_declaration_l_absence_de_ci_refuse_toujours() -> None:
    """Le comportement d'avant ce ticket, inchange."""
    assert niveau_peut_merger(NiveauAutonomie.merge, "none") is False


def test_la_declaration_n_eleve_aucun_niveau() -> None:
    """Elle lève une condition du merge, elle n'autorise pas à merger."""
    assert niveau_peut_merger(NiveauAutonomie.pr, "none", sans_ci=True) is False
    assert niveau_peut_merger(NiveauAutonomie.commit, "none", sans_ci=True) is False
