"""Développement d'un chemin comme le ferait le shell — ticket-931.

`~` et `$VAR` se développent avant toute comparaison au périmètre : sans cela,
`~/.bashrc` serait lu comme `<racine>/~/.bashrc`, dans le projet.
"""
import os
import re

_GIT_BASH = re.compile(r"^/([a-zA-Z])/(.*)$")


def developper(brut: str) -> str:
    """Le chemin avec `~` et les variables développés, forme Git Bash ramenée à `C:/…` sous Windows."""
    texte = os.path.expanduser(os.path.expandvars(brut.strip()))
    if os.name == "nt":
        correspondance = _GIT_BASH.match(texte)
        if correspondance:
            return f"{correspondance[1].upper()}:/{correspondance[2]}"
    return texte


def est_indetermine(texte: str) -> bool:
    """True si, développé, le chemin garde un `$`, une substitution ou un `~` de tête."""
    return "$" in texte or "`" in texte or texte.startswith("~")


def est_absolu(texte: str) -> bool:
    """Absolu au sens POSIX comme Windows (`/x`, `\\x`, `C:…`)."""
    return texte.startswith(("/", "\\")) or bool(re.match(r"^[A-Za-z]:", texte))
