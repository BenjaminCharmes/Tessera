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

#: Un shell qui reçoit une ligne complète derrière `-c`.
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "busybox"})

#: Une enveloppe qui exécute la commande qui la suit, sans la changer.
ENVELOPPES = frozenset(
    {"env", "command", "exec", "xargs", "time", "nohup", "timeout", "sudo", "nice", "doas"}
)

#: Ce qu'une enveloppe accepte avant la commande réelle : ses options, une
#: affectation `VAR=valeur`, une durée (`timeout 30`).
_JETON_D_ENVELOPPE = re.compile(r"^(-|[A-Za-z_][A-Za-z0-9_]*=|\d+(\.\d+)?[smhd]?$)")


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
        bruts = shlex.split(segment, posix=False)
    except ValueError:
        bruts = segment.split()
    return [_sans_guillemets(j) for j in bruts]


def _sans_guillemets(jeton: str) -> str:
    if len(jeton) >= 2 and jeton[0] == jeton[-1] and jeton[0] in "'\"":
        return jeton[1:-1]
    return jeton


def nom_de_commande(jeton: str) -> str:
    """`/usr/bin/git`, `C:\\...\\git.exe`, `GIT` → `git`."""
    nom = re.split(r"[\\/]", jeton)[-1].lower()
    return nom[:-4] if nom.endswith(".exe") else nom


def sans_enveloppe(jetons_: list[str]) -> list[str]:
    """Retire une enveloppe et ce qu'elle accepte avant la commande réelle."""
    reste = jetons_[1:]
    while reste and _JETON_D_ENVELOPPE.match(reste[0]):
        reste = reste[1:]
    return reste


def ligne_derriere_c(jetons_: list[str]) -> str | None:
    """La ligne qu'un shell exécute derrière `-c` (`-lc`, `-ec` compris)."""
    for index, jeton in enumerate(jetons_[1:], start=1):
        est_option_c = jeton == "-c" or (
            jeton.startswith("-") and not jeton.startswith("--") and "c" in jeton[1:]
        )
        if est_option_c and index + 1 < len(jetons_):
            return jetons_[index + 1]
    return None
