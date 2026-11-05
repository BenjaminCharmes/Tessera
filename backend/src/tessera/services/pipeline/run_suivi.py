"""Keeping the registry entry in step with a run's events — ticket-128.

Sorti de `run_executor.py` au ticket-834, qui plafonnait ce fichier : le suivi
d'un événement est une fonction pure du registre, sans I/O.
"""
from tessera.models.agent import AgentRole
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.run_registry import RunActif


def suivre(run: RunActif, event: OrchestratorEvent) -> None:
    """Keep the registry entry in step with what the run announces."""
    # Chaque événement compte, tokens et appels d'outils compris : c'est de là
    # que le détecteur d'anomalies lit le silence (ticket-834).
    # Sauf le constat du détecteur lui-même : il dit le silence, il ne le rompt pas.
    if event.type is not EventType.RUN_ANOMALY:
        run.dernier_evenement_a = event.timestamp
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
        # Le ticket que la file annonce est le ticket courant : le statut d'une
        # file le rend, et `ticket_status_changed` n'arrive qu'après (ticket-431).
        run.ticket_id = event.ticket_id or run.ticket_id
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
    elif event.type is EventType.EXTERNAL_WAIT:
        # Le silence d'une attente extérieure est voulu (ticket-559).
        run.attente_exterieure = bool(event.data.get("waiting"))
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
