from pathlib import Path

from pydantic import BaseModel, Field


class Project(BaseModel):
    id: str = Field(description="Nom du dossier projet, ex: ide-core")
    name: str
    path: Path
    description: str = ""
    active_agents: list[str] = Field(default_factory=list)
    stack: str | None = None
    raw_claude_md: str = ""
