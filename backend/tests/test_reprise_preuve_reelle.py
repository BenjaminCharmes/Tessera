"""A PR waiting for a real proof is never resumed by the watcher at startup — ticket-949."""
import json
from pathlib import Path

from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.github.github_service import PrOuverte
from tessera.services.livraison.reprise_surveillance import SurveillanceProjet, reprendre_surveillances
from tessera.services.livraison.sha_approbation import noter_poussee
from tessera.services.noyau.database import init_db
from tessera.services.noyau.database_runs import create_run
from tessera.services.noyau.pipeline_events import OrchestratorEvent

PROJET = "demo"
BASE = "develop"


async def _sans_evenement(event: OrchestratorEvent) -> None:
    """Event callback that drops everything."""


class Espion:
    """Fake GitHub side: every PR open, the listed ones open on GitHub too."""

    def __init__(self, ouvertes: list[PrOuverte]) -> None:
        self.ouvertes = ouvertes
        self.surveillees: list[tuple[str, str, int]] = []

    def fabrique(self, project_id: str, politique: PolitiqueRun) -> SurveillanceProjet:
        async def etat_pr(pr: int) -> str:
            return "open"

        async def surveiller(p_id: str, t_id: str, pr: int, _on_event: object) -> None:
            self.surveillees.append((p_id, t_id, pr))

        async def prs_ouvertes() -> list[PrOuverte]:
            return self.ouvertes

        return SurveillanceProjet(
            etat_pr=etat_pr, surveiller=surveiller, prs_ouvertes=prs_ouvertes, base_branch=BASE
        )


async def _base(tmp_path: Path, ticket_id: str) -> tuple[Path, Path, Path]:
    workspace = tmp_path / "ws"
    projet = workspace / PROJET
    projet.mkdir(parents=True)
    (projet / "agents.json").write_text(json.dumps({"autonomy": "merge"}), encoding="utf-8")
    db = tmp_path / "ide.db"
    await init_db(db)
    run_id = await create_run(db, PROJET, ticket_id)
    await noter_poussee(db, run_id, "a" * 40)
    return workspace, projet, db


def _ecrire_fiche(projet: Path, dossier: str, ticket_id: str, pr: int | None, preuve: bool) -> None:
    cible = projet / "tickets" / dossier
    cible.mkdir(parents=True, exist_ok=True)
    lignes = [
        "---",
        f"id: {ticket_id}",
        "title: Un ticket",
        "type: fix",
        f"status: {dossier}",
        "priority: medium",
        "agent: codeur",
    ]
    if pr is not None:
        lignes.append(f"pr_number: {pr}")
    if preuve:
        lignes.append("preuve_reelle: true")
    texte = "\n".join(lignes) + "\n---\n\nCorps.\n"
    (cible / f"{ticket_id}-sujet.md").write_text(texte, encoding="utf-8")


def _log(projet: Path) -> str:
    chemin = projet / "memory" / "pipeline-log.md"
    return chemin.read_text(encoding="utf-8") if chemin.exists() else ""


async def test_in_review_ticket_with_real_proof_is_not_resumed(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path, "ticket-901")
    _ecrire_fiche(projet, "in-review", "ticket-901", 7, preuve=True)
    espion = Espion([])

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == []
    assert "ticket-901 PR #7 non reprise : merge après preuve réelle" in _log(projet)


async def test_github_pr_of_a_real_proof_ticket_is_not_resumed(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path, "ticket-034")
    _ecrire_fiche(projet, "in-progress", "ticket-034", None, preuve=True)
    espion = Espion([PrOuverte(41, "ticket-034-une-feature", BASE)])

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == []
    assert "ticket-034 PR #41 non reprise : merge après preuve réelle" in _log(projet)


async def test_ticket_without_real_proof_is_still_resumed(tmp_path: Path) -> None:
    workspace, projet, db = await _base(tmp_path, "ticket-901")
    _ecrire_fiche(projet, "in-review", "ticket-901", 7, preuve=False)
    espion = Espion([])

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == [(PROJET, "ticket-901", 7)]
