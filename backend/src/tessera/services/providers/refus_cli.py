"""Spots the tool calls the embedded CLI itself refuses (ticket-515).

A refusal of Tessera's own guard arrives as ``PreToolUse:<tool> hook error``
and is already journaled. The CLI has a second way to say no: a ``tool_result``
in error carrying a fixed sentence, which nothing read until now. The coder
simply stopped, and the round was lost without a trace.
"""

from claude_agent_sdk import (
    AssistantMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

# Le début du message que le CLI rend à un outil qu'il ne laisse pas passer.
MESSAGE_REFUS_CLI = "The user doesn't want to take this action right now"

_OUTIL_INCONNU = "inconnu"


def _texte_du_resultat(contenu: object) -> str:
    """The text of a ``tool_result``, whether it is a string, blocks or empty."""
    if isinstance(contenu, str):
        return contenu
    if isinstance(contenu, list):
        morceaux = [b.get("text", "") for b in contenu if isinstance(b, dict)]
        return "".join(m for m in morceaux if isinstance(m, str))
    return ""


class ReleveDesRefusCli:
    """Follows a call's messages and collects the tools the CLI refused."""

    def __init__(self) -> None:
        self._noms_par_appel: dict[str, str] = {}
        self.outils_refuses: list[str] = []

    def observer(self, message: object) -> None:
        """Remembers each tool call, and notes each one the CLI refuses."""
        if isinstance(message, AssistantMessage):
            for bloc in message.content:
                if isinstance(bloc, ToolUseBlock):
                    self._noms_par_appel[bloc.id] = bloc.name
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for bloc in message.content:
                if isinstance(bloc, ToolResultBlock) and self._est_un_refus(bloc):
                    self.outils_refuses.append(
                        self._noms_par_appel.get(bloc.tool_use_id, _OUTIL_INCONNU)
                    )

    @staticmethod
    def _est_un_refus(bloc: ToolResultBlock) -> bool:
        if not bloc.is_error:
            return False
        return _texte_du_resultat(bloc.content).lstrip().startswith(MESSAGE_REFUS_CLI)
