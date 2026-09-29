"""Un rôle qui lit le web n'a pas de shell — ticket-245.

Une page lue peut porter des instructions. Un agent qui a `Bash` et
`acceptEdits` a de quoi les exécuter : `curl` vers l'extérieur, un script. On
ne sait pas filtrer une page ; on sait retirer le shell.
"""
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.par_role import OUTILS_WEB, provider_pour_role
from tessera.services.providers.repli import ProviderAvecRepli

_IDE_CORE = Path(__file__).resolve().parents[2] / "projects" / "ide-core"


@pytest.fixture(autouse=True)
def _sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")


def _projet(tmp_path: Path, **agent: object) -> Path:
    projet = tmp_path / "p"
    projet.mkdir()
    entree = {"role": "architect", "model": "m", "max_tokens": 1, "prompt_file": "x"} | agent
    (projet / "agents.json").write_text(json.dumps({"agents": [entree]}), encoding="utf-8")
    return projet


def _outils(provider: object) -> list[str]:
    assert isinstance(provider, ClaudeAgentSDKProvider)
    return provider._allowed_tools


def test_un_role_web_lit_le_web_et_perd_bash(tmp_path: Path) -> None:
    outils = _outils(provider_pour_role(_projet(tmp_path, web=True), "architect"))

    assert set(OUTILS_WEB) <= set(outils)
    assert "Bash" not in outils
    assert {"Read", "Write", "Edit", "Glob", "Grep"} <= set(outils)


def test_sans_web_rien_ne_change(tmp_path: Path) -> None:
    outils = _outils(provider_pour_role(_projet(tmp_path), "architect"))

    assert outils == ClaudeAgentSDKProvider.ALLOWED_TOOLS


def test_le_web_s_ajoute_a_une_liste_explicite(tmp_path: Path) -> None:
    outils = _outils(
        provider_pour_role(_projet(tmp_path, web=True), "architect", tools=["Read", "Bash"])
    )

    assert outils == ["Read", *OUTILS_WEB]


def test_un_role_sans_outils_ne_gagne_pas_le_web(tmp_path: Path) -> None:
    outils = _outils(
        provider_pour_role(_projet(tmp_path, web=True), "architect", allow_tools=False)
    )

    assert outils == []


def test_le_repli_a_les_memes_outils(tmp_path: Path) -> None:
    projet = _projet(
        tmp_path, web=True, fallback={"provider": "agent_sdk", "model": "m2"}
    )

    provider = provider_pour_role(projet, "architect")

    assert isinstance(provider, ProviderAvecRepli)
    assert _outils(provider._principal) == _outils(provider._repli)
    assert "Bash" not in _outils(provider._repli)


def test_l_architecte_d_ide_core_lit_le_web() -> None:
    manifeste = json.loads((_IDE_CORE / "agents.json").read_text(encoding="utf-8"))
    architecte = next(a for a in manifeste["agents"] if a["role"] == "architect")

    assert architecte.get("web") is True
