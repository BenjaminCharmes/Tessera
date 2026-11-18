"""Tests for the LOW findings of the 17/11 audit (ticket-1001)."""
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.creation_projet.hook_pre_push import BaseDesRunsIllisible, main, projets_avec_run_ouvert
from tessera.services.verification.env_du_code_de_projet import env_du_code_de_projet, est_un_nom_de_secret
from tessera.services.verification.lancement_compte import EchecLancementCompte, env_du_compte
from tessera.services.verification.relance_instable import _commande, relancer_les_instables
from tessera.services.worktrees.dossier_agent import DossierAgentRefuse, refuser_droit_herite

_RACINE = Path(__file__).resolve().parents[2]


def test_extra_cannot_bring_a_secret_back() -> None:
    env = env_du_code_de_projet({"MON_TOKEN": "x", "github_token": "x", "API_KEY": "x", "OK": "1"})
    assert env["OK"] == "1"
    assert not [n for n in ("MON_TOKEN", "github_token", "API_KEY") if n in env]
    assert est_un_nom_de_secret("db_password")


def test_account_env_filters_extra_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr("tessera.services.verification.lancement_compte.path_du_compte", lambda: "C:\\outils")
    env = env_du_compte({"DB_PASSWORD": "x", "MODE": "test"})
    assert "DB_PASSWORD" not in env
    assert env["MODE"] == "test"


def test_account_env_refuses_path_in_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    with pytest.raises(EchecLancementCompte):
        env_du_compte({"Path": "C:\\autre"})


def test_retry_command_puts_files_after_double_dash() -> None:
    assert _commande("vitest", ["a.test.ts"]) == ["npx", "vitest", "run", "a.test.ts"]
    assert _commande("pytest", ["tests/test_a.py"])[-2:] == ["--", "tests/test_a.py"]


@pytest.mark.parametrize("genre", ["pytest", "vitest"])
def test_retry_command_refuses_a_name_starting_with_dash(genre: str) -> None:
    with pytest.raises(ValueError):
        _commande(genre, ["--rootdir=/x"])


async def test_retry_is_skipped_for_a_dash_name(tmp_path: Path) -> None:
    sortie = "FAILED --evil.py::test_a - Failed: Timeout >5.0s"

    async def executer(cmd: list[str], cwd: Path) -> tuple[int, str]:
        raise AssertionError("must not run")

    assert await relancer_les_instables(sortie, [], tmp_path, tmp_path, executer) is None


def test_password_file_is_created_with_its_final_acl() -> None:
    texte = (_RACINE / "scripts" / "agent-setup-admin.ps1").read_text(encoding="ascii")
    assert texte.index("SetAccessRuleProtection") < texte.index("System.IO.FileStream")
    assert texte.index("System.IO.FileStream") < texte.index("$Flux.Write")
    assert "New-Item -ItemType File" not in texte
    assert "Set-Content -LiteralPath $Remise" not in texte


def test_pre_push_runs_the_vault_from_tessera_root() -> None:
    hook = SourceFileLoader("pre_push", str(_RACINE / "scripts" / "hooks" / "pre-push")).load_module()
    vus: dict[str, object] = {}

    def lancer(cmd: list[str], **kw: object) -> "subprocess.CompletedProcess[str]":
        vus.update(kw)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    hook.load_forbidden_terms(_RACINE, lancer)
    assert vus["cwd"] == _RACINE


async def test_inherited_right_for_users_is_refused(tmp_path: Path) -> None:
    async def icacls(args: list[str]) -> tuple[int, str]:
        return 0, f"{tmp_path} BUILTIN\\Users:(I)(OI)(CI)(RX)\n NT AUTHORITY\\SYSTEM:(OI)(CI)(F)\n"

    with pytest.raises(DossierAgentRefuse):
        await refuser_droit_herite(tmp_path, "tessera-agent", icacls)


async def test_inherited_right_for_the_agent_account_is_refused(tmp_path: Path) -> None:
    async def icacls(args: list[str]) -> tuple[int, str]:
        return 0, f"{tmp_path} PC\\tessera-agent:(I)(RX)\n"

    with pytest.raises(DossierAgentRefuse):
        await refuser_droit_herite(tmp_path, "tessera-agent", icacls)


async def test_explicit_rights_are_accepted(tmp_path: Path) -> None:
    async def icacls(args: list[str]) -> tuple[int, str]:
        return 0, f"{tmp_path} PC\\tessera-agent:(RX)\n NT AUTHORITY\\SYSTEM:(OI)(CI)(F)\n"

    await refuser_droit_herite(tmp_path, "tessera-agent", icacls)


def test_doctor_checks_inherited_rights() -> None:
    texte = (_RACINE / "scripts" / "tessera.ps1").read_text(encoding="utf-8-sig")
    assert "IsInherited" in texte and "S-1-5-32-545" in texte


def test_unreadable_runs_database_is_not_read_as_no_open_run(tmp_path: Path) -> None:
    base = tmp_path / "t.db"
    base.write_bytes(b"not a sqlite database at all" * 10)
    with pytest.raises(BaseDesRunsIllisible):
        projets_avec_run_ouvert(base)


def test_command_refuses_without_installing_when_database_is_unreadable(tmp_path: Path) -> None:
    espace = tmp_path / "ws"
    projet = espace / "p"
    (projet / ".git").mkdir(parents=True)
    base = tmp_path / "t.db"
    base.write_bytes(b"not a sqlite database at all" * 10)
    assert main(espace, base) == 1
    assert not (projet / ".git" / "hooks" / "pre-push").exists()
