"""Persistance des conversations du chat — ticket-048."""
from pathlib import Path

from vibe_ide.services.database import (
    ChatMessageRow,
    conversation_cost_usd,
    init_db,
    list_chat_messages,
    save_chat_message,
)


async def _db(tmp_path: Path) -> Path:
    db_path = tmp_path / "vibe.db"
    await init_db(db_path)
    return db_path


async def test_une_conversation_survit_au_rechargement(tmp_path: Path) -> None:
    # Le critère d'acceptation : la conversation ne doit pas disparaître quand
    # l'utilisateur recharge la page.
    db_path = await _db(tmp_path)

    await save_chat_message(db_path, "ide-core", "conv-1", "user", "Salut", 0.0)
    await save_chat_message(db_path, "ide-core", "conv-1", "assistant", "Bonjour", 0.02)

    messages = await list_chat_messages(db_path, "ide-core", "conv-1")

    assert [m.role for m in messages] == ["user", "assistant"]
    assert [m.content for m in messages] == ["Salut", "Bonjour"]
    assert isinstance(messages[0], ChatMessageRow)


async def test_les_conversations_sont_cloisonnees_par_projet(tmp_path: Path) -> None:
    db_path = await _db(tmp_path)

    await save_chat_message(db_path, "projet-a", "conv-1", "user", "A", 0.0)
    await save_chat_message(db_path, "projet-b", "conv-1", "user", "B", 0.0)

    assert [m.content for m in await list_chat_messages(db_path, "projet-a", "conv-1")] == ["A"]
    assert [m.content for m in await list_chat_messages(db_path, "projet-b", "conv-1")] == ["B"]


async def test_le_cout_cumule_d_une_conversation_est_lisible(tmp_path: Path) -> None:
    # LLM_MAX_BUDGET_USD borne UN appel, pas une conversation : sans total
    # cumulé, une longue discussion consomme le quota sans que rien ne le voie.
    db_path = await _db(tmp_path)

    await save_chat_message(db_path, "ide-core", "conv-1", "user", "q1", 0.0)
    await save_chat_message(db_path, "ide-core", "conv-1", "assistant", "r1", 0.03)
    await save_chat_message(db_path, "ide-core", "conv-1", "assistant", "r2", 0.07)
    await save_chat_message(db_path, "ide-core", "conv-2", "assistant", "autre", 5.0)

    assert await conversation_cost_usd(db_path, "ide-core", "conv-1") == 0.1


async def test_cout_d_une_conversation_inconnue_vaut_zero(tmp_path: Path) -> None:
    db_path = await _db(tmp_path)
    assert await conversation_cost_usd(db_path, "ide-core", "jamais-vue") == 0.0
