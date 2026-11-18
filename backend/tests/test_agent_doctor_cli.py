"""ticket-983: the doctor launches the tools under the agent account."""
import asyncio
from pathlib import Path

import pytest
from pydantic import SecretStr

from tessera import agent_doctor_cli
from tessera.agent_doctor_cli import DOSSIER_OUTILS, verifier_outils
from tessera.config import settings
from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.verification import lancement_compte
from tessera.services.verification.chaine_python import CHAINE_PYTHON
from tests.chaine_factice import chaine_factice  # noqa: F401
from tests.doubles_compte import LanceurDouble, ProcessDouble


class ProcessLent(ProcessDouble):
    async def wait(self) -> int:
        await asyncio.sleep(10)
        return 0


CACHE_AGENT = "C:/Users/tessera-agent/AppData/Local/npm-cache".replace("/", chr(92)).encode()


class LanceurNeuf(LanceurDouble):
    """Gives a fresh process per call, whose output is the npm cache folder."""

    def __init__(self, cache: bytes = CACHE_AGENT) -> None:
        super().__init__()
        self._cache = cache

    async def lancer(self, commande, **kwargs):  # type: ignore[no-untyped-def]
        self.processus = ProcessDouble(sortie=self._cache)
        return await super().lancer(commande, **kwargs)


@pytest.fixture
def compte(monkeypatch: pytest.MonkeyPatch, chaine: Path) -> None:
    (chaine / "uv").mkdir()
    (chaine / "uv" / "uv.exe").write_bytes(b"")
    (chaine / "node" / "npm.cmd").write_bytes(b"")
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("pw-secret"))


async def test_all_tools_ok(compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lanceur = LanceurNeuf()
    assert await verifier_outils(tmp_path, lanceur) == 0
    sortie = capsys.readouterr().out
    commandes = [a["commande"] for a in lanceur.appels]
    assert [c[0].replace(chr(92), "/").rsplit("/", 1)[-1] for c in commandes] == [
        "node.exe", "uv.exe", "uv.exe", "npm.cmd",
    ]
    assert commandes[2][1:] == ["run", "--no-project", "python", "--version"]
    assert sortie.count(": ok") == 4
    assert "pw-secret" not in sortie


async def test_one_tool_failing_stops_and_names_it(
    compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lanceur = LanceurDouble(refus="EPERM")
    assert await verifier_outils(tmp_path, lanceur) == 1
    sortie = capsys.readouterr().out
    assert "node" in sortie and "EPERM" in sortie and "agent setup" in sortie
    assert len(lanceur.appels) >= 1 and "uv :" not in sortie


async def test_non_zero_exit_code_fails(compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lanceur = LanceurDouble(ProcessDouble(code=2))
    assert await verifier_outils(tmp_path, lanceur) == 1
    assert "code de sortie 2" in capsys.readouterr().out


async def test_timeout_fails(compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lanceur = LanceurDouble(ProcessLent())
    assert await verifier_outils(tmp_path, lanceur, delai_s=0.05) == 1
    assert "délai" in capsys.readouterr().out


async def test_missing_password_fails_without_launching(
    monkeypatch: pytest.MonkeyPatch, chaine: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr(""))
    lanceur = LanceurDouble()
    assert await verifier_outils(tmp_path, lanceur) == 1
    assert lanceur.appels == []
    assert "mot de passe" in capsys.readouterr().out


async def test_missing_account_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    assert await verifier_outils(tmp_path, LanceurDouble()) == 1


async def test_npm_cache_under_the_user_profile_fails_naming_agent_setup(
    compte: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lanceur = LanceurNeuf("C:/Users/alice/AppData/Local/npm-cache".replace("/", chr(92)).encode())
    assert await verifier_outils(tmp_path, lanceur) == 1
    sortie = capsys.readouterr().out
    assert "npm cache" in sortie and "profil" in sortie and "agent setup" in sortie


async def test_npm_cache_in_a_sibling_profile_fails(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurNeuf("C:/Users/tessera-agent-2/npm-cache".replace("/", chr(92)).encode())
    assert await verifier_outils(tmp_path, lanceur) == 1


async def test_python_check_gets_the_shared_toolchain_variables(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurNeuf()
    assert await verifier_outils(tmp_path, lanceur) == 0
    env = lanceur.appels[2]["env"]
    assert env["UV_PYTHON_INSTALL_DIR"] == str(CHAINE_PYTHON)
    assert env["UV_PYTHON_PREFERENCE"] == "only-managed"
    assert env["UV_PYTHON_DOWNLOADS"] == "never"
    assert "UV_PYTHON_DOWNLOADS" not in lanceur.appels[0]["env"]


async def test_droits_refused_becomes_a_failure_line(
    compte: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def refuse(dossier: Path) -> Path:
        raise DroitsAgentRefuses("pas un worktree")

    monkeypatch.setattr(lancement_compte, "ouvrir_appel", refuse)
    assert await verifier_outils(tmp_path, LanceurDouble()) == 1
    sortie = capsys.readouterr().out
    assert "ÉCHEC" in sortie and "agent setup" in sortie and "Traceback" not in sortie


def test_main_launches_outside_any_git_repository(
    compte: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    vus: list[Path] = []

    async def espion(dossier: Path) -> int:
        vus.append(dossier)
        return 0

    monkeypatch.chdir(Path(__file__).parent)  # le checkout : backend/tests
    monkeypatch.setattr(agent_doctor_cli, "verifier_outils", espion)
    assert agent_doctor_cli.main() == 0
    assert vus == [DOSSIER_OUTILS]
    assert not any((p / ".git").exists() for p in (DOSSIER_OUTILS, *DOSSIER_OUTILS.parents))


async def test_ouvrir_appel_never_receives_the_repository_root(
    compte: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    recus: list[Path] = []

    async def espion(dossier: Path) -> None:
        recus.append(Path(dossier))

    monkeypatch.setattr(lancement_compte, "ouvrir_appel", espion)
    assert await verifier_outils(DOSSIER_OUTILS, LanceurNeuf()) == 0
    assert recus and all(d == DOSSIER_OUTILS for d in recus)
