"""Handling of one message of the SDK stream, split from ``agent_sdk``."""
from claude_agent_sdk import AssistantMessage, RateLimitEvent, ResultMessage, StreamEvent, TextBlock, ToolUseBlock

from tessera.services.providers.base import StreamCallback, ToolEventCallback
from tessera.services.providers.messages_sdk import OUTIL_SORTIE_STRUCTUREE, _extract_stream_delta
from tessera.services.usage.quota_tracker import QuotaTracker


async def traiter_message(
    message: object,
    *,
    chunks: list[str],
    quota: QuotaTracker,
    on_token: StreamCallback | None,
    on_tool_use: ToolEventCallback | None,
) -> ResultMessage | None:
    """Dispatches one message; returns it when it is the final ``ResultMessage``."""
    if isinstance(message, RateLimitEvent):
        # L'état du quota d'abonnement : la seule mesure de la ressource
        # réellement finie en mode abonnement.
        quota.observe(getattr(message, "rate_limit_info", None))
    elif isinstance(message, ResultMessage):
        return message
    elif isinstance(message, StreamEvent):
        # Affichage en direct seulement : le texte fait foi par les TextBlock,
        # sinon il serait compté deux fois.
        delta = _extract_stream_delta(message.event) if on_token is not None else None
        if on_token is not None and delta:
            await on_token(delta)
    elif isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                chunks.append(block.text)
            # La sortie structurée n'est pas une action de l'agent.
            elif (isinstance(block, ToolUseBlock) and on_tool_use is not None
                  and block.name != OUTIL_SORTIE_STRUCTUREE):
                await on_tool_use(block.name, dict(block.input))
    return None
