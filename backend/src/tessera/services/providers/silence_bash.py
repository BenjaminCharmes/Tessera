"""Silence bound while a ``Bash`` call waits for its result (ticket-957).

Le CLI borne lui-même un appel `Bash` (10 minutes au plus) : un appel encore
ouvert au-delà est figé, pas lent. On le coupe donc plus tôt que la garde de
silence générale.
"""
from claude_agent_sdk import AssistantMessage, ToolResultBlock, ToolUseBlock, UserMessage

from tessera.config import settings


class SuiviAppelsBash:
    """Tracks the ``Bash`` tool calls that have no ``tool_result`` yet."""

    def __init__(self, silence_max_s: float, bash_silence_max_s: float | None) -> None:
        self._silence_max_s = silence_max_s
        self._bash_silence_max_s = (
            settings.bash_silence_max_s if bash_silence_max_s is None else bash_silence_max_s
        )
        self._ouverts: set[str] = set()

    def observer(self, message: object) -> None:
        """Records a ``Bash`` tool_use, or clears it when its result arrives."""
        if isinstance(message, AssistantMessage):
            for bloc in message.content:
                if isinstance(bloc, ToolUseBlock) and bloc.name == "Bash":
                    self._ouverts.add(bloc.id)
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for bloc in message.content:
                if isinstance(bloc, ToolResultBlock):
                    self._ouverts.discard(bloc.tool_use_id)

    @property
    def bash_en_attente(self) -> bool:
        """True when the shorter Bash bound applies."""
        return bool(self._ouverts) and 0 < self._bash_silence_max_s < self._effective_generale()

    def _effective_generale(self) -> float:
        # Une borne générale désactivée (≤ 0) vaut « sans limite ».
        return self._silence_max_s if self._silence_max_s > 0 else float("inf")

    def borne(self) -> float | None:
        """Silence bound in seconds now in force; None when there is none."""
        if self.bash_en_attente:
            return self._bash_silence_max_s
        return self._silence_max_s if self._silence_max_s > 0 else None

    def message_d_arret(self) -> str:
        """Text of the ``ProviderIndisponible`` raised on a silence."""
        borne = self.borne() or 0.0
        if self.bash_en_attente:
            return f"appel Bash sans réponse depuis {borne:.0f} s"
        return f"agent silencieux depuis {borne:.0f} s"
