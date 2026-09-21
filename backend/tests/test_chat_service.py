"""ChatService — ticket-048."""
from pathlib import Path

import pytest

from tessera.services.chat_service import (
    ChatBudgetExceeded,
    ChatReply,
    ChatService,
)
from tessera.services.database import ChatMessageRow
from tessera.services.providers.base import ProviderResult


class _FakeProvider:
    def __init__(self, content: str = "Voici ma réponse.", cost: float = 0.02) -> None:
        self.content = content
        self.cost = cost
        self.calls: list[dict[str, object]] = []

    async def stream(self, **kwargs: object) -> ProviderResult:
        self.calls.append(kwargs)
        on_token = kwargs.get("on_token")
        if on_token is not None:
            await on_token(self.content)  # type: ignore[operator]
        return ProviderResult(
            content=self.content,
            input_tokens=10,
            output_tokens=5,
            cost_usd=self.cost,
            provider_name="fake",
        )


class _FakeGit:
    def __init__(self, dirty: bool = True) -> None:
        self.dirty = dirty
        self.branches: list[str] = []
        self.commits: list[str] = []

    async def is_clean(self) -> bool:
        return not self.dirty

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        name = f"{ticket_id}-{slug}"
        self.branches.append(name)
        return name

    async def commit_all(self, message: str) -> str | None:
        self.commits.append(message)
        self.dirty = False
        return "cafe123"


def _prompts(tmp_path: Path) -> Path:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "chat.md").write_text("Tu es l'assistant de Tessera.", encoding="utf-8")
    return prompts


def _service(tmp_path: Path, **kwargs: object) -> ChatService:
    defaults: dict[str, object] = dict(
        provider=_FakeProvider(),
        prompts_dir=_prompts(tmp_path),
        project_path=tmp_path / "projet",
        project_context="contexte projet",
        git_workspace=None,
        max_conversation_usd=1.0,
    )
    defaults.update(kwargs)
    return ChatService(**defaults)  # type: ignore[arg-type]


async def test_send_retourne_la_reponse_et_son_cout(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    reply = await svc.send(history=[], message="Salut")

    assert isinstance(reply, ChatReply)
    assert reply.content == "Voici ma réponse."
    assert reply.cost_usd == 0.02


async def test_send_streame_les_tokens(tmp_path: Path) -> None:
    tokens: list[str] = []

    async def _on_token(token: str) -> None:
        tokens.append(token)

    svc = _service(tmp_path)
    await svc.send(history=[], message="Salut", on_token=_on_token)

    assert "".join(tokens) == "Voici ma réponse."


async def test_send_transmet_l_historique_au_provider(tmp_path: Path) -> None:
    # Le provider est sans état : l'historique doit être reconstruit dans le
    # message, sinon chaque tour repart de zéro.
    provider = _FakeProvider()
    svc = _service(tmp_path, provider=provider)

    history = [
        ChatMessageRow(role="user", content="Comment tester ?", cost_usd=0.0, ts="t1"),
        ChatMessageRow(role="assistant", content="Avec pytest.", cost_usd=0.01, ts="t2"),
    ]
    await svc.send(history=history, message="Et le frontend ?")

    sent = str(provider.calls[0]["user"])
    assert "Comment tester ?" in sent
    assert "Avec pytest." in sent
    assert "Et le frontend ?" in sent


async def test_send_refuse_au_dela_du_plafond_de_conversation(tmp_path: Path) -> None:
    # LLM_MAX_BUDGET_USD borne un appel, pas une conversation. Sans ce
    # plafond, une longue discussion épuise le quota silencieusement.
    svc = _service(tmp_path, max_conversation_usd=0.05)

    with pytest.raises(ChatBudgetExceeded) as exc:
        await svc.send(history=[], message="Salut", spent_usd=0.05)

    assert "0.05" in str(exc.value)


# ------------------------------------------------------------------
# Cohabitation git — ADR-019
# ------------------------------------------------------------------


async def test_les_ecritures_du_chat_sont_commitees_sur_une_branche_chat(
    tmp_path: Path,
) -> None:
    # ADR-018 fait reposer l'enchaînement des tickets sur un arbre propre au
    # démarrage. Un chat qui écrit sans committer enverrait le ticket suivant
    # en `blocked`. ADR-019 : le chat commite comme un run de pipeline.
    git = _FakeGit(dirty=True)
    svc = _service(tmp_path, git_workspace=git)

    reply = await svc.send(history=[], message="Ajoute un fichier")

    assert len(git.branches) == 1
    assert git.branches[0].startswith("chat-")
    assert len(git.commits) == 1
    assert git.commits[0].startswith("chore: chat")
    assert reply.commit_sha == "cafe123"
    assert reply.branch == git.branches[0]


async def test_le_chat_ne_commite_pas_quand_il_n_a_rien_ecrit(tmp_path: Path) -> None:
    # Un tour purement conversationnel ne doit pas créer de branche ni de
    # commit : sinon chaque question produirait une branche morte.
    git = _FakeGit(dirty=False)
    svc = _service(tmp_path, git_workspace=git)

    reply = await svc.send(history=[], message="Explique-moi le pipeline")

    assert git.branches == []
    assert git.commits == []
    assert reply.commit_sha is None


async def test_le_chat_fonctionne_sans_depot_git(tmp_path: Path) -> None:
    svc = _service(tmp_path, git_workspace=None)
    reply = await svc.send(history=[], message="Salut")

    assert reply.content == "Voici ma réponse."
    assert reply.commit_sha is None


# ------------------------------------------------------------------
# Suggestion de pipeline — ticket-055
# ------------------------------------------------------------------


async def test_la_suggestion_est_extraite_et_le_marqueur_retire(tmp_path: Path) -> None:
    provider = _FakeProvider(
        content="J'ai créé le ticket.\n\nSUGGESTION_PIPELINE: ticket-042"
    )
    svc = _service(tmp_path, provider=provider)

    reply = await svc.send(history=[], message="Crée un ticket")

    assert reply.suggested_ticket_id == "ticket-042"
    assert "SUGGESTION_PIPELINE" not in reply.content
    assert reply.content == "J'ai créé le ticket."


async def test_sans_marqueur_aucune_suggestion(tmp_path: Path) -> None:
    svc = _service(tmp_path, provider=_FakeProvider(content="Voici l'explication."))
    reply = await svc.send(history=[], message="Explique")

    assert reply.suggested_ticket_id is None
    assert reply.content == "Voici l'explication."
