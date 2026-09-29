"""Workflow GitHub d'un ticket : pousser, ouvrir la PR, merger — ticket-064.

Merger, c'est décider qu'un travail est bon. Sur le dépôt d'un client, c'est le
seul point du pipeline où un humain tranche, et c'est ce qui rend acceptable
tout le reste de l'automatisation. Sur un dépôt personnel doté d'une CI, exiger
ce clic ne protège personne.

Ce module ne choisit donc pas : il obéit à ce que le projet déclare dans son
`agents.json` (ADR-029). Le défaut, lui, protège — sans déclaration, rien ne
part sur le distant.

Le maillon que ce module avait ajouté est le push. `create-pr` demandait à
GitHub une branche `head` que rien n'avait jamais poussée : la fonctionnalité
n'avait jamais pu aboutir.
"""
import re
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from pathlib import Path

from tessera.services.autonomie import (
    NiveauAutonomie,
    lire_niveau,
    niveau_peut_merger,
)
from tessera.services.politique_run import PolitiqueRun
from tessera.services.sync_map import SyncMapService
from tessera.services.termes_interdits import (
    CommitInfo,
    TermesInterditsChecker,
    TermesInterditsService,
)
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


class WorkflowError(Exception):
    """Une opération de workflow a été refusée."""


@dataclass(frozen=True)
class PullRequestResult:
    pr_number: int
    pr_url: str
    branch: str


class _GitWorkspace(Protocol):
    async def push_branch(self, branch_name: str) -> None: ...
    async def current_diff(self) -> str: ...
    async def diff_de_branche(self, base: str, branch: str) -> str: ...
    async def commits_depuis_base(self, base: str, branch: str) -> list[CommitInfo]: ...


class _GitHub(Protocol):
    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str | None = None,
    ) -> tuple[int, str]: ...

    async def get_pull_request_status(self, pr_number: int) -> Any: ...

    async def merge_pull_request(self, pr_number: int) -> None: ...


def _section(ticket_body: str, heading: str) -> str:
    """Extrait une section `## <heading>` du corps d'un ticket."""
    pattern = re.compile(
        rf"^##\s*{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(ticket_body or "")
    return match.group(1).strip() if match else ""


def build_pr_body(
    ticket_id: str, ticket_title: str, ticket_body: str, issue: int | None = None
) -> str:
    """Rédige le corps de la PR depuis le ticket.

    Aucune mention d'outil d'IA (ticket-060) : ce texte part dans le dépôt de
    l'utilisateur, parfois celui d'un client.

    `Closes #N` referme l'issue d'origine au merge (ticket-084). Sans lui la
    boucle ne se referme pas : la PR part, elle est mergée, et l'issue reste
    ouverte à refermer à la main.
    """
    parts = [f"Ticket **{ticket_id}** — {ticket_title}"]

    objectif = _section(ticket_body, "Objectif")
    if objectif:
        parts.append(f"## Objectif\n\n{objectif}")

    criteres = _section(ticket_body, "Critères d'acceptation")
    if criteres:
        parts.append(f"## Critères d'acceptation\n\n{criteres}")

    if issue is not None:
        parts.append(f"Closes #{issue}")

    return "\n\n".join(parts) + "\n"


class GitHubWorkflowService:
    """Pousse une branche, ouvre sa PR, et merge si le projet l'a déclaré.

    Jusqu'ou le service va depend du projet (ticket-082), pas du service :
    `project_path` designe le dossier dont `agents.json` porte la declaration.
    Sans lui, le service se comporte comme avant ADR-029 — il n'est autorise a
    rien de plus que pousser et ouvrir.
    """

    def __init__(
        self,
        git_workspace: Optional[_GitWorkspace],
        github: Optional[_GitHub],
        base_branch: str,
        project_path: Path | None = None,
        politique: PolitiqueRun | None = None,
        termes: TermesInterditsChecker | None = None,
    ) -> None:
        self._git = git_workspace
        self._github = github
        self._base_branch = base_branch
        self._project_path = project_path
        # Figée par l'orchestrateur avant le premier agent (ticket-119). Sans
        # elle — geste demandé depuis l'IDE — le fichier fait foi, comme avant.
        self._politique = politique
        # Contrôle des termes interdits (ADR-048). Construit ici quand
        # l'appelant ne le fournit pas : aucun appelant ne le passait, et le
        # contrôle ne tournait donc jamais (ticket-206).
        self._termes = termes if termes is not None else TermesInterditsService()

    def _niveau(self) -> NiveauAutonomie:
        """Le niveau qui vaut pour cet appel : figé s'il l'a été, lu sinon."""
        if self._politique is not None:
            return self._politique.autonomy
        assert self._project_path is not None
        return lire_niveau(self._project_path)

    async def open_pull_request(
        self,
        *,
        branch: str | None,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        autonome: bool = True,
    ) -> PullRequestResult:
        """Pousse la branche **puis** ouvre la PR.

        L'ordre est le correctif : GitHub refuse une `head` qu'il ne connaît
        pas, et rien ne poussait jusqu'ici.

        `autonome` distingue les deux appelants. Un run qui avance seul est
        soumis a la declaration du projet : sur un depot client, l'utilisateur
        pousse lui-meme parce que les acces y sont souvent specifiques, et un
        push parti tout seul serait une decision prise a sa place. Le meme
        geste demande explicitement depuis l'IDE (`autonome=False`) est la
        decision de l'utilisateur, et ne se lui refuse pas.
        """
        if autonome and self._project_path is not None:
            if self._niveau() not in (NiveauAutonomie.pr, NiveauAutonomie.merge):
                raise WorkflowError(
                    "Ce projet ne laisse pas l'IDE pousser tout seul. Le travail "
                    "est commité sur sa branche ; à toi de pousser. Pour changer "
                    'cela, déclare `"autonomy": "pr"` dans son agents.json.'
                )
        if self._git is None:
            raise WorkflowError("Ce projet n'a pas de dépôt git utilisable.")
        if branch is None:
            raise WorkflowError(
                "Aucune branche à pousser : lance d'abord le pipeline sur ce ticket."
            )
        if self._github is None:
            raise WorkflowError(
                "GitHub n'est pas configuré pour ce projet : il faut un "
                "GITHUB_TOKEN et un dépôt distant lié."
            )

        await self._verifier_termes_interdits(branch)

        await self._git.push_branch(branch)

        pr_number, pr_url = await self._github.create_pull_request(
            title=f"{ticket_id} — {ticket_title}",
            body=build_pr_body(
                ticket_id, ticket_title, ticket_body, issue=self._issue_de(ticket_id)
            ),
            head=branch,
            base=self._base_branch,
        )
        _logger.info(
            "pull_request_opened",
            extra={"ticket_id": ticket_id, "pr_number": pr_number, "branch": branch},
        )
        return PullRequestResult(pr_number=pr_number, pr_url=pr_url, branch=branch)


    async def _verifier_termes_interdits(self, branch: str) -> None:
        """Bloque le push si un terme interdit est trouvé — ADR-048.

        Court-circuité quand le service est inactif ou quand le projet se
        déclare professionnel. Sans politique de run — un push demandé depuis
        l'IDE —, la politique vient du manifeste : ADR-048 dit « avant tout
        push ». On lit ce que la branche a **commité** : au push, l'arbre de
        travail est propre et `current_diff` serait vide.
        """
        if not self._termes.actif:
            return
        politique = self._politique
        if politique is None and self._project_path is not None:
            politique = PolitiqueRun.lire(self._project_path)
        if politique is not None and politique.exempte_controle_termes:
            return
        assert self._git is not None  # vérifié avant cet appel
        diff = await self._git.diff_de_branche(self._base_branch, branch)
        lignes_ajoutees = [l for l in diff.splitlines() if l.startswith("+")]
        commits = await self._git.commits_depuis_base(self._base_branch, branch)
        violations = self._termes.verifier(
            lignes_ajoutees=lignes_ajoutees,
            commits=commits,
        )
        if violations:
            sources = ", ".join(v.source for v in violations)
            raise WorkflowError(
                f"Push bloqué : terme interdit détecté. Sources : {sources}"
            )

    def _issue_de(self, ticket_id: str) -> int | None:
        """Le numéro d'issue GitHub dont ce ticket est né, s'il en vient d'une.

        La carte de synchronisation est la source : c'est elle que
        `github-sync` écrit en créant le ticket.
        """
        if self._project_path is None:
            return None
        entree = SyncMapService().load(self._project_path).get(ticket_id)
        return entree.issue if entree else None

    async def etat_ci(self, pr_number: int) -> str:
        """L'état agrégé de la CI de la PR : passing, failing, pending, none.

        Sans GitHub configuré, `none` : aucune CI n'est observable, et
        l'absence de signal n'est pas un signal favorable.
        """
        if self._github is None:
            return "none"
        statut = await self._github.get_pull_request_status(pr_number)
        return str(getattr(statut, "ci_status", "none"))

    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool:
        """Merge la PR **si** le projet l'autorise et **si** la CI est verte.

        ADR-022 interdisait tout merge. Elle devient conditionnelle (ADR-029) :
        la declaration du projet dit que l'utilisateur renonce a sa relecture
        sur ce depot-la, et la CI verte est le seul signal objectif dont l'IDE
        dispose pour savoir que le code passe.

        Les deux conditions se verifient **ici**, au moment d'agir. Un plan
        calcule plus tot aurait pu l'etre sur une CI qui depuis est passee au
        rouge.

        Rend `False` sans rien faire des qu'une condition manque : c'est le cas
        normal sur la grande majorite des projets, pas une erreur.
        """
        if self._github is None or self._project_path is None:
            return False
        # La declaration se lit avant l'appel reseau : sur la grande majorite
        # des projets elle suffit a repondre, et interroger GitHub pour un
        # merge qui ne se fera de toute facon pas est du bruit.
        if self._niveau() is not NiveauAutonomie.merge:
            return False

        statut = await self._github.get_pull_request_status(pr_number)
        ci = str(getattr(statut, "ci_status", "none"))
        sans_ci = self._politique is not None and self._politique.merge_without_ci
        if not niveau_peut_merger(self._niveau(), ci_status=ci, sans_ci=sans_ci):
            _logger.info(
                "merge_refuse",
                extra={"pr": pr_number, "ci": ci, "projet": str(self._project_path)},
            )
            return False

        await self._github.merge_pull_request(pr_number)
        _logger.info("merge_effectue", extra={"pr": pr_number, "ci": ci})
        return True


#: Les hébergeurs reconnus, pour nommer celui qu'on a devant soi.
_FORGES = {
    "github.com": "GitHub",
    "dev.azure.com": "Azure DevOps",
    "bitbucket.org": None,  # nommé par son hôte, faute de mieux
}


def _forge_depuis_hote(host: str) -> str | None:
    """The readable name of a forge from its lowercased hostname."""
    host = host.lower()
    for cle, nom in _FORGES.items():
        if host == cle or host.endswith("." + cle):
            return nom or host
    if "gitlab" in host:
        return "GitLab"
    return host or None


def parse_remote(raw: str | None) -> tuple[str | None, str | None]:
    """Parse any remote form into (forge_name, 'owner/repo').

    Accepted forms:
    - 'owner/repo'                              → GitHub assumed
    - 'https://github.com/owner/repo'
    - 'https://github.com/owner/repo.git'
    - 'git@github.com:owner/repo.git'

    Returns (None, None) when the input is empty or unrecognisable.
    The raw value in agents.json is never rewritten (ADR-036 pattern).
    """
    if not raw:
        return None, None

    raw = raw.strip()

    # SSH form: git@host:owner/repo[.git]
    if raw.startswith("git@") and ":" in raw:
        after_at = raw[4:]  # drop 'git@'
        host, _, path = after_at.partition(":")
        slug = path.removesuffix(".git")
        return _forge_depuis_hote(host), slug

    # HTTPS form: https://[user@]host/owner/repo[.git]
    if "://" in raw:
        sans_schema = raw.split("://", 1)[1]
        host_part, sep, rest = sans_schema.partition("/")
        if not sep:
            return None, None
        host = host_part.split("@")[-1]
        slug = rest.removesuffix(".git")
        return _forge_depuis_hote(host), slug

    # Short form: owner/repo (no scheme, no host → GitHub assumed)
    if "/" in raw:
        return "GitHub", raw

    return None, None


def nom_de_la_forge(remote: str | None) -> str | None:
    """Le nom lisible de l'hébergeur d'un dépôt, ou son hôte à défaut.

    Dire « ce dépôt n'est pas sur GitHub » sans dire où il est n'aide personne
    à décider quoi faire.
    """
    if not remote:
        return None
    # Deux formes coexistent : `https://[identifiant@]hote/chemin` et
    # `git@hote:chemin`. Retirer le schéma d'abord, sinon « https » passe pour
    # l'hôte.
    sans_schema = remote.split("://", 1)[-1]
    hote = sans_schema.split("/")[0].split("@")[-1].split(":")[0].lower()
    return _forge_depuis_hote(hote)


def forge_supportee(remote: str | None) -> bool:
    """True si l'IDE sait ouvrir une pull request sur ce dépôt.

    Seul GitHub l'est : `GitHubService` tape sur `api.github.com`. Ailleurs, le
    bouton poussait la branche **puis** échouait sur l'appel d'API — donc il
    poussait sans rien demander. Sur le dépôt d'un client, pousser est
    précisément la décision qui ne se prend pas par mégarde (ticket-081).
    """
    return nom_de_la_forge(remote) == "GitHub"
