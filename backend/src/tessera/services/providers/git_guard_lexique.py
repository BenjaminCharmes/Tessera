"""Lire une ligne de shell assez bien pour y trouver le git — ticket-119.

Le garde d'ADR-027 comparait le premier jeton de chaque segment à `git`.
Vérifié en exécution : `ls\\ngit push`, `env git push`, `sh -c 'git push'`,
`/usr/bin/git push`, `git.exe push` et `GIT push` passaient tous. Un garde
qu'un retour à la ligne suffit à contourner donne l'apparence d'une
protection sans en être une.

Ce module ne décide rien : il découpe, déballe les enveloppes (`env`, `sudo`,
`sh -c`…) et normalise le nom de la commande. `git_guard.py` dit ce qui est
interdit. Ce qui ne se lit pas avec certitude est rendu tel quel et passera —
un faux refus priverait l'agent de son moyen de vérifier son travail.
"""
import re
import shlex

#: Ce qui sépare deux commandes : `;`, `&&`, `||`, `|`, `&`, une fin de ligne,
#: une parenthèse ou un accent grave — `echo $(git push)` et `(git push)`
#: exécutent bien git.
_SEPARATEURS = re.compile(r"\|\||&&|[;|&\n\r`()]|\$")

#: Un shell qui reçoit une ligne complète derrière `-c` (`/c` pour `cmd`,
#: `-Command` pour PowerShell : Tessera tourne aussi sous Windows).
SHELLS = frozenset(
    {"sh", "bash", "zsh", "dash", "ksh", "busybox", "cmd", "powershell", "pwsh"}
)

#: Ce que `cmd` et PowerShell lisent derrière leur option : toute la fin du
#: segment, pas un seul jeton.
#: Sous Git Bash, `/c` est réécrit en chemin : la forme qui marche est `//c`.
_OPTIONS_CMD = frozenset({"/c", "/k", "//c", "//k"})
_OPTIONS_POWERSHELL = frozenset({"-c", "-command"})

#: PowerShell accepte toute abréviation de `-EncodedCommand` (`-e`, `-ec`,
#: `-enc`…) : la ligne est en base64, le garde ne peut pas la lire.
_ENCODED_COMMAND = "-encodedcommand"

#: Un mot de shell qui introduit une commande sans en être une : le nom lu en
#: tête de segment serait `then`, pas `git`.
MOTS_CLES = frozenset({"if", "elif", "then", "else", "while", "until", "do", "{", "!"})

#: `NOM=valeur` en tête de segment : `GIT_AUTHOR_NAME=x git commit` lance git.
_AFFECTATION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

#: Une affectation qui change le comportement de git ou de gh sans passer par
#: `-c` : `GIT_CONFIG_COUNT`, `GIT_EXTERNAL_DIFF`, `GH_*`, un pager ou un
#: éditeur, `SSH_*`. Windows ignore la casse des variables : nous aussi.
_ENV_SENSIBLE = re.compile(r"^((GIT|GH|SSH)_[A-Za-z0-9_]*|PAGER|EDITOR|VISUAL)=", re.IGNORECASE)

#: Une enveloppe qui exécute la commande qui la suit, sans la changer.
ENVELOPPES = frozenset(
    {
        "env", "command", "exec", "xargs", "time", "nohup", "timeout", "sudo", "nice",
        "doas", "setsid", "stdbuf", "flock",
    }
)

#: Les options de chaque enveloppe qui prennent leur valeur dans le jeton
#: suivant : sans cela, `env -u HOME git push` lirait `HOME` comme la commande.
#: Par enveloppe, parce qu'un même nom change de sens (`sudo -s` n'a pas de
#: valeur, `timeout -s` en a une).
_OPTIONS_A_VALEUR: dict[str, frozenset[str]] = {
    "env": frozenset({"-u", "--unset", "-C", "--chdir"}),
    "timeout": frozenset({"-s", "-k", "--signal", "--kill-after"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "xargs": frozenset({"-n", "-s", "-a", "-I", "-d", "-L", "-P", "-E"}),
    "sudo": frozenset({"-u", "-g", "-p", "-C", "-D", "-R", "-T", "-r", "-t", "-U"}),
    "doas": frozenset({"-u", "-C"}),
    "time": frozenset({"-f", "-o"}),
    "exec": frozenset({"-a"}),
    "stdbuf": frozenset({"-i", "-o", "-e"}),
    "flock": frozenset({"-w", "-E", "--timeout", "--conflict-exit-code"}),
}

#: Ce qu'une enveloppe accepte avant la commande réelle : ses options, une
#: affectation `VAR=valeur`, une durée (`timeout 30`).
_JETON_D_ENVELOPPE = re.compile(r"^(-|[A-Za-z_][A-Za-z0-9_]*=|\d+(\.\d+)?[smhd]?$)")


#: Un mot : morceaux entre guillemets et morceaux nus collés, comme le shell
#: (`'g'it` est un seul mot). Les antislashs restent, pour les chemins Windows.
_MOT = re.compile(r"""(?:'[^']*'|"[^"]*"|[^\s'"])+""")


def segments(commande: str) -> list[str]:
    """Les commandes élémentaires d'une ligne, séparateurs compris."""
    return [s.strip() for s in _SEPARATEURS.split(commande) if s and s.strip()]


def jetons(segment: str) -> list[str]:
    """Les mots d'un segment, guillemets retirés mais antislashs conservés.

    `posix=False` : en mode POSIX, `C:\\Git\\bin\\git.exe` perdrait ses
    antislashs et son nom avec. Les guillemets restent alors collés aux
    jetons ; on les retire nous-mêmes, pour que `sh -c 'git push'` rende la
    ligne `git push` intacte.
    """
    try:
        bruts = _MOT.findall(segment)
        if "".join("".join(bruts).split()) != "".join(segment.split()):
            raise ValueError("guillemet non fermé")
    except ValueError:
        bruts = segment.split()
    return [_sans_guillemets(j) for j in bruts]


def _sans_guillemets(jeton: str) -> str:
    if len(jeton) >= 2 and jeton[0] == jeton[-1] and jeton[0] in "'\"":
        return jeton[1:-1]
    return jeton


#: Les noms que les gardes (git, kill) savent juger : si une seule des deux
#: lectures d'un jeton en désigne un, c'est celle-là qui compte.
NOMS_SURVEILLES = (
    SHELLS | ENVELOPPES
    | {"eval", "git", "gh", "kill", "pkill", "killall", "taskkill", "tskill",
       "stop-process", "spps", "wmic"}
)


def _sans_extension(nom: str) -> str:
    nom = nom.lower()
    return nom[:-4] if nom.endswith(".exe") else nom


def _lecture_posix(jeton: str) -> str | None:
    """Le jeton comme bash le lit : `g''it` et `g\\it` donnent `git`."""
    try:
        mots = shlex.split(jeton, posix=True)
    except ValueError:
        return None
    if len(mots) != 1:
        return None
    return _sans_extension(mots[0].split("/")[-1])


def nom_de_commande(jeton: str) -> str:
    """`/usr/bin/git`, `C:\\...\\git.exe`, `GIT`, `g''it` → `git`.

    Deux lectures : celle d'un chemin Windows (coupé sur `\\` et `/`) et celle
    de bash (guillemets concaténés, antislash d'échappement retirés). La
    lecture surveillée l'emporte : un faux refus vaut mieux qu'un passage.
    """
    nom = _sans_extension(re.split(r"[\\/]", jeton)[-1])
    if nom in NOMS_SURVEILLES:
        return nom
    posix = _lecture_posix(jeton)
    return posix if posix in NOMS_SURVEILLES and posix is not None else nom


def sans_enveloppe(jetons_: list[str]) -> list[str]:
    """Retire une enveloppe et ce qu'elle accepte avant la commande réelle."""
    nom = nom_de_commande(jetons_[0])
    valeurs = _OPTIONS_A_VALEUR.get(nom, frozenset())
    reste = jetons_[1:]
    while reste and _JETON_D_ENVELOPPE.match(reste[0]):
        reste = reste[2:] if reste[0] in valeurs else reste[1:]
    if nom == "flock" and reste:
        reste = reste[1:]  # le fichier de verrou précède la commande
    return reste


def sans_prefixe(jetons_: list[str]) -> list[str]:
    """Retire les affectations et mots-clés qui précèdent la commande réelle."""
    debut = 0
    while debut < len(jetons_) and (
        _AFFECTATION.match(jetons_[debut]) or jetons_[debut].lower() in MOTS_CLES
    ):
        debut += 1
    return jetons_[debut:]


def affecte_environnement(avant: list[str], apres: list[str]) -> bool:
    """True si ce que `sans_prefixe` ou `sans_enveloppe` a retiré règle git.

    `avant` est la liste reçue, `apres` ce qu'il en reste : la différence est
    le préfixe (affectations, mots-clés, enveloppe et ses options) qui a été
    sauté sans être lu.
    """
    retires = avant[: len(avant) - len(apres)]
    return any(_ENV_SENSIBLE.match(jeton) for jeton in retires)


def _fin_derriere(jetons_: list[str], options: frozenset[str]) -> str | None:
    """Tout ce qui suit la première option de `options`, en une ligne."""
    for index, jeton in enumerate(jetons_[1:], start=1):
        if jeton.lower() in options:
            reste = jetons_[index + 1:]
            return " ".join(reste) if reste else None
    return None


def commande_opaque(jetons_: list[str]) -> bool:
    """True pour un `powershell -EncodedCommand` : la ligne n'est pas lisible."""
    if nom_de_commande(jetons_[0]) not in ("powershell", "pwsh"):
        return False
    return any(
        len(j) >= 2 and j.startswith("-") and _ENCODED_COMMAND.startswith(j.lower())
        for j in jetons_[1:]
    ) or any(j.lower() == "-ec" for j in jetons_[1:])


def _ligne_powershell(jetons_: list[str]) -> str | None:
    """Derrière `-Command` ; sans cette option, PowerShell lit la fin du
    segment comme une ligne de commande, options mises à part."""
    if any(j.lower() in _OPTIONS_POWERSHELL for j in jetons_[1:]):
        return _fin_derriere(jetons_, _OPTIONS_POWERSHELL)
    reste = jetons_[1:]
    while reste and reste[0].startswith("-"):
        reste = reste[1:]
    return " ".join(reste) if reste else None


def ligne_derriere_c(jetons_: list[str]) -> str | None:
    """La ligne qu'un shell exécute derrière `-c` (`-lc`, `-ec` compris).

    `cmd /c` et `powershell -Command` prennent la fin du segment, guillemets
    ou non.
    """
    nom = nom_de_commande(jetons_[0])
    if nom == "cmd":
        return _fin_derriere(jetons_, _OPTIONS_CMD)
    if nom in ("powershell", "pwsh"):
        return _ligne_powershell(jetons_)
    for index, jeton in enumerate(jetons_[1:], start=1):
        est_option_c = jeton == "-c" or (
            jeton.startswith("-") and not jeton.startswith("--") and "c" in jeton[1:]
        )
        if est_option_c and index + 1 < len(jetons_):
            return jetons_[index + 1]
    return None
