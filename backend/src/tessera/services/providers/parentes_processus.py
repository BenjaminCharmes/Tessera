"""Parent links between processes, read without opening any process — ticket-997.

`CreateToolhelp32Snapshot` donne, pour chaque PID, le `th32ParentProcessID`, même
quand le processus refuse son ouverture. C'est ce qui permet de dire qu'un
processus au jeton illisible descend d'un processus de l'appel.
"""
import ctypes
from ctypes import wintypes
from typing import Any

from tessera.services.providers.droits_worktree import DroitsAgentRefuses

_CTYPES: Any = ctypes
_TH32CS_SNAPPROCESS = 0x2
_MAX_PARENTS = 4096


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
    ]


def parents_toolhelp() -> dict[int, int]:
    """The parent PID of every running process; raises ``DroitsAgentRefuses`` when unreadable."""
    k32: Any = _CTYPES.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    instantane = k32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if instantane in (None, ctypes.c_void_p(-1).value):
        raise DroitsAgentRefuses(f"filiation des processus illisible (erreur Windows {_CTYPES.get_last_error()})")
    parents: dict[int, int] = {}
    try:
        entree = _ProcessEntry()
        entree.dwSize = ctypes.sizeof(entree)
        suite = k32.Process32FirstW(instantane, ctypes.byref(entree))
        while suite:
            parents[entree.th32ProcessID] = entree.th32ParentProcessID
            suite = k32.Process32NextW(instantane, ctypes.byref(entree))
    finally:
        k32.CloseHandle(instantane)
    return parents


def descend_de(pid: int, racines: set[int], parents: dict[int, int]) -> bool:
    """Whether the parent chain of ``pid`` reaches one of ``racines`` (cycle-safe)."""
    vus: set[int] = {pid}
    courant = parents.get(pid)
    while courant is not None and courant not in vus and len(vus) < _MAX_PARENTS:
        if courant in racines:
            return True
        vus.add(courant)
        courant = parents.get(courant)
    return False
