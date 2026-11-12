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
from pathlib import Path
from typing import Any, Protocol

import httpx

from tessera.config import settings
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.gardes.secrets_diff import refus_secrets
from tessera.services.gardes.termes_interdits import CommitInfo, TermesInterditsChecker, TermesInterditsService
from tessera.services.github.github_service import MergeabiliteTimeoutError, PRNonFusionnableError, PrOuverte
from tessera.services.github.sync_map import SyncMapService
from tessera.services.projets.autonomie import NiveauAutonomie, lire_niveau, niveau_peut_merger
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

    async def find_open_pull_request(self, branch: str) -> int | None: ...

    async def find_merged_pull_request(
        self, prefix: str, base: str | None = None
    ) -> int | None: ...

    async def find_open_pull_requests(self, base: str) -> list[PrOuverte]: ...

    async def get_pull_request_state(self, pr_number: int) -> str: ...

    async def get_pull_request_head_sha(self, pr_number: int) -> str: ...

    async def has_workflows(self) -> bool: ...

    async def merge_pull_request(
        self,
        pr_number: int,
        method: str = "squash",
        commit_title: str | None = None,
    ) -> None: ...

    async def merge_quand_fusionnable(
        self,
        pr_number: int,
        method: str = "squash",
        commit_title: str | None = None,
        attente_fusionnabilite_max_s: float = 300.0,
        *,
        sha: str | None = None,
    ) -> None: ...


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

    # La preuve réelle se lit dans la PR : l'humain la constate avant de
    # merger (ticket-949).
    # Les trois sections sont recopiées telles quelles, dans cet ordre.
    for titre in ("Objectif", "Critères d'acceptation", "Preuve réelle"):
        texte = _section(ticket_body, titre)
        if texte:
            parts.append(f"## {titre}\n\n{texte}")

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
        git_workspace: _GitWorkspace | None,
        github: _GitHub | None,
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
        # Code HTTP du dernier refus de lecture de la CI (ticket-449) : la
        # livraison le cite quand l'état vaut `unreadable`.
        self.code_http_ci: int | None = None

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
        ticket_type: str = "",
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
        diff = await self._git.diff_de_branche(self._base_branch, branch)
        if refus := refus_secrets(diff):
            raise WorkflowError(refus)

        await self._git.push_branch(branch)

        pr_title = (
            f"{ticket_type}: {ticket_id} — {ticket_title}"
            if ticket_type
            else f"{ticket_id} — {ticket_title}"
        )
        pr_number, pr_url = await self._github.create_pull_request(
            title=pr_title,
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
        lignes_ajoutees = [ln for ln in diff.splitlines() if ln.startswith("+")]
        commits = await self._git.commits_depuis_base(self._base_branch, branch)
        violations = self._termes.verifier(lignes_ajoutees=lignes_ajoutees, commits=commits)
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
        """L'état agrégé de la CI de la PR : passing, failing, pending, none,
        unreadable (le jeton ne peut pas la lire, code dans `code_http_ci`),
        conflicting (la PR est en conflit avec sa base, ticket-452).

        `conflicting` prime sur tout état de CI : une PR qu'on ne peut pas
        fusionner n'a plus rien à attendre. Seul `dirty` le déclenche ;
        `unknown` (calcul en cours côté GitHub) ne change rien.

        Sans GitHub configuré, `none` : aucune CI n'est observable, et
        l'absence de signal n'est pas un signal favorable.
        """
        if self._github is None:
            return "none"
        statut = await self._github.get_pull_request_status(pr_number)
        code = getattr(statut, "ci_http_status", None)
        self.code_http_ci = code if isinstance(code, int) else None
        if getattr(statut, "mergeable_state", None) == "dirty":
            return "conflicting"
        return str(getattr(statut, "ci_status", "none"))

    async def pr_ouverte_de(self, branch: str) -> int | None:
        """Le numéro de la PR ouverte portée par `branch`, ou `None` (ticket-455).

        Sans GitHub configuré, `None` : il n'y a rien à retrouver.
        """
        if self._github is None:
            return None
        return await self._github.find_open_pull_request(branch)

    async def prs_ouvertes(self) -> list[PrOuverte]:
        """Les PR ouvertes vers la base du projet (ticket-516).

        Sans GitHub configuré, aucune : il n'y a rien à retrouver.
        """
        if self._github is None:
            return []
        return await self._github.find_open_pull_requests(self._base_branch)

    @property
    def base_branch(self) -> str:
        """La branche de base des PR de ce projet."""
        return self._base_branch

    async def pr_mergee_de_branche(self, prefix: str) -> int | None:
        """Le numéro d'une PR mergée dans la base depuis `prefix…`, ou `None` (ticket-482).

        Sans GitHub configuré, `None` : il n'y a rien à retrouver.
        """
        if self._github is None:
            return None
        return await self._github.find_merged_pull_request(
            prefix, self._base_branch
        )

    async def has_workflows(self) -> bool:
        """Le dépôt déclare-t-il au moins un workflow ? Sans GitHub : non."""
        if self._github is None:
            return False
        return await self._github.has_workflows()

    async def pr_state(self, pr_number: int) -> str:
        """L'état de la PR (open, closed, merged), ou `unknown` sans GitHub."""
        if self._github is None:
            return "unknown"
        return str(await self._github.get_pull_request_state(pr_number))

    async def tete_pr(self, pr_number: int) -> str | None:
        """Le SHA de tête de la PR, ou `None` sans GitHub (ticket-492)."""
        if self._github is None:
            return None
        return await self._github.get_pull_request_head_sha(pr_number)

    async def merge_si_la_ci_est_verte(
        self, pr_number: int, sha_attendu: str | None = None
    ) -> bool:
        """Merge la PR **si** le projet l'autorise et **si** la CI est verte.

        Avec `sha_attendu`, le merge est lié à ce commit : GitHub le refuse si
        la tête de la PR a bougé entre-temps (ticket-492).

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

        # La méthode de merge vient de la politique figée avant le premier
        # agent (ticket-265). Sans politique — geste manuel depuis l'IDE —,
        # on revient au défaut système : squash.
        merge_method = "squash"
        if self._politique is not None:
            merge_method = self._politique.merge_method
        # `sha` ne part que s'il est demandé : sans lui, l'appel reste celui d'avant.
        lie_au_sha: dict[str, str] = {} if sha_attendu is None else {"sha": sha_attendu}
        try:
            await self._github.merge_quand_fusionnable(
                pr_number,
                method=merge_method,
                attente_fusionnabilite_max_s=settings.attente_fusionnabilite_max_s,
                **lie_au_sha,
            )
        except (MergeabiliteTimeoutError, PRNonFusionnableError) as exc:
            _logger.warning(
                "merge_fusionnabilite_refusee",
                extra={"pr": pr_number, "raison": str(exc)},
            )
            return False
        except httpx.HTTPStatusError as exc:
            _logger.warning(
                "merge_http_erreur",
                extra={"pr": pr_number, "status": exc.response.status_code},
            )
            return False
        _logger.info(
            "merge_effectue",
            extra={"pr": pr_number, "ci": ci, "methode": merge_method},
        )
        return True
