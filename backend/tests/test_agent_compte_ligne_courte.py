"""The CLI command line fits Windows' 1 024 characters under the agent account (ticket-946)."""
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from anyio.abc import Process
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from pydantic import SecretStr

from tessera.config import settings
from tessera.services.providers.agent_sdk import _build_options
from tessera.services.providers.fichiers_appel import creer_dossier_d_appel, deporter_les_valeurs, supprimer_dossier_d_appel
from tessera.services.providers.lanceur_windows import LIMITE_LIGNE, LanceurWindows, ligne_de_commande, message_de_logon
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.transport_agent import TransportCompteAgent, transport_du_compte


@pytest.fixture(autouse=True)
def sans_droits_reels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le droit d'écriture par appel (ticket-943) a ses propres tests : ici, pas d'`icacls`."""
    async def rien(*_: object) -> None:
        return None

    monkeypatch.setattr("tessera.services.providers.transport_agent.ouvrir_appel", rien)
    monkeypatch.setattr("tessera.services.providers.transport_agent.clore_appel", rien)


class LanceurEspion:
    """Records the command line and which of its files exist at launch time."""

    def __init__(self, echec: bool = False) -> None:
        self.ligne = ""
        self.fichiers: list[Path] = []
        self.echec = echec

    async def lancer(
        self, commande: Sequence[str], *, compte: str, mot_de_passe: str,
        env: Mapping[str, str], cwd: str | None, avec_stderr: bool,
    ) -> Process:
        self.ligne = ligne_de_commande(commande)
        self.fichiers = [Path(a) for a in commande if Path(a).is_absolute() and Path(a).exists()
                         and "tessera-appel-" in a]
        if self.echec:
            raise ProviderIndisponible("refus")
        raise RuntimeError("stop")


async def _icacls_ok(args: list[str]) -> tuple[int, str]:
    return 0, ""


@pytest.fixture(autouse=True)
def compte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tessera.services.providers.fichiers_appel._icacls_reel", _icacls_ok)
    monkeypatch.setattr(settings, "agent_user", "agent-test")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("mdp-factice"))
    monkeypatch.setattr(settings, "agent_oauth_token", SecretStr("jeton-factice"))


def _options() -> ClaudeAgentOptions:
    return _build_options(
        system="règle détaillée " * 600, model="m", max_turns=1, max_budget_usd=None,
        cwd=Path.cwd(), allowed_tools=["Read", "Write", "Edit", "Bash"], compte_agent=True,
    )


async def _connecter(lanceur: LanceurEspion) -> TransportCompteAgent:
    transport = transport_du_compte("p", _options(), lanceur, compte_agent=True)
    assert isinstance(transport, TransportCompteAgent)
    with pytest.raises((RuntimeError, ProviderIndisponible)):
        await transport.connect()
    return transport


async def test_realistic_coder_command_fits_the_limit() -> None:
    lanceur = LanceurEspion()
    await _connecter(lanceur)
    assert 0 < len(lanceur.ligne) <= LIMITE_LIGNE
    assert "--system-prompt-file" in lanceur.ligne


def test_line_over_the_limit_is_refused_with_its_length() -> None:
    with pytest.raises(ProviderIndisponible, match=r"1101 caractères, au plus 1024"):
        ligne_de_commande(["x" * 1101])


async def test_windows_launcher_refuses_before_any_windows_call() -> None:
    with pytest.raises(ProviderIndisponible, match="au plus 1024"):
        await LanceurWindows().lancer(
            ["x" * 2000], compte="c", mot_de_passe="m", env={}, cwd=None, avec_stderr=False
        )


def test_invalid_parameter_is_not_reported_as_a_refused_logon() -> None:
    texte = message_de_logon(-2147024809, "agent-test")
    assert "logon" not in texte and "invalide" in texte
    assert "logon" in message_de_logon(1326, "agent-test")
    assert "accès refusé" in message_de_logon(5, "agent-test")


async def test_call_files_are_removed_after_close() -> None:
    lanceur = LanceurEspion()
    transport = await _connecter(lanceur)
    assert lanceur.fichiers == [] or all(not f.exists() for f in lanceur.fichiers)
    assert transport._dossier_d_appel is None  # noqa: SLF001
    await transport.close()


async def test_call_files_exist_during_launch_and_vanish_when_launch_fails() -> None:
    lanceur = LanceurEspion(echec=True)
    await _connecter(lanceur)
    assert lanceur.fichiers
    assert all(not f.exists() for f in lanceur.fichiers)
    assert all(not f.parent.exists() for f in lanceur.fichiers)


async def test_call_folder_is_removed_by_close_after_a_launch() -> None:
    dossier = await creer_dossier_d_appel("agent-test")
    (dossier / "a.txt").write_text("x", encoding="utf-8")
    supprimer_dossier_d_appel(dossier)
    assert not dossier.exists()
    supprimer_dossier_d_appel(None)


def test_only_long_json_and_prompts_move_to_files(tmp_path: Path) -> None:
    long_json = json.dumps({"mcpServers": {"a": "b" * 300}})
    commande = ["cli", "--system-prompt", "court", "--append-system-prompt", "z" * 300,
                "--settings", long_json, "--mcp-config", "C:/deja/un/chemin.json", "--verbose"]
    sortie = deporter_les_valeurs(commande, tmp_path)
    assert sortie[:3] == ["cli", "--system-prompt", "court"]
    assert "--append-system-prompt-file" in sortie and "--verbose" in sortie
    assert "C:/deja/un/chemin.json" in sortie
    fichier = Path(sortie[sortie.index("--settings") + 1])
    assert fichier.read_text(encoding="utf-8") == long_json


class LanceurQuiReussit(LanceurEspion):
    """Starts a fake process; records the call files that exist at launch."""

    async def lancer(
        self, commande: Sequence[str], *, compte: str, mot_de_passe: str,
        env: Mapping[str, str], cwd: str | None, avec_stderr: bool,
    ) -> Process:
        self.ligne = ligne_de_commande(commande)
        self.fichiers = [Path(a) for a in commande if "tessera-appel-" in a and Path(a).exists()]
        faux: Any = SimpleNamespace(pid=4242, stdout=None, stderr=None, stdin=None)
        return faux  # type: ignore[no-any-return]


async def test_call_files_outlive_a_successful_launch_and_vanish_on_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fermeture_du_parent(self: SubprocessCLITransport) -> None:
        return None

    monkeypatch.setattr(SubprocessCLITransport, "close", fermeture_du_parent)
    lanceur = LanceurQuiReussit()
    transport = transport_du_compte("p", _options(), lanceur, compte_agent=True)
    assert isinstance(transport, TransportCompteAgent)
    await transport.connect()
    assert lanceur.fichiers, "le prompt système long doit passer par un fichier"
    assert all(f.exists() for f in lanceur.fichiers)  # le CLI les lit pendant tout l'appel
    await transport.close()
    assert all(not f.exists() for f in lanceur.fichiers)
    assert all(not f.parent.exists() for f in lanceur.fichiers)
