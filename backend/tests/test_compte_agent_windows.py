"""Real launch under the agent account; skipped without ``TESSERA_TEST_AGENT_USER`` (ticket-894).

Le test lance `whoami`, puis lit le `.env` de Tessera, sous le compte : on
constate le nom, puis le refus. Un troisième lance le vrai CLI en tuyaux.
"""
import os
import sys

import anyio
import pytest

from tessera.config import Settings
from tessera.services.providers.env_agent import CLI_PARTAGE
from tessera.services.providers.transport_agent import fabriquer_lanceur

windows_only = pytest.mark.skipif(
    sys.platform != "win32" or not os.environ.get("TESSERA_TEST_AGENT_USER"),
    reason="needs Windows and TESSERA_TEST_AGENT_USER",
)

COMPTE = os.environ.get("TESSERA_TEST_AGENT_USER", "")
MOT_DE_PASSE = os.environ.get("TESSERA_TEST_AGENT_PASSWORD", "")


async def _sortie(commande: list[str]) -> tuple[str, int]:
    env = {
        "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
        "USERPROFILE": rf"C:\Users\{COMPTE}",
    }
    process = await fabriquer_lanceur().lancer(
        commande, compte=COMPTE, mot_de_passe=MOT_DE_PASSE, env=env, cwd=None, avec_stderr=False
    )
    assert process.stdin is not None and process.stdout is not None
    await process.stdin.aclose()
    morceaux: list[bytes] = []
    with anyio.fail_after(30):
        try:
            while True:
                morceaux.append(await process.stdout.receive())
        except anyio.EndOfStream:
            pass
        code = await process.wait()
    return b"".join(morceaux).decode("utf-8", "replace"), code


@windows_only
async def test_whoami_runs_under_the_agent_account() -> None:
    sortie, code = await _sortie(["whoami"])
    assert code == 0
    assert COMPTE.lower() in sortie.lower()


@windows_only
async def test_agent_account_cannot_read_the_tessera_env_file() -> None:
    sortie, code = await _sortie(["cmd", "/c", "type", str(Settings.env_file)])
    assert code != 0
    assert "VERCEL_TOKEN" not in sortie


@windows_only
async def test_the_shared_cli_answers_through_pipes() -> None:
    sortie, code = await _sortie([CLI_PARTAGE, "--version"])
    assert code == 0
    assert sortie.strip()
