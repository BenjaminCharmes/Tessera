"""`preuve_reelle` is read before any agent runs, never after — ticket-964."""
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from tessera.models.ticket import TicketStatus
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.livraison.preuve_sur_la_base import preuve_reelle_sur_la_base
from tessera.services.livraison.reprise_surveillance import reprendre_surveillances
from tessera.services.noyau.pipeline_events import OrchestratorEvent, PipelineResult
from tessera.services.pipeline import pipeline_livraison
from tessera.services.pipeline.pipeline_approbation import ARRET_PREUVE_REELLE
from tests.test_reprise_preuve_reelle import BASE, Espion, _base, _ecrire_fiche, _sans_evenement


class _FicheReecrite:
    """Ticket service whose file, read after the run, says the opposite."""

    def __init__(self, apres: bool) -> None:
        self._ticket = SimpleNamespace(preuve_reelle=apres)

    async def get_ticket(self, ticket_id: str) -> Any:
        return self._ticket


async def _livrer(figee: bool, relue: bool, monkeypatch: Any) -> tuple[PipelineResult, list[int]]:
    surveilles: list[int] = []

    async def livrer(resultat: PipelineResult) -> Livraison:
        return Livraison(pr_number=7)

    async def surveiller(projet: str, ticket: str, pr: int, on_event: Any) -> None:
        surveilles.append(pr)

    async def finaliser(orch: Any, livraison: Livraison) -> None:
        return None

    async def on_event(event: OrchestratorEvent) -> None:
        return None

    monkeypatch.setattr(pipeline_livraison.fin_de_file, "finaliser_livraison", finaliser)
    orch = SimpleNamespace(
        _livrer=livrer, _surveiller=surveiller, _ticket_svc=_FicheReecrite(relue),
        _preuves_reelles={"ticket-001": figee}, _log=lambda ligne: None,
    )
    resultat = PipelineResult(
        ticket_id="ticket-001", final_status=TicketStatus.done, rounds=1, approved=True
    )
    rendu = await pipeline_livraison.livrer_le_resultat(orch, resultat, "p", on_event)  # type: ignore[arg-type]
    return rendu, surveilles


async def test_coder_dropping_the_flag_does_not_release_the_pr(monkeypatch: Any) -> None:
    rendu, surveilles = await _livrer(figee=True, relue=False, monkeypatch=monkeypatch)
    assert rendu.livraison is not None
    assert rendu.livraison.arret == ARRET_PREUVE_REELLE
    assert surveilles == []


async def test_coder_adding_the_flag_keeps_the_usual_delivery(monkeypatch: Any) -> None:
    rendu, surveilles = await _livrer(figee=False, relue=True, monkeypatch=monkeypatch)
    assert rendu.livraison is not None
    assert rendu.livraison.arret is None
    assert surveilles == [7]


def _git(depot: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=testeur", *args],
        cwd=depot, check=True, capture_output=True,
    )


def _fiche_sur_la_base(projet: Path, preuve: bool) -> None:
    _git(projet, "init", "-q")
    _ecrire_fiche(projet, "todo", "ticket-901", None, preuve=preuve)
    _git(projet, "add", "tickets")
    _git(projet, "commit", "-q", "-m", "chore: ticket")
    _git(projet, "update-ref", f"refs/remotes/origin/{BASE}", "HEAD")


async def test_flag_is_read_on_the_base(tmp_path: Path) -> None:
    projet = tmp_path / "depot"
    projet.mkdir()
    _fiche_sur_la_base(projet, True)
    assert await preuve_reelle_sur_la_base(projet, "ticket-901", BASE) is True
    assert await preuve_reelle_sur_la_base(projet, "ticket-902", BASE) is None
    assert await preuve_reelle_sur_la_base(projet, "ticket-901", None) is None


async def test_restart_does_not_resume_a_pr_whose_base_ticket_asks_for_proof(
    tmp_path: Path,
) -> None:
    workspace, projet, db = await _base(tmp_path, "ticket-901")
    _fiche_sur_la_base(projet, True)
    # Le dossier du run a perdu le drapeau : la base fait foi.
    _ecrire_fiche(projet, "in-review", "ticket-901", 7, preuve=False)
    espion = Espion([])

    await reprendre_surveillances(workspace, db, espion.fabrique, _sans_evenement)

    assert espion.surveillees == []
