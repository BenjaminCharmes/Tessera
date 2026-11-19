"""The profile of the agent account is wiped between calls — ticket-1008.

ADR-087. `~/.bashrc`, `~/.npmrc`, `uv.toml` ou un `.pth` écrits par un appel ne
doivent pas survivre jusqu'au suivant. Tout le dossier de profil est supprimé,
sauf `npm-cache` et `uv\\cache` ; le dossier est recréé et le compte retrouve
`M` dessus. Aucun lien (jonction, lien symbolique) n'est suivi : il se retire
lui-même. Un échec est une `DroitsAgentRefuses` (ADR-037).
"""
import asyncio
import ntpath
import os
import stat
from pathlib import Path

from tessera.services.providers.droits_worktree import DroitsAgentRefuses, Icacls, _icacls_reel, _lancer
from tessera.services.providers.env_agent import CACHE_NPM, CACHE_UV, PROFIL_AGENT, env_du_profil
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

DOSSIER_PROFIL = Path(PROFIL_AGENT)
#: Attribut Windows d'un lien (jonction, lien symbolique) ; `stat` ne le porte que sous Windows.
_REPARSE_POINT = 0x400
#: Chemins relatifs qui survivent au nettoyage.
_GARDES: tuple[tuple[str, ...], ...] = (
    (CACHE_NPM,), tuple(CACHE_UV.split("\\")),
)


def _est_un_lien(chemin: Path) -> bool:
    """Whether `chemin` is a symlink or a junction (never followed)."""
    attributs = getattr(os.lstat(chemin), "st_file_attributes", 0)
    return chemin.is_symlink() or bool(attributs & _REPARSE_POINT)


def _retirer(chemin: Path) -> None:
    """Remove a file, a link, or a real folder with its content."""
    if _est_un_lien(chemin):
        # Un lien vers un dossier se retire par `rmdir`, jamais en le parcourant.
        if chemin.is_dir():
            os.rmdir(chemin)
        else:
            os.unlink(chemin)
    elif chemin.is_dir():
        for enfant in list(chemin.iterdir()):
            _retirer(enfant)
        os.rmdir(chemin)
    else:
        os.chmod(chemin, stat.S_IWRITE)
        os.unlink(chemin)


def _purger(dossier: Path, gardes: tuple[tuple[str, ...], ...]) -> None:
    """Remove everything under `dossier` except the kept relative paths."""
    for enfant in list(dossier.iterdir()):
        suite = [g[1:] for g in gardes if g[0] == enfant.name]
        # Un lien ne se garde jamais, même sous le nom d'un cache.
        if not suite or _est_un_lien(enfant):
            _retirer(enfant)
        elif all(suite) and enfant.is_dir():
            # Un garde plus profond (`uv\cache`) : on descend, le reste part.
            _purger(enfant, tuple(suite))
        # Sinon le chemin entier est gardé (`suite` contient ()).


def _vider(profil: Path) -> None:
    try:
        _purger(profil, _GARDES)
    except OSError as exc:
        raise DroitsAgentRefuses(f"profil de l'agent non nettoyé ({profil}) : {exc}") from exc


def _recreer(profil: Path) -> None:
    """Recreate the folders that `TEMP`, `APPDATA` and `LOCALAPPDATA` point to, from `env_du_profil`."""
    env = env_du_profil("")
    try:
        for cle in ("TEMP", "APPDATA", "LOCALAPPDATA"):
            # Chemins Windows, lus aussi sous Linux (CI) : `ntpath`, jamais `Path`.
            relatif = ntpath.relpath(env[cle], PROFIL_AGENT).split("\\")
            profil.joinpath(*relatif).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DroitsAgentRefuses(f"profil de l'agent non recréé ({profil}) : {exc}") from exc


async def reinitialiser_profil(compte: str, icacls: Icacls = _icacls_reel, profil: Path | None = None) -> None:
    """Wipe the agent profile except the two caches, recreate it, give `compte` modify on it.

    Un dossier absent (installation non faite) se journalise : `agent doctor` le
    signale, et aucun droit n'est posé sur un chemin que `agent setup` n'a pas créé.
    """
    dossier = profil or DOSSIER_PROFIL
    if not dossier.is_dir():
        _logger.warning("profil_agent_absent", extra={"dossier": str(dossier)})
        return
    await asyncio.to_thread(_vider, dossier)
    await asyncio.to_thread(_recreer, dossier)
    await _lancer(icacls, [str(dossier), "/grant", f"{compte}:(OI)(CI)M", "/L"])
