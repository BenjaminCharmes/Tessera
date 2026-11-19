"""Scheduled tasks of the agent account are removed — ticket-1018.

ADR-088. Le compte peut créer une tâche planifiée (`schtasks /create`) : elle
survivrait à la clôture de l'appel. Les commandes partent sous le compte, car le
backend, non administrateur, ne voit pas les tâches d'un autre compte ; leurs
arguments sont fixés ici. Les tâches sous `\\Microsoft\\` sont celles de
Windows : elles restent. Un échec est une `DroitsAgentRefuses` (ADR-037).
"""
import csv
import importlib
import ntpath
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.config import settings
from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.env_agent import PROFIL_AGENT
from tessera.services.providers.noms import ProviderIndisponible
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Lance une commande sous le compte : code de sortie et sortie.
LanceurTaches = Callable[[list[str]], Awaitable[tuple[int, str]]]

_PREFIXE_WINDOWS = "\\Microsoft\\"


def _schtasks() -> str:
    racine = os.environ.get("SystemRoot", "C:\\Windows")
    return ntpath.join(racine, "System32", "schtasks.exe")


async def _lanceur_reel(args: list[str]) -> tuple[int, str]:
    """Run `args` under the account, outside any worktree, and wait for its end."""
    # Import tardif : `verification` importe ce domaine (droits_appel), pas l'inverse.
    lancement = importlib.import_module("tessera.services.verification.lancement_compte")
    processus = await lancement.lancer_sous_compte(args, Path(PROFIL_AGENT), None, None, sans_droits=True)
    try:
        sortie, erreur = await processus.communicate()
        code: int = processus.returncode or 0
    finally:
        await processus.clore()
    return code, (sortie + erreur).decode("utf-8", errors="replace")


def noms_de_taches(sortie: str) -> list[str]:
    """Task names of a `schtasks /query /fo csv /nh` output, Windows' own excluded."""
    lignes = [ligne for ligne in sortie.splitlines() if ligne.startswith('"')]
    noms = [ligne_csv[0] for ligne_csv in csv.reader(lignes) if ligne_csv]
    return [nom for nom in noms if not nom.startswith(_PREFIXE_WINDOWS)]


async def _lancer(lanceur: LanceurTaches, args: list[str]) -> tuple[int, str]:
    """Run one command; a launch failure or an I/O error is a refusal, never another exception (ADR-037)."""
    try:
        return await lanceur(args)
    except (ProviderIndisponible, OSError) as exc:
        raise DroitsAgentRefuses(f"tâches planifiées du compte : lancement impossible ({exc})") from exc


#: Tant que le dernier retrait a échoué, `ouvrir_appel` refuse : une tâche
#: du compte ne survit jamais jusqu'à un autre run. Remis à zéro par un retrait réussi.
_TACHES_ECHOUEES = False


def taches_en_echec() -> bool:
    """Whether the last removal of the account's tasks failed: the next call is refused."""
    return _TACHES_ECHOUEES


async def retirer_les_taches(lanceur: LanceurTaches | None = None) -> None:
    """Delete every scheduled task of the account; nothing runs without `AGENT_USER`.

    Un échec lève `DroitsAgentRefuses` et marque `taches_en_echec()`.
    """
    global _TACHES_ECHOUEES
    if not settings.agent_user:
        return
    try:
        await _supprimer_les_taches(lanceur or _lanceur_reel)
    except DroitsAgentRefuses:
        _TACHES_ECHOUEES = True
        raise
    _TACHES_ECHOUEES = False


async def _supprimer_les_taches(lanceur: LanceurTaches) -> None:
    code, sortie = await _lancer(lanceur, [_schtasks(), "/query", "/fo", "csv", "/nh"])
    if code != 0:
        raise DroitsAgentRefuses(f"liste des tâches planifiées du compte illisible (code {code})")
    for nom in noms_de_taches(sortie):
        code, retour = await _lancer(lanceur, [_schtasks(), "/delete", "/tn", nom, "/f"])
        if code != 0:
            raise DroitsAgentRefuses(f"tâche planifiée {nom} non supprimée (code {code}) : {retour.strip()}")
        _logger.warning("tache_planifiee_retiree", extra={"tache": nom})
