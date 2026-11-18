"""The processes of the agent account, found by token SID — ticket-991.

`clore_appel` arrête les processus restants du compte à la fin de chaque appel
(ticket-943). Il les listait par la commande système qui résout le nom de compte de
chaque processus : 87 s par appel sur le poste, payées par chaque étape de test
(typecheck, lint, vitest), jusqu'à faire sauter le délai du testeur.

Ici, aucun nom n'est résolu : le SID du compte est lu une fois, puis comparé à
celui du jeton de chaque processus. Un jeton qui ne s'ouvre pas est « illisible » : sans suite pour un processus
sans suite, sauf s'il descend du backend ou d'un processus du compte (sorti du job,
DACL réécrite) : `DroitsAgentRefuses`. La filiation vient de Toolhelp.
"""
import ctypes
import ntpath
import os
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.parentes_processus import descend_de, parents_toolhelp

# `ctypes.WinDLL` n'existe que sous Windows : passer par `Any` garde mypy muet sous Linux.
_CTYPES: Any = ctypes

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_TOKEN_QUERY = 0x0008
_TOKEN_USER = 1
_MAX_PIDS = 16384
_ERREUR_PID_INCONNU = 87
_ERREUR_ACCES_REFUSE = 5
#: Processus qui refuse jusqu'à son ouverture (≠ None : disparu, sans objet ou SYSTEM).
ILLISIBLE = b""
_MAX_CHEMIN = 32768


def _dll(nom: str) -> Any:
    return _CTYPES.WinDLL(nom, use_last_error=True)


def sid_du_compte(compte: str) -> bytes:
    """The binary SID of ``compte``; raises ``DroitsAgentRefuses`` when unknown."""
    adv = _dll("advapi32")
    taille_sid, taille_dom, usage = wintypes.DWORD(0), wintypes.DWORD(0), wintypes.DWORD(0)
    adv.LookupAccountNameW(None, compte, None, ctypes.byref(taille_sid), None,
                           ctypes.byref(taille_dom), ctypes.byref(usage))
    sid = ctypes.create_string_buffer(max(taille_sid.value, 1))
    domaine = ctypes.create_unicode_buffer(max(taille_dom.value, 1))
    if not adv.LookupAccountNameW(None, compte, sid, ctypes.byref(taille_sid), domaine,
                                  ctypes.byref(taille_dom), ctypes.byref(usage)):
        raise DroitsAgentRefuses(f"compte {compte} introuvable (erreur Windows {_CTYPES.get_last_error()})")
    return sid.raw[: taille_sid.value]


def _lire_pids(capacite: int) -> tuple[list[int], bool]:
    """The PIDs listed in a buffer of ``capacite`` entries, and whether it was full."""
    tableau = (wintypes.DWORD * capacite)()
    octets = wintypes.DWORD(0)
    if not _dll("psapi").EnumProcesses(tableau, ctypes.sizeof(tableau), ctypes.byref(octets)):
        raise DroitsAgentRefuses(f"liste des processus illisible (erreur Windows {_CTYPES.get_last_error()})")
    pids = list(tableau[: octets.value // ctypes.sizeof(wintypes.DWORD)])
    return pids, octets.value >= ctypes.sizeof(tableau)


def _pids(lire: Callable[[int], tuple[list[int], bool]] = _lire_pids) -> list[int]:
    """Every PID; the buffer doubles while it comes back full (no silent truncation)."""
    capacite = _MAX_PIDS
    pids, plein = lire(capacite)
    while plein:
        capacite *= 2
        pids, plein = lire(capacite)
    return pids


def processus_existe(pid: int) -> bool:
    """Whether ``pid`` still exists (a denied open still means it exists)."""
    k32 = _dll("kernel32")
    processus = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if processus:
        k32.CloseHandle(processus)
        return True
    return bool(_CTYPES.get_last_error() != _ERREUR_PID_INCONNU)


def _sid_du_processus(pid: int) -> bytes | None:
    k32, adv = _dll("kernel32"), _dll("advapi32")
    processus = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not processus:
        # Seule l'ouverture refusée est la signature d'une DACL réécrite : un processus
        # SYSTEM ou protégé (PPL) laisse ouvrir le processus en lecture limitée.
        return ILLISIBLE if _CTYPES.get_last_error() == _ERREUR_ACCES_REFUSE else None
    try:
        jeton = wintypes.HANDLE()
        # Processus ouvrable mais jeton refusé : cas courant des processus SYSTEM, jamais suspect.
        if not adv.OpenProcessToken(processus, _TOKEN_QUERY, ctypes.byref(jeton)):
            return None
        try:
            taille = wintypes.DWORD(0)
            adv.GetTokenInformation(jeton, _TOKEN_USER, None, 0, ctypes.byref(taille))
            tampon = ctypes.create_string_buffer(max(taille.value, 1))
            if not adv.GetTokenInformation(jeton, _TOKEN_USER, tampon, taille, ctypes.byref(taille)):
                return None
            # TOKEN_USER commence par un SID_AND_ATTRIBUTES, dont le premier champ est le PSID.
            psid = ctypes.cast(tampon, ctypes.POINTER(ctypes.c_void_p))[0]
            return ctypes.string_at(psid, adv.GetLengthSid(ctypes.c_void_p(psid)))
        finally:
            k32.CloseHandle(jeton)
    finally:
        k32.CloseHandle(processus)


def _image_du_processus(pid: int) -> str | None:
    k32 = _dll("kernel32")
    processus = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not processus:
        return None
    try:
        tampon = ctypes.create_unicode_buffer(_MAX_CHEMIN)
        taille = wintypes.DWORD(_MAX_CHEMIN)
        if not k32.QueryFullProcessImageNameW(processus, 0, tampon, ctypes.byref(taille)):
            return None
        return ntpath.basename(tampon.value)
    finally:
        k32.CloseHandle(processus)


def processus_par_sid(
    sid: bytes,
    pids: Callable[[], list[int]] = _pids,
    sid_de: Callable[[int], bytes | None] = _sid_du_processus,
    image_de: Callable[[int], str | None] = _image_du_processus,
    parents: Callable[[], dict[int, int]] = parents_toolhelp,
    backend: int | None = None,
) -> list[tuple[int, str]]:
    """The (pid, image name) of every process whose token carries ``sid``.

    A process whose token is unreadable is suspect only when its parent chain reaches the
    backend or a process of the account; a system process (parent ``services.exe``…) is ignored.
    """
    trouves: list[tuple[int, str]] = []
    illisibles: list[int] = []
    for pid in pids():
        lu = sid_de(pid) if pid else None
        if lu == sid:
            trouves.append((pid, image_de(pid) or "?"))
        elif lu == ILLISIBLE:
            illisibles.append(pid)
    suspects = _descendants(illisibles, {p for p, _ in trouves} | {os.getpid() if backend is None else backend}, parents)
    if suspects:
        raise ProcessusIllisibles(suspects, trouves)
    return trouves


def _descendants(illisibles: list[int], racines: set[int], parents: Callable[[], dict[int, int]]) -> list[int]:
    if not illisibles:
        return []
    liens = parents()
    return [pid for pid in illisibles if descend_de(pid, racines, liens)]


class ProcessusIllisibles(DroitsAgentRefuses):
    """New processes whose token cannot be read; ``trouves`` are the readable ones to stop first."""

    def __init__(self, suspects: list[int], trouves: list[tuple[int, str]]) -> None:
        super().__init__(f"processus récents au jeton illisible, peut-être du compte : {suspects}")
        self.trouves = trouves


def processus_du_compte(sid: bytes) -> list[tuple[int, str]]:
    """The processes of the account whose SID is ``sid``, on this machine."""
    return processus_par_sid(sid)
