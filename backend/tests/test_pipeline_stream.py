"""L'emetteur WebSocket partage par les trois modes de run — ticket-121.

Trois fonctions quasi identiques emettaient vers la socket : une seule
avalait les erreurs. Une socket morte en mode file ou autonome interrompait
donc le run avant son commit. Il n'en reste qu'une.
"""
from pathlib import Path

import aiosqlite
import pytest

from tessera.config import settings
from tessera.routers.pipeline_stream import emetteur
from tessera.services.database import create_run, init_db
from tessera.services.pipeline_events import EventType, OrchestratorEvent


class _SocketMorte:
    async def send_text(self, data: str) -> None:
        raise RuntimeError("WebSocket is not connected")


class _SocketVivante:
    def __init__(self) -> None:
        self.envoyes: list[str] = []

    async def send_text(self, data: str) -> None:
        self.envoyes.append(data)


def _event() -> OrchestratorEvent:
    return OrchestratorEvent(
        type=EventType.PIPELINE_DONE, ticket_id="ticket-001", data={"approved": True}
    )


async def _evenements_persistes(db_path: Path, run_id: str) -> int:
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM agent_events WHERE run_id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def test_une_socket_morte_ne_leve_pas_et_l_evenement_est_persiste(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le run continue cote serveur quand l'onglet se ferme, et l'historique
    # doit garder ses evenements : sinon rien ne dit ce qui s'est passe.
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    run_id = await create_run(db_path, "p", "ticket-001")

    await emetteur(_SocketMorte(), run_id=run_id)(_event())  # type: ignore[arg-type]

    assert await _evenements_persistes(db_path, run_id) == 1


async def test_sans_run_id_rien_n_est_persiste_mais_la_socket_recoit(
    tmp_path: Path,
) -> None:
    # Les modes file et autonome n'ont pas de `run_id` cote socket : ils
    # emettent, sans ecrire une ligne orpheline en base.
    socket = _SocketVivante()

    await emetteur(socket, run_id=None)(_event())  # type: ignore[arg-type]

    assert len(socket.envoyes) == 1
    assert '"pipeline_done"' in socket.envoyes[0]
