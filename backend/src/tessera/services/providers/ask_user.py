"""The `ask_user` tool — how an agent stops to ask a question (ticket-066).

An agent that hits an ambiguity used to decide alone: its assumption surfaced
at commit time, often after the wrong code had already been written. This tool
lets it suspend its turn instead and put the question to the user.

## Why a tool, and not a keyword in the prose

ADR-009 parses the reviewer's verdict by looking for `CHANGES_REQUESTED` in
free text, because nothing better was available for a plain completion. Here
the SDK offers a structured mechanism, so there is no reason to go back to
matching strings: an agent that merely *writes* "QUESTION: ..." in a sentence
about questions would otherwise suspend the run by accident.

The tool is served from an in-process SDK MCP server. Its qualified name —
`mcp__tessera__ask_user` — is what has to appear in `allowed_tools`: the SDK
would otherwise expose the tool and then refuse every call to it.
"""
from collections.abc import Awaitable, Callable
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, SdkMcpTool, create_sdk_mcp_server, tool

#: Le serveur MCP in-process qui porte l'outil.
ASK_USER_SERVER_NAME = "tessera"

#: Nom qualifié tel que le SDK le résout. Doit figurer dans `allowed_tools`.
ASK_USER_TOOL_NAME = f"mcp__{ASK_USER_SERVER_NAME}__ask_user"

_DESCRIPTION = (
    "Pose une question à l'utilisateur et attend sa réponse. À n'utiliser que "
    "face à une ambiguïté qu'aucune lecture du ticket, du code ou des ADR ne "
    "lève, et dont la réponse change ce que tu vas écrire. La réponse peut "
    "indiquer qu'aucun humain n'est disponible : dans ce cas, poursuis en "
    "énonçant l'hypothèse que tu retiens."
)

#: Ce que l'outil rend quand il est appelé sans question exploitable. Le run
#: ne doit pas se suspendre sur un écran vide : personne ne saurait quoi
#: répondre, et le délai d'ADR-025 s'écoulerait pour rien.
_EMPTY = (
    "Appel ignoré : aucune question n'a été fournie. Formule une question "
    "précise, ou poursuis en énonçant ton hypothèse."
)


def build_ask_user_tool(
    asker: Callable[[str], Awaitable[str]],
) -> SdkMcpTool[Any]:
    """Construit l'outil au-dessus d'un `asker` — en pratique `DialogueChannel.ask`."""

    @tool(
        "ask_user",
        _DESCRIPTION,
        {"question": str},
    )
    async def ask_user(args: dict[str, Any]) -> dict[str, Any]:
        question = str(args.get("question", "")).strip()
        if not question:
            return {"content": [{"type": "text", "text": _EMPTY}]}
        return {"content": [{"type": "text", "text": await asker(question)}]}

    return ask_user


def build_ask_user_server(
    asker: Callable[[str], Awaitable[str]],
) -> McpSdkServerConfig:
    """Le serveur MCP in-process à passer dans `ClaudeAgentOptions.mcp_servers`."""
    return create_sdk_mcp_server(
        name=ASK_USER_SERVER_NAME,
        tools=[build_ask_user_tool(asker)],
    )
