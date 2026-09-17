import re
from dataclasses import dataclass
from pathlib import Path

_ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


class AgentNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class AgentInfo:
    role: str
    is_builtin: bool
    has_prompt: bool


class AgentRegistryService:
    BUILTIN_ROLES: frozenset[str] = frozenset(
        {
            "codeur",
            "reviewer",
            "orchestrateur",
            "architect",
            "project-creator",
            "project-analyzer",
        }
    )

    def __init__(self, prompts_dir: Path) -> None:
        self._prompts_dir = prompts_dir

    @property
    def prompts_dir(self) -> Path:
        """Directory the prompts are read from — surfaced in error messages."""
        return self._prompts_dir

    def list_agents(self) -> list[AgentInfo]:
        agents: dict[str, AgentInfo] = {}

        for role in sorted(self.BUILTIN_ROLES):
            prompt_file = self._prompts_dir / f"{role}.md"
            agents[role] = AgentInfo(
                role=role, is_builtin=True, has_prompt=prompt_file.exists()
            )

        if self._prompts_dir.exists():
            for prompt_file in sorted(self._prompts_dir.glob("*.md")):
                role = prompt_file.stem
                if role not in agents:
                    agents[role] = AgentInfo(role=role, is_builtin=False, has_prompt=True)

        return list(agents.values())

    def get_prompt(self, role: str) -> str:
        """Read {role}.md. Raises AgentNotFoundError if absent."""
        prompt_file = self._prompts_dir / f"{role}.md"
        if not prompt_file.exists():
            raise AgentNotFoundError(f"Agent '{role}' introuvable dans {self._prompts_dir}")
        return prompt_file.read_text(encoding="utf-8")

    def create_agent(self, role: str, prompt: str) -> None:
        """Write {role}.md. Validates name against ^[a-z][a-z0-9-]*$."""
        if not _ROLE_PATTERN.match(role):
            raise ValueError(
                f"Nom d'agent invalide : '{role}' (doit correspondre à ^[a-z][a-z0-9-]*$)"
            )
        self._prompts_dir.mkdir(parents=True, exist_ok=True)
        (self._prompts_dir / f"{role}.md").write_text(prompt, encoding="utf-8")

    def update_prompt(self, role: str, prompt: str) -> None:
        """Réécrit le prompt d'un agent existant — natif compris (ticket-079).

        Un agent natif s'ajuste : c'est le premier levier de réglage de l'IDE,
        et le refuser obligerait à éditer le fichier dans VSCode juste après
        l'avoir lu à l'écran. La suppression, elle, reste interdite sur un
        natif : régler n'est pas effacer.
        """
        prompt_file = self._prompts_dir / f"{role}.md"
        if not prompt_file.is_file():
            raise AgentNotFoundError(
                f"Agent '{role}' introuvable dans {self._prompts_dir}"
            )
        if not prompt.strip():
            raise ValueError(
                "Un prompt vide priverait l'agent de toute définition."
            )
        prompt_file.write_text(prompt, encoding="utf-8")

    def delete_agent(self, role: str) -> None:
        """Delete {role}.md. Refuses built-in agents."""
        if self.is_builtin(role):
            raise ValueError(f"L'agent built-in '{role}' ne peut pas être supprimé")
        prompt_file = self._prompts_dir / f"{role}.md"
        if not prompt_file.exists():
            raise AgentNotFoundError(f"Agent '{role}' introuvable")
        prompt_file.unlink()

    def is_builtin(self, role: str) -> bool:
        return role in self.BUILTIN_ROLES
