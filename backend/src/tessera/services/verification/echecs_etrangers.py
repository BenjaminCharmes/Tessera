"""Spot a failure in a step output that the timeout reader does not account for.

A retry that comes back green must not hide a type error, a lint error or a
failing test the parser did not read (ticket-971): any such sign keeps the
step red, the original output untouched.
"""
import re

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_ENTETE_D_ETAPE = re.compile(r"^(?:ruff|mypy|mypy-linux|tsc|eslint|consignes)\s*:\s*$", re.M)
_AUTRE_OUTIL = re.compile(
    r"error TS\d+|:\d+(?::\d+)?: error:|Found \d+ errors?|\d+ problems? \(|Unhandled (?:Rejection|Error)s?",
    re.I,
)
_FICHIERS_VITEST = re.compile(r"Test Files\s+(\d+) failed")
_PYTEST_LIGNE = re.compile(r"^[\s=]*((?:\d+ [\w-]+(?:, | and )?)+)\s+in [\d.]+s", re.M)
_PYTEST_COMPTE = re.compile(r"(\d+) (?:failed|errors?)\b")


def contient_un_echec_etranger(sortie: str, fichiers_vitest: int, tests_pytest: int) -> bool:
    """True when the output shows more failures than the ones already read.

    ``fichiers_vitest`` counts distinct failing vitest files read, ``tests_pytest``
    the failing pytest ids read; a summary that announces more disqualifies them.
    """
    texte = _ANSI.sub("", sortie)
    if _ENTETE_D_ETAPE.search(texte) or _AUTRE_OUTIL.search(texte):
        return True
    for annonce in _FICHIERS_VITEST.findall(texte):
        if int(annonce) != fichiers_vitest:
            return True
    annonces = [int(n) for ligne in _PYTEST_LIGNE.findall(texte) for n in _PYTEST_COMPTE.findall(ligne)]
    return bool(annonces) and sum(annonces) != tests_pytest
