"""Detect a Smart App Control refusal and repair the venv once (ticket-948).

Windows only: elsewhere nothing is detected and nothing is repaired. A second
failure after the repair stays an environment failure (ADR-037).
"""

import re
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from tessera.services.verification.resultat_de_test import TestResult
from tessera.services.verification.venv_sac import VenvIrreparable, reparer_venv
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

T = TypeVar("T")

CODE_REFUS = 4551
_MARQUEURS = re.compile(
    r"os error 4551|WinError 4551|contr[ôo]le d.application a bloqu|"
    r"Application Control policy has blocked",
    re.IGNORECASE,
)


def _est_windows() -> bool:
    return sys.platform == "win32"


def refuse_par_sac(sortie: str) -> bool:
    """Return True when ``sortie`` shows a refused launcher of a ``.venv``."""
    return bool(_MARQUEURS.search(sortie)) and ".venv" in sortie.replace("\\", "/")


def erreur_de_refus(exc: OSError) -> bool:
    """Return True for the OS error Smart App Control raises at launch."""
    return getattr(exc, "winerror", None) == CODE_REFUS


def reparer_les_venvs(dossiers: list[Path], racine_ecriture: Path, projet: str) -> bool:
    """Repair the ``.venv`` of each folder; True when a file was replaced."""
    if not _est_windows():
        return False
    repare = False
    for dossier in dict.fromkeys(dossiers):
        venv = dossier / ".venv"
        if not venv.is_dir():
            continue
        try:
            ecrits = reparer_venv(venv, racine_ecriture)
        except VenvIrreparable as exc:
            _logger.warning("venv_irreparable", extra={"projet": projet, "erreur": str(exc)})
            continue
        if ecrits:
            _logger.warning("venv_repare", extra={"projet": projet, "dossier": str(dossier)})
            repare = True
    return repare


async def relancer_apres_refus(
    issue: "tuple[int, str] | TestResult",
    refaire: Callable[[], Awaitable["tuple[int, str] | TestResult"]],
    dossier: Path,
    racine: Path,
) -> "tuple[int, str] | TestResult":
    """Run ``refaire`` once more when a refused launcher was just repaired."""
    if isinstance(issue, TestResult) or issue[0] == 0 or not refuse_par_sac(issue[1]):
        return issue
    if not reparer_les_venvs([dossier, racine], racine, racine.name):
        return issue
    return await refaire()


async def relancer_si_refuse(
    exc: OSError,
    refaire: Callable[[], Awaitable[T]],
    dossier: Path,
    racine: Path,
    projet: str,
) -> T:
    """Launch again once after repairing the venv, or raise ``exc`` unchanged."""
    if not erreur_de_refus(exc) or not reparer_les_venvs([dossier, racine], racine, projet):
        raise exc
    return await refaire()
