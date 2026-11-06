import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from tessera import reglages
from tessera.auth import HostOriginMiddleware, StaticTokenMiddleware
from tessera.config import settings
from tessera.config_coffre import source_effective
from tessera.routers import (
    agent_admin,
    agents,
    chat,
    fs,
    observation,
    orchestrator,
    projects,
    runs,
    salle_tessera,
    services_activite,
    services_running,
    signalements,
    supervision_recap,
    ticket_proposals,
    tickets,
    tickets_archive,
    usage,
)
from tessera.routers import captures as captures_router
from tessera.routers import provisioning as provisioning_router
from tessera.routers import reglages as reglages_router
from tessera.routers import services as services_router
from tessera.services.livraison.reprise_surveillance import reprendre_surveillances
from tessera.services.livraison.surveillance_run import surveillance_de_reprise
from tessera.services.noyau.database import init_db
from tessera.services.noyau.database_runs import solder_les_runs_orphelins
from tessera.services.noyau.eveil import relacher as eveil_relacher
from tessera.services.noyau.event_hub import EVENT_HUB
from tessera.services.noyau.prompt_loader import MissingPromptError
from tessera.services.noyau.shell_detection import agent_shell_ok, resolve_git_bash, warn_if_shell_missing
from tessera.services.pipeline.reprise_orphelin import reprendre_depots_orphelins
from tessera.services.pipeline.reprise_worktrees import reprendre_worktrees_orphelins
from tessera.services.pipeline.run_registry import RUN_REGISTRY
from tessera.services.pipeline.signalements_en_attente import migrer_ancien_fichier
from tessera.services.supervision.anomalies.detecteur import DetecteurDAnomalies, arreter_le_detecteur
from tessera.services.supervision.superviseur_collecte import boucle_du_superviseur
from tessera.services.verification.process_registry import PROCESS_REGISTRY
from tessera.utils.access_log_redaction import install_token_redaction
from tessera.utils.logger import configure_file_logging, get_logger, install_asyncio_exception_handler

_logger = get_logger(__name__)

# Le jeton d'une WebSocket voyage en query string : il ne doit pas finir dans
# le journal d'accès d'uvicorn (ticket-758).
install_token_redaction()

# Résolution unique au démarrage : la variable d'environnement ne change pas
# en cours d'exécution. Sous Windows, un bash.exe introuvable loge un
# avertissement dans le lifespan et se reflète dans GET /health (ticket-319).
_GIT_BASH_PATH: str | None = resolve_git_bash(settings.claude_code_git_bash_path)
_AGENT_SHELL_OK: bool = agent_shell_ok(_GIT_BASH_PATH)


async def _reprendre_les_surveillances() -> None:
    """Resume the CI watch of PR handed over before the stop (ticket-510).

    Une erreur est journalisée : elle ne doit jamais empêcher le démarrage.
    """
    try:
        await reprendre_surveillances(
            settings.ide_workspace_dir,
            settings.ide_db_path,
            surveillance_de_reprise,
            EVENT_HUB.publish,
        )
    except Exception:  # noqa: BLE001 — la reprise est un filet, pas une condition
        _logger.exception("reprise_surveillances_echec")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Le chemin peut venir de l'environnement : il reste sous backend/logs.
    configure_file_logging(
        settings.ide_log_file, racine=Path(__file__).resolve().parents[2] / "logs"
    )
    install_asyncio_exception_handler()
    warn_if_shell_missing(_GIT_BASH_PATH)
    await init_db(settings.ide_db_path)
    # Les surcharges de réglages passent en cache : la base est prête (ADR-075).
    await reglages.charger(settings.ide_db_path)
    # La file des signalements a quitté le dépôt (ticket-430).
    migrer_ancien_fichier()
    # Les runs qu'un processus tué a laissés « en cours » (ticket-177).
    orphelins = await solder_les_runs_orphelins(settings.ide_db_path)
    if orphelins:
        _logger.warning("runs_orphelins_soldes", extra={"runs": orphelins})
    # Remet d'aplomb les dépôts laissés en état intermédiaire (ticket-369), y
    # compris ceux d'un arrêt propre : ces runs sont `interrupted` en base,
    # donc absents de `orphelins` (ticket-665).
    await reprendre_depots_orphelins(
        orphelins, settings.ide_db_path, settings.ide_workspace_dir
    )
    # Les worktrees de run qu'un arrêt a laissés : commit, puis suppression (ticket-520).
    await reprendre_worktrees_orphelins(
        settings.ide_workspace_dir, settings.ide_worktrees_dir
    )
    await _reprendre_les_surveillances()
    # Le témoin des runs (ADR-078) : une tâche de fond, qui n'agit sur rien.
    detecteur = (
        asyncio.create_task(
            DetecteurDAnomalies(RUN_REGISTRY, EVENT_HUB, settings.ide_db_path, settings).boucle()
        )
        if settings.anomalies_actives
        else None
    )
    # Le superviseur (ADR-080) : ne démarre que si un projet déclare le rôle actif.
    superviseur = asyncio.create_task(boucle_du_superviseur().boucle())
    yield
    await arreter_le_detecteur(superviseur)
    await arreter_le_detecteur(detecteur)
    # Les services lancés pour un projet sont des enfants de ce process et
    # s'arrêtent avec lui (ADR-042). Les terminer explicitement rend l'arrêt
    # propre plutôt que brutal : l'alternative — les détacher — laisserait un
    # serveur derrière soi, avec son port et rien pour l'arrêter.
    arretes = await PROCESS_REGISTRY.tout_arreter()
    if arretes:
        _logger.info("services_arretes", extra={"nombre": arretes})
    # Filet de sécurité : relâche la demande de veille au cas où un run
    # n'aurait pas été fermé proprement avant l'arrêt (ticket-394).
    eveil_relacher()


app = FastAPI(title="Tessera", version="0.1.0", lifespan=lifespan)


async def _missing_prompt_handler(request: Request, exc: Exception) -> JSONResponse:
    """Surface a missing agent prompt as an actionable message, not a 500 blob.

    `MissingPromptError` already carries the file, the directory searched and
    the setting that overrides it. Left unhandled it reaches the UI as
    "Internal Server Error", which is exactly the opacity ticket-051 exists to
    remove.
    """
    _logger.error("missing_prompt", extra={"error": str(exc)})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_exception_handler(MissingPromptError, _missing_prompt_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Toujours installé : il lit `settings.static_token` à chaque requête et laisse
# tout passer quand elle est vide. L'installer sous condition figeait le choix
# au démarrage et rendait le comportement intestable (ticket-120).
app.add_middleware(StaticTokenMiddleware)
# Ajouté en dernier donc le plus externe : un `Host` ou un `Origin` étranger est
# refusé avant tout le reste, token compris (ticket-704).
app.add_middleware(HostOriginMiddleware)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(provisioning_router.router, prefix="/api/v1")
app.include_router(ticket_proposals.router, prefix="/api/v1/projects")
app.include_router(tickets.router, prefix="/api/v1/projects")
app.include_router(tickets_archive.router, prefix="/api/v1/projects")
app.include_router(chat.router, prefix="/api/v1/projects")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(orchestrator.router, prefix="/api/v1")
app.include_router(observation.router, prefix="/api/v1")
app.include_router(services_router.router, prefix="/api/v1")
app.include_router(services_running.router, prefix="/api/v1")
app.include_router(services_activite.router, prefix="/api/v1")
app.include_router(captures_router.router, prefix="/api/v1")
app.include_router(agent_admin.router, prefix="/api/v1")
app.include_router(fs.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(reglages_router.router, prefix="/api/v1")
app.include_router(signalements.router, prefix="/api/v1")
app.include_router(salle_tessera.router, prefix="/api/v1")
app.include_router(supervision_recap.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str | bool]:
    # `secrets` : d'où viennent les secrets (ADR-073), jamais un nom ni une valeur.
    return {
        "status": "ok",
        "version": "0.1.0",
        "agent_shell": _AGENT_SHELL_OK,
        "secrets": source_effective(),
    }
