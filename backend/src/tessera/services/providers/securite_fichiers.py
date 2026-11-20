"""Reading and taking back the security of a file by handle — ticket-1027.

ADR-091, ADR-083. Implémentation réelle de `SecuriteFichiers` en `ctypes` (pas
de `pywin32`). Chaque entrée s'ouvre par un handle `FILE_FLAG_OPEN_REPARSE_POINT` :
jamais par un chemin qui résoudrait la cible d'un lien.
"""
import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

_CTYPES: Any = ctypes

_READ_CONTROL = 0x20000
_WRITE_DAC = 0x40000
_WRITE_OWNER = 0x80000
_SHARE_TOUT = 0x7
_OPEN_EXISTING = 3
_BACKUP_SEMANTICS = 0x02000000
_OPEN_REPARSE_POINT = 0x00200000
_SE_FILE_OBJECT = 1
_OWNER = 0x1
_DACL = 0x4
_DACL_NON_PROTEGEE = 0x20000000
_SE_DACL_PROTECTED = 0x1000
_ERREUR_FICHIER_ABSENT = (2, 3)


@dataclass(frozen=True)
class InfoSecurite:
    """What the take-back needs to know about one entry."""

    proprietaire_sid: str
    dacl_protegee: bool


class SecuriteFichiers(Protocol):
    """Reads and takes back the security of one entry, never following a link."""

    def sid_de(self, compte: str) -> str: ...

    def lire(self, chemin: Path) -> InfoSecurite: ...

    def reprendre(self, chemin: Path, backend_sid: str, *, proprietaire_seul: bool) -> None: ...


class SecuriteNulle:
    """Hors Windows : aucune entrée n'appartient au compte, rien à reprendre."""

    def sid_de(self, compte: str) -> str:
        return compte

    def lire(self, chemin: Path) -> InfoSecurite:
        return InfoSecurite(proprietaire_sid="", dacl_protegee=False)

    def reprendre(self, chemin: Path, backend_sid: str, *, proprietaire_seul: bool) -> None:
        return None


def chemin_long(chemin: Path) -> str:
    """The path as Windows opens it beyond 260 characters: absolute, extended-length prefix.

    Sans lui, une entrée profonde (un `node_modules`) se lisait « absente » et
    restait au compte, sans bruit (preuve du 20/11).
    """
    texte = str(chemin)
    if sys.platform != "win32" or texte.startswith("\\\\") or not chemin.is_absolute():
        return texte
    return "\\\\?\\" + texte


def _erreur(chemin: Path, action: str) -> OSError:
    code = int(_CTYPES.get_last_error())
    if code in _ERREUR_FICHIER_ABSENT:
        return FileNotFoundError(str(chemin))
    return OSError(f"{action} a échoué (erreur Windows {code}) sur {chemin}")


class SecuriteWindows:
    """`SecuriteFichiers` over `advapi32`; tests réels ignorés hors Windows."""

    def __init__(self) -> None:
        self._k32: Any = _CTYPES.WinDLL("kernel32", use_last_error=True)
        self._adv: Any = _CTYPES.WinDLL("advapi32", use_last_error=True)
        self._k32.CreateFileW.restype = wintypes.HANDLE
        self._k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                          wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self._k32.LocalFree.argtypes = [ctypes.c_void_p]
        self._adv.GetSecurityInfo.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        self._adv.SetSecurityInfo.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        self._adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self._adv.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p]
        self._adv.GetSecurityDescriptorControl.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

    def _ouvrir(self, chemin: Path, acces: int) -> int:
        poignee = self._k32.CreateFileW(chemin_long(chemin), acces, _SHARE_TOUT, None, _OPEN_EXISTING,
                                        _BACKUP_SEMANTICS | _OPEN_REPARSE_POINT, None)
        if poignee in (None, wintypes.HANDLE(-1).value):
            raise _erreur(chemin, "ouverture")
        return int(poignee)

    def sid_de(self, compte: str) -> str:
        from tessera.services.providers.processus_compte import sid_du_compte

        brut = sid_du_compte(compte)
        tampon = ctypes.create_string_buffer(brut)
        texte = ctypes.c_void_p()
        if not self._adv.ConvertSidToStringSidW(ctypes.addressof(tampon), ctypes.byref(texte)):
            raise OSError(f"SID de {compte} illisible")
        valeur = str(ctypes.wstring_at(texte.value or 0))
        self._k32.LocalFree(texte)
        return valeur

    def lire(self, chemin: Path) -> InfoSecurite:
        poignee = self._ouvrir(chemin, _READ_CONTROL)
        try:
            proprietaire, descripteur = ctypes.c_void_p(), ctypes.c_void_p()
            if self._adv.GetSecurityInfo(poignee, _SE_FILE_OBJECT, _OWNER | _DACL, ctypes.byref(proprietaire),
                                         None, None, None, ctypes.byref(descripteur)) != 0:
                raise OSError(f"lecture de la sécurité refusée sur {chemin}")
            try:
                return InfoSecurite(self._sid_texte(proprietaire), self._protegee(descripteur))
            finally:
                self._k32.LocalFree(descripteur)
        finally:
            self._k32.CloseHandle(poignee)

    def _sid_texte(self, sid: ctypes.c_void_p) -> str:
        texte = ctypes.c_void_p()
        if not self._adv.ConvertSidToStringSidW(sid, ctypes.byref(texte)):
            raise OSError("propriétaire illisible")
        valeur = str(ctypes.wstring_at(texte.value or 0))
        self._k32.LocalFree(texte)
        return valeur

    def _protegee(self, descripteur: ctypes.c_void_p) -> bool:
        controle, revision = wintypes.WORD(0), wintypes.DWORD(0)
        if not self._adv.GetSecurityDescriptorControl(descripteur, ctypes.byref(controle), ctypes.byref(revision)):
            raise OSError("contrôle du descripteur illisible")
        return bool(controle.value & _SE_DACL_PROTECTED)

    def reprendre(self, chemin: Path, backend_sid: str, *, proprietaire_seul: bool) -> None:
        poignee = self._ouvrir(chemin, _WRITE_OWNER | _WRITE_DAC | _READ_CONTROL)
        try:
            sid = ctypes.c_void_p()
            if not self._adv.ConvertStringSidToSidW(backend_sid, ctypes.byref(sid)):
                raise OSError(f"SID {backend_sid} invalide")
            try:
                self._changer_proprietaire(poignee, sid, chemin)
                if not proprietaire_seul:
                    self._rendre_a_l_heritage(poignee, chemin)
            finally:
                self._k32.LocalFree(sid)
        finally:
            self._k32.CloseHandle(poignee)

    def _changer_proprietaire(self, poignee: int, sid: ctypes.c_void_p, chemin: Path) -> None:
        if self._adv.SetSecurityInfo(poignee, _SE_FILE_OBJECT, _OWNER, sid, None, None, None) != 0:
            raise OSError(f"changement de propriétaire refusé sur {chemin}")

    def _rendre_a_l_heritage(self, poignee: int, chemin: Path) -> None:
        # ACL vide (en-tête de 8 octets) + drapeau « non protégée » : il ne reste que l'héritage.
        vide = ctypes.create_string_buffer(8)
        self._adv.InitializeAcl(vide, 8, 2)
        if self._adv.SetSecurityInfo(poignee, _SE_FILE_OBJECT, _DACL | _DACL_NON_PROTEGEE, None, None,
                                     ctypes.addressof(vide), None) != 0:
            raise OSError(f"remise à l'héritage refusée sur {chemin}")


def securite_par_defaut() -> SecuriteFichiers:
    """The real implementation on Windows, the null one elsewhere."""
    return SecuriteWindows() if sys.platform == "win32" else SecuriteNulle()
