"""The single gateway to the operating system vault (ADR-073).

Windows Credential Manager, macOS Keychain or Secret Service, through
``keyring``. Entries live under the ``tessera`` service, the user name being
the variable name in capitals. This module never imports ``tessera.config``:
the settings read the vault through it, not the other way round.
"""
from typing import Final, Protocol

import keyring
from keyring.backend import KeyringBackend
from keyring.backends import fail, null
from keyring.errors import NoKeyringError, PasswordDeleteError

SERVICE: Final = "tessera"

#: Les onze secrets rangés au coffre (design §1) : tout le reste reste dans `.env`.
NOMS_SECRETS: Final[tuple[str, ...]] = (
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "VERCEL_TOKEN",
    "NEON_API_KEY",
    "RESEND_API_KEY",
    "STRIPE_API_KEY",
    "CLOUDFLARE_API_TOKEN",
    "STATIC_TOKEN",
    "FORBIDDEN_TERMS",
    "AGENT_LOGON_PASSWORD",
    "AGENT_OAUTH_TOKEN",
)


class CoffreAbsent(Exception):
    """No usable vault on this machine."""


class CoffreEnErreur(Exception):
    """The vault exists, but the call failed (locked, refused, value mangled)."""


class Coffre(Protocol):
    """What the backend may do with the vault."""

    def lire(self, nom: str) -> str | None:
        """Return the stored value, or None when the entry is missing."""

    def ecrire(self, nom: str, valeur: str) -> None:
        """Store a value, read it back, raise CoffreEnErreur if it differs."""

    def supprimer(self, nom: str) -> None:
        """Remove an entry; a missing entry is not an error."""

    def presents(self) -> frozenset[str]:
        """Return the names of NOMS_SECRETS the vault holds."""


class _CoffreKeyring:
    """A ``Coffre`` over one ``keyring`` backend."""

    def __init__(self, backend: KeyringBackend) -> None:
        self._backend = backend

    def lire(self, nom: str) -> str | None:
        """Return the stored value, or None when the entry is missing."""
        echec: str | None = None
        try:
            return self._backend.get_password(SERVICE, nom)
        except NoKeyringError:
            echec = "absent"
        except Exception as erreur:  # noqa: BLE001 — toute panne du coffre
            echec = type(erreur).__name__
        # Levée hors du bloc `except` : l'erreur de `keyring` peut citer le nom
        # ou la valeur, elle ne doit pas survivre en `__context__`.
        raise _erreur("lecture", echec)

    def ecrire(self, nom: str, valeur: str) -> None:
        """Store a value, read it back, raise CoffreEnErreur if it differs."""
        echec: str | None = None
        try:
            self._backend.set_password(SERVICE, nom, valeur)
        except NoKeyringError:
            echec = "absent"
        except Exception as erreur:  # noqa: BLE001
            echec = type(erreur).__name__
        if echec is not None:
            raise _erreur("écriture", echec)
        # Relire toujours : une entrée trop longue pourrait être tronquée sans bruit.
        if self.lire(nom) != valeur:
            raise CoffreEnErreur("écriture dans le coffre : la relecture diffère")

    def supprimer(self, nom: str) -> None:
        """Remove an entry; a missing entry is not an error."""
        if self.lire(nom) is None:
            return
        echec: str | None = None
        try:
            self._backend.delete_password(SERVICE, nom)
        except PasswordDeleteError:
            return
        except Exception as erreur:  # noqa: BLE001
            echec = type(erreur).__name__
        if echec is not None:
            raise _erreur("suppression", echec)

    def presents(self) -> frozenset[str]:
        """Return the names of NOMS_SECRETS the vault holds."""
        return frozenset(nom for nom in NOMS_SECRETS if self.lire(nom) is not None)


def _erreur(operation: str, echec: str | None) -> Exception:
    """Build a value-free error: only the operation and the exception type."""
    if echec == "absent":
        return CoffreAbsent(f"{operation} dans le coffre : aucun coffre utilisable")
    return CoffreEnErreur(f"{operation} dans le coffre impossible ({echec})")


def coffre_du_systeme() -> Coffre:
    """Return the vault of this machine.

    Raise CoffreAbsent for keyring's fail and null backends: ``null`` answers
    "missing" and drops writes, so a migration would believe it had written.
    """
    try:
        backend = keyring.get_keyring()
    except Exception as erreur:  # noqa: BLE001
        nom_erreur = type(erreur).__name__
    else:
        if isinstance(backend, (fail.Keyring, null.Keyring)):
            raise CoffreAbsent("aucun coffre utilisable sur cette machine")
        return _CoffreKeyring(backend)
    raise CoffreEnErreur(f"ouverture du coffre impossible ({nom_erreur})")
