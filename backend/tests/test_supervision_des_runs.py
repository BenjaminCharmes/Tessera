"""Registry of live runs and event hub — ticket-127.

Ce qui justifie ces deux objets : `pipeline_stream.emetteur()` écrit sur
**une** socket et sur elle seule, si bien qu'un run n'est observable que par
le client qui l'a lancé. Le hub rend la diffusion multiple ; le registre dit
ce qui tourne. ticket-128 les branche sur le pipeline.
"""
import asyncio

import pytest

from tessera.services.event_hub import EventHub
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_lock import RunAlreadyInProgress, RunLock
from tessera.services.run_registry import RunRegistry


def _token(texte: str = "x") -> OrchestratorEvent:
    return OrchestratorEvent(
        type=EventType.AGENT_TOKEN, ticket_id="ticket-001", data={"text": texte}
    )


def _transition() -> OrchestratorEvent:
    return OrchestratorEvent(
        type=EventType.PIPELINE_DONE, ticket_id="ticket-001", data={}
    )


# --------------------------------------------------------------------------
# EventHub
# --------------------------------------------------------------------------


async def test_le_hub_diffuse_a_tous_les_abonnes() -> None:
    """Every subscriber receives a published event."""
    # Le cœur du ticket : l'émetteur actuel n'a qu'un destinataire. Sans
    # diffusion multiple, ouvrir un second onglet fait disparaître le premier.
    hub = EventHub()
    abonnes = [hub.subscribe() for _ in range(3)]

    await hub.publish(_transition())

    for abonne in abonnes:
        recu = await asyncio.wait_for(abonne.recevoir(), timeout=1)
        assert recu.type is EventType.PIPELINE_DONE


async def test_une_file_pleine_perd_un_token_et_garde_la_transition() -> None:
    """A full queue drops tokens, never transitions."""
    # La règle qui rend le canal sûr. Perdre du texte dégrade l'affichage ;
    # perdre un verdict, un commit ou un changement de statut le rend faux.
    hub = EventHub()
    abonne = hub.subscribe(taille=2)

    await hub.publish(_token("a"))
    await hub.publish(_token("b"))
    await hub.publish(_transition())

    recus = abonne.vider()
    types = [event.type for event in recus]
    assert EventType.PIPELINE_DONE in types
    assert types.count(EventType.AGENT_TOKEN) < 2
    assert abonne.perdus == 1


async def test_un_abonne_sature_ne_bloque_pas_la_publication() -> None:
    """Publishing stays fast when a subscriber never reads."""
    # Un client lent ne doit pas ralentir un run : le pipeline publie depuis
    # la boucle qui fait tourner les agents.
    hub = EventHub()
    hub.subscribe(taille=2)

    async def publier_beaucoup() -> None:
        for i in range(200):
            await hub.publish(_token(str(i)))

    await asyncio.wait_for(publier_beaucoup(), timeout=2)


async def test_un_abonne_ferme_ne_recoit_plus_rien() -> None:
    """Closing a subscription removes it from the hub."""
    # Sans retrait, chaque onglet fermé laisserait une file qui grossit
    # jusqu'à l'arrêt du backend.
    hub = EventHub()
    abonne = hub.subscribe()
    abonne.fermer()

    await hub.publish(_transition())

    assert abonne.vider() == []
    assert hub.nombre_d_abonnes == 0


# --------------------------------------------------------------------------
# RunRegistry
# --------------------------------------------------------------------------


async def test_l_instantane_contient_les_runs_de_deux_projets() -> None:
    """Two projects running at once both appear in the snapshot."""
    # ADR-038 autorise un run par projet et N projets en parallèle : c'est
    # exactement le parallélisme que l'UI ne montrait pas.
    registre = RunRegistry()
    async with registre.acquire("projet-a", "ticket-001"):
        async with registre.acquire("projet-b", "ticket-002"):
            instantane = registre.instantane()

    projets = {run["project_id"] for run in instantane}
    assert projets == {"projet-a", "projet-b"}


async def test_le_registre_met_a_jour_l_etape_courante() -> None:
    """The current stage of a run is readable while it runs."""
    # C'est ce que la vue de supervision affiche : sans étape courante, une
    # carte de run ne dit que « ça tourne ».
    registre = RunRegistry()
    async with registre.acquire("projet-a", "ticket-001") as run:
        registre.mettre_a_jour(run.run_id, etape="revue", agent="reviewer")
        instantane = registre.instantane()

    assert instantane[0]["etape"] == "revue"
    assert instantane[0]["agent"] == "reviewer"


async def test_un_run_termine_sort_de_l_instantane() -> None:
    """A finished run leaves the registry."""
    # Le registre décrit le présent. Un run qui y reste après sa fin ferait
    # croire à une activité, et bloquerait le projet côté verrou.
    registre = RunRegistry()
    async with registre.acquire("projet-a", "ticket-001"):
        pass

    assert registre.instantane() == []


async def test_un_run_qui_echoue_libere_le_projet() -> None:
    """An exception inside the run still frees the project."""
    # Reprend la garantie du `finally` de RunLock : un pipeline qui échoue
    # laissait sinon le projet verrouillé jusqu'au redémarrage du backend.
    registre = RunRegistry()
    with pytest.raises(ValueError):
        async with registre.acquire("projet-a", "ticket-001"):
            raise ValueError("panne de production")

    assert registre.projet_occupe("projet-a") is False


# --------------------------------------------------------------------------
# RunLock délègue, sans changer de comportement
# --------------------------------------------------------------------------


async def test_le_verrou_repond_comme_avant_la_delegation() -> None:
    """RunLock keeps is_running and ticket_en_cours intact."""
    # Tous les points d'entrée appellent ces deux méthodes (ADR-038) : une
    # régression ici sérialise ou désérialise les runs sans rien signaler.
    registre = RunRegistry()
    verrou = RunLock(registre)

    assert verrou.is_running("projet-a") is False
    async with verrou.acquire("projet-a", "ticket-001"):
        assert verrou.is_running("projet-a") is True
        assert verrou.ticket_en_cours("projet-a") == "ticket-001"
    assert verrou.is_running("projet-a") is False
    assert verrou.ticket_en_cours("projet-a") is None


async def test_le_refus_nomme_toujours_le_ticket_en_cours() -> None:
    """A second run on a busy project is refused, naming the ticket."""
    # Le message est ce que l'utilisateur lit dans le 409 : « attends la fin »
    # sans dire quoi n'aide personne.
    registre = RunRegistry()
    verrou = RunLock(registre)

    async with verrou.acquire("projet-a", "ticket-001"):
        with pytest.raises(RunAlreadyInProgress) as refus:
            async with verrou.acquire("projet-a", "ticket-002"):
                pass

    assert "ticket-001" in str(refus.value)
    assert refus.value.project_id == "projet-a"


async def test_deux_projets_tournent_en_parallele() -> None:
    """The lock is per project, not global."""
    # ADR-008 : deux pipelines sur des projets différents ne partagent rien.
    registre = RunRegistry()
    verrou = RunLock(registre)

    async with verrou.acquire("projet-a", "ticket-001"):
        async with verrou.acquire("projet-b", "ticket-002"):
            assert verrou.is_running("projet-a") is True
            assert verrou.is_running("projet-b") is True
