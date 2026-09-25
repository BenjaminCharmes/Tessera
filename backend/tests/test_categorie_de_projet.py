"""Un projet declare sa categorie — ticket-175.

Neuf projets dans une liste plate : des depots clients, des projets
personnels, le bootstrap, un banc d'essai. Se tromper de depot au moment de
lancer un pipeline est le risque qu'ADR-031 borne cote ecriture, pris par
l'autre bout.
"""

import json
from pathlib import Path

from tessera.services.project_loader import load_project


def _projet(racine: Path, nom: str, **manifeste: object) -> Path:
    p = racine / nom
    p.mkdir(parents=True)
    (p / "CLAUDE.md").write_text(f"# {nom}\n", encoding="utf-8")
    if manifeste:
        (p / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return p


def test_la_categorie_declaree_est_lue(tmp_path: Path) -> None:
    p = _projet(tmp_path, "un-client", category="Pro")

    assert load_project(p).category == "Pro"


def test_sans_manifeste_le_projet_n_a_pas_de_categorie(tmp_path: Path) -> None:
    """Le defaut ne cache jamais : il range ailleurs."""
    p = _projet(tmp_path, "sans-rien")

    assert load_project(p).category is None


def test_un_manifeste_muet_laisse_le_projet_sans_categorie(tmp_path: Path) -> None:
    p = _projet(tmp_path, "muet", autonomy="pr")

    assert load_project(p).category is None


def test_un_manifeste_illisible_ne_fait_pas_echouer_le_chargement(tmp_path: Path) -> None:
    p = _projet(tmp_path, "casse")
    (p / "agents.json").write_text("{ pas du json", encoding="utf-8")

    assert load_project(p).category is None


def test_une_valeur_qui_n_est_pas_une_chaine_est_ignoree(tmp_path: Path) -> None:
    p = _projet(tmp_path, "mal-type", category=42)

    assert load_project(p).category is None


def test_une_categorie_vide_vaut_pas_de_categorie(tmp_path: Path) -> None:
    """Sinon un groupe sans nom apparaitrait a l'ecran."""
    p = _projet(tmp_path, "vide", category="   ")

    assert load_project(p).category is None
