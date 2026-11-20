"""Tests of the system vault gateway (ticket-794, ADR-073).

Every test installs an in-memory ``keyring`` backend: none reaches the real
vault of the machine.
"""
from collections.abc import Iterator

import keyring
import keyring.core
import pytest
from keyring.backend import KeyringBackend
from keyring.backends import fail, null
from keyring.errors import KeyringLocked

from tessera import coffre
from tessera.coffre import CoffreAbsent, CoffreEnErreur, coffre_du_systeme

VALEUR_FACTICE = "valeur-factice-0123456789"


class _MemoireKeyring(KeyringBackend):
    """Keyring backend that keeps its entries in a dict."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.entrees: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.entrees.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.entrees[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if (service, username) not in self.entrees:
            raise keyring.errors.PasswordDeleteError("absent")
        del self.entrees[(service, username)]


class _TronqueKeyring(_MemoireKeyring):
    """Backend that silently keeps only the first characters."""

    def set_password(self, service: str, username: str, password: str) -> None:
        self.entrees[(service, username)] = password[:4]


class _VerrouilleKeyring(_MemoireKeyring):
    """Backend whose every call reports a locked vault."""

    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringLocked(f"locked while reading {username}")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise KeyringLocked(f"locked while writing {password}")


@pytest.fixture
def poser_backend() -> Iterator[object]:
    """Install a backend for one test, then put the previous one back."""
    precedent = keyring.core._keyring_backend

    def poser(backend: KeyringBackend) -> KeyringBackend:
        keyring.set_keyring(backend)
        return backend

    yield poser
    keyring.core._keyring_backend = precedent


def test_noms_secrets_lists_the_eleven_names() -> None:
    assert coffre.NOMS_SECRETS == (
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
    assert coffre.SERVICE == "tessera"


def test_lire_returns_none_for_a_missing_entry(poser_backend) -> None:
    poser_backend(_MemoireKeyring())
    assert coffre_du_systeme().lire("VERCEL_TOKEN") is None


def test_ecrire_then_lire_round_trips(poser_backend) -> None:
    backend = poser_backend(_MemoireKeyring())
    le_coffre = coffre_du_systeme()
    le_coffre.ecrire("VERCEL_TOKEN", VALEUR_FACTICE)
    assert le_coffre.lire("VERCEL_TOKEN") == VALEUR_FACTICE
    assert backend.entrees == {("tessera", "VERCEL_TOKEN"): VALEUR_FACTICE}


def test_ecrire_fails_when_the_vault_returns_another_value(poser_backend) -> None:
    poser_backend(_TronqueKeyring())
    with pytest.raises(CoffreEnErreur):
        coffre_du_systeme().ecrire("VERCEL_TOKEN", VALEUR_FACTICE)


def test_supprimer_missing_entry_is_a_noop(poser_backend) -> None:
    poser_backend(_MemoireKeyring())
    le_coffre = coffre_du_systeme()
    le_coffre.supprimer("VERCEL_TOKEN")
    le_coffre.ecrire("VERCEL_TOKEN", VALEUR_FACTICE)
    le_coffre.supprimer("VERCEL_TOKEN")
    assert le_coffre.lire("VERCEL_TOKEN") is None


def test_presents_only_lists_known_names(poser_backend) -> None:
    backend = poser_backend(_MemoireKeyring())
    backend.entrees[("tessera", "AUTRE_CHOSE")] = "x"
    backend.entrees[("autre-service", "GITHUB_TOKEN")] = "x"
    coffre_du_systeme().ecrire("STATIC_TOKEN", VALEUR_FACTICE)
    assert coffre_du_systeme().presents() == frozenset({"STATIC_TOKEN"})


def test_coffre_du_systeme_raises_absent_for_the_fail_backend(poser_backend) -> None:
    poser_backend(fail.Keyring())
    with pytest.raises(CoffreAbsent):
        coffre_du_systeme()


def test_coffre_du_systeme_raises_absent_for_the_null_backend(poser_backend) -> None:
    poser_backend(null.Keyring())
    with pytest.raises(CoffreAbsent):
        coffre_du_systeme()


def test_a_locked_vault_raises_coffre_en_erreur(poser_backend) -> None:
    poser_backend(_VerrouilleKeyring())
    with pytest.raises(CoffreEnErreur):
        coffre_du_systeme().lire("GITHUB_TOKEN")
    with pytest.raises(CoffreEnErreur):
        coffre_du_systeme().presents()


def test_error_messages_never_hold_a_secret_value(poser_backend) -> None:
    poser_backend(_VerrouilleKeyring())
    with pytest.raises(CoffreEnErreur) as ecriture:
        coffre_du_systeme().ecrire("GITHUB_TOKEN", VALEUR_FACTICE)
    poser_backend(_TronqueKeyring())
    with pytest.raises(CoffreEnErreur) as relecture:
        coffre_du_systeme().ecrire("GITHUB_TOKEN", VALEUR_FACTICE)
    for erreur in (ecriture.value, relecture.value):
        texte = f"{erreur} {erreur!r} {erreur.__cause__!r} {erreur.__context__!r}"
        assert VALEUR_FACTICE not in texte
        assert VALEUR_FACTICE[:4] not in str(erreur)
        assert "GITHUB_TOKEN" not in str(erreur)
