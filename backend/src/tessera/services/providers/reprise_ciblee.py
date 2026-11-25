"""Targeted take-back of what the agent account left in a worktree — ticket-1027.

ADR-091. Au lieu d'un `/setowner /T` et d'un `/reset /T` sur tout l'arbre, on ne
reprend que les entrées dont le compte est propriétaire ou dont la DACL est
protégée. Un lien n'est jamais suivi ni parcouru. Entrée illisible ou non reprise :
`DroitsAgentRefuses` nommant le chemin, sans contenu (run `blocked`, ADR-037).
"""
import asyncio
import os
from collections.abc import Collection, Iterator
from pathlib import Path

from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.securite_fichiers import InfoSecurite, SecuriteFichiers, chemin_long
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_REPARSE_POINT = 0x400


def _est_lien(entree: os.DirEntry[str]) -> bool:
    """A symlink or a junction, read from the scandir entry without following it."""
    if entree.is_symlink():
        return True
    attributs = getattr(entree.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributs & _REPARSE_POINT)


def _entrees(dossier: Path, ignorer: Collection[Path]) -> Iterator[tuple[Path, bool, bool]]:
    """Children of `dossier` as (path, is_link, is_directory); a vanished folder yields nothing."""
    try:
        with os.scandir(chemin_long(dossier)) as it:
            liste = list(it)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise DroitsAgentRefuses(f"dossier illisible : {dossier} ({type(exc).__name__})") from exc
    for entree in liste:
        chemin = dossier / entree.name
        if chemin in ignorer:
            continue
        try:
            lien = _est_lien(entree)
            dossier_reel = not lien and entree.is_dir(follow_symlinks=False)
        except FileNotFoundError:
            continue
        yield chemin, lien, dossier_reel


def _lire(securite: SecuriteFichiers, chemin: Path) -> InfoSecurite | None:
    try:
        return securite.lire(chemin)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise DroitsAgentRefuses(f"sécurité illisible : {chemin} ({type(exc).__name__})") from exc


def _reprendre(securite: SecuriteFichiers, chemin: Path, backend_sid: str, lien: bool) -> bool:
    """Take `chemin` back; `False` when it vanished meanwhile."""
    try:
        securite.reprendre(chemin, backend_sid, proprietaire_seul=lien)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise DroitsAgentRefuses(f"reprise refusée : {chemin} ({type(exc).__name__})") from exc
    return True


def _a_reprendre(info: InfoSecurite, compte_sid: str, chemin: Path, lien: bool) -> bool:
    if lien and info.dacl_protegee:
        raise DroitsAgentRefuses(f"lien à DACL protégée : {chemin}")
    return info.proprietaire_sid == compte_sid or info.dacl_protegee


def _verifier(securite: SecuriteFichiers, chemin: Path, backend_sid: str, lien: bool) -> None:
    """After the take-back: owner is the backend and the DACL is no longer protected."""
    info = _lire(securite, chemin)
    if info is None:
        return
    if info.proprietaire_sid != backend_sid or (not lien and info.dacl_protegee):
        raise DroitsAgentRefuses(f"entrée non reprise : {chemin}")


def _reprendre_sync(
    racine: Path, compte_sid: str, backend_sid: str, securite: SecuriteFichiers, ignorer: Collection[Path],
) -> list[Path]:
    reprises: list[tuple[Path, bool]] = []
    a_voir = [racine]
    while a_voir:
        for chemin, lien, dossier in _entrees(a_voir.pop(), ignorer):
            info = _lire(securite, chemin)
            if info is None:
                continue
            if _a_reprendre(info, compte_sid, chemin, lien) and _reprendre(securite, chemin, backend_sid, lien):
                reprises.append((chemin, lien))
            if dossier:
                a_voir.append(chemin)
    for chemin, lien in reprises:
        _verifier(securite, chemin, backend_sid, lien)
    _logger.info("reprise_ciblee", extra={"racine": str(racine), "reprises": len(reprises)})
    return [chemin for chemin, _ in reprises]


async def reprendre_arbre(
    racine: Path, compte: str, backend: str, securite: SecuriteFichiers, ignorer: Collection[Path] = (),
) -> list[Path]:
    """Take back every entry of `racine` owned by `compte` or with a protected DACL.

    Returns the paths taken back. Entries of `ignorer` (the root `.git`) are
    skipped; links are never followed. Runs in a thread (one `scandir` per folder).
    """
    compte_sid = await asyncio.to_thread(securite.sid_de, compte)
    backend_sid = await asyncio.to_thread(securite.sid_de, backend)
    return await asyncio.to_thread(_reprendre_sync, racine, compte_sid, backend_sid, securite, ignorer)
