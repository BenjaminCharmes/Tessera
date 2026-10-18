"""Un diff qui touche la configuration des tests le dit au reviewer — ticket-490."""
import json
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.services.config_tests_touchee import (
    TITRE_CONFIG_TESTS,
    avertissement_config_tests,
    fichiers_de_config_touches,
)
from tessera.services.diff_changements import lire_diff
from tessera.services.orchestrator import Orchestrator
from tessera.services.validator import ValidatorService
from tests.test_orchestrator import _FakeGit, _make_agent_result, _make_ticket, _noop
from tests.test_providers_base import FakeProvider

_CONFTEST = (
    "diff --git a/backend/tests/conftest.py b/backend/tests/conftest.py\n"
    "--- a/backend/tests/conftest.py\n+++ b/backend/tests/conftest.py\n"
    "@@ -1,2 +1,3 @@\n import pytest\n+import os\n x = 1\n"
)
_VITEST = (
    "diff --git a/frontend/vitest.config.ts b/frontend/vitest.config.ts\n"
    "--- a/frontend/vitest.config.ts\n+++ b/frontend/vitest.config.ts\n"
    "@@ -1,2 +1,2 @@\n-const a = 1\n+const a = 2\n const b = 1\n"
)
_CODE = (
    "diff --git a/backend/src/app.py b/backend/src/app.py\n"
    "--- a/backend/src/app.py\n+++ b/backend/src/app.py\n"
    "@@ -1,1 +1,2 @@\n x = 1\n+y = 2\n"
)
_PYPROJECT = (
    '[project]\nname = "x"\n\n[tool.pytest.ini_options]\naddopts = "-q"\n\n'
    "[tool.ruff]\nline-length = 100\n"
)
_PACKAGE = (
    '{\n  "name": "x",\n  "scripts": {\n    "test": "vitest run"\n  },\n'
    '  "dependencies": {}\n}\n'
)


def _diff_de(chemin: str, debut: int, anciennes: list[str], nouvelles: list[str]) -> str:
    """A one-hunk diff replacing `anciennes` by `nouvelles` from line `debut`."""
    corps = "".join(f"-{t}\n" for t in anciennes) + "".join(f"+{t}\n" for t in nouvelles)
    return (
        f"diff --git a/{chemin} b/{chemin}\n--- a/{chemin}\n+++ b/{chemin}\n"
        f"@@ -{debut},{len(anciennes)} +{debut},{len(nouvelles)} @@\n{corps}"
    )


def test_le_diff_se_lit_ligne_par_ligne() -> None:
    (fichier,) = lire_diff(_CONFTEST)

    assert fichier.chemin == "backend/tests/conftest.py"
    (ajout,) = fichier.changements
    assert (ajout.limite, ajout.ajoute, ajout.texte) == (2, True, "import os")


def test_conftest_et_vitest_sont_nommes() -> None:
    fichiers = fichiers_de_config_touches(_CODE + _CONFTEST + _VITEST, [])

    assert fichiers == ["backend/tests/conftest.py", "frontend/vitest.config.ts"]


def test_un_diff_sans_configuration_ne_porte_pas_davertissement() -> None:
    fichiers = fichiers_de_config_touches(_CODE, [])

    assert fichiers == []
    assert avertissement_config_tests(fichiers) == ""


def test_lavertissement_nomme_les_fichiers() -> None:
    texte = avertissement_config_tests(["backend/tests/conftest.py"])

    assert texte.startswith(f"## {TITRE_CONFIG_TESTS}")
    assert "`backend/tests/conftest.py`" in texte and "affaiblie" in texte


def test_pyproject_ne_compte_que_dans_pytest_ou_mypy(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
    dans_pytest = _diff_de("pyproject.toml", 5, ['addopts = ""'], ['addopts = "-q"'])
    dans_ruff = _diff_de("pyproject.toml", 8, ["line-length = 80"], ["line-length = 100"])

    assert fichiers_de_config_touches(dans_pytest, [tmp_path]) == ["pyproject.toml"]
    assert fichiers_de_config_touches(dans_ruff, [tmp_path]) == []


def test_package_json_ne_compte_que_dans_scripts(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(_PACKAGE, encoding="utf-8")
    dans_scripts = _diff_de("package.json", 4, ['    "test": "vitest"'], ['    "test": "vitest run"'])
    ailleurs = _diff_de("package.json", 6, ['  "dependencies": {"a": 1}'], ['  "dependencies": {}'])

    assert fichiers_de_config_touches(dans_scripts, [tmp_path]) == ["package.json"]
    assert fichiers_de_config_touches(ailleurs, [tmp_path]) == []


def test_un_fichier_qui_ne_se_relit_plus_est_signale(tmp_path: Path) -> None:
    supprime = _diff_de("package.json", 1, ['{"scripts": {}}'], [])

    assert fichiers_de_config_touches(supprime, [tmp_path]) == ["package.json"]


_VERDICT = {
    "criteria": [{"index": 1, "criterion": "c", "passed": True, "note": ""}],
    "feedback": "ok",
}


class _Runner:
    """Records the message the reviewer receives."""

    def __init__(self) -> None:
        self.contextes_reviewer: list[str] = []

    async def run(self, **kwargs: object) -> AgentResult:
        role = kwargs["role"]
        assert isinstance(role, AgentRole)
        if role == AgentRole.reviewer:
            self.contextes_reviewer.append(str(kwargs["project_context"]))
            return _make_agent_result("APPROVED", role=role)
        return _make_agent_result("prose du codeur", role=role)


async def _contexte_du_reviewer(tmp_path: Path, diff: str) -> tuple[str, str]:
    """Run a pipeline whose coder produced `diff`; return reviewer message and log."""
    runner = _Runner()
    service = AsyncMock()
    service.get_ticket.return_value = _make_ticket(
        body="## Critères d'acceptation\n- [ ] ça marche\n"
    )
    log = tmp_path / "memory" / "pipeline-log.md"
    orch = Orchestrator(
        runner=runner, ticket_service=service, project_context="ctx",  # type: ignore[arg-type]
        agent_configs=[], pipeline_log_path=log,
        validator=ValidatorService(
            FakeProvider(content=json.dumps(_VERDICT)), Path("agents/prompts")
        ),
        git_workspace=_FakeGit(diff),  # type: ignore[arg-type]
    )

    await orch.run_pipeline("projet", "ticket-001", _noop)

    (contexte,) = runner.contextes_reviewer
    return contexte, log.read_text(encoding="utf-8")


async def test_le_message_du_reviewer_commence_par_lavertissement(tmp_path: Path) -> None:
    contexte, journal = await _contexte_du_reviewer(tmp_path, _CODE + _CONFTEST + _VITEST)

    assert contexte.startswith(f"## {TITRE_CONFIG_TESTS}")
    entete = contexte.split("ctx", 1)[0]
    assert "`backend/tests/conftest.py`" in entete
    assert "`frontend/vitest.config.ts`" in entete
    assert "configuration des tests modifiée" in journal
    assert "backend/tests/conftest.py, frontend/vitest.config.ts" in journal


async def test_sans_configuration_le_message_du_reviewer_est_inchange(tmp_path: Path) -> None:
    contexte, journal = await _contexte_du_reviewer(tmp_path, _CODE)

    assert TITRE_CONFIG_TESTS not in contexte
    assert "ctx" in contexte
    assert "configuration des tests" not in journal
