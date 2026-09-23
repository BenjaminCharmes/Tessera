"""Faire mourir les services avec le backend, même quand il est tué — ticket-150.

ADR-042 posait que les services sont des enfants du backend et meurent avec
lui. C'était vrai d'un arrêt **propre**, par le `lifespan` ; un backend tué
n'exécute rien, et ses enfants survivent — vingt-deux orphelins tournaient sur
la machine quand on s'en est aperçu.

Le système d'exploitation sait faire ce que le code applicatif ne peut pas
garantir :

- **Windows** — un *job object* avec `KILL_ON_JOB_CLOSE`. Quand le dernier
  handle se ferme, ce qui arrive y compris sur un `kill`, le système termine
  tous les processus du job. C'est la seule voie qui tienne aussi en cas de
  plantage.
- **Unix** — les enfants ne meurent pas non plus avec leur parent, et le
  remède (`PR_SET_PDEATHSIG`) est propre à Linux. Le `lifespan` reste le
  chemin nominal, et l'absence de filet est documentée plutôt que masquée.

Aucune dépendance ajoutée : `ctypes` fait partie de la bibliothèque standard.
"""
import os
from typing import Any, Optional

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: `JobObjectExtendedLimitInformation`, et le drapeau qui tue à la fermeture.
_CLASSE_LIMITES_ETENDUES = 9
_TUER_A_LA_FERMETURE = 0x2000

#: Le job du process, gardé ouvert pour toute sa vie : c'est la fermeture du
#: dernier handle qui déclenche la mise à mort, donc le lâcher trop tôt
#: reviendrait à ne rien faire.
_job: Optional[Any] = None


def _construire_le_job() -> Optional[Any]:
    import ctypes
    from ctypes import wintypes

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _BASIC_LIMITS(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _EXTENDED_LIMITS(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BASIC_LIMITS),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW")

    limites = _EXTENDED_LIMITS()
    limites.BasicLimitInformation.LimitFlags = _TUER_A_LA_FERMETURE
    if not kernel32.SetInformationJobObject(
        job,
        _CLASSE_LIMITES_ETENDUES,
        ctypes.byref(limites),
        ctypes.sizeof(limites),
    ):
        raise OSError(ctypes.get_last_error(), "SetInformationJobObject")
    return job


def groupe_disponible() -> bool:
    """True quand la plateforme sait tuer les enfants avec le parent."""
    return os.name == "nt"


def rattacher(pid: int) -> bool:
    """Rattache un processus au groupe qui mourra avec ce backend.

    Rend `False` quand la plateforme ne sait pas le faire, ou que l'appel
    échoue : le lancement continue alors, sans filet. Refuser de démarrer un
    service parce que le filet manque coûterait plus que le risque qu'il
    couvre — mais le journal le dit, pour que ce ne soit pas silencieux.
    """
    global _job
    if not groupe_disponible():
        return False
    try:
        import ctypes

        if _job is None:
            _job = _construire_le_job()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        poignee = kernel32.OpenProcess(0x1F0FFF, False, pid)
        if not poignee:
            raise OSError(ctypes.get_last_error(), "OpenProcess")
        try:
            if not kernel32.AssignProcessToJobObject(_job, poignee):
                raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject")
        finally:
            kernel32.CloseHandle(poignee)
        return True
    except Exception as exc:  # noqa: BLE001 — sans filet vaut mieux que sans service
        _logger.warning(
            "service_sans_filet",
            extra={"pid": pid, "erreur": str(exc)},
        )
        return False
