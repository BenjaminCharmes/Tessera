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

from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.process_agent import ProcessAgent

# `WinDLL`, `get_last_error` et `msvcrt` n'existent que sous Windows : lus
# dynamiquement, le module s'importe et se type aussi sous Linux (CI, mypy-linux).
_CTYPES: Any = ctypes

_LOGON_WITH_PROFILE = 0x1
_CREATE_UNICODE_ENVIRONMENT = 0x400
_CREATE_NO_WINDOW = 0x08000000
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


def message_de_logon(code: int, compte: str) -> str:
    """Returns the refusal text for a ``GetLastError`` code (no password in it)."""
    return f"logon du compte {compte} refusé : {_ERREURS_DE_LOGON.get(code, f'erreur Windows {code}')}"


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
        k32 = _CTYPES.WinDLL("kernel32", use_last_error=True)
        adv = _CTYPES.WinDLL("advapi32", use_last_error=True)
        in_enfant, in_parent = _tuyau(k32, parent_lit=False)
        out_enfant, out_parent = _tuyau(k32, parent_lit=True)
        err_enfant, err_parent = _tuyau(k32, True) if avec_stderr else (_nul(k32), 0)
        info = _ProcessInfo()
        si = _StartupInfo()
        si.cb = ctypes.sizeof(_StartupInfo)
        si.dwFlags = _STARTF_USESTDHANDLES
        si.hStdInput, si.hStdOutput, si.hStdError = in_enfant, out_enfant, err_enfant
        ligne = ctypes.create_unicode_buffer(subprocess.list2cmdline(list(commande)))
        ok = adv.CreateProcessWithLogonW(
            compte, ".", mot_de_passe, _LOGON_WITH_PROFILE, None, ligne,
            _CREATE_UNICODE_ENVIRONMENT | _CREATE_NO_WINDOW, bloc_d_environnement(env),
            cwd, ctypes.byref(si), ctypes.byref(info),
        )
        code = _CTYPES.get_last_error()
        for h in (in_enfant, out_enfant, err_enfant):
            k32.CloseHandle(h)
        if not ok:
            for h in (in_parent, out_parent, err_parent):
                if h:
                    k32.CloseHandle(h)
            raise ProviderIndisponible(message_de_logon(code, compte))
        k32.CloseHandle(info.hThread)
        return self._process(k32, info, in_parent, out_parent, err_parent)

    @staticmethod
    def _process(k32: Any, info: _ProcessInfo, i: int, o: int, e: int) -> Process:
        proc = info.hProcess

        def attendre() -> int:
            k32.WaitForSingleObject(proc, _INFINITE)
            return _code(k32, proc)

        def sonder() -> int | None:
            code = _code(k32, proc)
            return None if code == _STILL_ACTIVE else code

        return ProcessAgent(
            pid=info.dwProcessId, attendre=attendre,
            arreter=lambda: k32.TerminateProcess(proc, 1), sonder=sonder,
            stdin=_fichier(i, "wb"), stdout=_fichier(o, "rb"),
            stderr=_fichier(e, "rb") if e else None,
        )


def _code(k32: Any, proc: wintypes.HANDLE) -> int:
    code = wintypes.DWORD()
    k32.GetExitCodeProcess(proc, ctypes.byref(code))
    return int(code.value)
