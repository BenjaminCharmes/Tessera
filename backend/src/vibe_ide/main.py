from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vibe_ide.routers import agents, orchestrator, projects, tickets

app = FastAPI(title="vibe-ide", version="0.1.0")

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
