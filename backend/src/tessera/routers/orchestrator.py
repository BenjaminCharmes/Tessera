import asyncio
from typing import TypedDict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from tessera.config import settings
from tessera.services.assemblage_run import build_orchestrator
from tessera.services.controles_depart import manques_avant_depart
from tessera.services.event_hub import EVENT_HUB
from tessera.services.file_vivante import (
    FileFermee,
    FileVivante,
    lecteur_sur_la_base,
    trier_ajouts,
)
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.issues_agent_ready import tirer_les_issues as _tirer_les_issues
from tessera.services.orchestrator import Orchestrator
from tessera.services.politique_run import PolitiqueRun
from tessera.services.reprise_outils import ecrire_log
from tessera.services.run_dans_worktree import (
    OrchestrateurRefuse,
    RunRefuse,
    ouvrir_worktree,
    retirer_apres_echec,
)
from tessera.services.run_executor import executer
from tessera.services.run_lock import RUN_LOCK
from tessera.services.run_registry import RUN_REGISTRY, RunActif, RunAlreadyInProgress
from tessera.services.run_worktree import RunWorktree
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger
from tessera.utils.project_id import validate_project_id

_logger = get_logger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

# Un run à la fois par projet, sur tous les points d'entrée — le même
# verrou que `/chat/run` (ticket-121).
_RUN_LOCK = RUN_LOCK


class RunRequest(BaseModel):
    project_id: str
    #: Optionnel depuis ticket-128 : une file porte `ticket_ids`, un run
    #: autonome ne porte ni l'un ni l'autre.
    ticket_id: str | None = None
    ticket_ids: list[str] = Field(default_factory=list)
    mode: str = "single"
    max_tickets: int = 5
    depuis_github: bool = False
    #: Plafond de dépense explicite d'une file (ticket-383) : remplace le calcul
    #: `run_max_budget_usd × nombre de tickets`. Strictement positif — 0
    #: voudrait dire « sans plafond » et permettrait à tout appelant de
    #: lever la borne. None : calcul par défaut. Ignoré hors mode file.
    budget_usd: float | None = Field(default=None, gt=0)
    #: Passe outre les manques relevés avant le départ (ticket-477) : ils sont
    #: journalisés, le run démarre quand même.
    force: bool = False
    #: Mode « pressé » (ticket-578) : un rôle qui déclare un `fallback` est
    #: construit directement avec lui, sans tenter le principal. Faux par
    #: défaut : le réglage du manifeste économise le quota.
    rapide: bool = False

    @field_validator("project_id")
    @classmethod
    def _check_project_id(cls, v: str) -> str:
        if not validate_project_id(v):
            raise ValueError(f"project_id invalide : {v!r}")
        return v


class _OptionsDuRun(TypedDict, total=False):
    """The keywords `build_orchestrator` only receives when they are set."""

    rapide: bool


class RunStarted(BaseModel):
    """What POST /run answers: the run started, here is how to watch it."""

    run_id: str


class RunAutonomousRequest(BaseModel):
    project_id: str
    max_tickets: int = 5
    #: Tirer d'abord les issues `agent-ready` de GitHub, pour partir d'elles
    #: (ticket-084). Faux par défaut : un appel réseau vers le dépôt d'un
    #: client ne part pas sans qu'on l'ait demandé.
    depuis_github: bool = False

    @field_validator("project_id")
    @classmethod
    def _check_project_id(cls, v: str) -> str:
        if not validate_project_id(v):
            raise ValueError(f"project_id invalide : {v!r}")
        return v



#: Les tâches de run en vol. Sans référence forte, asyncio peut collecter
#: une tâche en cours de route : le run s'arrêterait au milieu, sans commit,
#: ce qu'ADR-018 interdit.
_TACHES: set[asyncio.Task[None]] = set()


def _ticket_initial(request: RunRequest) -> str | None:
    """Le premier ticket traité par le run — le seul connu au démarrage."""
    if request.ticket_id:
        return request.ticket_id
    if request.ticket_ids:
        return request.ticket_ids[0]
    return None


async def _lire_titre(
    ticket_svc: TicketService, ticket_id: str | None
) -> str | None:
    """Lit le titre d'un ticket ; renvoie None si illisible ou absent."""
    if not ticket_id:
        return None
    try:
        ticket = await ticket_svc.get_ticket(ticket_id)
        return ticket.title if ticket else None
    except Exception:  # noqa: BLE001
        return None


class Limites(BaseModel):
    """Les plafonds de dépense, pour que l'écran situe un coût (ticket-197)."""

    run_max_budget_usd: float
    llm_max_budget_usd: float


@router.get("/limits", response_model=Limites)
async def get_limits() -> Limites:
    return Limites(
        run_max_budget_usd=settings.run_max_budget_usd,
        llm_max_budget_usd=settings.llm_max_budget_usd,
    )


async def _preparer_orchestrateur(
    request: RunRequest,
    run: RunActif,
    ticket_svc: TicketService,
    ticket_id: str | None,
) -> Orchestrator | RunRefuse:
    """Build the orchestrator of a run, in its worktree when the project declares one.

    Le worktree se crée ici, sous le verrou déjà pris par `RUN_REGISTRY.ouvrir`
    et avant tout arbre jugé propre (ADR-056). Une création refusée rend un run
    `blocked` qui n'a rien écrit ; toute autre panne libère le projet et le
    worktree (ADR-038).
    """
    project_path = settings.ide_workspace_dir / request.project_id
    wt: RunWorktree | None = None
    # `rapide` ne voyage que lorsqu'il est vrai : l'appel reste celui d'avant
    # ticket-578 pour tout run ordinaire.
    options: _OptionsDuRun = {"rapide": True} if request.rapide else {}
    try:
        politique = PolitiqueRun.lire(project_path)
        if politique.worktree is None:
            orchestrator = await build_orchestrator(request.project_id, **options)
        else:
            # Échoue fermé : un projet à worktree ne tourne jamais dans le
            # checkout, file et autonome compris, `ticket_id` fourni ou non.
            if request.mode != "single" or not ticket_id:
                raise HTTPException(
                    status_code=422,
                    detail="Un projet à worktree ne se lance qu'un ticket à la fois (mode single).",
                )
            ticket = await ticket_svc.get_ticket(ticket_id)
            wt, absents = await ouvrir_worktree(
                project_path, request.project_id, ticket_id,
                ticket.title if ticket else ticket_id, politique,
            ) or (None, [])
            orchestrator = await build_orchestrator(
                request.project_id, wt, tuple(absents), **options
            )
        if request.mode == "autonomous" and request.depuis_github:
            await _tirer_les_issues(request.project_id)
        return orchestrator
    except OrchestrateurRefuse as exc:
        return RunRefuse(exc.arret)
    except Exception as exc:
        # Rien n'a démarré : libérer le projet, sinon il resterait occupé par
        # un run qui n'existe pas.
        RUN_REGISTRY.fermer(run.run_id)
        if wt is not None:
            await retirer_apres_echec(wt, project_path)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/run", status_code=202, response_model=RunStarted)
async def run_pipeline(request: RunRequest) -> RunStarted:
    """Start a run, and answer with its id without waiting for it to end.

    Le run était porté par sa WebSocket avant ticket-128 : il n'était donc
    observable que depuis l'onglet qui l'avait ouverte. Il est maintenant une
    tâche que personne ne possède, et que `/orchestrator/observe` regarde.

    La réservation se fait **ici** et non dans la tâche : deux POST
    rapprochés passeraient tous les deux si le projet n'était marqué occupé
    qu'une fois la réponse partie (ADR-038).
    """
    if request.mode == "single" and not request.ticket_id:
        raise HTTPException(status_code=422, detail="ticket_id requis en mode single")

    # Lire le titre du ticket initial avant de réserver le run (ticket-286).
    project_path = settings.ide_workspace_dir / request.project_id
    ticket_svc = TicketService(project_path, request.project_id)
    initial_ticket_id = _ticket_initial(request)
    ticket_titre = await _lire_titre(ticket_svc, initial_ticket_id)

    # Refus d'emblée, avant toute réservation : le projet reste libre
    # (ticket-413).
    # Les manques se listent tous ; `force` laisse passer en les journalisant
    # (ticket-477).
    manques = manques_avant_depart(project_path, settings.github_token)
    if manques and not request.force:
        raise HTTPException(status_code=422, detail=" ; ".join(manques))
    if manques:
        _logger.warning(
            "depart_force",
            extra={"project_id": request.project_id, "manques": manques},
        )

    try:
        run = RUN_REGISTRY.ouvrir(
            request.project_id,
            initial_ticket_id,
            mode=request.mode,
            ticket_titre=ticket_titre,
        )
    except RunAlreadyInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # La file d'un run `queue` reste ouverte aux ajouts pendant qu'il tourne
    # (ticket-478) ; le registre la porte pour que l'endpoint la retrouve.
    file = FileVivante(request.ticket_ids) if request.mode == "queue" else None
    run.file = file

    orchestrator = await _preparer_orchestrateur(request, run, ticket_svc, initial_ticket_id)

    async def titre_getter(ticket_id: str) -> str | None:
        return await _lire_titre(ticket_svc, ticket_id)

    tache = asyncio.create_task(
        executer(
            run,
            orchestrator,
            EVENT_HUB,
            RUN_REGISTRY,
            ticket_ids=file if file is not None else request.ticket_ids,
            max_tickets=request.max_tickets,
            titre_getter=titre_getter,
            budget_usd=request.budget_usd,
        )
    )
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return RunStarted(run_id=run.run_id)


class AppendRequest(BaseModel):
    ticket_ids: list[str] = Field(min_length=1)


class AppendResult(BaseModel):
    """What an append did: added at the end, left alone, or refused with a reason."""

    ajoutes: list[str]
    ignores: dict[str, str]
    refuses: dict[str, str]


@router.post("/runs/{run_id}/append", response_model=AppendResult)
async def append_to_run(run_id: str, request: AppendRequest) -> AppendResult:
    """Add tickets to the end of a queue that is still running (ticket-478).

    409 quand le run est terminé ou inconnu, n'est pas une file, ou a fini de
    lire sa liste : un ajout n'y serait jamais exécuté.
    """
    run = RUN_REGISTRY.get(run_id)
    if run is None or run.file is None or not run.file.ouverte:
        raise HTTPException(
            status_code=409,
            detail="Ce run n'est pas une file en cours : aucun ticket ne peut y être ajouté.",
        )
    file = run.file
    project_path = settings.ide_workspace_dir / run.project_id
    ticket_svc = TicketService(project_path, run.project_id)
    # Un ticket mergé après le lancement n'est que sur la base distante : on
    # la lit sans toucher à l'arbre du run (ticket-504).
    repli = lecteur_sur_la_base(
        GitWorkspaceService(project_path, politique=PolitiqueRun.lire(project_path)),
        run.project_id,
    )
    acceptes, ignores, refuses = await trier_ajouts(
        file, ticket_svc, request.ticket_ids, repli
    )
    try:
        # Aucun `await` entre le contrôle d'ouverture de `ajouter` et l'ajout.
        ajoutes = file.ajouter_acceptes(acceptes, ignores)
    except FileFermee as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AppendResult(ajoutes=ajoutes, ignores=ignores, refuses=refuses)


class RemoveRequest(BaseModel):
    ticket_ids: list[str] = Field(min_length=1)


class RemoveResult(BaseModel):
    """What a removal did: taken out of the queue, absent, or refused with a reason."""

    retires: list[str]
    ignores: dict[str, str]
    refuses: dict[str, str]


@router.post("/runs/{run_id}/remove", response_model=RemoveResult)
async def remove_from_run(run_id: str, request: RemoveRequest) -> RemoveResult:
    """Take tickets not yet started out of a queue that is still running (ticket-513).

    409 quand le run est terminé ou inconnu, n'est pas une file, ou a fini de
    lire sa liste. La fiche du ticket n'est pas modifiée : retirer n'est pas
    annuler.
    """
    run = RUN_REGISTRY.get(run_id)
    if run is None or run.file is None or not run.file.ouverte:
        raise HTTPException(
            status_code=409,
            detail="Ce run n'est pas une file en cours : aucun ticket ne peut en être retiré.",
        )
    try:
        # Aucun `await` entre le contrôle d'ouverture et le retrait.
        retires, ignores, refuses = run.file.retirer(request.ticket_ids)
    except FileFermee as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    projet = settings.ide_workspace_dir / run.project_id
    for ticket_id in retires:
        ecrire_log(projet, f"[{run.project_id}] {ticket_id} retiré de la file")
    return RemoveResult(retires=retires, ignores=ignores, refuses=refuses)
