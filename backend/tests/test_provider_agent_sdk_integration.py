import shutil
from pathlib import Path

import pytest

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
