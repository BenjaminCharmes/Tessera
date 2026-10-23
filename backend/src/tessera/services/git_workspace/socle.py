"""Shared state, command runner and repository identity checks."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.services.git_workspace.erreurs import GitCommandError, NotAGitRepository

if TYPE_CHECKING:
    from tessera.services.politique_run import PolitiqueRun
    from tessera.services.worktree_dossiers import DossiersWorktree


def _dossier_sans_hooks() -> Path:
    """Un dossier vide, hors de tout projet, à donner comme `core.hooksPath`.

    Un chemin inexistant ferait aussi l'affaire pour git, mais un dossier qui
    existe et qu'on contrôle ne laisse aucune place à l'interprétation. Créé à
    la demande : `tempfile.gettempdir()` n'est pas connu au chargement du
    module sur toutes les plateformes.
    """
    dossier = Path(tempfile.gettempdir()) / "tessera-sans-hooks"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


class GitCore:
    """Shared state, command runner and repository identity checks."""

    def __init__(
        self,
        project_path: Path,
        politique: "PolitiqueRun | None" = None,
        worktree: "DossiersWorktree | None" = None,
    ) -> None:
        self._project_path = project_path
        # Le worktree du run (ADR-056) : `project_path` est alors le dossier du
        # projet *dans* ce worktree, et ADR-024 se vérifie contre lui.
        self._worktree = worktree
        # `git_root` décide d'où l'on stage (`.` ou `:/`). Figé par
        # l'orchestrateur avant le premier agent : lu au moment de committer,
        # il obéirait à ce qu'un codeur aurait écrit dans `agents.json` pendant
        # le run (ticket-119). Sans politique — chat, endpoints — on lit le
        # fichier, comme avant.
        self._politique = politique
        # The ref checked out the first time this service touches the repo.
        # Every subsequent ticket branch forks from this ref, never from the
        # previously created ticket branch — otherwise ticket N would carry
        # ticket N-1's commits (isolation-by-branch relies on this).
        self._base_ref: str | None = None
        # Pourquoi la dernière tentative du résolveur a échoué (ticket-453).
        # `rejouer_sur` rend seulement les fichiers en conflit : sans ceci, un
        # résolveur tenté et en échec produit le même arrêt qu'un résolveur
        # jamais appelé.
        self.raison_resolveur: str | None = None
        # Migrations Prisma renumérotées par le dernier `rejouer_sur`, en
        # (ancien chemin, nouveau chemin) — `Livraison` les met au journal
        # sans que la signature de `rejouer_sur` change (ticket-484).
        self.migrations_renumerotees: tuple[tuple[str, str], ...] = ()
        # Untracked files already sitting in the tree when the run started.
        # They were not produced by the coder, so `commit_all`'s blanket
        # `git add -A` must not sweep them into the ticket's commit (that is
        # the counterpart of `is_clean` ignoring untracked files: both ends
        # agree on what "not ours" means).
        self._preexisting_untracked: tuple[str, ...] = ()
        # Basenames of tracked ticket files at run start (ticket-343).
        # Set by `create_branch`; `None` means it was not called yet.
        # `commit_bookkeeping` uses this to decide whether an untracked file
        # under `tickets/` is a status-folder move (basename was tracked → stage)
        # or a freshly created ticket (→ leave untracked).
        # When None, falls back to the original behaviour: stage every
        # untracked ticket file that is not pre-existing (ticket-314 scenario
        # where bookkeeping is committed before the branch switch).
        self._tracked_ticket_basenames: frozenset[str] | None = None
        # The commit from which the current ticket branch diverged from its
        # base. On a fresh branch this equals `_base_ref`; on a resumed branch
        # it is the merge-base of the branch and `_base_ref` (ticket-208). Used by `diff_depuis_base` to include all prior
        # commits on the branch, not only the uncommitted work of the current
        # turn.
        self._fork_point: str | None = None
        # Commits que la branche reprise porte au-delà de `_fork_point`
        # (ticket-497). 0 sur une branche neuve : le pipeline s'en sert pour
        # décider de vérifier le travail existant avant de rappeler le codeur.
        self.commits_repris: int = 0

    async def _has_head(self) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--verify", "--quiet", "HEAD",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _branch_exists(self, branch_name: str) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch_name}",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    def _travaille_dans_le_parent(self) -> bool:
        """True si le projet déclare travailler dans le dépôt qui le contient.

        ADR-024 refuse par défaut qu'un projet agisse sur un dépôt ancêtre :
        un dossier client posé dans `projects/` faisait sinon remonter git
        jusqu'à celui de Tessera, où le run créait sa branche et son commit.

        Mais c'est exactement ce que fait le projet bootstrap d'ADR-001 : il
        construit l'IDE, donc il travaille **volontairement** dans le dépôt qui
        le contient. L'exception se déclare donc, fichier par fichier, comme le
        mode des artefacts — le défaut protège, le cas particulier s'énonce
        (ticket-081).
        """
        if self._politique is not None:
            return self._politique.dans_le_depot_parent
        agents_json = self._project_path / "agents.json"
        if not agents_json.is_file():
            return False
        try:
            data = json.loads(agents_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        return bool(data.get("git_root") == "ancestor")

    async def _is_own_repository(self) -> bool:
        """True only if the project directory is itself the root of a repository.

        `--is-inside-work-tree` is not enough, and the difference is what let
        this class break its own promise never to touch Tessera. A project
        folder with no repository of its own makes git walk *up* the tree; in
        `projects/<client>/`, the repository it finds is Tessera's own. Every
        subsequent command then succeeds — against the wrong repository.

        Comparing the toplevel to the project path is the check that holds.
        Locale-independent: it reads a path, never stderr text.
        """
        if self._worktree is not None:
            return await self._is_declared_worktree()
        if self._travaille_dans_le_parent():
            return await self._is_inside_any_work_tree()

        toplevel = await self._toplevel()
        if toplevel is None:
            return False
        return toplevel == self._project_path.resolve()

    async def _toplevel(self) -> Path | None:
        """The resolved `--show-toplevel` of the project folder, `None` if git fails."""
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--show-toplevel",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        texte = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 or not texte:
            return None
        try:
            return Path(texte).resolve()
        except OSError:
            return None

    async def _is_declared_worktree(self) -> bool:
        """True only for the run's own linked worktree (ADR-056, ticket-525).

        Dans un worktree, `--show-toplevel` renvoie la racine du worktree : le
        contrôle d'ADR-024 y vaut sans `git_root: ancestor`. Trois choses
        doivent tenir : le dossier du projet est celui du worktree déclaré, git
        y voit la racine déclarée, et cette racine est un worktree *lié* — son
        `.git` est un fichier. Un dépôt étranger a un dossier `.git` : refusé.
        """
        wt = self._worktree
        if wt is None:
            return False
        try:
            if self._project_path.resolve() != wt.projet.resolve():
                return False
            if not (wt.racine / ".git").is_file():
                return False
        except OSError:
            return False
        return await self._toplevel() == wt.racine.resolve()

    async def _is_inside_any_work_tree(self) -> bool:
        """True si un dépôt existe, ici ou au-dessus — pour le cas déclaré."""
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--is-inside-work-tree",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _ensure_own_repository(self) -> None:
        """Refuse to act at all when the project has no repository of its own."""
        if await self._is_own_repository():
            return
        raise NotAGitRepository(
            command=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stderr=(
                f"{self._project_path} n'est pas la racine d'un dépôt git. "
                "Tessera refuse d'agir sur le dépôt parent : un projet qui "
                "contient plusieurs dépôts doit être déclaré par sous-dossier."
            ),
        )

    async def _run(self, *args: str) -> str:
        # Les hooks du dépôt ne tournent jamais depuis l'orchestrateur. Ils
        # vivent sous la racine du projet, donc à portée d'un agent : un
        # `pre-commit` déposé pendant le run s'exécutait au commit de fin de
        # run, sous l'identité de l'utilisateur, sans qu'une seule commande
        # git ait transité par `Bash` (ticket-119). Le hook de périmètre
        # refuse désormais `.git/`, mais un fichier arrivé par un autre chemin
        # — `python -c`, un clone déjà piégé — ne doit pas tourner non plus.
        # `-c` prime sur `.git/config`, donc sur un `core.hooksPath` qu'un
        # agent y aurait écrit.
        command = [
            "git",
            "-c", f"core.hooksPath={_dossier_sans_hooks()}",
            "-c", "core.quotePath=false",
            # Chemins longs de Windows : un worktree de run vit sous un dossier profond.
            "-c", "core.longpaths=true",
            *args,
        ]
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            # `communicate()` has awaited the process, so returncode is set;
            # the `or 0` is only there to satisfy its `int | None` type.
            returncode = proc.returncode or 0
            if not await self._is_own_repository():
                raise NotAGitRepository(
                    command=command, returncode=returncode, stderr=stderr_text
                )
            raise GitCommandError(
                command=command, returncode=returncode, stderr=stderr_text
            )
        return stdout_text
