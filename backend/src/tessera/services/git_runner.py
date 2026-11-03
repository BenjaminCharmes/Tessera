"""The one git command runner of the backend services — ticket-677.

Sept modules lançaient chacun leur `git`, avec trois types de retour et, pour
quatre d'entre eux, sans neutraliser les hooks : un `pre-commit` ou un
`post-checkout` déposé dans `.git/hooks/` pendant un run s'exécutait alors sous
l'identité du backend (ADR-027). Un seul exécuteur, un seul résultat.

Les hooks sont neutralisés pour toute commande qui n'est pas une lecture connue
(`-c core.hooksPath=<dossier vide>`, qui prime sur `.git/config`). Le choix se
fait sur une liste blanche de lectures : une sous-commande inconnue est traitée
comme une écriture. Les lectures ne paient donc pas la création du dossier vide.
"""
import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

#: Sous-commandes qui ne déclenchent aucun hook et ne modifient rien. Tout ce qui
#: n'y figure pas — checkout, pull, commit, merge, rebase, worktree, branch… —
#: passe hooks neutralisés.
_READS = frozenset({
    "diff", "status", "rev-parse", "log", "show", "ls-files", "ls-tree",
    "cat-file", "check-ignore", "rev-list", "merge-base", "symbolic-ref",
    "for-each-ref", "describe",
})

#: Options placées avant la sous-commande, dont la valeur est l'argument suivant.
_OPTIONS_WITH_VALUE = frozenset({"-c", "-C", "--git-dir", "--work-tree", "--namespace"})


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


@dataclass(frozen=True)
class GitResult:
    """What a git command returned: exit code, decoded stdout, decoded stderr."""

    code: int
    out: str
    err: str
    command: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.code == 0


def _subcommand(args: tuple[str, ...]) -> str | None:
    """The git subcommand in `args`, global options skipped; None when absent."""
    suivants = iter(args)
    for arg in suivants:
        if arg in _OPTIONS_WITH_VALUE:
            next(suivants, None)
        elif not arg.startswith("-"):
            return arg
    return None


def writes(args: tuple[str, ...]) -> bool:
    """True unless the command is a known read (fail closed)."""
    return _subcommand(args) not in _READS


def build_command(args: tuple[str, ...]) -> list[str]:
    """The full argv: cosmetic options always, hooks disabled for a write."""
    options = ["-c", "core.quotePath=false", "-c", "core.longpaths=true"]
    if writes(args):
        options = ["-c", f"core.hooksPath={_dossier_sans_hooks()}", *options]
    return ["git", *options, *args]


async def git(cwd: Path, *args: str) -> GitResult:
    """Run git in `cwd`; never raises on a non-zero exit, the caller reads `code`."""
    command = build_command(args)
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return GitResult(
        code=proc.returncode or 0,
        out=out.decode("utf-8", errors="replace"),
        err=err.decode("utf-8", errors="replace"),
        command=tuple(command),
    )

