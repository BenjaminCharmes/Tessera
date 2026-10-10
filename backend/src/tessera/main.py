from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from tessera.auth import StaticTokenMiddleware
from tessera.config import settings
from tessera.services.process_registry import PROCESS_REGISTRY
from tessera.services.shell_detection import agent_shell_ok, resolve_git_bash, warn_if_shell_missing
from tessera.routers import (
    agent_admin,
    agents,
    chat,
    fs,
    observation,
    orchestrator,
    projects,
    runs,
    services as services_router,
    tickets,
    usage,
)
from tessera.services.database import init_db, solder_les_runs_orphelins
from tessera.services.eveil import relacher as eveil_relacher
from tessera.services.reprise_orphelin import reprendre_depots_orphelins
from tessera.services.prompt_loader import MissingPromptError
from tessera.utils.logger import configure_file_logging, get_logger, install_asyncio_exception_handler

_logger = get_logger(__name__)

# Résolution unique au démarrage : la variable d'environnement ne change pas
# en cours d'exécution. Sous Windows, un bash.exe introuvable loge un
# avertissement dans le lifespan et se reflète dans GET /health (ticket-319).
_GIT_BASH_PATH: str | None = resolve_git_bash(settings.claude_code_git_bash_path)
_AGENT_SHELL_OK: bool = agent_shell_ok(_GIT_BASH_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Le chemin peut venir de l'environnement : il reste sous backend/logs.
    configure_file_logging(
        settings.ide_log_file, racine=Path(__file__).resolve().parents[2] / "logs"
    )
    install_asyncio_exception_handler()
    warn_if_shell_missing(_GIT_BASH_PATH)
    await init_db(settings.ide_db_path)
    # Les runs qu'un processus tué a laissés « en cours » (ticket-177).
    orphelins = await solder_les_runs_orphelins(settings.ide_db_path)
    if orphelins:
        _logger.warning("runs_orphelins_soldes", extra={"runs": orphelins})
        # Remet d'aplomb les dépôts laissés en état intermédiaire (ticket-369).
        await reprendre_depots_orphelins(
            orphelins, settings.ide_db_path, settings.ide_workspace_dir
        )
    yield
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

app.include_router(projects.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1/projects")
app.include_router(chat.router, prefix="/api/v1/projects")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(orchestrator.router, prefix="/api/v1")
app.include_router(observation.router, prefix="/api/v1")
app.include_router(services_router.router, prefix="/api/v1")
app.include_router(agent_admin.router, prefix="/api/v1")
app.include_router(fs.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {"status": "ok", "version": "0.1.0", "agent_shell": _AGENT_SHELL_OK}
