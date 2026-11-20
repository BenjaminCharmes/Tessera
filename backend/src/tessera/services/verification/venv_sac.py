"""Repair a uv venv whose launcher Smart App Control refuses (ticket-948).

Smart App Control judges each file by reputation and sometimes refuses the
``python.exe`` launcher uv copies into ``.venv/Scripts`` (os error 4551). The
base interpreter stays allowed: copying its launcher files into the venv
makes it run again, Python finding its venv through ``pyvenv.cfg``.

The repair runs in the backend, while everything it reads comes from a
folder the agent writes. So the source is trusted only under the uv
interpreters root, read on the backend side, and the destination only under
the run's write root, links excluded.
"""

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

SUFFIXE_ORIGINAL = ".lanceur-uv"
_REPARSE_POINT = 0x400
_MOTIFS = ("python.exe", "pythonw.exe", "python3*.dll", "vcruntime140*.dll")


class VenvIrreparable(Exception):
    """The venv cannot be repaired safely; nothing was copied."""


def est_un_lien(chemin: Path) -> bool:
    """Return True for a symlink or a Windows junction / reparse point."""
    if chemin.is_symlink():
        return True
    try:
        attributs = getattr(os.lstat(chemin), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributs & _REPARSE_POINT)


@lru_cache(maxsize=1)
def _racine_uv_declaree() -> str:
    """Ask uv once where it keeps its interpreters."""
    try:
        sortie = subprocess.run(  # noqa: S603 — commande fixe, sans entrée du projet
            ["uv", "python", "dir"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return sortie.stdout.strip() if sortie.returncode == 0 else ""


def racine_uv() -> Path:
    """Return the resolved root of uv's interpreters, read on the backend side."""
    brut = os.environ.get("UV_PYTHON_INSTALL_DIR") or _racine_uv_declaree()
    if not brut:
        raise VenvIrreparable("racine des interpréteurs uv inconnue")
    try:
        return Path(brut).resolve(strict=True)
    except OSError as exc:
        raise VenvIrreparable(f"racine des interpréteurs uv illisible : {exc}") from exc


def _home(venv: Path) -> Path:
    """Return the resolved ``home`` of ``pyvenv.cfg``, only if under uv's root."""
    try:
        lignes = (venv / "pyvenv.cfg").read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise VenvIrreparable(f"pyvenv.cfg illisible : {exc}") from exc
    valeurs = [v.strip() for k, _, v in (ligne.partition("=") for ligne in lignes) if k.strip() == "home"]
    if not valeurs or not valeurs[0]:
        raise VenvIrreparable("pyvenv.cfg sans clé home")
    try:
        home = Path(valeurs[0]).resolve(strict=True)
    except OSError as exc:
        raise VenvIrreparable(f"home introuvable : {exc}") from exc
    if not home.is_dir() or not home.is_relative_to(racine_uv()):
        raise VenvIrreparable("home hors de la racine des interpréteurs uv")
    return home


def _scripts(venv: Path, racine_ecriture: Path) -> Path:
    """Return ``.venv/Scripts`` after checking it stays under the write root."""
    racine = racine_ecriture.resolve()
    scripts = venv / "Scripts"
    for dossier in (venv, scripts):
        if est_un_lien(dossier):
            raise VenvIrreparable(f"{dossier.name} est un lien")
        if not dossier.is_dir():
            raise VenvIrreparable(f"{dossier.name} absent")
        if not dossier.resolve(strict=True).is_relative_to(racine):
            raise VenvIrreparable("venv hors de la racine d'écriture du run")
    return scripts


def _sources(home: Path) -> list[Path]:
    """Return the interpreter files to copy: ordinary files only, fixed names."""
    sources = [f for motif in _MOTIFS for f in sorted(home.glob(motif))]
    if not any(f.name == "python.exe" for f in sources):
        raise VenvIrreparable("python.exe absent de l'interpréteur de base")
    for fichier in sources:
        if est_un_lien(fichier) or not fichier.is_file():
            raise VenvIrreparable(f"{fichier.name} n'est pas un fichier ordinaire")
    return sources


def _a_copier(sources: list[Path], scripts: Path) -> list[Path]:
    """Keep the sources whose target differs; refuse a target that is a link."""
    restant: list[Path] = []
    for source in sources:
        cible = scripts / source.name
        if cible.exists() or cible.is_symlink():
            if est_un_lien(cible):
                raise VenvIrreparable(f"{cible.name} est un lien")
            if cible.is_file() and _meme_contenu(source, cible):
                continue
        restant.append(source)
    return restant


def _meme_contenu(a: Path, b: Path) -> bool:
    return a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()


def reparer_venv(venv: Path, racine_ecriture: Path) -> list[str]:
    """Copy the base interpreter's launcher files into ``venv/Scripts``.

    Return the names written (empty when already repaired). The original
    launcher is kept as ``<name>.lanceur-uv`` and never overwritten. Raise
    ``VenvIrreparable`` before copying anything when a check fails.
    """
    scripts = _scripts(venv, racine_ecriture)
    restant = _a_copier(_sources(_home(venv)), scripts)
    for source in restant:
        cible = scripts / source.name
        garde = scripts / (source.name + SUFFIXE_ORIGINAL)
        if cible.exists() and not garde.exists():
            cible.rename(garde)
        shutil.copyfile(source, cible)
    return [s.name for s in restant]
