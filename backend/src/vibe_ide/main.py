from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vibe_ide.config import settings
from vibe_ide.routers import agents, orchestrator, projects, tickets
from vibe_ide.services.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db(settings.ide_db_path)
    yield


app = FastAPI(title="vibe-ide", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1/projects")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(orchestrator.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
