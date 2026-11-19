"""Parent links between processes, read without opening any process — ticket-997.

`CreateToolhelp32Snapshot` donne, pour chaque PID, le `th32ParentProcessID`, même
quand le processus refuse son ouverture. C'est ce qui permet de dire qu'un
processus au jeton illisible descend d'un processus de l'appel.

Un PID de parent survit à son processus : Windows le réattribue. Le 19/11, `csrss.exe`
et `winlogon.exe` portaient le PID de leur parent mort, repris une minute plus tard par
un processus de l'utilisateur, et passaient pour ses descendants (ticket-1012). Un lien
ne vaut donc que si le parent est né avant l'enfant ; les dates viennent de
`NtQuerySystemInformation`, qui n'ouvre aucun processus non plus.
"""
import ctypes
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

from tessera.services.providers.droits_worktree import DroitsAgentRefuses

_CTYPES: Any = ctypes
_TH32CS_SNAPPROCESS = 0x2
_MAX_PARENTS = 4096
_SYSTEM_PROCESS_INFORMATION = 5
_STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
_MAX_TAMPON = 1 << 28


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
    ]


class _UnicodeString(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT), ("Buffer", ctypes.c_void_p)]


class _SystemProcess(ctypes.Structure):
    """Head of ``SYSTEM_PROCESS_INFORMATION``: only the fields read here and those before them."""

    _fields_ = [
        ("NextEntryOffset", wintypes.ULONG), ("NumberOfThreads", wintypes.ULONG),
        ("WorkingSetPrivateSize", ctypes.c_longlong), ("HardFaultCount", wintypes.ULONG),
        ("NumberOfThreadsHighWatermark", wintypes.ULONG), ("CycleTime", ctypes.c_ulonglong),
        ("CreateTime", ctypes.c_longlong), ("UserTime", ctypes.c_longlong),
        ("KernelTime", ctypes.c_longlong), ("ImageName", _UnicodeString),
        ("BasePriority", wintypes.LONG), ("UniqueProcessId", ctypes.c_void_p),
    ]


def naissances() -> dict[int, int]:
    """The creation time (FILETIME ticks) of every running process, read without opening any."""
    ntdll: Any = _CTYPES.WinDLL("ntdll")
    taille = wintypes.ULONG(1 << 20)
    while True:
        tampon = ctypes.create_string_buffer(taille.value)
        statut = ntdll.NtQuerySystemInformation(_SYSTEM_PROCESS_INFORMATION, tampon, taille, ctypes.byref(taille)) & 0xFFFFFFFF
        if statut != _STATUS_INFO_LENGTH_MISMATCH or taille.value > _MAX_TAMPON:
            break
        # La liste grossit entre deux appels : demander plus large que la taille annoncée.
        taille = wintypes.ULONG(taille.value * 2)
    if statut != 0:
        raise DroitsAgentRefuses(f"dates de création des processus illisibles (statut NT {statut:#x})")
    dates: dict[int, int] = {}
    position = 0
    while True:
        entree = _SystemProcess.from_buffer(tampon, position)
        dates[entree.UniqueProcessId or 0] = entree.CreateTime
        if not entree.NextEntryOffset:
            return dates
        position += entree.NextEntryOffset


def liens_vivants(parents: dict[int, int], dates: dict[int, int]) -> dict[int, int]:
    """``parents`` without the links whose parent was born after its child (a reused PID).

    A link missing one of its two dates is kept: unknown stays suspect.
    """
    def reutilise(enfant: int, parent: int) -> bool:
        ne_enfant, ne_parent = dates.get(enfant, 0), dates.get(parent, 0)
        return ne_enfant > 0 and ne_parent > ne_enfant

    return {enfant: parent for enfant, parent in parents.items() if not reutilise(enfant, parent)}


def parents_toolhelp(
    lire: Callable[[], dict[int, int]] | None = None,
    dates: Callable[[], dict[int, int]] | None = None,
) -> dict[int, int]:
    """The living parent of every running process; raises ``DroitsAgentRefuses`` when unreadable."""
    return liens_vivants((lire or _lire_toolhelp)(), (dates or naissances)())


def _lire_toolhelp() -> dict[int, int]:
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
