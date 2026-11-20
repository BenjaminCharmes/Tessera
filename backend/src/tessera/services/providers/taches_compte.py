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
import importlib
import ntpath
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.config import settings
from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.env_agent import PROFIL_AGENT
from tessera.services.providers.noms import ProviderIndisponible
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DECLARATION = re.compile(r"<\?xml[^>]*\?>")
_COMMENTAIRE = re.compile(r"<!--(.*?)-->", re.DOTALL)
_TACHE = re.compile(r"<Task[\s>].*?</Task>", re.DOTALL)
_INTERDIT = re.compile(r"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)

#: Lance une commande sous le compte : code de sortie et sortie.
LanceurTaches = Callable[[list[str]], Awaitable[tuple[int, str]]]

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


def _sid_texte(binaire: bytes) -> str:
    """The `S-1-…` text form of a binary SID."""
    sous_autorites = binaire[1]
    autorite = int.from_bytes(binaire[2:8], "big")
    parties = [str(int.from_bytes(binaire[8 + 4 * i: 12 + 4 * i], "little")) for i in range(sous_autorites)]
    return "-".join(["S", str(binaire[0]), str(autorite), *parties])


def sid_texte_du_compte(compte: str) -> str:
    """The text SID of `compte`, as `<UserId>` writes it."""
    # Import tardif : `processus_compte` charge ctypes.WinDLL, absent hors Windows.
    processus = importlib.import_module("tessera.services.providers.processus_compte")
    return _sid_texte(processus.sid_du_compte(compte))


def _local(balise: str) -> str:
    return balise.rpartition("}")[2]


def _textes(racine: ET.Element, balise: str) -> list[str]:
    return [(e.text or "").strip() for e in racine.iter() if _local(e.tag) == balise]


def _analyser(fragment: str, commentaire: str, compte: str, sid: str) -> tuple[str, bool] | None:
    """One `<Task>`: (name, authored by `compte`) when it runs as `compte`, else None."""
    try:
        racine = ET.fromstring(fragment)
    except ET.ParseError as exc:
        raise DroitsAgentRefuses(f"tâche planifiée illisible : {exc}") from exc
    comptes = _textes(racine, "UserId")
    if not any(c.lower() == sid.lower() or _est_le_compte(c, compte) for c in comptes if c):
        return None
    nom = next((n for n in _textes(racine, "URI") if n), commentaire)
    if not nom:
        raise DroitsAgentRefuses("tâche du compte sans nom : elle ne peut pas se retirer")
    return nom, any(_est_le_compte(a, compte) for a in _textes(racine, "Author"))


def taches_du_compte(sortie: str, compte: str, sid: str = "") -> dict[str, bool]:
    """Tasks that run as `compte` in a `schtasks /query /xml` output: name → authored by `compte`.

    La sortie n'est pas un document : on la découpe aux déclarations `<?xml`, et
    chaque `<Task>` s'analyse seul. Échec fermé (ADR-037) : DOCTYPE, ENTITY,
    fragment illisible, ou déclarations sans aucune tâche lue.
    """
    if _INTERDIT.search(sortie):
        raise DroitsAgentRefuses("tâches planifiées : DOCTYPE ou ENTITY refusé")
    segments = _DECLARATION.split(sortie)
    taches: dict[str, bool] = {}
    lues = 0
    for avant, segment in zip(segments, segments[1:], strict=False):
        commentaires = _COMMENTAIRE.findall(avant)
        trouve = _TACHE.search(segment)
        if trouve is None:
            continue
        lues += 1
        tache = _analyser(trouve.group(0), commentaires[-1].strip() if commentaires else "", compte, sid)
        if tache is not None:
            taches.setdefault(*tache)
    if len(segments) > 1 and lues == 0:
        raise DroitsAgentRefuses("tâches planifiées : déclarations sans aucune tâche lisible")
    return taches


def noms_de_taches(sortie: str, compte: str, sid: str = "") -> list[str]:
    """Names of the tasks that run as `compte`, in listing order."""
    return list(taches_du_compte(sortie, compte, sid))


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
    code, sortie = await _lancer(lanceur, [_schtasks(), "/query", "/xml"])
    if code != 0:
        raise DroitsAgentRefuses(f"liste des tâches planifiées du compte illisible (code {code})")
    for nom, du_compte in taches_du_compte(sortie, settings.agent_user, sid_texte_du_compte(settings.agent_user)).items():
        code, retour = await _lancer(lanceur, [_schtasks(), "/delete", "/tn", nom, "/f"])
        if code == 0:
            _logger.warning("tache_planifiee_retiree", extra={"tache": nom})
        elif du_compte:
            raise DroitsAgentRefuses(f"tâche planifiée {nom} non supprimée (code {code}) : {retour.strip()}")
        else:
            # Créée par Windows pour le compte : il ne peut pas la supprimer, donc pas la détourner.
            _logger.warning("tache_du_compte_non_supprimable", extra={"tache": nom, "code": code})
