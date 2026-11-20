"""Le garde qui refuse de tuer des processus par leur nom — ticket-899."""
import pytest

from tessera.services.providers.kill_guard import commande_kill_interdite, hook_refus_kill

INTERDITES = [
    'grep -r x . ; pkill -f "python" 2>/dev/null; true',
    "killall node",
    "taskkill /F /IM python.exe",
    "Stop-Process -Name python",
    "kill -9 1234",
    "kill -1",
    "kill 0",
    "kill $(pgrep python)",
    "kill `pgrep python`",
    'sh -c "pkill python"',
    'powershell -Command "Stop-Process -Name node"',
    "eval pkill python",
    "pgrep python | xargs kill",
    "sudo killall node",
    "wmic process where name='python.exe' delete",
    "echo $(pkill python)",
]

PERMISES = [
    "kill %1",
    "npm run dev & sleep 5; kill $!",
    "grep pkill notes.md",
    "echo killall",
    "kill -9 $!",
    "timeout 5 pytest -q",
    "ls",
]


@pytest.mark.parametrize("commande", INTERDITES)
def test_commande_kill_interdite_refuse(commande: str) -> None:
    assert commande_kill_interdite(commande), commande


@pytest.mark.parametrize("commande", PERMISES)
def test_commande_kill_interdite_laisse_passer(commande: str) -> None:
    assert not commande_kill_interdite(commande), commande


async def test_hook_refuse_pkill_et_explique() -> None:
    sortie = await hook_refus_kill(
        {"tool_name": "Bash", "tool_input": {"command": "pkill -f python"}}, None, None
    )
    decision = sortie["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "kill $!" in decision["permissionDecisionReason"]


async def test_hook_laisse_passer_ls_et_les_autres_outils() -> None:
    assert await hook_refus_kill({"tool_name": "Bash", "tool_input": {"command": "ls"}}, None, None) == {}
    assert await hook_refus_kill({"tool_name": "Write", "tool_input": {}}, None, None) == {}


def test_hook_est_installe_sur_bash() -> None:
    from tessera.services.providers.agent_sdk import _build_options

    options = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=["Read", "Bash"],
    )
    matchers = (options.hooks or {}).get("PreToolUse", [])
    assert any(
        m.matcher == "Bash" and any(cb.__name__ == "hook_refus_kill" for cb in m.hooks)
        for m in matchers
    )
