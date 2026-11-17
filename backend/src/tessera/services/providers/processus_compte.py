"""The processes of the agent account, found by token SID — ticket-991.

`clore_appel` arrête les processus restants du compte à la fin de chaque appel
(ticket-943). Il les listait par la commande système qui résout le nom de compte de
chaque processus : 87 s par appel sur le poste, payées par chaque étape de test
(typecheck, lint, vitest), jusqu'à faire sauter le délai du testeur.

Ici, aucun nom n'est résolu : le SID du compte est lu une fois, puis comparé à
celui du jeton de chaque processus. Un processus dont le jeton ne s'ouvre pas
n'est pas celui du compte que le backend a lancé (le backend ouvre ceux-là).
"""
import ctypes
import ntpath
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

from tessera.services.providers.droits_worktree import DroitsAgentRefuses

# `ctypes.WinDLL` n'existe que sous Windows : passer par `Any` garde mypy muet sous Linux.
_CTYPES: Any = ctypes

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_TOKEN_QUERY = 0x0008
_TOKEN_USER = 1
_MAX_PIDS = 16384
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


def _pids() -> list[int]:
    tableau = (wintypes.DWORD * _MAX_PIDS)()
    octets = wintypes.DWORD(0)
    if not _dll("psapi").EnumProcesses(tableau, ctypes.sizeof(tableau), ctypes.byref(octets)):
        raise DroitsAgentRefuses(f"liste des processus illisible (erreur Windows {_CTYPES.get_last_error()})")
    return list(tableau[: octets.value // ctypes.sizeof(wintypes.DWORD)])


def _sid_du_processus(pid: int) -> bytes | None:
    k32, adv = _dll("kernel32"), _dll("advapi32")
    processus = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not processus:
        return None
    try:
        jeton = wintypes.HANDLE()
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
) -> list[tuple[int, str]]:
    """The (pid, image name) of every process whose token carries ``sid``."""
    return [(pid, image_de(pid) or "?") for pid in pids() if pid and sid_de(pid) == sid]


def processus_du_compte(sid: bytes) -> list[tuple[int, str]]:
    """The processes of the account whose SID is ``sid``, on this machine."""
    return processus_par_sid(sid)
