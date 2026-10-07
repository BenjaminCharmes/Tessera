"""Running a pipeline as a task nobody owns — ticket-128.

Le run était porté par la WebSocket qui l'avait lancé : son émetteur écrivait
sur cette socket, son `DialogueChannel` n'écoutait que ses messages, et
fermer l'onglet coupait le seul chemin de réponse. Ici le run est une tâche
`asyncio` ordinaire : il publie sur `EventHub`, son canal de dialogue vit
dans `RunRegistry`, et les observateurs vont et viennent sans qu'il s'en
aperçoive.

`finish_run` est appelé dans un `finally`, avant toute autre écriture : placé
après, il disparaissait dès que le transport mourait, et l'historique restait
bloqué sur « en cours » (ticket-079, ticket-121).
"""
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

from tessera.config import settings
from tessera.services.database import create_run, finish_run, save_event
from tessera.models.agent import AgentRole
from tessera.services.dialogue import DialogueChannel
from tessera.services.event_hub import EventHub
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.run_registry import RunActif, RunRegistry
from tessera.utils.logger import get_logger

#: Récupère le titre d'un ticket depuis son identifiant. Retourne None si
#: le ticket est illisible, sans lever d'exception (ticket-286).
TitreGetter = Callable[[str], Awaitable[str | None]]

_logger = get_logger(__name__)


def _log_pipeline(project_id: str, message: str) -> None:
    """Write a 'file interrompue' line to the project's pipeline log.

    Mirrors the `_log` method of `Orchestrator` so the user can see that the
    queue died, even when the exception was raised outside of the orchestrator
    (e.g. a DB error or an unexpected crash in `executer`).
    """
    log_path: Path = settings.ide_workspace_dir / project_id / "memory" / "pipeline-log.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"- {ts} — [{project_id}] file interrompue : {message}\n"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("pipeline_log_write_failed", extra={"error": str(exc)})


class Orchestrateur(Protocol):
    """Ce que l'exécuteur attend, sans importer le moteur lui-même."""

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: Any,
        run_id: str | None = ...,
        dialogue: Any = ...,
    ) -> PipelineResult: ...


def emetteur(
    hub: EventHub,
    run: RunActif,
    run_id_en_base: Optional[str],
    titre_getter: Optional[TitreGetter] = None,
) -> EventCallback:
    """Publish on the hub, then persist — in that order.

    La persistance vient **après** la publication pour la même raison qu'avant
    ticket-128 : un défaut d'écriture ne doit pas priver les observateurs de
    l'événement. L'inverse ferait dépendre l'affichage de SQLite.
    """

    async def envoyer(event: OrchestratorEvent) -> None:
        event.run_id = run.run_id
        event.project_id = run.project_id
        ancien_ticket_id = run.ticket_id
        _suivre(run, event)
        # Tout ticket_status_changed porte ticket_titre dès que le run le connaît.
        # Le titre n'est relu sur disque qu'au changement de ticket (ticket-324).
        if (
            titre_getter is not None
            and event.type is EventType.TICKET_STATUS_CHANGED
            and run.ticket_id
        ):
            if run.ticket_id != ancien_ticket_id:
                # Le ticket vient de changer : relire depuis le disque.
                try:
                    run.ticket_titre = await titre_getter(run.ticket_id)
                except Exception:  # noqa: BLE001
                    run.ticket_titre = None
            if run.ticket_titre is not None:
                event.data["ticket_titre"] = run.ticket_titre
        await hub.publish(event)
        if run_id_en_base is None:
            return
        try:
            await save_event(
                settings.ide_db_path,
                run_id_en_base,
                event.type.value,
                event.agent.value if event.agent else None,
                event.data,
                event.timestamp.isoformat(),
                ticket_id=event.ticket_id or None,
            )
        except Exception as exc:  # noqa: BLE001
            # Un événement non persisté dégrade l'historique ; le faire
            # remonter interromprait le run avant son commit (ADR-037).
            _logger.warning("event_non_persiste", extra={"erreur": str(exc)})

    return envoyer


def _suivre(run: RunActif, event: OrchestratorEvent) -> None:
    """Keep the registry entry in step with what the run announces."""
    if event.type is EventType.AGENT_STARTED:
        run.etape = str(event.data.get("stage") or event.type.value)
        run.agent = event.agent.value if event.agent else None
        run.outils = 0
        # Reviewer démarre : marquer l'étape de revue en cours (ticket-289).
        if event.agent is AgentRole.reviewer and "revue" not in run.etapes_en_cours:
            run.etapes_en_cours.append("revue")
    elif event.type is EventType.AGENT_DONE:
        cout = event.data.get("cost_usd")
        if isinstance(cout, (int, float)):
            run.cout_usd += float(cout)
        run.appels += 1
        # Reviewer terminé : retirer "revue" des étapes en cours (ticket-289).
        if event.agent is AgentRole.reviewer:
            try:
                run.etapes_en_cours.remove("revue")
            except ValueError:
                pass
    elif event.type is EventType.TICKET_STATUS_CHANGED:
        run.ticket_id = event.ticket_id or run.ticket_id
    elif event.type is EventType.QUEUE_PROGRESS:
        index = event.data.get("index")
        total = event.data.get("total")
        if isinstance(index, int):
            run.file_index = index
        if isinstance(total, int):
            run.file_total = total
        restants = event.data.get("restants")
        if isinstance(restants, list):
            run.file_restants = tuple(str(t) for t in restants)
        faits = event.data.get("faits")
        if isinstance(faits, list):
            run.file_faits = tuple(str(t) for t in faits)
    elif event.type is EventType.AGENT_QUESTION:
        question = event.data.get("question")
        run.question = str(question) if question else None
        expire = event.data.get("expire_a")
        run.question_expire_a = str(expire) if expire else None
    elif event.type in (EventType.AGENT_TOKEN, EventType.AGENT_TOOL_USE):
        if event.type is EventType.AGENT_TOOL_USE:
            run.outils += 1
        # L'agent a repris — sur réponse ou sur l'hypothèse d'ADR-025. Garder
        # la question afficherait une attente qui n'existe plus, et on
        # répondrait à un agent qui n'écoute pas.
        run.question = None
        run.question_expire_a = None
    elif event.type is EventType.VALIDATION_STARTED:
        run.etape = "validation"
        # Validateur démarre : marquer l'étape en cours (ticket-289).
        if "validation" not in run.etapes_en_cours:
            run.etapes_en_cours.append("validation")
    elif event.type is EventType.DOCUMENTATION_STARTED:
        run.etape = "documentation"
    elif event.type is EventType.LIVRAISON_STARTED:
        run.etape = "livraison"
    elif event.type is EventType.VALIDATION_DONE:
        # Validateur terminé : retirer "validation" des étapes en cours (ticket-289).
        try:
            run.etapes_en_cours.remove("validation")
        except ValueError:
            pass
        verdict = event.data.get("verdict")
        if verdict:
            run.verdict = str(verdict)
    elif event.type is EventType.SECURITY_AUDIT_DONE:
        verdict = event.data.get("verdict")
        if verdict:
            run.verdict = str(verdict)
    tour = event.data.get("round")
    if isinstance(tour, int):
        run.tour = tour


def dialogue_du_run(envoyer: EventCallback, run: RunActif) -> DialogueChannel:
    """The run's dialogue channel, which the registry then holds."""

    async def annoncer(question: str) -> None:
        # L'échéance part avec la question : cinq minutes de silence se lisent
        # comme une panne tant que rien ne dit que l'attente est bornée
        # (ticket-186). Absolue plutôt qu'une durée, pour qu'un client arrivé
        # en cours de route sache combien il reste, et non combien il restait.
        expire_a = datetime.now(timezone.utc) + timedelta(
            seconds=settings.dialogue_timeout_s
        )
        await envoyer(
            OrchestratorEvent(
                type=EventType.AGENT_QUESTION,
                ticket_id=run.ticket_id or "",
                data={
                    "question": question,
                    "expire_a": expire_a.isoformat(),
                },
            )
        )

    # `interactive` reste vrai même sans observateur connecté : ADR-025 fait
    # reprendre l'agent sur une hypothèse énoncée passé le délai, et c'est ce
    # comportement-là qu'on veut, pas une réponse immédiate.
    return DialogueChannel(
        timeout_s=settings.dialogue_timeout_s,
        interactive=run.mode != "autonomous",
        on_question=annoncer,
    )


async def executer(
    run: RunActif,
    orchestrator: Any,
    hub: EventHub,
    registry: RunRegistry,
    *,
    ticket_ids: Optional[list[str]] = None,
    max_tickets: int = 5,
    titre_getter: Optional[TitreGetter] = None,
    budget_usd: Optional[float] = None,
) -> None:
    """Run the pipeline to its end, then free the project.

    Ne lève jamais : la tâche n'a pas d'appelant pour rattraper son
    exception, et un run qui meurt sans fermer son entrée laisserait le
    projet verrouillé jusqu'au redémarrage du backend.
    """
    run_id_en_base: str | None = None
    try:
        run_id_en_base = await create_run(
            settings.ide_db_path,
            run.project_id,
            run.ticket_id or run.mode,
            mode=run.mode,
        )
        # Exposé dans l'instantané pour que le frontend puisse relire
        # les événements persistés au rechargement de page (ticket-325).
        run.db_run_id = run_id_en_base
    except Exception as exc:  # noqa: BLE001
        _logger.warning("run_non_persiste", extra={"erreur": str(exc)})

    envoyer = emetteur(hub, run, run_id_en_base, titre_getter=titre_getter)
    run.dialogue = dialogue_du_run(envoyer, run)

    resultats: list[PipelineResult] = []
    echec: str | None = None
    try:
        if run.mode == "autonomous":
            resultats = await orchestrator.run_autonomous(
                run.project_id, max_tickets, envoyer,
                envelope_run_id=run_id_en_base,
            )
        elif run.mode == "queue":
            resultats = await orchestrator.run_queue(
                run.project_id, ticket_ids or [], envoyer, run.dialogue,
                envelope_run_id=run_id_en_base,
                budget_override_usd=budget_usd,
            )
        else:
            resultats = [
                await orchestrator.run_pipeline(
                    run.project_id,
                    run.ticket_id or "",
                    envoyer,
                    run_id=run_id_en_base,
                    dialogue=run.dialogue,
                )
            ]
    except Exception as exc:  # noqa: BLE001 — voir la docstring
        echec = str(exc)
        _logger.warning("run_interrompu", extra={"erreur": echec})
        _log_pipeline(run.project_id, echec)
    finally:
        # Libérer le projet **avant** d'écrire en base : le pipeline a rendu
        # la main, et quelqu'un qui relance au signal de fin ne doit pas
        # prendre un 409 le temps d'un aller-retour SQLite. La fenêtre ne
        # disparaît pas tout à fait — `pipeline_done` est publié par
        # l'orchestrateur, donc avant ce `finally` — mais elle tombe de
        # plusieurs millisecondes à presque rien.
        registry.fermer(run.run_id)
        await _clore(run, run_id_en_base, resultats, echec, envoyer)


async def _clore(
    run: RunActif,
    run_id_en_base: str | None,
    resultats: list[PipelineResult],
    echec: str | None,
    envoyer: EventCallback,
) -> None:
    dernier = resultats[-1] if resultats else None
    if run_id_en_base is not None:
        try:
            await finish_run(
                settings.ide_db_path,
                run_id_en_base,
                dernier.rounds if dernier else 0,
                dernier.approved if dernier else False,
                dernier.final_status.value if dernier else "interrupted",
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning("run_non_clos", extra={"erreur": str(exc)})

    if echec is not None:
        await envoyer(
            OrchestratorEvent(
                type=EventType.ERROR,
                ticket_id=run.ticket_id or "",
                data={"error": echec},
            )
        )

    # Toujours, et en dernier : c'est le seul événement dont un client peut
    # déduire que le projet est de nouveau libre, et le seul qui porte encore
    # `arret` depuis que le POST ne rend plus le résultat (ADR-037).
    # `db_run_id` permet au frontend d'appeler GET /runs/{id}/events pour
    # relire les événements du run terminé (ticket-280).
    await envoyer(
        OrchestratorEvent(
            type=EventType.RUN_CLOSED,
            ticket_id=dernier.ticket_id if dernier else (run.ticket_id or ""),
            data={
                "approved": dernier.approved if dernier else False,
                "rounds": dernier.rounds if dernier else 0,
                "final_status": (
                    dernier.final_status.value if dernier else "interrupted"
                ),
                "branch": dernier.branch if dernier else None,
                "commit_sha": dernier.commit_sha if dernier else None,
                "arret": (dernier.arret if dernier else None) or echec,
                "resultats": len(resultats),
                "db_run_id": run_id_en_base,
            },
        )
    )
