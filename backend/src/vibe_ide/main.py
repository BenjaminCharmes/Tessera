from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from vibe_ide.config import settings
from vibe_ide.routers import agent_admin, agents, orchestrator, projects, tickets
from vibe_ide.services.database import init_db
from vibe_ide.services.prompt_loader import MissingPromptError
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db(settings.ide_db_path)
    yield


class StaticTokenMiddleware(BaseHTTPMiddleware):
    """Verifies Authorization: Bearer <token> when STATIC_TOKEN is configured."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {settings.static_token}":
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


app = FastAPI(title="vibe-ide", version="0.1.0", lifespan=lifespan)


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

if settings.static_token:
    app.add_middleware(StaticTokenMiddleware)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1/projects")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(orchestrator.router, prefix="/api/v1")
app.include_router(agent_admin.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
