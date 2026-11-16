"""The only place that builds the ``PATH`` of an agent-account process (ADR-086)."""
import ntpath
import os
from pathlib import Path

from tessera.services.providers.noms import ProviderIndisponible

#: La chaîne d'outils partagée, hors de tout profil (ticket-981 l'installe).
TOOLCHAIN = Path(r"C:\ProgramData\Tessera\toolchain")

_SOUS_DOSSIERS = ("node", "uv", "python", r"python\Scripts")


class ChaineAbsente(ProviderIndisponible):
    """The shared toolchain is not installed: ``agent setup`` has not run."""


def _racines_admises() -> list[str]:
    """System folders whose entries may stay on the account's PATH."""
    noms = ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")
    racines = [os.environ.get(nom, "") for nom in noms]
    racines.append(r"C:\Windows")
    return [ntpath.normcase(ntpath.normpath(r)) for r in racines if r]


def _est_sous(chemin: str, racine: str) -> bool:
    norme = ntpath.normcase(ntpath.normpath(chemin))
    return norme == racine or norme.startswith(racine + "\\")


def _entrees_du_backend() -> list[str]:
    """Backend PATH entries under a system folder and present on disk."""
    racines = _racines_admises()
    gardees: list[str] = []
    for entree in os.environ.get("PATH", os.environ.get("Path", "")).split(os.pathsep):
        if entree and any(_est_sous(entree, r) for r in racines) and Path(entree).is_dir():
            gardees.append(entree)
    return gardees


def path_du_compte() -> str:
    """Builds the account's ``PATH``: toolchain first, then system entries only.

    Raises ``ChaineAbsente`` when ``node.exe`` is missing from the toolchain;
    never falls back on the backend's PATH (ADR-037).
    """
    if not (TOOLCHAIN / "node" / "node.exe").is_file():
        raise ChaineAbsente(
            f"chaîne d'outils absente ({TOOLCHAIN}) : lancer `agent setup` (ADR-086)"
        )
    entrees = [str(TOOLCHAIN / sous) for sous in _SOUS_DOSSIERS]
    return os.pathsep.join(entrees + _entrees_du_backend())
