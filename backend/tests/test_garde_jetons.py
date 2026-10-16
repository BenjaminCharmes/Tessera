"""The hook refusing Tessera's own `.env` to agents — ADR-053, ticket-464."""
import os
from pathlib import Path
from typing import Any, cast

import pytest
from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from tessera.services.providers.garde_jetons import ENV_REFUS, hook_refus_env_tessera


class _Depot:
    """A fake repository: Tessera's `.env` at the root, a project under it."""

    def __init__(self, racine: Path) -> None:
        self.racine = racine
        self.env = racine / ".env"
        self.exemple = racine / ".env.example"
        self.projet = racine / "projects" / "client"
        self.env_projet = self.projet / ".env"
        self.projet.mkdir(parents=True)
        for fichier in (self.env, self.exemple, self.env_projet):
            fichier.write_text("X=1\n", encoding="utf-8")


@pytest.fixture
def depot(tmp_path: Path) -> _Depot:
    return _Depot(tmp_path)


async def _appeler(
    depot: _Depot, outil: str, **entrees: Any
) -> HookJSONOutput:
    hook = hook_refus_env_tessera(depot.projet, env_file=depot.env)
    entree = cast(HookInput, {"tool_name": outil, "tool_input": entrees})
    return await hook(entree, None, cast(HookContext, None))


def _refuse(sortie: HookJSONOutput) -> bool:
    decision = cast(dict[str, Any], sortie).get("hookSpecificOutput", {})
    return bool(decision.get("permissionDecision") == "deny")


# ------------------------------------------------------------------
# Read
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "forme", ["absolu", "relatif", "avec_point_point"]
)
async def test_read_refuses_the_tessera_env(depot: _Depot, forme: str) -> None:
    chemin = {
        "absolu": str(depot.env),
        "relatif": os.path.join("..", "..", ".env"),
        "avec_point_point": str(depot.projet / ".." / ".." / ".env"),
    }[forme]

    sortie = await _appeler(depot, "Read", file_path=chemin)

    assert _refuse(sortie)
    reponse = cast(dict[str, Any], sortie)["hookSpecificOutput"]
    assert reponse["permissionDecisionReason"] == ENV_REFUS


def test_the_refusal_says_what_the_guard_cannot_do() -> None:
    assert "évasion" in ENV_REFUS
    assert "portée" in ENV_REFUS


async def test_read_lets_the_example_and_the_project_env_through(depot: _Depot) -> None:
    for chemin in (depot.exemple, depot.env_projet, depot.projet / "x.py"):
        assert not _refuse(await _appeler(depot, "Read", file_path=str(chemin)))
    assert not _refuse(await _appeler(depot, "Read", file_path=".env"))


# ------------------------------------------------------------------
# Glob
# ------------------------------------------------------------------


@pytest.mark.parametrize("motif", ["../../.env", "../../.en*"])
async def test_glob_refuses_a_relative_pattern_reaching_the_env(
    depot: _Depot, motif: str
) -> None:
    assert _refuse(await _appeler(depot, "Glob", pattern=motif))


async def test_glob_refuses_an_absolute_pattern_and_a_search_from_the_root(
    depot: _Depot,
) -> None:
    assert _refuse(await _appeler(depot, "Glob", pattern=str(depot.env)))
    assert _refuse(await _appeler(depot, "Glob", pattern=".env", path=str(depot.racine)))
    assert _refuse(await _appeler(depot, "Glob", pattern="**/.env", path=str(depot.racine)))


async def test_glob_lets_the_example_the_project_env_and_wildcards_through(
    depot: _Depot,
) -> None:
    assert not _refuse(await _appeler(depot, "Glob", pattern=".env.example", path=str(depot.racine)))
    assert not _refuse(await _appeler(depot, "Glob", pattern=".env"))
    assert not _refuse(await _appeler(depot, "Glob", pattern="**/*.py", path=str(depot.racine)))
    assert not _refuse(await _appeler(depot, "Glob", pattern="*", path=str(depot.racine)))


# ------------------------------------------------------------------
# Grep
# ------------------------------------------------------------------


@pytest.mark.parametrize("chemin", ["absolu", "relatif", "avec_point_point"])
async def test_grep_refuses_the_tessera_env_as_path(depot: _Depot, chemin: str) -> None:
    valeur = {
        "absolu": str(depot.env),
        "relatif": os.path.join("..", "..", ".env"),
        "avec_point_point": str(depot.projet / ".." / ".." / ".env"),
    }[chemin]

    assert _refuse(await _appeler(depot, "Grep", pattern="TOKEN", path=valeur))


async def test_grep_refuses_a_glob_naming_the_env(depot: _Depot) -> None:
    sortie = await _appeler(depot, "Grep", pattern="TOKEN", path=str(depot.racine), glob=".env")

    assert _refuse(sortie)


async def test_grep_lets_the_example_and_the_project_env_through(depot: _Depot) -> None:
    for chemin in (depot.exemple, depot.env_projet, depot.projet):
        assert not _refuse(await _appeler(depot, "Grep", pattern="X", path=str(chemin)))
    assert not _refuse(await _appeler(depot, "Grep", pattern="X"))


# ------------------------------------------------------------------
# Bash
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "commande",
    [
        "cat {abs}",
        "cat ../../.env",
        'cat "../../.env"',
        "type ..\\..\\.env",
        "Get-Content ..\\..\\.env",
        "Get-Content -Path ..\\..\\.env | Select-String TOKEN",
        "grep TOKEN ../../.env && echo fin",
        "docker run --env-file=../../.env app",
    ],
)
async def test_bash_refuses_a_command_reading_the_tessera_env(
    depot: _Depot, commande: str
) -> None:
    sortie = await _appeler(depot, "Bash", command=commande.format(abs=depot.env.as_posix()))

    assert _refuse(sortie)


@pytest.mark.skipif(os.name != "nt", reason="Git Bash path style only exists on Windows")
async def test_bash_refuses_the_git_bash_spelling_of_the_path(depot: _Depot) -> None:
    lecteur = depot.env.drive[0].lower()
    commande = f"cat /{lecteur}/{depot.env.as_posix()[3:]}"

    assert _refuse(await _appeler(depot, "Bash", command=commande))


@pytest.mark.parametrize(
    "commande",
    [
        "ls -la",
        "uv run pytest -q",
        "cat .env",
        "cat ../../.env.example",
        "cat .env.example",
        "type .env",
        "echo environnement",
    ],
)
async def test_bash_lets_an_unrelated_command_through(depot: _Depot, commande: str) -> None:
    assert not _refuse(await _appeler(depot, "Bash", command=commande))


async def test_other_tools_are_ignored(depot: _Depot) -> None:
    sortie = await _appeler(depot, "Write", file_path=str(depot.env), content="x")

    assert sortie == {}


async def test_without_a_cwd_an_absolute_path_is_still_refused(depot: _Depot) -> None:
    hook = hook_refus_env_tessera(None, env_file=depot.env)
    entree = cast(HookInput, {"tool_name": "Read", "tool_input": {"file_path": str(depot.env)}})

    assert _refuse(await hook(entree, None, cast(HookContext, None)))


def test_the_hook_is_installed_on_every_agent_call(tmp_path: Path) -> None:
    # Un garde écrit mais jamais branché donne l'apparence d'une protection.
    from tessera.services.providers.agent_sdk import _build_options

    options = _build_options(
        system="s", model="m", max_turns=1, max_budget_usd=None, cwd=tmp_path
    )

    matchers = (options.hooks or {})["PreToolUse"]
    assert "Read|Glob|Grep|Bash" in {m.matcher for m in matchers}
