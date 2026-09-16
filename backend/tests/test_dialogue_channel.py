"""Canal de dialogue entre l'utilisateur et un run en cours — ticket-066."""
import asyncio

import pytest

from vibe_ide.services.dialogue import DialogueChannel, NO_HUMAN_ANSWER


# ------------------------------------------------------------------
# L'agent demande
# ------------------------------------------------------------------


async def test_l_agent_recoit_la_reponse_de_l_utilisateur() -> None:
    canal = DialogueChannel(timeout_s=5.0, interactive=True)

    question = asyncio.create_task(canal.ask("Quel format pour la date ?"))
    await canal.wait_for_question()
    canal.answer("ISO 8601")

    assert await question == "ISO 8601"


async def test_la_question_en_attente_est_lisible_pendant_l_attente() -> None:
    # C'est ce que l'UI affiche : sans cela, l'utilisateur voit un run fige
    # sans savoir qu'on lui demande quelque chose.
    canal = DialogueChannel(timeout_s=5.0, interactive=True)

    question = asyncio.create_task(canal.ask("On casse l'API ?"))
    await canal.wait_for_question()

    assert canal.pending_question == "On casse l'API ?"

    canal.answer("non")
    await question
    assert canal.pending_question is None


async def test_sans_reponse_l_agent_reprend_sur_une_hypothese() -> None:
    # ADR-018 : un run en pause tient du travail non commite. Un agent qui
    # attend jusqu'au matin bloque la file des tickets suivants. Au-dela du
    # delai il reprend seul, en enoncant son hypothese.
    canal = DialogueChannel(timeout_s=0.01, interactive=True)

    reponse = await canal.ask("Quel format ?")

    assert reponse == NO_HUMAN_ANSWER
    assert canal.pending_question is None


async def test_en_mode_autonome_la_question_ne_bloque_jamais() -> None:
    # Personne ne regarde : attendre le delai complet a chaque question
    # gacherait un run nocturne sans que quiconque puisse repondre.
    canal = DialogueChannel(timeout_s=3600.0, interactive=False)

    reponse = await asyncio.wait_for(canal.ask("Quel format ?"), timeout=1.0)

    assert reponse == NO_HUMAN_ANSWER


async def test_une_reponse_sans_question_est_ignoree() -> None:
    canal = DialogueChannel(timeout_s=5.0, interactive=True)

    canal.answer("personne n'a rien demande")  # ne doit pas lever

    assert canal.pending_question is None


# ------------------------------------------------------------------
# L'utilisateur intervient
# ------------------------------------------------------------------


async def test_les_messages_spontanes_se_vident_en_une_fois() -> None:
    canal = DialogueChannel(timeout_s=5.0, interactive=True)

    canal.interject("utilise pathlib")
    canal.interject("et pas os.path")

    assert canal.drain() == ["utilise pathlib", "et pas os.path"]
    assert canal.drain() == []


async def test_un_message_spontane_ne_repond_pas_a_la_question() -> None:
    # Les deux canaux sont distincts : intervenir pendant qu'une question est
    # posee ne doit pas etre pris pour la reponse, sans quoi un « au fait,
    # pense aux tests » deviendrait la reponse a « on casse l'API ? ».
    canal = DialogueChannel(timeout_s=0.05, interactive=True)

    question = asyncio.create_task(canal.ask("On casse l'API ?"))
    await canal.wait_for_question()
    canal.interject("au fait, pense aux tests")

    assert await question == NO_HUMAN_ANSWER
    assert canal.drain() == ["au fait, pense aux tests"]


async def test_la_question_est_annoncee_a_l_exterieur() -> None:
    # Le canal ne connait pas le transport, mais quelqu'un doit prevenir l'UI :
    # une question posee sans evenement ressemble, cote utilisateur, a un run
    # qui s'est fige tout seul.
    annoncees: list[str] = []

    async def _annoncer(question: str) -> None:
        annoncees.append(question)

    canal = DialogueChannel(timeout_s=0.01, interactive=True, on_question=_annoncer)
    await canal.ask("On casse l'API ?")

    assert annoncees == ["On casse l'API ?"]


async def test_en_mode_autonome_rien_n_est_annonce() -> None:
    annoncees: list[str] = []

    async def _annoncer(question: str) -> None:
        annoncees.append(question)

    canal = DialogueChannel(timeout_s=5.0, interactive=False, on_question=_annoncer)
    await canal.ask("On casse l'API ?")

    assert annoncees == []
