"""Les fichiers qu'une ligne de shell écrit, pour les formes simples — ticket-088.

Extrait de `perimetre.py`, qui pose le périmètre ; ici on ne fait que lire une
commande `Bash` et en rendre les cibles. `Bash` est couvert **pour les formes
simples** : `> fichier`, `>> fichier`, `tee fichier`. C'est ce qui attrape une
erreur, pas une frontière contre quelqu'un qui cherche à passer (ADR-031).

Un filet supplémentaire (ticket-326) attrape `python -c "open('CLAUDE.md','w')…"` :
un interpréteur invoqué en ligne avec le nom d'un fichier protégé et un mode
d'écriture. Même principe : ce qui ne se lit pas avec certitude passe.
"""
import re
import shlex
from pathlib import Path

#: `/dev/null`, `2>&1` : des flux, pas des fichiers du projet.
_NON_FICHIERS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr"})


def cibles_ecrites(commande: str) -> list[str]:
    """Les fichiers qu'une ligne de shell écrit, pour les formes simples.

    `>`, `>>` et `tee`. La ligne est **tokenisée**, jamais découpée à la main :
    `grep -r 'x > y' src/` ne redirige rien, et une comparaison de caractères
    le prendrait pour une écriture — un faux refus qui priverait l'agent d'une
    commande parfaitement légitime.

    Volontairement incomplet : ce qui ne se lit pas avec certitude n'est pas
    rendu, et passera donc.
    """
    try:
        jetons = shlex.split(commande, posix=True)
    except ValueError:
        # Guillemet non fermé : on ne sait pas lire cette ligne, donc on
        # n'invente pas de cible.
        return []

    cibles: list[str] = []
    for index, jeton in enumerate(jetons):
        suivant = jetons[index + 1] if index + 1 < len(jetons) else None
        cible: str | None = None
        if jeton in (">", ">>"):
            cible = suivant
        elif jeton.startswith(">") and len(jeton) > 1:
            cible = jeton.lstrip(">")
        elif jeton == "tee" and suivant and not suivant.startswith("-"):
            cible = suivant
        if cible and cible not in _NON_FICHIERS and not cible.startswith("&"):
            cibles.append(cible)
    return cibles


#: Noms et préfixes de fichiers protégés qu'on cherche dans le code inline.
_NOMS_PROTEGES_INLINE: tuple[str, ...] = (
    "CLAUDE.md",
    "CLAUDE.local.md",
    "agents.json",
    ".claude/",
    ".github/workflows/",
    ".git/",
)

#: Un appel open() avec mode écriture : open('x','w'), open('x',"a+"), etc.
_RE_OPEN_ECRITURE = re.compile(r"""open\s*\([^)]*['"]\s*,\s*['"][wa]""")

#: Méthode d'écriture directe : .write( ou .write_text(
_RE_WRITE_METHOD = re.compile(r"""\.write(?:_text)?\s*\(""")

#: Interpréteurs Python et Node reconnus comme premier jeton.
_RE_INTERPRETE = re.compile(
    r"^(python3?(\.\d+)?(\.exe)?|node(\.exe)?)$", re.IGNORECASE
)


def cibles_interpreteur_ecriture(commande: str) -> list[str]:
    """Noms protégés qu'un `python -c` ou `node -c` tente d'écrire.

    Attrape le cas `python -c "open('CLAUDE.md','w').write(…)"`.
    ADR-031 : filet, pas une garantie — ce qui ne se lit pas avec certitude passe.
    """
    try:
        jetons = shlex.split(commande, posix=True)
    except ValueError:
        return []

    if not jetons or not _RE_INTERPRETE.match(Path(jetons[0]).name):
        return []

    # Extraire le code inline après -c
    code: str | None = None
    for i, jeton in enumerate(jetons):
        if jeton == "-c" and i + 1 < len(jetons):
            code = jetons[i + 1]
            break

    if code is None:
        return []

    has_write = bool(_RE_OPEN_ECRITURE.search(code)) or bool(
        _RE_WRITE_METHOD.search(code)
    )
    if not has_write:
        return []

    return [nom for nom in _NOMS_PROTEGES_INLINE if nom in code]


__all__ = ["cibles_ecrites", "cibles_interpreteur_ecriture"]
