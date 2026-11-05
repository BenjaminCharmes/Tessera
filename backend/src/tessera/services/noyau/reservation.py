"""Fichier d'état des numéros réservés — ticket-848.

Un numéro rendu par `numerotation.reserver` est pris, utilisé ou non. Ce module
tient le fichier qui s'en souvient (`numeros_reserves.json`), son verrou et son
écriture atomique. Bibliothèque standard seule, comme `numerotation`.
"""
import json
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

NOM_FICHIER = "numeros_reserves.json"
NOM_VERROU = "numeros_reserves.lock"
SUFFIXE_CORROMPU = ".corrompu"

# Plus grand numéro réservé, par dépôt puis par genre.
Reserves = dict[str, dict[str, int]]


@contextmanager
def verrou(chemin: Path) -> Iterator[None]:
    """Hold an exclusive lock on `chemin` (created if absent) for the block."""
    with open(chemin, "a+b") as poignee:
        _prendre(poignee.fileno())
        try:
            yield
        finally:
            _rendre(poignee.fileno())


def _prendre(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        for _ in range(100):
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.05)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)  # dernier essai : l'erreur remonte
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)


def _rendre(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


def _valide(donnees: object) -> Reserves | None:
    """`donnees` as Reserves, or None when its shape is not the expected one."""
    if not isinstance(donnees, dict):
        return None
    lu: Reserves = {}
    for cle, genres in donnees.items():
        if not isinstance(cle, str) or not isinstance(genres, dict):
            return None
        lu[cle] = {}
        for genre, numero in genres.items():
            est_numero = isinstance(numero, int) and not isinstance(numero, bool)
            if not isinstance(genre, str) or not est_numero or numero < 0:
                return None
            lu[cle][genre] = numero
    return lu


def lire(fichier: Path) -> Reserves:
    """The reservations in `fichier`; an unreadable file is set aside, never overwritten."""
    if not fichier.exists():
        return {}
    try:
        lu = _valide(json.loads(fichier.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        lu = None
    if lu is None:
        os.replace(fichier, fichier.with_name(fichier.name + SUFFIXE_CORROMPU))
        return {}
    return lu


def ecrire(fichier: Path, reserves: Reserves) -> None:
    """Write `reserves` to `fichier` through a temporary file and a rename."""
    temporaire = fichier.with_name(fichier.name + ".tmp")
    temporaire.write_text(json.dumps(reserves, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporaire, fichier)
