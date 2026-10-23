"""Relire ce qu'un run a produit, sans quitter l'IDE — ticket-069.

Le pipeline relit le diff git réel depuis ADR-018, et `GitWorkspaceService`
sait déjà le produire — mais rien ne l'exposait. Pour juger un run, il fallait
donc ouvrir VSCode et taper `git diff`, ce qui vide le cockpit d'une bonne part
de son intérêt : on y pilote la flotte sans pouvoir regarder ce qu'elle a fait.

`current_diff()` ne convient pas ici : elle compare l'arbre de travail à `HEAD`,
or un run se termine toujours par un commit et laisse l'arbre propre. Ce qu'on
veut relire, c'est **la branche du ticket contre sa base**.
"""
import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Ce que l'orchestrateur réécrit lui-même — statut des tickets, journal de
#: pipeline. Ce n'est pas le travail du codeur, et le montrer noierait le diff
#: réel sous de la tenue de livres.
_CHEMINS_ARTEFACTS = ("tickets/", "memory/", "agents.json")
_ARTEFACTS = tuple(f":(exclude){c}" for c in _CHEMINS_ARTEFACTS)

#: Ce que la documentation du dépôt contient : le commit de documentation d'un
#: run précédent est dans le diff du ticket, et l'agent le relirait comme du code.
_DOCUMENTATION = (":(exclude)README.md", ":(exclude)docs/")


class TicketDiff(BaseModel):
    """Le diff d'un ticket, et de quoi l'afficher sans le relire."""

    ticket_id: str
    branch: str | None = None
    #: Le commit retrouvé quand la branche n'existe plus (ticket-116).
    #: Supprimer la branche après le merge est la pratique normale ; sans ce
    #: repli, le diff disparaissait pour tout ticket proprement terminé.
    commit: str | None = None
    diff: str = ""
    files: list[str] = Field(default_factory=list)


async def _git(cwd: Path, *args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", "-c", "core.quotepath=false", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", errors="replace")


def _prefixe_du_projet(project_path: Path, racine: Path) -> str:
    """Le chemin du projet sous la racine du dépôt, avec `/` final ; vide à la racine."""
    try:
        relatif = project_path.resolve().relative_to(racine.resolve())
    except ValueError:
        return ""
    return "" if not relatif.parts else relatif.as_posix() + "/"


def _pathspec(prefixe: str, hors_documentation: bool) -> list[str]:
    """`--`, la portée, puis les exclusions préfixées du chemin du projet.

    Les artefacts sont ceux **du projet** : un `tickets/` ailleurs dans le
    dépôt est du code. `README.md` et `docs/` sont ceux de la racine.
    """
    exclusions = [f":(exclude){prefixe}{c}" for c in _CHEMINS_ARTEFACTS]
    if hors_documentation:
        exclusions.extend(_DOCUMENTATION)
    return ["--", ".", *exclusions]


async def _branche_du_ticket(racine: Path, ticket_id: str) -> str | None:
    code, sortie = await _git(
        racine, "branch", "--list", f"{ticket_id}-*", "--format=%(refname:short)"
    )
    if code != 0:
        return None
    branches = [ligne.strip() for ligne in sortie.splitlines() if ligne.strip()]
    return branches[0] if branches else None


async def _reference(racine: Path, branche: str, base: str | None) -> str:
    """Ce contre quoi la branche se compare.

    Une base explicite l'emporte (locale, sinon `origin/`). Sans elle, la
    branche courante si ce n'est pas celle du ticket, sinon `main` — ce qui,
    pour le ticket d'un run encore sur sa branche et un projet dont la base
    est `develop`, ferait entrer dans le diff tout ce que `develop` a de plus.
    """
    for candidate in (base, f"origin/{base}") if base else ():
        code, _ = await _git(racine, "rev-parse", "--verify", "--quiet", candidate)
        if code == 0:
            return candidate
    code, courante = await _git(racine, "symbolic-ref", "--short", "HEAD")
    return courante.strip() if code == 0 and courante.strip() != branche else "main"


async def _lire(
    racine: Path, verbe: str, args: list[str], specs: list[str]
) -> tuple[int, str, list[str]]:
    """Le diff d'une commande git, et les noms de fichiers qu'elle touche."""
    code, diff = await _git(racine, verbe, *args, *specs)
    if code != 0:
        return code, "", []
    code, noms = await _git(racine, verbe, "--name-only", *args, *specs)
    fichiers = [n.strip() for n in noms.splitlines() if n.strip()] if code == 0 else []
    return 0, diff.strip(), fichiers


async def diff_du_ticket(
    project_path: Path,
    ticket_id: str,
    *,
    base: str | None = None,
    depot: Path | None = None,
    hors_documentation: bool = False,
) -> TicketDiff:
    """Le diff de la branche du ticket contre le point où elle a divergé.

    `base...branche` — trois points — compare à l'ancêtre commun, pas à la
    pointe de la base : sans cela, tout ce qui a avancé sur la base depuis la
    création de la branche apparaîtrait comme retiré par le ticket.

    Par défaut le diff se prend dans le dossier du projet. `depot` est la
    racine du dépôt (`git_root: ancestor`) : le diff couvre alors tout le
    dépôt, et les artefacts exclus restent ceux du projet. `base` est la
    branche de base déclarée ; `hors_documentation` retire `README.md` et
    `docs/`.
    """
    racine = depot or project_path
    specs = _pathspec(_prefixe_du_projet(project_path, racine), hors_documentation)
    branche = await _branche_du_ticket(racine, ticket_id)
    if branche is None:
        return await _diff_par_commit(racine, ticket_id, specs)

    reference = await _reference(racine, branche, base)
    code, diff, fichiers = await _lire(racine, "diff", [f"{reference}...{branche}"], specs)
    if code != 0:
        _logger.warning("diff_indisponible", extra={"ticket": ticket_id})
        return TicketDiff(ticket_id=ticket_id, branch=branche)
    return TicketDiff(ticket_id=ticket_id, branch=branche, diff=diff, files=fichiers)


async def _diff_par_commit(
    racine: Path, ticket_id: str, specs: list[str]
) -> TicketDiff:
    """Le diff retrouvé par le message de commit, faute de branche.

    Supprimer la branche après le merge est la pratique normale — c'est ce que
    fait `gh pr merge --delete-branch`. Chercher uniquement `git branch --list`
    faisait donc disparaître le diff de **tout ticket proprement terminé**, et
    l'écran annonçait « jamais lancé », ce qui était faux (ticket-116).

    Les messages portent tous l'identifiant du ticket — `CLAUDE.md` l'impose et
    le pipeline l'applique — y compris après un squash.

    Plusieurs commits peuvent le mentionner : celui du travail, puis celui de
    clôture. Le second ne touche que `tickets/`, que `_ARTEFACTS` exclut déjà,
    donc son diff est **vide** une fois filtré. On descend du plus récent au
    plus ancien et on rend le premier diff non vide.
    """
    code, sortie = await _git(
        racine, "log", "--all", f"--grep={ticket_id}", "--format=%H", "-n", "20"
    )
    if code != 0:
        return TicketDiff(ticket_id=ticket_id)

    for sha in (l.strip() for l in sortie.splitlines() if l.strip()):
        code, diff, fichiers = await _lire(racine, "show", [sha, "--format="], specs)
        if code == 0 and diff:
            return TicketDiff(
                ticket_id=ticket_id, commit=sha[:12], diff=diff, files=fichiers
            )

    return TicketDiff(ticket_id=ticket_id)
