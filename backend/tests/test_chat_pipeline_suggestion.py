"""Suggestion de lancement de pipeline depuis le chat — ticket-055."""
import pytest

from tessera.services.chat_suggestion import (
    PipelineSuggestion,
    RunLock,
    RunAlreadyInProgress,
    parse_pipeline_suggestion,
    summarize_conversation,
)
from tessera.services.database import ChatMessageRow


# ------------------------------------------------------------------
# Détection de la suggestion
# ------------------------------------------------------------------


def test_detecte_une_suggestion_en_fin_de_reponse() -> None:
    content = (
        "J'ai créé le ticket. Il couvre l'endpoint et son test.\n\n"
        "SUGGESTION_PIPELINE: ticket-042"
    )

    suggestion = parse_pipeline_suggestion(content)

    assert suggestion == PipelineSuggestion(ticket_id="ticket-042")


def test_une_reponse_sans_marqueur_ne_suggere_rien() -> None:
    assert parse_pipeline_suggestion("Voici comment fonctionne le pipeline.") is None


def test_le_marqueur_est_retire_du_texte_affiche() -> None:
    # Le marqueur est un protocole, pas du contenu : l'utilisateur voit un
    # bouton, pas une ligne technique.
    from tessera.services.chat_suggestion import strip_suggestion_marker

    content = "C'est prêt.\n\nSUGGESTION_PIPELINE: ticket-042"
    assert strip_suggestion_marker(content).strip() == "C'est prêt."


def test_un_identifiant_de_ticket_invalide_est_ignore() -> None:
    # Le marqueur vient d'un agent : il ne doit pas pouvoir injecter n'importe
    # quoi dans un chemin ou une commande.
    assert parse_pipeline_suggestion("SUGGESTION_PIPELINE: ../../etc/passwd") is None
    assert parse_pipeline_suggestion("SUGGESTION_PIPELINE: ") is None


def test_seule_la_derniere_suggestion_compte() -> None:
    content = "SUGGESTION_PIPELINE: ticket-001\ntexte\nSUGGESTION_PIPELINE: ticket-002"
    suggestion = parse_pipeline_suggestion(content)
    assert suggestion is not None and suggestion.ticket_id == "ticket-002"


# ------------------------------------------------------------------
# Résumé transmis au pipeline
# ------------------------------------------------------------------


def test_le_resume_reprend_la_conversation_dans_l_ordre() -> None:
    history = [
        ChatMessageRow(role="user", content="Il faut un endpoint /health", cost_usd=0, ts="t1"),
        ChatMessageRow(role="assistant", content="D'accord, avec un test", cost_usd=0, ts="t2"),
    ]

    summary = summarize_conversation(history)

    assert "endpoint /health" in summary
    assert "avec un test" in summary
    assert summary.index("endpoint /health") < summary.index("avec un test")


def test_le_resume_est_borne_en_taille() -> None:
    # Le contexte projet est déjà volumineux : une conversation de cinquante
    # tours ne doit pas le doubler dans le prompt du codeur.
    history = [
        ChatMessageRow(role="user", content=f"message {i} " + "x" * 500, cost_usd=0, ts=f"t{i}")
        for i in range(50)
    ]

    summary = summarize_conversation(history, max_chars=2000)

    assert len(summary) <= 2000
    # Les tours les plus récents sont ceux qui comptent.
    assert "message 49" in summary


def test_une_conversation_vide_ne_produit_pas_de_resume() -> None:
    assert summarize_conversation([]) == ""


# ------------------------------------------------------------------
# Un seul run à la fois par projet
# ------------------------------------------------------------------


async def test_un_second_run_concurrent_est_refuse() -> None:
    # Deux pipelines sur le même dépôt violeraient l'isolation par branche
    # d'ADR-018 : ils se marcheraient dessus dans le même arbre de travail.
    lock = RunLock()

    async with lock.acquire("mon-projet"):
        with pytest.raises(RunAlreadyInProgress) as exc:
            async with lock.acquire("mon-projet"):
                pass

    assert "mon-projet" in str(exc.value)


async def test_deux_projets_differents_peuvent_tourner_ensemble() -> None:
    lock = RunLock()

    async with lock.acquire("projet-a"):
        async with lock.acquire("projet-b"):
            pass


async def test_le_verrou_est_libere_meme_si_le_run_echoue() -> None:
    lock = RunLock()

    with pytest.raises(RuntimeError):
        async with lock.acquire("mon-projet"):
            raise RuntimeError("le pipeline a échoué")

    # Le projet doit rester utilisable après un échec.
    async with lock.acquire("mon-projet"):
        pass
