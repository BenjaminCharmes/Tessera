"""The Windows launcher: ``CreateProcessWithLogonW`` through ``ctypes`` (ADR-083).

Pas de pywin32 : une DLL de plus à faire accepter par WDAC et Smart App
Control. Le compte, son mot de passe et l'environnement sont donnés tels
quels ; rien n'est hérité du backend.
"""
import ctypes
import importlib
import os
import subprocess
from collections.abc import Mapping, Sequence
from ctypes import wintypes
from typing import Any, BinaryIO, cast

import anyio
from anyio.abc import Process

from tessera.services.noyau.groupe_de_processus import creer_groupe, fermer_le_groupe
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.process_agent import ProcessAgent

# `WinDLL`, `get_last_error` et `msvcrt` n'existent que sous Windows : lus
# dynamiquement, le module s'importe et se type aussi sous Linux (CI, mypy-linux).
_CTYPES: Any = ctypes

_LOGON_WITH_PROFILE = 0x1
_CREATE_UNICODE_ENVIRONMENT = 0x400
_CREATE_NO_WINDOW = 0x08000000
_CREATE_SUSPENDED = 0x4
_ECHEC_REPRISE = 0xFFFFFFFF
_STARTF_USESTDHANDLES = 0x100
_HANDLE_FLAG_INHERIT = 0x1
_INFINITE = 0xFFFFFFFF
_STILL_ACTIVE = 259
_GENERIC_WRITE = 0x40000000
_FILE_SHARE_RW = 0x3
_OPEN_EXISTING = 3

#: Codes de `GetLastError` qui disent un compte ou un mot de passe refusé.
_ERREURS_DE_LOGON = {1326: "compte inconnu ou mot de passe refusé", 1327: "restriction de compte",
                     1330: "mot de passe expiré", 1331: "compte désactivé", 1909: "compte verrouillé"}
#: Limite de `lpCommandLine` pour `CreateProcessWithLogonW`, en caractères.
LIMITE_LIGNE = 1024
_ERROR_ACCESS_DENIED = 5
_ERROR_INVALID_PARAMETER = 87


class _StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE),
    ]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class _Attributs(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wintypes.BOOL)]


def _code_win32(code: int) -> int:
    """Folds an HRESULT 0x8007xxxx (what `get_last_error` can return as a signed int) to its Win32 code."""
    return code & 0xFFFF if (code & 0xFFFF0000) == 0x80070000 else code


def message_de_logon(code: int, compte: str) -> str:
    """Returns the refusal text for a ``GetLastError`` code (no password in it)."""
    code = _code_win32(code)
    if code == _ERROR_INVALID_PARAMETER:
        return f"lancement sous {compte} impossible : paramètre invalide (ligne de commande ou environnement)"
    if code == _ERROR_ACCESS_DENIED:
        return f"lancement sous {compte} impossible : accès refusé (droits sur le CLI ou le dossier de travail)"
    return f"logon du compte {compte} refusé : {_ERREURS_DE_LOGON.get(code, f'erreur Windows {code}')}"


def ligne_de_commande(commande: Sequence[str]) -> str:
    """Returns the command line; refuses one over the Windows limit, before any call."""
    ligne = subprocess.list2cmdline(list(commande))
    if len(ligne) > LIMITE_LIGNE:
        raise ProviderIndisponible(
            f"ligne de commande de {len(ligne)} caractères, au plus {LIMITE_LIGNE}"
        )
    return ligne


def texte_d_environnement(env: Mapping[str, str]) -> str:
    """Returns the sorted KEY=value entries, each NUL-terminated, plus a final NUL."""
    return "\0".join(sorted(f"{k}={v}" for k, v in env.items())) + "\0\0"


def bloc_d_environnement(env: Mapping[str, str]) -> "ctypes.Array[ctypes.c_wchar]":
    """Builds the Unicode environment block for ``CreateProcessWithLogonW``."""
    texte = texte_d_environnement(env)
    return ctypes.create_unicode_buffer(texte, len(texte))


def _tuyau(k32: Any, parent_lit: bool) -> tuple[int, int]:
    """Makes a pipe; returns (child end, parent end) with only the child end inheritable."""
    lecture, ecriture = wintypes.HANDLE(), wintypes.HANDLE()
    attrs = _Attributs(ctypes.sizeof(_Attributs), None, True)
    if not k32.CreatePipe(ctypes.byref(lecture), ctypes.byref(ecriture), ctypes.byref(attrs), 0):
        raise ProviderIndisponible("tuyau de l'agent impossible à créer")
    enfant, parent = (ecriture, lecture) if parent_lit else (lecture, ecriture)
    k32.SetHandleInformation(parent, _HANDLE_FLAG_INHERIT, 0)
    return cast(int, enfant.value), cast(int, parent.value)


def _nul(k32: Any) -> int:
    attrs = _Attributs(ctypes.sizeof(_Attributs), None, True)
    k32.CreateFileW.restype = wintypes.HANDLE
    h = k32.CreateFileW("NUL", _GENERIC_WRITE, _FILE_SHARE_RW, ctypes.byref(attrs), _OPEN_EXISTING, 0, None)
    return cast(int, h)


def _fichier(handle: int, mode: str) -> BinaryIO:
    flags = os.O_RDONLY if mode == "rb" else os.O_WRONLY
    descripteur = importlib.import_module("msvcrt").open_osfhandle(handle, flags)
    return cast(BinaryIO, os.fdopen(descripteur, mode, buffering=0))


def lancer_dans_un_job(
    k32: Any, adv: Any, groupe: Any,
    cible: tuple[str, str, Any, Any, str | None], structures: tuple[_StartupInfo, _ProcessInfo],
) -> tuple[bool, int]:
    """Starts the process suspended, puts it in `groupe`, then resumes it (ticket-943).

    `cible` : compte, mot de passe, ligne de commande, environnement, dossier.
    Rend (démarré, code d'erreur). Le processus ne tourne jamais hors du job : si
    l'affectation ou la reprise échoue, il est terminé et `ProviderIndisponible` levée.
    """
    compte, mot_de_passe, ligne, env, cwd = cible
    si, info = structures
    ok = adv.CreateProcessWithLogonW(
        compte, ".", mot_de_passe, _LOGON_WITH_PROFILE, None, ligne,
        _CREATE_UNICODE_ENVIRONMENT | _CREATE_NO_WINDOW | _CREATE_SUSPENDED, env,
        cwd, ctypes.byref(si), ctypes.byref(info),
    )
    code = _CTYPES.get_last_error()
    if not ok:
        return False, code
    # Le `hProcess` rendu porte les droits requis ; un `OpenProcess` sur un
    # processus d'un autre compte les refuserait.
    if not k32.AssignProcessToJobObject(groupe, info.hProcess) or k32.ResumeThread(info.hThread) == _ECHEC_REPRISE:
        k32.TerminateProcess(info.hProcess, 1)
        k32.CloseHandle(info.hThread)
        k32.CloseHandle(info.hProcess)
        raise ProviderIndisponible(f"processus de {compte} impossible à placer dans un job ou à reprendre")
    k32.CloseHandle(info.hThread)
    return True, code


class LanceurWindows:
    """``LanceurAgent`` over ``CreateProcessWithLogonW``."""

    async def lancer(
        self, commande: Sequence[str], *, compte: str, mot_de_passe: str,
        env: Mapping[str, str], cwd: str | None, avec_stderr: bool,
    ) -> Process:
        return await anyio.to_thread.run_sync(
            lambda: self._lancer(commande, compte, mot_de_passe, env, cwd, avec_stderr)
        )

    def _lancer(
        self, commande: Sequence[str], compte: str, mot_de_passe: str,
        env: Mapping[str, str], cwd: str | None, avec_stderr: bool,
    ) -> Process:
        texte_ligne = ligne_de_commande(commande)
        k32 = _CTYPES.WinDLL("kernel32", use_last_error=True)
        adv = _CTYPES.WinDLL("advapi32", use_last_error=True)
        # Le job d'abord : sans lui, rien ne démarre (ticket-943, ADR-037).
        groupe = creer_groupe()
        if groupe is None:
            raise ProviderIndisponible("job object impossible à créer : l'agent ne démarre pas sans lui")
        in_enfant, in_parent = _tuyau(k32, parent_lit=False)
        out_enfant, out_parent = _tuyau(k32, parent_lit=True)
        err_enfant, err_parent = _tuyau(k32, True) if avec_stderr else (_nul(k32), 0)
        info = _ProcessInfo()
        si = _StartupInfo()
        si.cb = ctypes.sizeof(_StartupInfo)
        si.dwFlags = _STARTF_USESTDHANDLES
        si.hStdInput, si.hStdOutput, si.hStdError = in_enfant, out_enfant, err_enfant
        ligne = ctypes.create_unicode_buffer(texte_ligne)
        ok, code = False, 0
        try:
            ok, code = lancer_dans_un_job(
                k32, adv, groupe, (compte, mot_de_passe, ligne, bloc_d_environnement(env), cwd), (si, info)
            )
        finally:
            for h in (in_enfant, out_enfant, err_enfant):
                k32.CloseHandle(h)
            if not ok:
                fermer_le_groupe(groupe)
                for h in (in_parent, out_parent, err_parent):
                    if h:
                        k32.CloseHandle(h)
        if not ok:
            raise ProviderIndisponible(message_de_logon(code, compte))
        return self._process(k32, info, groupe, in_parent, out_parent, err_parent)

    @staticmethod
    def _process(k32: Any, info: _ProcessInfo, groupe: Any, i: int, o: int, e: int) -> Process:
        proc = info.hProcess
        ferme: list[bool] = []

        def fermer_le_job() -> None:
            # Fermer le job tue tout ce qu'il contient ; une seule fois.
            if not ferme:
                ferme.append(True)
                fermer_le_groupe(groupe)

        def arreter() -> None:
            k32.TerminateProcess(proc, 1)
            fermer_le_job()

        def attendre() -> int:
            k32.WaitForSingleObject(proc, _INFINITE)
            return _code(k32, proc)

        def sonder() -> int | None:
            code = _code(k32, proc)
            return None if code == _STILL_ACTIVE else code

        return ProcessAgent(
            pid=info.dwProcessId, attendre=attendre,
            arreter=arreter, sonder=sonder, fermer=fermer_le_job,
            stdin=_fichier(i, "wb"), stdout=_fichier(o, "rb"),
            stderr=_fichier(e, "rb") if e else None,
        )


def _code(k32: Any, proc: wintypes.HANDLE) -> int:
    code = wintypes.DWORD()
    k32.GetExitCodeProcess(proc, ctypes.byref(code))
    return int(code.value)
