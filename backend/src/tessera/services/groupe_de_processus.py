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


def _kernel32() -> Any:
    """Return Windows' kernel32, loaded late.

    `getattr` et non `ctypes.WinDLL` : l'attribut n'existe pas hors Windows,
    et mypy analyse la plateforme sur laquelle il tourne. Le mypy local
    (win32) acceptait ce que la CI Linux refusait — la même asymétrie que
    pour `os.killpg`, prise par l'autre bout.
    """
    import ctypes

    return getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)


def _derniere_erreur() -> int:
    """Return the last Win32 error code."""
    import ctypes

    return int(getattr(ctypes, "get_last_error")())


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

    kernel32 = _kernel32()
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(_derniere_erreur(), "CreateJobObjectW")

    limites = _EXTENDED_LIMITS()
    limites.BasicLimitInformation.LimitFlags = _TUER_A_LA_FERMETURE
    if not kernel32.SetInformationJobObject(
        job,
        _CLASSE_LIMITES_ETENDUES,
        ctypes.byref(limites),
        ctypes.sizeof(limites),
    ):
        raise OSError(_derniere_erreur(), "SetInformationJobObject")
    return job


def creer_groupe() -> Optional[Any]:
    """Un groupe propre à un service, qu'on fermera pour tuer tout son arbre.

    `taskkill /T` ne suit que la filiation **déclarée** par Windows. Or
    `npm.cmd` lance `node` puis se termine : les petits-enfants perdent leur
    parent, et trois processus survivaient à l'arrêt (ticket-153). Un job,
    lui, est hérité par toute la descendance quelle que soit la généalogie.
    """
    if not groupe_disponible():
        return None
    try:
        return _construire_le_job()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("groupe_de_service_indisponible", extra={"erreur": str(exc)})
        return None


def rattacher_au_groupe(groupe: Any, pid: int) -> bool:
    """Met un processus — et sa descendance à venir — dans ce groupe."""
    if groupe is None:
        return False
    try:
        kernel32 = _kernel32()
        poignee = kernel32.OpenProcess(0x1F0FFF, False, pid)
        if not poignee:
            raise OSError(_derniere_erreur(), "OpenProcess")
        try:
            if not kernel32.AssignProcessToJobObject(groupe, poignee):
                raise OSError(_derniere_erreur(), "AssignProcessToJobObject")
        finally:
            kernel32.CloseHandle(poignee)
        return True
    except Exception as exc:  # noqa: BLE001
        _logger.warning("service_sans_groupe", extra={"pid": pid, "erreur": str(exc)})
        return False


def fermer_le_groupe(groupe: Any) -> bool:
    """Ferme le groupe, ce qui termine tout ce qu'il contient."""
    if groupe is None:
        return False
    try:
        return bool(_kernel32().CloseHandle(groupe))
    except Exception as exc:  # noqa: BLE001
        _logger.warning("groupe_non_ferme", extra={"erreur": str(exc)})
        return False


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
        if _job is None:
            _job = _construire_le_job()
        kernel32 = _kernel32()
        poignee = kernel32.OpenProcess(0x1F0FFF, False, pid)
        if not poignee:
            raise OSError(_derniere_erreur(), "OpenProcess")
        try:
            if not kernel32.AssignProcessToJobObject(_job, poignee):
                raise OSError(_derniere_erreur(), "AssignProcessToJobObject")
        finally:
            kernel32.CloseHandle(poignee)
        return True
    except Exception as exc:  # noqa: BLE001 — sans filet vaut mieux que sans service
        _logger.warning(
            "service_sans_filet",
            extra={"pid": pid, "erreur": str(exc)},
        )
        return False


async def tuer_l_arbre(pid: int) -> bool:
    """Termine un processus **et toute sa descendance**.

    `terminate()` ne frappe que le premier maillon. Or un service en lance
    souvent d'autres — `npm run dev` lance `concurrently`, qui lance deux
    serveurs — et ce sont les petits-enfants qui gardent les ports.

    Windows : `taskkill /T /F`, qui suit l'arbre. Unix : le groupe de
    processus, à condition d'avoir lancé avec `start_new_session`. Un échec
    n'interrompt rien : l'appelant terminera le parent de toute façon, et un
    arrêt partiel vaut mieux qu'une exception au milieu d'une extinction.
    """
    import asyncio as _asyncio

    try:
        if os.name == "nt":
            proc = await _asyncio.create_subprocess_exec(
                "taskkill",
                "/T",
                "/F",
                "/PID",
                str(pid),
                stdout=_asyncio.subprocess.DEVNULL,
                stderr=_asyncio.subprocess.DEVNULL,
            )
            await _asyncio.wait_for(proc.wait(), timeout=10)
            return proc.returncode == 0
        # `getattr` et non l'appel direct : `os.killpg` n'existe pas sous
        # Windows, et mypy analyse avec cette plateforme. Le branchement
        # ci-dessus garantit qu'on n'arrive ici que sur Unix.
        getpgid = getattr(os, "getpgid", None)
        killpg = getattr(os, "killpg", None)
        if getpgid is None or killpg is None:
            return False

        groupe = getpgid(pid)
        # **Jamais notre propre groupe.** Sans `start_new_session`, un service
        # hérite du groupe du backend : `killpg` tuerait alors le backend et,
        # en test, pytest lui-même. La CI Linux a annulé le job là-dessus —
        # sur Windows ce chemin n'est jamais pris, donc rien ne se voyait
        # (ticket-153).
        if groupe == getpgid(0):
            _logger.warning(
                "arbre_non_tue",
                extra={"pid": pid, "erreur": "le service partage notre groupe"},
            )
            return False
        killpg(groupe, 15)
        return True
    except Exception as exc:  # noqa: BLE001 — voir la docstring
        _logger.warning("arbre_non_tue", extra={"pid": pid, "erreur": str(exc)})
        return False
