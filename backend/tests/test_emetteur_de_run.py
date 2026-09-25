"""L'emetteur partage par les trois modes de run — ticket-121, ticket-128.

Trois fonctions quasi identiques emettaient vers la socket : une seule
avalait les erreurs. Une socket morte en mode file ou autonome interrompait
donc le run avant son commit. Il n'en reste qu'une.

Depuis ticket-128 elle n'ecrit plus sur une socket mais publie sur
`EventHub` : le run ne connait plus ses observateurs. Les deux garanties de
ticket-079 restent les memes, et sont ce que ce fichier verrouille — une
panne d'ecriture n'interrompt pas le run, et un run sans ligne en base emet
quand meme.
"""
from pathlib import Path

import aiosqlite
import pytest

from tessera.config import settings
from tessera.services.database import create_run, init_db
from tessera.services.event_hub import EventHub
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_executor import emetteur
from tessera.services.run_registry import RunActif


def _event() -> OrchestratorEvent:
    return OrchestratorEvent(
        type=EventType.PIPELINE_DONE, ticket_id="ticket-001", data={"approved": True}
    )


def _run() -> RunActif:
    return RunActif(run_id="run-1", project_id="p", ticket_id="ticket-001")


async def _evenements_persistes(db_path: Path, run_id: str) -> int:
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM agent_events WHERE run_id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def test_l_evenement_est_publie_et_persiste(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le run continue cote serveur quand l'onglet se ferme, et l'historique
    # doit garder ses evenements : sinon rien ne dit ce qui s'est passe.
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    run_id = await create_run(db_path, "p", "ticket-001")

    hub = EventHub()
    abonne = hub.subscribe()
    await emetteur(hub, _run(), run_id)(_event())

    assert len(abonne.vider()) == 1
    assert await _evenements_persistes(db_path, run_id) == 1


async def test_une_panne_de_persistance_n_interrompt_pas_le_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La garantie de ticket-079, prise par l'autre bout : faire remonter
    # l'erreur tuerait le run avant son commit, ce qu'ADR-018 interdit.
    monkeypatch.setattr(settings, "ide_db_path", tmp_path / "inexistant" / "x.db")

    hub = EventHub()
    abonne = hub.subscribe()
    await emetteur(hub, _run(), "run-inconnu")(_event())

    assert len(abonne.vider()) == 1


async def test_sans_ligne_en_base_rien_n_est_persiste_mais_le_hub_recoit(
    tmp_path: Path,
) -> None:
    # Un run dont la ligne n'a pas pu s'ouvrir emet quand meme : perdre
    # l'affichage en plus de l'historique serait payer deux fois.
    hub = EventHub()
    abonne = hub.subscribe()

    await emetteur(hub, _run(), None)(_event())

    recus = abonne.vider()
    assert len(recus) == 1
    assert recus[0].type is EventType.PIPELINE_DONE


async def test_l_evenement_porte_son_run_et_son_projet() -> None:
    # Le canal porte tous les runs a la fois : sans ces deux champs, un
    # client ne saurait pas a quelle carte rattacher ce qu'il recoit.
    hub = EventHub()
    abonne = hub.subscribe()

    await emetteur(hub, _run(), None)(_event())

    recu = abonne.vider()[0]
    assert recu.run_id == "run-1"
    assert recu.project_id == "p"
