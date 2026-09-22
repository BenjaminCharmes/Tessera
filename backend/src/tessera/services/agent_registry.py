import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


class AgentNotFoundError(Exception):
    pass


class MomentAgent(str, Enum):
    """Quand cet agent parle — la seule chose utile à lire sur une liste.

    Le badge disait « natif » / « ajouté », c'est-à-dire qui avait écrit le
    prompt. Ça n'apprenait rien : c'est toujours un agent. Pire, il annonçait
    « requis » pour des prompts que **rien n'appelle jamais** — `testeur`,
    dont l'étape lance un sous-processus sans agent (ticket-097). `architect`
    a depuis trouvé sa place : il tient l'étape de production des tickets
    `design` (ticket-098).
    """

    #: Appelé automatiquement pendant un run de pipeline.
    pipeline = "pipeline"
    #: Appelé quand l'utilisateur déclenche une action précise.
    demande = "demande"
    #: Rien ne l'appelle. C'est l'information qui manquait.
    jamais = "jamais"


@dataclass(frozen=True)
class AgentInfo:
    role: str
    is_builtin: bool
    has_prompt: bool
    moment: MomentAgent = MomentAgent.jamais


class AgentRegistryService:
    #: Les agents que le dépôt livre et dont quelque chose dépend. Ils ne se
    #: suppriment pas depuis l'IDE.
    #:
    #: Deux motifs, et un seul suffit (ticket-094, ticket-096) :
    #:   - le **code** charge ce prompt par son nom — supprimer `codeur.md`
    #:     casse le pipeline au prochain run ;
    #:   - un **projet du dépôt** le déclare dans son `agents.json` —
    #:     supprimer `analyste-carriere.md` casse le projet `carriere`.
    #:
    #: Ce n'est pas « qui a écrit le prompt » : c'est toujours un agent, livré
    #: ou créé depuis le chat. C'est « qu'est-ce qui casse s'il disparaît ».
    #:
    #: Cette liste était restée à six rôles alors que le dépôt en livre treize.
    #: Sept agents du pipeline — dont `securite`, `testeur`, `validateur` et
    #: `agent-creator` — passaient donc pour des créations de l'utilisateur et
    #: se supprimaient d'un clic. `agent-creator` a effectivement disparu le
    #: 2026-09-17 (ticket-079).
    #:
    #: `test_agents_livres.py` refuse tout prompt livré qui n'apparaîtrait pas
    #: ici : ajouter un agent au dépôt sans le déclarer fait échouer la suite.
    BUILTIN_ROLES: frozenset[str] = frozenset(
        {
            "agent-creator",
            "analyste-carriere",
            "architect",
            "chat",
            "codeur",
            "doc-fonctionnelle",
            "doc-technique",
            "planificateur",
            "project-analyzer",
            "project-creator",
            "resolveur-conflit",
            "reviewer",
            "securite",
            "validateur",
        }
    )

    #: Les rôles que le pipeline appelle de lui-même pendant un run.
    ROLES_PIPELINE: frozenset[str] = frozenset(
        {
            "architect",
            "codeur",
            "reviewer",
            "securite",
            "validateur",
            "resolveur-conflit",
            "doc-technique",
            "doc-fonctionnelle",
        }
    )

    #: Les rôles qu'une action de l'utilisateur déclenche.
    ROLES_A_LA_DEMANDE: frozenset[str] = frozenset(
        {
            "chat",
            "planificateur",
            "agent-creator",
            "project-analyzer",
            "project-creator",
        }
    )
    # `github-sync` n'est pas ici : il n'a pas de prompt. L'agent lit l'API
    # GitHub et écrit des tickets, sans jamais appeler un modèle.

    def __init__(self, prompts_dir: Path, projects_dir: Path | None = None) -> None:
        self._prompts_dir = prompts_dir
        # Un projet peut substituer son propre prompt à une étape du pipeline
        # (ticket-097). Un prompt branché ainsi parle, même si aucun code ne
        # le nomme.
        self._projects_dir = projects_dir

    @property
    def prompts_dir(self) -> Path:
        """Directory the prompts are read from — surfaced in error messages."""
        return self._prompts_dir

    def list_agents(self) -> list[AgentInfo]:
        branches = self._prompts_branches_par_un_projet()
        agents: dict[str, AgentInfo] = {}

        for role in sorted(self.BUILTIN_ROLES):
            prompt_file = self._prompts_dir / f"{role}.md"
            agents[role] = AgentInfo(
                role=role,
                is_builtin=True,
                has_prompt=prompt_file.exists(),
                moment=self._moment(role, branches),
            )

        if self._prompts_dir.exists():
            for prompt_file in sorted(self._prompts_dir.glob("*.md")):
                role = prompt_file.stem
                if role not in agents:
                    agents[role] = AgentInfo(
                        role=role,
                        is_builtin=False,
                        has_prompt=True,
                        moment=self._moment(role, branches),
                    )

        return list(agents.values())

    def _moment(self, role: str, branches: frozenset[str]) -> MomentAgent:
        if role in self.ROLES_PIPELINE or role in branches:
            return MomentAgent.pipeline
        if role in self.ROLES_A_LA_DEMANDE:
            return MomentAgent.demande
        return MomentAgent.jamais

    def _prompts_branches_par_un_projet(self) -> frozenset[str]:
        """Les prompts qu'un `agents.json` substitue à une étape du pipeline."""
        if self._projects_dir is None or not self._projects_dir.is_dir():
            return frozenset()
        branches: set[str] = set()
        for agents_json in self._projects_dir.glob("*/agents.json"):
            try:
                data = json.loads(agents_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for agent in data.get("agents", []):
                if agent.get("role") not in self.ROLES_PIPELINE:
                    continue
                if fichier := agent.get("prompt_file"):
                    branches.add(Path(str(fichier)).stem)
        return frozenset(branches)

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
