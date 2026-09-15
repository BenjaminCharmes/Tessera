"""Attacher un dépôt git et un remote GitHub à un projet — ticket-061.

Trois des quatre façons d'obtenir un projet donnent un dépôt utilisable. Deux
n'en donnent aucun : une création de zéro, et un import en mode `copy`, qui
exclut `.git` de la copie.

Sans dépôt, `GitWorkspaceService` échoue : aucune branche n'est créée et
**aucun commit n'est fait**. Le travail de l'agent reste dans l'arbre, sans
trace — tout l'apport d'ADR-018 disparaît, silencieusement.

Ce module ne fait rien de destructif : il n'initialise que si `.git` est
absent, et ne remplace jamais un remote existant sans confirmation.
"""
import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

# Une URL de dépôt git plausible : https, ssh, ou git@. On refuse le reste
# plutôt que de laisser `git remote add` accepter n'importe quelle chaîne.
_REPO_URL = re.compile(
    r"^(https?://[\w.\-]+/[\w.\-]+/[\w.\-]+(\.git)?/?"
    r"|git@[\w.\-]+:[\w.\-]+/[\w.\-]+(\.git)?"
    r"|ssh://git@[\w.\-]+/[\w.\-]+/[\w.\-]+(\.git)?)$"
)

_INITIAL_COMMIT_MESSAGE = "chore: initial commit"


class GitLinkError(Exception):
    """Une opération de liaison git a été refusée."""


class RemoteNotEmpty(GitLinkError):
    """Le dépôt distant a déjà un historique ; la liaison doit être confirmée."""

    def __init__(self, repo_url: str) -> None:
        self.repo_url = repo_url
        super().__init__(
            f"Le dépôt '{repo_url}' n'est pas vide. Attacher un projet local à "
            "un dépôt qui a déjà un historique produit des conflits au premier "
            "push : confirme si c'est bien ce que tu veux."
        )


@dataclass(frozen=True)
class GitStatus:
    """Ce que l'IDE a besoin de savoir de l'état git d'un projet.

    `is_own_repository` est la seule question qui compte pour le pipeline :
    un projet peut se trouver *dans* un dépôt sans en avoir un. C'est le cas
    de `projects/ide-core`, qui vit dans le dépôt de vibe-ide. Git y répond
    « oui, dépôt » en remontant au parent — et le pipeline commiterait alors
    dans le dépôt englobant, pas dans le projet.
    """

    is_own_repository: bool
    has_commits: bool = False
    remote_url: str | None = None
    # Chemin du dépôt englobant, quand le projet n'a pas le sien.
    is_nested_in: str | None = None

    @property
    def is_repository(self) -> bool:
        """Compatibilité : un projet imbriqué n'est pas un dépôt utilisable."""
        return self.is_own_repository


async def _run(cwd: Path, *args: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return (
        proc.returncode or 0,
        out.decode("utf-8", errors="replace"),
        err.decode("utf-8", errors="replace"),
    )


async def git_status(project_path: Path) -> GitStatus:
    """Décrit l'état git d'un projet, sans jamais le modifier."""
    code, out, _ = await _run(project_path, "rev-parse", "--show-toplevel")
    if code != 0 or not out.strip():
        return GitStatus(is_own_repository=False)

    toplevel = Path(out.strip()).resolve()
    if toplevel != project_path.resolve():
        # Le projet est dans un dépôt, mais ce n'est pas le sien : tout ce que
        # git rapporte ici décrit le dépôt englobant.
        return GitStatus(is_own_repository=False, is_nested_in=str(toplevel))

    has_commits = (await _run(project_path, "rev-parse", "--verify", "HEAD"))[0] == 0

    code, out, _ = await _run(project_path, "remote", "get-url", "origin")
    remote = out.strip() if code == 0 and out.strip() else None

    return GitStatus(is_own_repository=True, has_commits=has_commits, remote_url=remote)


async def init_repository(project_path: Path) -> GitStatus:
    """Initialise un dépôt et y commite l'état courant. Sans effet s'il existe.

    Le premier commit compte : sans lui, tout le contenu existant du projet
    apparaîtrait au pipeline comme des modifications non suivies, et finirait
    balayé dans le commit du premier ticket.
    """
    status = await git_status(project_path)
    if status.is_own_repository:
        return status

    code, _, err = await _run(project_path, "init", "-q")
    if code != 0:
        raise GitLinkError(f"Impossible d'initialiser un dépôt git : {err.strip()}")

    # Une identité locale seulement si la machine n'en a pas : on ne touche
    # pas à la configuration globale de l'utilisateur.
    if (await _run(project_path, "config", "user.email"))[0] != 0:
        await _run(project_path, "config", "user.email", "vibe-ide@localhost")
        await _run(project_path, "config", "user.name", "vibe-ide")

    await _run(project_path, "add", "-A", "--", ".")
    code, _, err = await _run(project_path, "commit", "-q", "-m", _INITIAL_COMMIT_MESSAGE)
    if code != 0 and "nothing to commit" not in err.lower():
        _logger.warning("initial_commit_failed", extra={"error": err.strip()})

    return await git_status(project_path)


async def link_remote(
    project_path: Path,
    repo_url: str,
    *,
    remote_is_empty: bool,
    confirmed: bool = False,
) -> GitStatus:
    """Attache `origin` au dépôt distant et consigne l'URL dans `agents.json`.

    `remote_is_empty` est déterminé par l'appelant, qui seul a le token pour
    interroger GitHub. `confirmed` couvre les deux cas où l'utilisateur doit
    trancher : un remote distant non vide, et un `origin` déjà configuré.
    """
    if not _REPO_URL.match(repo_url.strip()):
        raise GitLinkError(
            f"URL de dépôt invalide : '{repo_url}'. Attendu une URL https ou ssh "
            "vers un dépôt git, par exemple https://github.com/moi/mon-repo.git"
        )

    status = await git_status(project_path)
    if not status.is_own_repository:
        raise GitLinkError(
            "Ce projet n'est pas un dépôt git. Initialise-le d'abord "
            "(POST /projects/{id}/git/init)."
        )

    if status.remote_url and not confirmed:
        raise GitLinkError(
            f"Ce projet a déjà un remote 'origin' ({status.remote_url}). "
            "Confirme le remplacement si c'est bien l'intention."
        )

    if not remote_is_empty and not confirmed:
        raise RemoteNotEmpty(repo_url)

    action = "set-url" if status.remote_url else "add"
    code, _, err = await _run(project_path, "remote", action, "origin", repo_url.strip())
    if code != 0:
        raise GitLinkError(f"Impossible d'attacher le remote : {err.strip()}")

    _store_github_remote(project_path, repo_url.strip())
    return await git_status(project_path)


def _store_github_remote(project_path: Path, repo_url: str) -> None:
    """Consigne l'URL dans `agents.json`, où les endpoints PR et sync la lisent."""
    agents_json = project_path / "agents.json"
    data: dict[str, object] = {}
    if agents_json.exists():
        try:
            data = json.loads(agents_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _logger.warning("agents_json_illisible", extra={"path": str(agents_json)})
            data = {}

    agents_json.write_text(
        json.dumps({**data, "github_remote": repo_url}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
