"""Path and glob forms the secret-file guard sees through — ticket-928.

Two helpers of ``garde_jetons.py``, kept apart to hold its size:

* ``ramener_prefixe_windows`` folds the Windows spellings of a local drive path
  (extended-length prefix, loopback UNC share) back to ``C:/``, because
  ``Path.resolve()`` keeps the prefix and the result never equals the guarded path;
* ``glob_peut_designer`` tells whether a ``Grep`` glob, braces expanded, can
  select a guarded file under the searched folder.

Like the rest of the guard, it catches a mistake, not an evasion (ADR-031).
"""
import fnmatch
import re
from pathlib import Path

_HOTES_LOCAUX = r"(?:localhost|127\.0\.0\.1)"
# Formes données avec des `/` : l'appelant a déjà converti les `\`.
_PREFIXES = (
    re.compile(rf"^//[?.]/UNC/{_HOTES_LOCAUX}/([a-zA-Z])\$(?:/(.*))?$", re.IGNORECASE),
    re.compile(rf"^//{_HOTES_LOCAUX}/([a-zA-Z])\$(?:/(.*))?$", re.IGNORECASE),
    re.compile(r"^//[?.]/([a-zA-Z]):(?:/(.*))?$"),
)
_ACCOLADES = re.compile(r"\{([^{}]*)\}")
_LIMITE_VARIANTES = 256


def ramener_prefixe_windows(texte: str) -> str:
    """Fold ``//?/C:/x``, ``//localhost/C$/x``… (slashes) to ``C:/x``."""
    for motif in _PREFIXES:
        correspondance = motif.match(texte)
        if correspondance:
            reste = correspondance[2] or ""
            return f"{correspondance[1].upper()}:/{reste}"
    return texte


def developper_accolades(glob: str) -> list[str]:
    """Expand ``{a,b}`` groups, innermost first, up to a fixed number of variants."""
    variantes = [glob]
    while len(variantes) < _LIMITE_VARIANTES:
        suivantes: list[str] = []
        for variante in variantes:
            trouve = _ACCOLADES.search(variante)
            if trouve is None:
                suivantes.append(variante)
                continue
            for option in trouve[1].split(","):
                suivantes.append(variante[: trouve.start()] + option + variante[trouve.end():])
        if suivantes == variantes:
            break
        variantes = suivantes
    return variantes[:_LIMITE_VARIANTES]


def glob_peut_designer(glob: str, dossier: Path, fichier: Path) -> bool:
    """True if ``glob`` can select ``fichier`` by name or relative path under ``dossier``."""
    if not fichier.is_relative_to(dossier):
        return False
    relatif = fichier.relative_to(dossier).as_posix().lower()
    nom = fichier.name.lower()
    for variante in developper_accolades(glob.replace("\\", "/").lower()):
        motif = variante.lstrip("!")
        sans_double_etoile = motif.removeprefix("**/")
        if any(fnmatch.fnmatchcase(cible, m) for m in (motif, sans_double_etoile)
               for cible in (nom, relatif)):
            return True
    return False
