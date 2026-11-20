"""The one git command builder of the backend — tickets 677, 941.

Toute commande git lancée par le backend, quel que soit le domaine, passe par
`build_command` : options cosmétiques, `core.fsmonitor=false` (une clé écrite
dans `.git/config` par un agent ne lance aucun programme, ticket-933) et, pour
une écriture, hooks neutralisés (ADR-027). Un test structurel refuse tout autre
lancement direct de `git` dans `src/tessera`.
"""
import tempfile
from pathlib import Path

#: Sous-commandes qui ne déclenchent aucun hook et ne modifient rien. Tout ce qui
#: n'y figure pas — checkout, pull, commit, merge, rebase, worktree, branch… —
#: passe hooks neutralisés.
_READS = frozenset({
    "diff", "status", "rev-parse", "log", "show", "ls-files", "ls-tree",
    "cat-file", "check-ignore", "rev-list", "merge-base",
    "for-each-ref", "describe",
})
# `symbolic-ref` n'y figure pas : lecture à un nom, écriture dès le second
# (voir `writes`).

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


def _subcommand(args: tuple[str, ...]) -> str | None:
    """The git subcommand in `args`, global options skipped; None when absent."""
    suivants = iter(args)
    for arg in suivants:
        if arg in _OPTIONS_WITH_VALUE:
            next(suivants, None)
        elif not arg.startswith("-"):
            return arg
    return None


def _symbolic_ref_writes(args: tuple[str, ...]) -> bool:
    """`symbolic-ref` reads with one name; a second name, -d or -m writes a ref."""
    apres = args[args.index("symbolic-ref") + 1:]
    if any(arg in ("-d", "--delete", "-m") for arg in apres):
        return True
    return sum(1 for arg in apres if not arg.startswith("-")) > 1


def writes(args: tuple[str, ...]) -> bool:
    """True unless the command is a known read (fail closed)."""
    sous_commande = _subcommand(args)
    if sous_commande == "symbolic-ref":
        return _symbolic_ref_writes(args)
    return sous_commande not in _READS


def build_command(args: tuple[str, ...]) -> list[str]:
    """The full argv: cosmetic options always, hooks disabled for a write."""
    # `core.fsmonitor=false` : une clé écrite dans `.git/config` par un agent ne
    # lance aucun programme au `git status` suivant (ticket-933).
    options = ["-c", "core.quotePath=false", "-c", "core.longpaths=true"]
    for reglage in _REGLAGES_SANS_PROGRAMME:
        options += ["-c", reglage]
    if writes(args):
        options = ["-c", f"core.hooksPath={_dossier_sans_hooks()}", *options]
    return ["git", *options, *_avec_diff_sans_programme(args)]


#: Clés qui nomment un programme : forcées à vide pour toute commande, une clé
#: écrite dans `.git/config` par un agent ne lance rien (ticket-965). Un
#: `filter.<nom>.*` ne se neutralise pas sans son nom : voir `pipeline_empreinte`.
_REGLAGES_SANS_PROGRAMME = (
    "core.fsmonitor=false", "commit.gpgsign=false", "tag.gpgSign=false",
    "gpg.program=", "core.sshCommand=", "diff.external=", "core.pager=cat",
)

#: Sous-commandes qui lisent un diff : ni programme externe ni textconv.
_SOUS_COMMANDES_DE_DIFF = frozenset({"diff", "show", "log"})


def _avec_diff_sans_programme(args: tuple[str, ...]) -> tuple[str, ...]:
    """`args` with `--no-ext-diff --no-textconv` right after a diff-reading subcommand."""
    if _subcommand(args) not in _SOUS_COMMANDES_DE_DIFF:
        return args
    suivants = iter(enumerate(args))
    for i, arg in suivants:
        if arg in _OPTIONS_WITH_VALUE:
            next(suivants, None)
        elif not arg.startswith("-"):
            return (*args[: i + 1], "--no-ext-diff", "--no-textconv", *args[i + 1:])
    return args


