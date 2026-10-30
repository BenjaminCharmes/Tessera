"""La liste blanche des lectures git et gh — ticket-705, ADR-067.

Une liste noire de sous-commandes laisse passer tout ce qu'on n'a pas pensé à
nommer : `git bisect run` et `git -c core.fsmonitor=…` exécutent une commande,
`git credential fill` livre un secret, `gh --repo o/r pr merge` cache sa
sous-commande derrière la valeur d'une option. Ici, ce qui n'est pas nommé
comme une lecture est refusé.

Ce module décide pour un `git …` ou un `gh …` déjà isolé et déballé par
`git_guard.py` ; il reçoit les arguments qui suivent le nom de la commande.
"""

#: Les sous-commandes git qui ne font que lire le dépôt. `branch` n'y est pas :
#: elle crée et supprime des branches.
GIT_LECTURES = frozenset({
    "status", "diff", "log", "show", "rev-parse", "ls-files", "blame", "grep",
    "describe", "cat-file", "merge-base", "shortlog", "for-each-ref", "ls-tree",
})

#: Options globales de git qui prennent la valeur dans le jeton suivant.
_OPTIONS_GIT_AVEC_VALEUR = frozenset({"-C", "--git-dir", "--work-tree"})

#: Options globales qui font exécuter ou injecter autre chose que la lecture.
_OPTIONS_GIT_DANGEREUSES = frozenset({"--exec-path", "--config-env"})

#: Options globales de gh qui prennent la valeur dans le jeton suivant.
_OPTIONS_GH_AVEC_VALEUR = frozenset({"-R", "--repo", "--hostname"})


def _reglage_cosmetique(reglage: str) -> bool:
    """`color.*` et `core.quotepath` changent l'affichage, rien d'autre."""
    cle = reglage.split("=", 1)[0].strip().lower()
    return cle.startswith("color.") or cle == "core.quotepath"


def _avance_option_git(arguments: list[str], i: int) -> int | None:
    """Combien de jetons occupe l'option globale en `i`, 0 si c'est la
    sous-commande, `None` si l'option est refusée (`-c` non cosmétique)."""
    jeton = arguments[i]
    valeur = arguments[i + 1] if i + 1 < len(arguments) else ""
    if jeton == "-c":
        return 2 if _reglage_cosmetique(valeur) else None
    if jeton.startswith("-c"):
        return 1 if _reglage_cosmetique(jeton[2:]) else None
    if jeton.split("=", 1)[0] in _OPTIONS_GIT_DANGEREUSES:
        return None
    if jeton in _OPTIONS_GIT_AVEC_VALEUR:
        return 2
    return 1 if jeton.startswith("-") else 0


def _option_qui_ecrit(sous: str, reste: list[str]) -> bool:
    """`--output` (et ses abréviations) écrit un fichier ; `grep -O` lance un
    pager choisi par l'appelant."""
    for jeton in reste:
        if jeton == "--":
            return False
        nom = jeton.split("=", 1)[0]
        if nom.startswith("--output") or (len(nom) >= 3 and "--output".startswith(nom)):
            return True
        if sous == "grep" and (jeton.startswith("-O") or nom == "--open-files-in-pager"):
            return True
    return False


def git_interdit(arguments: list[str]) -> bool:
    """True si ces arguments de `git` ne sont pas une lecture nommée."""
    i = 0
    while i < len(arguments):
        pas = _avance_option_git(arguments, i)
        if pas is None:
            return True
        if pas == 0:
            sous = arguments[i].lower()
            return sous not in GIT_LECTURES or _option_qui_ecrit(sous, arguments[i + 1:])
        i += pas
    return False


def _positionnels_gh(arguments: list[str]) -> list[str]:
    """Les arguments de `gh` à partir de la sous-commande, options globales
    (`--repo o/r`, `-R o/r`, `--hostname h`) sautées avec leur valeur."""
    i = 0
    while i < len(arguments):
        if arguments[i] in _OPTIONS_GH_AVEC_VALEUR:
            i += 2
        elif arguments[i].startswith("-"):
            i += 1
        else:
            return arguments[i:]
    return []


def _auth_status_sans_jeton(reste: list[str]) -> bool:
    """`gh auth status` seul : `--show-token` (`-t`) affiche le jeton."""
    for jeton in reste:
        court = jeton.startswith("-") and not jeton.startswith("--") and "t" in jeton[1:]
        if court or jeton.split("=", 1)[0] == "--show-token":
            return False
    return [j for j in reste if not j.startswith("-")] == ["status"]


def gh_interdit(arguments: list[str]) -> bool:
    """True si ces arguments de `gh` ne sont pas `auth status`."""
    positionnels = _positionnels_gh(arguments)
    if not positionnels:
        return False
    if positionnels[0].lower() != "auth":
        return True
    return not _auth_status_sans_jeton(positionnels[1:])
