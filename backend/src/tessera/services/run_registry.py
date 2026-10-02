"""What is running right now, on every project — ticket-127.

`RunLock` already held the answer to « ce projet est-il occupé ? » in a
`dict[str, str | None]`, but nothing exposed it and nobody could say *since
when*, *at which stage*, or *for how many tokens*. The registry holds that
state; `RunLock` becomes a façade over it, so that two structures describing
the same thing cannot drift apart (ADR-034).

En mémoire du process, comme le verrou dont il reprend le rôle : un backend
local n'a pas de second process à protéger (ADR-038).
"""
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


class RunAlreadyInProgress(Exception):
    """A pipeline is already running on this project."""

    def __init__(self, project_id: str, ticket_id: str | None = None) -> None:
        self.project_id = project_id
        self.ticket_id = ticket_id
        en_cours = f" ({ticket_id})" if ticket_id else ""
        super().__init__(
            f"Un pipeline tourne déjà sur le projet '{project_id}'{en_cours}. "
            "Deux exécutions simultanées se marcheraient dessus dans le même "
            "arbre de travail : attends la fin de celle en cours."
        )


@dataclass
class RunActif:
    """Un run en cours, tel que la supervision l'affiche."""

    run_id: str
    project_id: str
    mode: str = "single"
    ticket_id: str | None = None
    #: Titre lisible du ticket en cours — absent tant qu'il n'a pas pu être lu
    #: ou que le run n'a pas encore de ticket (autonome) (ticket-286).
    ticket_titre: str | None = None
    #: Identifiant en base (table `pipeline_runs`) — positionné dès que la
    #: ligne existe, pour que le frontend puisse relire les événements persistés
    #: au rechargement de page (ticket-325).
    db_run_id: str | None = None
    etape: str | None = None
    agent: str | None = None
    tour: int = 0
    tokens_entree: int = 0
    tokens_sortie: int = 0
    cout_usd: float = 0.0
    #: Ce que le run a déjà coûté se lit pendant qu'il tourne (ticket-197) :
    #: le nombre d'appels d'agent finis, et les appels d'outils de l'agent en
    #: cours — remis à zéro à chaque `agent_started`. C'est le compteur qui
    #: bouge en temps réel, et celui qui dit qu'un agent tourne en rond.
    appels: int = 0
    outils: int = 0
    verdict: str | None = None
    #: La question qu'un agent attend de voir répondue, s'il y en a une.
    #: Elle vit ici et pas seulement dans le flux d'événements : un
    #: observateur qui se connecte après coup ne reverra jamais
    #: `agent_question`, et resterait devant un run muet alors qu'ADR-025
    #: suppose qu'un humain peut répondre (ticket-163).
    question: str | None = None
    #: Quand l'agent repartira seul sur une hypothèse énoncée (ADR-025).
    #: Sans elle, l'attente se lit comme une panne : rien à l'écran ne
    #: distingue un run qui attend d'un run qui ne répond plus (ticket-186).
    question_expire_a: str | None = None
    #: Où en est la file, et ce qu'il lui reste. Une file est *un* run
    #: (ADR-041), donc une carte : sans ces champs, la Supervision ne pouvait
    #: pas dire s'il restait deux tickets derrière celui qui tourne
    #: (ticket-172). Vides hors file.
    file_index: int = 0
    file_total: int = 0
    file_restants: tuple[str, ...] = ()
    #: Les tickets que la file a déjà traités. Une file s'arrête au premier
    #: ticket non approuvé : savoir qu'un blocage est passé change ce qu'on
    #: fait de la suite (ticket-179).
    file_faits: tuple[str, ...] = ()
    #: Le `DialogueChannel` du run. C'est ce qui permet à n'importe quel
    #: observateur de répondre à un agent qui pose une question (ADR-025),
    #: au lieu du seul onglet qui a lancé le run.
    dialogue: Any = None
    #: Étapes actuellement en cours sur ce run — renseigné par `run_executor`
    #: quand le reviewer et le validateur tournent en parallèle (ticket-289).
    #: ``"revue"`` et ``"validation"`` peuvent coexister ; ``etape`` garde la
    #: dernière étape démarrée pour les clients qui s'en servent.
    etapes_en_cours: list[str] = field(default_factory=list)
    demarre_a: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def en_dict(self) -> dict[str, Any]:
        """Serialisable view — the dialogue channel is deliberately left out."""
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "mode": self.mode,
            "ticket_id": self.ticket_id,
            "ticket_titre": self.ticket_titre,
            "db_run_id": self.db_run_id,
            "etape": self.etape,
            "agent": self.agent,
            "tour": self.tour,
            "tokens_entree": self.tokens_entree,
            "tokens_sortie": self.tokens_sortie,
            "cout_usd": self.cout_usd,
            "appels": self.appels,
            "outils": self.outils,
            "verdict": self.verdict,
            "question": self.question,
            "question_expire_a": self.question_expire_a,
            "file_index": self.file_index,
            "file_total": self.file_total,
            "file_restants": list(self.file_restants),
            "file_faits": list(self.file_faits),
            "etapes_en_cours": list(self.etapes_en_cours),
            "demarre_a": self.demarre_a.isoformat(),
        }


class RunRegistry:
    """Les runs vivants, indexés par `run_id`, un seul par projet."""

    def __init__(self) -> None:
        self._runs: dict[str, RunActif] = {}

    # -- lecture ---------------------------------------------------------

    def projet_occupe(self, project_id: str) -> bool:
        return any(run.project_id == project_id for run in self._runs.values())

    def ticket_du_projet(self, project_id: str) -> str | None:
        for run in self._runs.values():
            if run.project_id == project_id:
                return run.ticket_id
        return None

    def run_du_projet(self, project_id: str) -> RunActif | None:
        for run in self._runs.values():
            if run.project_id == project_id:
                return run
        return None

    def get(self, run_id: str) -> RunActif | None:
        return self._runs.get(run_id)

    def instantane(self) -> list[dict[str, Any]]:
        """Every live run, as the supervision view receives it on connect."""
        return [run.en_dict() for run in self._runs.values()]

    # -- écriture --------------------------------------------------------

    def mettre_a_jour(self, run_id: str, **champs: Any) -> RunActif | None:
        run = self._runs.get(run_id)
        if run is None:
            return None
        for nom, valeur in champs.items():
            if hasattr(run, nom):
                setattr(run, nom, valeur)
        return run

    def ouvrir(
        self,
        project_id: str,
        ticket_id: str | None = None,
        *,
        mode: str = "single",
        run_id: Optional[str] = None,
        dialogue: Any = None,
        ticket_titre: str | None = None,
    ) -> RunActif:
        """Reserve `project_id`, refusing a second run on it.

        Séparé d'`acquire` parce que le lancement par POST (ticket-128) doit
        réserver **avant** de rendre la main : la tâche qui exécute le run
        démarre après la réponse, et deux POST rapprochés passeraient tous
        les deux si la réservation avait lieu dans la tâche.
        """
        if self.projet_occupe(project_id):
            raise RunAlreadyInProgress(project_id, self.ticket_du_projet(project_id))

        run = RunActif(
            run_id=run_id or uuid.uuid4().hex,
            project_id=project_id,
            mode=mode,
            ticket_id=ticket_id,
            ticket_titre=ticket_titre,
            dialogue=dialogue,
        )
        self._runs[run.run_id] = run
        return run

    def fermer(self, run_id: str) -> None:
        self._runs.pop(run_id, None)

    @asynccontextmanager
    async def acquire(
        self,
        project_id: str,
        ticket_id: str | None = None,
        *,
        mode: str = "single",
        run_id: Optional[str] = None,
        dialogue: Any = None,
        ticket_titre: str | None = None,
    ) -> AsyncIterator[RunActif]:
        """Open a run on `project_id`, refusing a second one on that project."""
        run = self.ouvrir(
            project_id, ticket_id, mode=mode, run_id=run_id, dialogue=dialogue,
            ticket_titre=ticket_titre,
        )
        try:
            yield run
        finally:
            # `finally` et non le chemin nominal : un pipeline qui échoue doit
            # laisser le projet utilisable, pas verrouillé jusqu'au
            # redémarrage du backend.
            self.fermer(run.run_id)


#: Le registre que les routeurs partagent, et sur lequel `RUN_LOCK` s'appuie.
RUN_REGISTRY = RunRegistry()
