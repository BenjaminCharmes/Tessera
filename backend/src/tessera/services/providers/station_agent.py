"""A desktop of its own for each agent call, on the session's automatic window station (ADR-089).

`CreateProcessWithLogonW` avec `lpDesktop` à `NULL` lance sur `WinSta0\\Default` : le
presse-papiers, les frappes et l'écran de l'utilisateur sont à portée. Ici, un bureau
créé par appel, dont la DACL ne nomme que le compte agent et le backend. Un nom de
station est refusé à un non-administrateur : `CreateWindowStationW(NULL)` rend la
station automatique de la session, où le compte reçoit une entrée le temps des appels.
Pas de pywin32 (ADR-083). Aucun repli : un échec lève `ProviderIndisponible` (ADR-037).
"""
import ctypes
import os
import threading
import uuid
from collections.abc import Callable
from ctypes import wintypes
from typing import Any, Protocol

from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.processus_compte import _sid_du_processus

# `WinDLL` n'existe que sous Windows : lu dynamiquement, le module se type sous Linux.
_CTYPES: Any = ctypes

_DROITS_STATION = 0xF037F
_DROITS_BUREAU = 0xF01FF
_DACL_SECURITY_INFORMATION = 4
_SE_WINDOW_OBJECT = 7
_UOI_NAME = 2
_SET_ACCESS, _REVOKE_ACCESS = 2, 4


class _Trustee(ctypes.Structure):
    _fields_ = [("pMultiple", ctypes.c_void_p), ("operation", wintypes.DWORD),
                ("forme", wintypes.DWORD), ("genre", wintypes.DWORD), ("nom", ctypes.c_void_p)]


class _Acces(ctypes.Structure):
    _fields_ = [("droits", wintypes.DWORD), ("mode", wintypes.DWORD),
                ("heritage", wintypes.DWORD), ("trustee", _Trustee)]


class _Attributs(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wintypes.BOOL)]


class BureauAgent:
    """An open desktop: ``nom`` is ``"<station>\\<bureau>"``; ``fermer`` is idempotent."""

    def __init__(self, nom: str, fermer: Callable[[], None]) -> None:
        self.nom = nom
        self._fermer: Callable[[], None] | None = fermer

    def fermer(self) -> None:
        fermer, self._fermer = self._fermer, None
        if fermer is not None:
            fermer()


class OuvreurBureau(Protocol):
    """Opens a desktop for the account with this SID (a fake stands in without Windows)."""

    def __call__(self, sid_compte: bytes) -> BureauAgent: ...


class EntreesStation:
    """Counts the open desktops: the account's entry leaves with the last one."""

    def __init__(self) -> None:
        self.verrou = threading.RLock()
        self.ouverts = 0

    def ouvrir(self, poser: Callable[[], None]) -> None:
        with self.verrou:
            poser()  # remplace une entrée restée d'un backend arrêté net, sans la doubler
            self.ouverts += 1

    def fermer(self, retirer: Callable[[], None]) -> None:
        with self.verrou:
            self.ouverts -= 1
            if self.ouverts == 0:
                retirer()


_ENTREES = EntreesStation()
_VERROU_STATION = threading.Lock()


def _dlls() -> tuple[Any, Any, Any]:
    u32 = _CTYPES.WinDLL("user32", use_last_error=True)
    adv = _CTYPES.WinDLL("advapi32", use_last_error=True)
    k32 = _CTYPES.WinDLL("kernel32", use_last_error=True)
    for f in (u32.CreateWindowStationW, u32.CreateDesktopW, u32.GetProcessWindowStation):
        f.restype = ctypes.c_void_p
    return u32, adv, k32


def _acl(adv: Any, ancienne: int | None, entrees: list[tuple[bytes, int, int]]) -> int:
    """The DACL that `ancienne` becomes once each (SID, droits, mode) entry is applied."""
    tampons = [ctypes.create_string_buffer(sid) for sid, _, _ in entrees]
    tableau = (_Acces * len(entrees))()
    for acces, tampon, (_, droits, mode) in zip(tableau, tampons, entrees, strict=True):
        acces.droits, acces.mode = droits, mode
        acces.trustee.nom = ctypes.cast(tampon, ctypes.c_void_p)
    nouvelle = ctypes.c_void_p()
    adv.SetEntriesInAclW.argtypes = [wintypes.ULONG, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    code = adv.SetEntriesInAclW(len(entrees), tableau, ancienne, ctypes.byref(nouvelle))
    if code or not nouvelle.value:
        raise ProviderIndisponible(f"bureau de l'agent : DACL impossible à bâtir (erreur Windows {code})")
    return int(nouvelle.value)


def _entree_du_compte(adv: Any, station: int, sid: bytes, mode: int) -> None:
    """Sets (`_SET_ACCESS`) or removes (`_REVOKE_ACCESS`) the account's entry on the station."""
    ancienne, descripteur = ctypes.c_void_p(), ctypes.c_void_p()
    code = adv.GetSecurityInfo(ctypes.c_void_p(station), _SE_WINDOW_OBJECT, _DACL_SECURITY_INFORMATION,
                               None, None, ctypes.byref(ancienne), None, ctypes.byref(descripteur))
    if code:
        raise ProviderIndisponible(f"station de l'agent : DACL illisible (erreur Windows {code})")
    nouvelle = _acl(adv, ancienne.value, [(sid, _DROITS_STATION, mode)])
    code = adv.SetSecurityInfo(ctypes.c_void_p(station), _SE_WINDOW_OBJECT, _DACL_SECURITY_INFORMATION,
                               None, None, ctypes.c_void_p(nouvelle), None)
    if code and mode == _SET_ACCESS:
        raise ProviderIndisponible(f"station de l'agent : entrée du compte refusée (erreur Windows {code})")


def _descripteur(adv: Any, sids: list[bytes]) -> tuple[Any, _Attributs]:
    """Security attributes whose DACL names only ``sids``."""
    dacl = _acl(adv, None, [(sid, _DROITS_BUREAU, _SET_ACCESS) for sid in sids])
    sd = ctypes.create_string_buffer(64)
    if not adv.InitializeSecurityDescriptor(sd, 1) or not adv.SetSecurityDescriptorDacl(
        sd, True, ctypes.c_void_p(dacl), False
    ):
        raise ProviderIndisponible("bureau de l'agent : descripteur de sécurité impossible à bâtir")
    return sd, _Attributs(ctypes.sizeof(_Attributs), ctypes.cast(sd, ctypes.c_void_p), False)


def _nom(u32: Any, objet: int) -> str:
    tampon, taille = ctypes.create_unicode_buffer(256), wintypes.DWORD(0)
    if not u32.GetUserObjectInformationW(ctypes.c_void_p(objet), _UOI_NAME, tampon, 512, ctypes.byref(taille)):
        raise ProviderIndisponible("bureau de l'agent : nom illisible")
    return tampon.value


def _creer_bureau(u32: Any, adv: Any, station: int, sids: list[bytes]) -> int:
    """Creates the desktop in `station`; the process's own station is always put back."""
    _, attributs = _descripteur(adv, sids)
    # La station du processus est un état global : de la lecture de l'origine à son
    # rétablissement, aucun autre fil ne bascule (appels parallèles possibles).
    with _VERROU_STATION:
        origine = u32.GetProcessWindowStation()
        if not u32.SetProcessWindowStation(ctypes.c_void_p(station)):
            raise ProviderIndisponible("bureau de l'agent : bascule sur la station impossible")
        try:
            bureau = u32.CreateDesktopW(f"tessera-{uuid.uuid4().hex[:12]}", None, None, 0,
                                        _DROITS_BUREAU, ctypes.byref(attributs))
        finally:
            u32.SetProcessWindowStation(ctypes.c_void_p(origine))
    if not bureau:
        raise ProviderIndisponible(f"bureau de l'agent impossible à créer (erreur Windows {_CTYPES.get_last_error()})")
    return int(bureau)


def ouvrir_bureau(sid_compte: bytes) -> BureauAgent:
    """Opens a desktop only the agent account and the backend can reach."""
    u32, adv, _ = _dlls()
    moi = _sid_du_processus(os.getpid())
    if not moi:
        raise ProviderIndisponible("bureau de l'agent : SID du backend illisible")
    station = u32.CreateWindowStationW(None, 0, _DROITS_STATION, None)
    if not station:
        raise ProviderIndisponible(f"station de l'agent impossible à ouvrir (erreur Windows {_CTYPES.get_last_error()})")
    try:
        _ENTREES.ouvrir(lambda: _entree_du_compte(adv, station, sid_compte, _SET_ACCESS))
    except ProviderIndisponible:
        u32.CloseWindowStation(ctypes.c_void_p(station))
        raise
    try:
        bureau = _creer_bureau(u32, adv, station, [sid_compte, moi])
        nom = f"{_nom(u32, station)}\\{_nom(u32, bureau)}"
    except ProviderIndisponible:
        _ENTREES.fermer(lambda: _entree_du_compte(adv, station, sid_compte, _REVOKE_ACCESS))
        u32.CloseWindowStation(ctypes.c_void_p(station))
        raise

    def fermer() -> None:
        u32.CloseDesktop(ctypes.c_void_p(bureau))
        _ENTREES.fermer(lambda: _entree_du_compte(adv, station, sid_compte, _REVOKE_ACCESS))
        u32.CloseWindowStation(ctypes.c_void_p(station))

    return BureauAgent(nom, fermer)
