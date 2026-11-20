"""Long CLI values moved to files, for the 1 024-character limit (ticket-946).

`CreateProcessWithLogonW` refuse une ligne de commande de plus de 1 024
caractères ; le prompt système, la config MCP et les réglages la dépassent.
Chaque valeur longue passe par un fichier d'un dossier propre à l'appel,
lisible par le compte agent (lecture seule : il ne peut ni modifier ni
supprimer), supprimé à la fin de l'appel.
"""
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from tessera.services.providers.droits_worktree import Icacls, _icacls_reel
from tessera.services.providers.noms import ProviderIndisponible

#: Valeur plus courte que ça : elle reste sur la ligne.
SEUIL_DEPORT = 200

#: Option du CLI -> option équivalente qui lit un fichier, et extension du fichier.
_VERS_FICHIER = {
    "--system-prompt": ("--system-prompt-file", ".txt"),
    "--append-system-prompt": ("--append-system-prompt-file", ".txt"),
    "--mcp-config": ("--mcp-config", ".json"),
    "--settings": ("--settings", ".json"),
}


def _a_deporter(option: str, valeur: str) -> bool:
    if option not in _VERS_FICHIER or len(valeur) <= SEUIL_DEPORT:
        return False
    # --mcp-config et --settings acceptent déjà un chemin : seul un JSON se déporte.
    return option in ("--system-prompt", "--append-system-prompt") or valeur.lstrip().startswith("{")


def deporter_les_valeurs(commande: Sequence[str], dossier: Path) -> list[str]:
    """Returns ``commande`` with its long values replaced by files under ``dossier``."""
    sortie: list[str] = []
    i = 0
    while i < len(commande):
        option = commande[i]
        valeur = commande[i + 1] if i + 1 < len(commande) else None
        if valeur is not None and _a_deporter(option, valeur):
            nouvelle, extension = _VERS_FICHIER[option]
            fichier = dossier / f"{len(sortie)}{extension}"
            fichier.write_text(valeur, encoding="utf-8")
            sortie += [nouvelle, str(fichier)]
            i += 2
        else:
            sortie.append(option)
            i += 1
    return sortie


async def creer_dossier_d_appel(compte: str, icacls: Icacls | None = None) -> Path:
    """Makes the call folder and gives ``compte`` read-only access, inherited by its files."""
    dossier = Path(tempfile.mkdtemp(prefix="tessera-appel-"))
    try:
        code, sortie = await (icacls or _icacls_reel)([str(dossier), "/grant", f"{compte}:(OI)(CI)R"])
    except BaseException:
        supprimer_dossier_d_appel(dossier)
        raise
    if code != 0:
        supprimer_dossier_d_appel(dossier)
        raise ProviderIndisponible(f"droits du dossier d'appel refusés (icacls {code}) : {sortie.strip()}")
    return dossier


def supprimer_dossier_d_appel(dossier: Path | None) -> None:
    """Removes the call folder; never raises."""
    if dossier is not None:
        shutil.rmtree(dossier, ignore_errors=True)
