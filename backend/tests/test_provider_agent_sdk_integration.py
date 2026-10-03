import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import ResultMessage

from tessera.services.providers import agent_sdk
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_agent_ecrit_un_fichier_reel(tmp_path: Path) -> None:
    """Requires an authenticated Claude Code session (`claude` on PATH)."""
    if shutil.which("claude") is None:
        pytest.skip("CLI Claude Code absent du PATH")

    projet = tmp_path / "projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text(
        "Tout fichier Python commence par le commentaire `# Tessera`.\n",
        encoding="utf-8",
    )

    provider = ClaudeAgentSDKProvider(max_turns=8, max_budget_usd=1.0)
    outils: list[str] = []

    async def on_tool(name: str, _: dict) -> None:
        outils.append(name)

    result = await provider.stream(
        system="Tu es un agent de test. Sois bref.",
        user="Crée hello.py avec une fonction hello() retournant 'bonjour'. "
        "Respecte les conventions du projet.",
        model="claude-sonnet-4-6",
        max_tokens=4096,
        cwd=projet,
        on_tool_use=on_tool,
    )

    cree = projet / "hello.py"
    assert cree.exists(), f"fichier non écrit ; outils appelés : {outils}"
    assert cree.read_text(encoding="utf-8").startswith("# Tessera")
    assert "Write" in outils
    assert result.output_tokens > 0
    assert result.cost_usd is not None


@pytest.mark.asyncio
async def test_opus_5_5_repond_par_le_sdk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bundled Claude Code must accept claude-opus-5-5 (CLI >= 2.1.280)."""
    if shutil.which("claude") is None:
        pytest.skip("CLI Claude Code absent du PATH")

    # Le provider ne remonte pas model_usage : on enveloppe query pour capter
    # le ResultMessage tel que le CLI embarqué le rend.
    resultats: list[ResultMessage] = []
    query_reelle = agent_sdk.query

    async def query_espion(**kwargs: Any) -> AsyncIterator[Any]:
        async for message in query_reelle(**kwargs):
            if isinstance(message, ResultMessage):
                resultats.append(message)
            yield message

    monkeypatch.setattr(agent_sdk, "query", query_espion)

    provider = ClaudeAgentSDKProvider(max_turns=1, max_budget_usd=0.5)
    result = await provider.complete(
        system="Réponds en un mot.",
        user="Dis bonjour.",
        model="claude-opus-5-5",
        max_tokens=64,
        cwd=tmp_path,
    )

    assert result.output_tokens > 0
    assert resultats, "aucun ResultMessage reçu"
    modeles = resultats[-1].model_usage or {}
    assert any("opus-5-5" in nom for nom in modeles), modeles
