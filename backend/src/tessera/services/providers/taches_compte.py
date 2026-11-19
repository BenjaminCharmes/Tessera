"""Scheduled tasks of the agent account are removed — ticket-1018.

ADR-088. Le compte peut créer une tâche planifiée (`schtasks /create`) : elle
survivrait à la clôture de l'appel. Les commandes partent sous le compte, car le
backend, non administrateur, ne voit pas les tâches d'un autre compte ; leurs
arguments sont fixés ici. Un compte ordinaire lit aussi les tâches des autres
(Adobe, OneDrive, celles de l'utilisateur) : seules celles dont le compte
d'exécution est le compte agent se retirent. Windows en crée pour lui (OneDrive)
qu'il ne peut ni modifier ni supprimer : un refus sur une tâche dont il n'est
pas l'auteur se journalise, sans bloquer (preuve du 19/11). Un refus sur une
tâche dont il est l'auteur est une `DroitsAgentRefuses` (ADR-037).
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

#: Colonnes de `schtasks /query /fo csv /nh /v`, fixes quelle que soit la langue :
#: le nom de la tâche et son compte d'exécution.
_COL_NOM = 1
_COL_AUTEUR = 7
_COL_COMPTE = 14


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
    # `schtasks` écrit dans la page de codes de la console, pas en UTF-8.
    return code, (sortie + erreur).decode("oem" if os.name == "nt" else "utf-8", errors="replace")


def _est_le_compte(valeur: str, compte: str) -> bool:
    """Whether a "run as" cell names `compte`, with or without its machine prefix."""
    nu = valeur.strip().lower()
    return nu == compte.lower() or nu.endswith(chr(92) + compte.lower())


def taches_du_compte(sortie: str, compte: str) -> dict[str, bool]:
    """Tasks that run as `compte` in a `schtasks /query /fo csv /nh /v` output: name → authored by `compte`.

    Une tâche revient une fois par déclencheur : chaque nom n'est rendu qu'une fois.
    Une ligne trop courte (message d'information) est ignorée.
    """
    lignes = [ligne for ligne in sortie.splitlines() if ligne.startswith('"')]
    taches: dict[str, bool] = {}
    for cellules in csv.reader(lignes):
        if len(cellules) > _COL_COMPTE and _est_le_compte(cellules[_COL_COMPTE], compte):
            taches.setdefault(cellules[_COL_NOM], _est_le_compte(cellules[_COL_AUTEUR], compte))
    return taches


def noms_de_taches(sortie: str, compte: str) -> list[str]:
    """Names of the tasks that run as `compte`, in listing order."""
    return list(taches_du_compte(sortie, compte))


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
    code, sortie = await _lancer(lanceur, [_schtasks(), "/query", "/fo", "csv", "/nh", "/v"])
    if code != 0:
        raise DroitsAgentRefuses(f"liste des tâches planifiées du compte illisible (code {code})")
    for nom, du_compte in taches_du_compte(sortie, settings.agent_user).items():
        code, retour = await _lancer(lanceur, [_schtasks(), "/delete", "/tn", nom, "/f"])
        if code == 0:
            _logger.warning("tache_planifiee_retiree", extra={"tache": nom})
        elif du_compte:
            raise DroitsAgentRefuses(f"tâche planifiée {nom} non supprimée (code {code}) : {retour.strip()}")
        else:
            # Créée par Windows pour le compte : il ne peut pas la supprimer, donc pas la détourner.
            _logger.warning("tache_du_compte_non_supprimable", extra={"tache": nom, "code": code})
