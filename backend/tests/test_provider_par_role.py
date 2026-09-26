"""Provider and model declared per role, with an explicit fallback — ticket-188.

Le provider était choisi une fois pour tout le backend, et cinq services
avaient leur modèle codé en dur. Un modèle local (ticket-189) n'aurait été
branchable nulle part sans basculer aussi le codeur.
"""
import json
import re
from pathlib import Path
from typing import Any

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.agent import AgentConfig, AgentRole
from tessera.services import project_loader
from tessera.services.database import init_db, create_run, save_agent_call
from tessera.services.documentation import DocumentationService
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType
from tessera.services.planner import PlannerService
from tessera.services.project_analyzer import ProjectAnalyzerService
from tessera.services.project_loader import (
    ModeleInconnu,
    load_agents_config,
    set_agent_model,
    set_agent_provider,
)
from tessera.services.providers import par_role
from tessera.services.providers.base import ProviderResult
from tessera.services.providers.noms import (
    PROVIDERS_CONNUS,
    ProviderInconnu,
    ProviderIndisponible,
)
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.providers.repli import ProviderAvecRepli
from tessera.services.security_auditor import SecurityAuditorService
from tessera.services.validator import ValidatorService
from tests.test_agent_runner import _make_ticket, _runner
from tests.test_providers_base import FakeProvider

_SRC = Path(__file__).resolve().parents[1] / "src" / "tessera"


def _manifeste(tmp_path: Path, agents: list[dict[str, Any]]) -> Path:
    projet = tmp_path / "projet"
    projet.mkdir(exist_ok=True)
    (projet / "CLAUDE.md").write_text("# projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(
        json.dumps({"project_id": "projet", "agents": agents}), encoding="utf-8"
    )
    return projet


def _agent(role: str, **extra: Any) -> dict[str, Any]:
    return {
        "role": role, "model": "claude-sonnet-4-6", "max_tokens": 4096,
        "prompt_file": f"agents/prompts/{role}.md", "active": True, **extra,
    }


# ------------------------------------------------------------------
# Le manifeste
# ------------------------------------------------------------------


def test_un_manifeste_sans_provider_charge_sur_agent_sdk(tmp_path: Path) -> None:
    # Les manifestes existants ne déclarent rien : rien ne doit changer pour eux.
    projet = _manifeste(tmp_path, [_agent("codeur")])
    [config] = load_agents_config(projet)
    assert config.provider == "agent_sdk"
    assert config.fallback is None


def test_un_provider_declare_est_lu_avec_son_repli(tmp_path: Path) -> None:
    projet = _manifeste(tmp_path, [_agent(
        "securite", provider="anthropic_api",
        fallback={"provider": "agent_sdk", "model": "claude-haiku-4-5"},
    )])
    [config] = load_agents_config(projet)
    assert config.provider == "anthropic_api"
    assert config.fallback is not None
    assert config.fallback.provider == "agent_sdk"
    assert config.fallback.model == "claude-haiku-4-5"


def test_un_provider_inconnu_fait_echouer_le_chargement_en_nommant_le_role(
    tmp_path: Path,
) -> None:
    # Un manifeste illisible rendait une liste vide en silence ; un provider
    # mal orthographié enverrait le rôle sur le défaut sans rien dire.
    projet = _manifeste(tmp_path, [_agent("securite", provider="olama")])
    with pytest.raises(ProviderInconnu, match="securite"):
        load_agents_config(projet)


def test_un_repli_sur_un_provider_inconnu_est_refuse_aussi(tmp_path: Path) -> None:
    projet = _manifeste(tmp_path, [_agent(
        "securite", fallback={"provider": "nulle-part", "model": "x"},
    )])
    with pytest.raises(ProviderInconnu, match="securite"):
        load_agents_config(projet)


def test_les_manifestes_du_depot_chargent_toujours() -> None:
    racine = Path(__file__).resolve().parents[2] / "projects"
    # `demineur` est un dépôt à part, absent d'un clone neuf de Tessera.
    for nom in ("ide-core", "demineur"):
        if nom != "ide-core" and not (racine / nom / "agents.json").is_file():
            continue
        assert load_agents_config(racine / nom), nom


# ------------------------------------------------------------------
# Le repli
# ------------------------------------------------------------------


class _ProviderEnPanne(FakeProvider):
    name = "en-panne"

    async def complete(self, **kwargs: Any) -> ProviderResult:
        self.calls.append(kwargs)
        raise ProviderIndisponible("connexion refusée")

    async def stream(self, **kwargs: Any) -> ProviderResult:
        self.calls.append(kwargs)
        raise ProviderIndisponible("connexion refusée")


class _ProviderIllisible(FakeProvider):
    async def complete(self, **kwargs: Any) -> ProviderResult:
        raise ValueError("JSON illisible")


async def _evenements_de(hub_types: set[EventType], action: Any) -> list[Any]:
    abonnement = EVENT_HUB.subscribe()
    try:
        await action()
        return [e for e in abonnement.vider() if e.type in hub_types]
    finally:
        EVENT_HUB.retirer(abonnement)


async def test_le_repli_prend_le_relais_sur_provider_indisponible() -> None:
    principal, repli = _ProviderEnPanne(), FakeProvider(content="du repli")
    provider = ProviderAvecRepli(
        principal, repli, modele_repli="claude-haiku-4-5", role="securite", project_id="p"
    )
    result = await provider.complete(system="s", user="u", model="qwen", max_tokens=1)

    assert result.content == "du repli"
    assert repli.calls[0]["model"] == "claude-haiku-4-5"
    assert result.model == "claude-haiku-4-5"
    assert result.provider_name == "fake"


async def test_un_repli_utilise_se_voit_sur_le_canal_d_observation() -> None:
    # ADR-039 : rien à l'écran ne distingue un audit sur le modèle prévu d'un
    # audit sur son repli. L'événement est ce qui le dit.
    provider = ProviderAvecRepli(
        _ProviderEnPanne(), FakeProvider(), modele_repli="claude-haiku-4-5",
        role="securite", project_id="demo",
    )

    async def action() -> None:
        await provider.complete(system="s", user="u", model="qwen", max_tokens=1)

    [evenement] = await _evenements_de({EventType.PROVIDER_FALLBACK}, action)
    assert evenement.project_id == "demo"
    assert evenement.data["role"] == "securite"
    assert evenement.data["tente"] == "en-panne"
    assert evenement.data["utilise"] == "fake"
    assert evenement.data["modele"] == "claude-haiku-4-5"


async def test_une_reponse_illisible_ne_declenche_pas_le_repli() -> None:
    # ADR-039 traite déjà ce cas en échouant fermé : un repli masquerait un
    # modèle qui ne tient pas, au lieu de le montrer.
    repli = FakeProvider()
    provider = ProviderAvecRepli(
        _ProviderIllisible(), repli, modele_repli="m", role="securite", project_id="p"
    )
    with pytest.raises(ValueError, match="illisible"):
        await provider.complete(system="s", user="u", model="qwen", max_tokens=1)
    assert repli.calls == []


async def test_sans_panne_le_principal_repond_seul() -> None:
    principal, repli = FakeProvider(content="principal"), FakeProvider()
    provider = ProviderAvecRepli(principal, repli, modele_repli="m", role="r", project_id="p")
    result = await provider.stream(system="s", user="u", model="qwen", max_tokens=1)
    assert result.content == "principal"
    assert repli.calls == []


def test_le_repli_porte_le_nom_et_le_quota_du_principal() -> None:
    # Le routeur lit `provider.quota` par `getattr` : un enveloppement ne
    # doit pas le rendre aveugle au quota d'abonnement (ticket-054).
    principal = FakeProvider()
    principal.quota = "le-quota"  # type: ignore[attr-defined]
    provider = ProviderAvecRepli(principal, FakeProvider(), modele_repli="m", role="r", project_id="p")
    assert provider.name == "fake"
    assert provider.quota == "le-quota"


# ------------------------------------------------------------------
# La fabrique par rôle
# ------------------------------------------------------------------


@pytest.fixture
def fabrique_enregistree(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    appels: list[dict[str, Any]] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> FakeProvider:
        appels.append({"name": name, **kwargs})
        p = FakeProvider()
        p.name = name or "agent_sdk"  # type: ignore[misc]
        return p

    monkeypatch.setattr(par_role, "get_provider", fausse)
    return appels


def test_la_fabrique_construit_le_provider_declare_pour_le_role(
    tmp_path: Path, fabrique_enregistree: list[dict[str, Any]]
) -> None:
    projet = _manifeste(tmp_path, [_agent("securite", provider="anthropic_api")])
    provider = provider_pour_role(projet, "securite", allow_tools=False)
    assert provider.name == "anthropic_api"
    assert fabrique_enregistree[0]["name"] == "anthropic_api"
    assert fabrique_enregistree[0]["allow_tools"] is False


def test_un_role_absent_du_manifeste_prend_le_provider_global(
    tmp_path: Path, fabrique_enregistree: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "anthropic_api")
    projet = _manifeste(tmp_path, [_agent("codeur")])
    provider_pour_role(projet, "planificateur", allow_tools=False)
    assert fabrique_enregistree[0]["name"] == "anthropic_api"


def test_un_projet_sans_manifeste_prend_le_provider_global(
    tmp_path: Path, fabrique_enregistree: list[dict[str, Any]]
) -> None:
    provider_pour_role(tmp_path / "inexistant", "project-creator", allow_tools=False)
    assert fabrique_enregistree[0]["name"] == settings.llm_provider


def test_un_repli_declare_enveloppe_le_provider(
    tmp_path: Path, fabrique_enregistree: list[dict[str, Any]]
) -> None:
    projet = _manifeste(tmp_path, [_agent(
        "securite", provider="anthropic_api",
        fallback={"provider": "agent_sdk", "model": "claude-haiku-4-5"},
    )])
    provider = provider_pour_role(projet, "securite", allow_tools=False, project_id="p")
    assert isinstance(provider, ProviderAvecRepli)
    assert [a["name"] for a in fabrique_enregistree] == ["anthropic_api", "agent_sdk"]
    # Le repli reçoit les mêmes restrictions d'outils que le principal.
    assert fabrique_enregistree[1]["allow_tools"] is False


def test_le_modele_du_role_vient_du_manifeste_sinon_du_defaut(tmp_path: Path) -> None:
    projet = _manifeste(tmp_path, [_agent("securite", model="claude-haiku-4-5")])
    assert modele_du_role(projet, "securite") == "claude-haiku-4-5"
    assert modele_du_role(projet, "validateur") is None
    assert modele_du_role(tmp_path / "inexistant", "securite") is None


# ------------------------------------------------------------------
# Les services à modèle codé en dur
# ------------------------------------------------------------------


def _prompts(tmp_path: Path) -> Path:
    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    for nom in ("securite", "validateur", "planificateur", "project-analyzer",
                "doc-technique", "doc-fonctionnelle"):
        (prompts / f"{nom}.md").write_text(f"Tu es {nom}.", encoding="utf-8")
    return prompts


async def test_la_securite_utilise_le_modele_recu(tmp_path: Path) -> None:
    provider = FakeProvider(content='{"issues": [], "verdict": "PASS", "summary": "ok"}')
    await SecurityAuditorService(provider, _prompts(tmp_path), model="qwen").audit("diff", tmp_path)
    assert provider.calls[0]["model"] == "qwen"


async def test_la_securite_garde_son_defaut_sans_modele(tmp_path: Path) -> None:
    provider = FakeProvider(content='{"issues": [], "verdict": "PASS", "summary": "ok"}')
    await SecurityAuditorService(provider, _prompts(tmp_path)).audit("diff", tmp_path)
    assert provider.calls[0]["model"] == "claude-sonnet-4-6"


async def test_le_validateur_utilise_le_modele_recu(tmp_path: Path) -> None:
    provider = FakeProvider(content='{"verdict": "APPROVED", "criteria": [], "feedback": ""}')
    svc = ValidatorService(provider, _prompts(tmp_path), model="qwen")
    await svc.validate(criteria=["un critère"], code_produced="d", test_result=None)
    assert provider.calls[0]["model"] == "qwen"


async def test_le_planificateur_utilise_le_modele_recu(tmp_path: Path) -> None:
    provider = FakeProvider(content='{"tickets": []}')
    projet = _manifeste(tmp_path, [])
    svc = PlannerService(provider, _prompts(tmp_path), tmp_path, model="qwen")
    try:
        await svc.plan(projet.name, "une description")
    except ValueError:
        pass  # la forme du plan n'est pas ce qu'on teste ici
    assert provider.calls[0]["model"] == "qwen"


async def test_l_analyseur_utilise_le_modele_recu(tmp_path: Path) -> None:
    provider = FakeProvider(content='{"stack": "x", "name": "p", "description": "d"}')
    projet = _manifeste(tmp_path, [])
    svc = ProjectAnalyzerService(provider, _prompts(tmp_path), model="qwen")
    try:
        await svc.analyze(projet, overwrite=True)
    except (ValueError, KeyError):
        pass
    assert provider.calls[0]["model"] == "qwen"


async def test_la_documentation_prend_provider_et_modele_par_role(tmp_path: Path) -> None:
    # Deux rôles, donc potentiellement deux providers : `doc-technique` sur un
    # modèle local et `doc-fonctionnelle` sur Claude doivent pouvoir coexister.
    technique, fonctionnel = FakeProvider(content="[]"), FakeProvider(content="[]")
    projet = _manifeste(tmp_path, [])
    (projet / "tickets" / "done").mkdir(parents=True)
    (projet / "tickets" / "done" / "ticket-001-x.md").write_text(
        "---\nid: ticket-001\ntitle: \"x\"\ntype: feat\nstatus: done\n---\n# x\n",
        encoding="utf-8",
    )

    def fournisseur(role: str) -> tuple[FakeProvider, str]:
        return (technique, "qwen") if role == "doc-technique" else (fonctionnel, "claude-haiku-4-5")

    svc = DocumentationService(FakeProvider(), _prompts(tmp_path), fournisseur=fournisseur)
    await svc.mettre_a_jour(projet)

    assert technique.calls and technique.calls[0]["model"] == "qwen"
    assert fonctionnel.calls and fonctionnel.calls[0]["model"] == "claude-haiku-4-5"


# ------------------------------------------------------------------
# Ce qui a tourné, en base
# ------------------------------------------------------------------


async def test_un_appel_enregistre_le_provider_qui_a_repondu(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    await init_db(db)
    run_id = await create_run(db, "p", "ticket-001")
    await save_agent_call(db, run_id, "ticket-001", "securite", "qwen", 1, 1, 0, 0.0, 1,
                          provider="ollama")
    async with aiosqlite.connect(db) as conn:
        async with conn.execute("SELECT provider, model FROM agent_calls") as cur:
            assert await cur.fetchone() == ("ollama", "qwen")


async def test_la_colonne_provider_arrive_par_migration(tmp_path: Path) -> None:
    # Une base existante n'est pas recréée : la colonne doit la rejoindre.
    db = tmp_path / "ancienne.db"
    async with aiosqlite.connect(db) as conn:
        await conn.execute(
            "CREATE TABLE agent_calls (id INTEGER PRIMARY KEY, run_id TEXT, "
            "ticket_id TEXT, role TEXT, model TEXT, input_tokens INTEGER, "
            "output_tokens INTEGER, cache_read_tokens INTEGER, cost_usd REAL, "
            "duration_ms INTEGER, created_at TEXT)"
        )
        await conn.commit()
    await init_db(db)
    async with aiosqlite.connect(db) as conn:
        async with conn.execute("PRAGMA table_info(agent_calls)") as cur:
            colonnes = [ligne[1] for ligne in await cur.fetchall()]
    assert "provider" in colonnes


async def test_le_runner_enregistre_le_provider_et_le_modele_utilises(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    await init_db(db)
    run_id = await create_run(db, "p", "ticket-001")
    provider = FakeProvider()
    runner = _runner(tmp_path, provider)
    runner._db_path = db
    provider._modele_rendu = "claude-haiku-4-5"  # type: ignore[attr-defined]

    class _Repli(FakeProvider):
        async def complete(self, **kwargs: Any) -> ProviderResult:
            result = await super().complete(**kwargs)
            result.model = "claude-haiku-4-5"
            return result

    runner._provider = _Repli()
    await runner.run(role=AgentRole.codeur, ticket=_make_ticket(), project_context="c", run_id=run_id)
    async with aiosqlite.connect(db) as conn:
        async with conn.execute("SELECT provider, model FROM agent_calls") as cur:
            assert await cur.fetchone() == ("fake", "claude-haiku-4-5")


# ------------------------------------------------------------------
# La liste blanche et l'API
# ------------------------------------------------------------------


def test_un_modele_hors_grille_passe_quand_le_provider_n_est_pas_anthropic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(project_loader, "PROVIDERS_CONNUS", (*PROVIDERS_CONNUS, "ollama"))
    projet = _manifeste(tmp_path, [_agent("securite", provider="ollama")])
    set_agent_model(projet, "securite", "qwen3-coder:30b")
    assert modele_du_role(projet, "securite") == "qwen3-coder:30b"


def test_un_modele_hors_grille_reste_refuse_sur_agent_sdk(tmp_path: Path) -> None:
    projet = _manifeste(tmp_path, [_agent("securite")])
    with pytest.raises(ModeleInconnu):
        set_agent_model(projet, "securite", "qwen3-coder:30b")


def test_set_agent_provider_ecrit_le_provider_et_le_repli(tmp_path: Path) -> None:
    projet = _manifeste(tmp_path, [_agent("securite"), _agent("codeur")])
    set_agent_provider(
        projet, "securite", "anthropic_api",
        fallback={"provider": "agent_sdk", "model": "claude-haiku-4-5"},
    )
    configs = {c.role: c for c in load_agents_config(projet)}
    assert configs["securite"].provider == "anthropic_api"
    assert configs["securite"].fallback is not None
    assert configs["codeur"].provider == "agent_sdk", "les autres ne bougent pas"
    set_agent_provider(projet, "securite", "agent_sdk", fallback=None)
    assert load_agents_config(projet)[0].fallback is None


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    projet = ws / "mon-projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(json.dumps({
        "project_id": "mon-projet",
        "agents": [_agent("securite", fallback={"provider": "agent_sdk", "model": "claude-haiku-4-5"})],
    }), encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


def test_l_api_rend_le_provider_le_repli_et_les_providers_connus(workspace: Path) -> None:
    body = TestClient(app).get("/api/v1/projects/mon-projet/agents").json()
    [agent] = body["agents"]
    assert agent["provider"] == "agent_sdk"
    assert agent["fallback"] == {"provider": "agent_sdk", "model": "claude-haiku-4-5"}
    assert set(body["known_providers"]) >= {"agent_sdk", "anthropic_api"}
    assert body["known_models_by_provider"]["agent_sdk"] == body["known_models"]


def test_l_api_change_le_provider_et_le_repli(workspace: Path) -> None:
    resp = TestClient(app).put(
        "/api/v1/projects/mon-projet/agents/securite",
        json={"model": "claude-haiku-4-5", "provider": "anthropic_api", "fallback": None},
    )
    assert resp.status_code == 200
    [agent] = resp.json()["agents"]
    assert agent["provider"] == "anthropic_api"
    assert agent["model"] == "claude-haiku-4-5"
    assert agent["fallback"] is None


def test_l_api_refuse_un_provider_inconnu(workspace: Path) -> None:
    resp = TestClient(app).put(
        "/api/v1/projects/mon-projet/agents/securite",
        json={"model": "claude-haiku-4-5", "provider": "olama"},
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------
# Un seul chemin de construction
# ------------------------------------------------------------------


def test_aucun_routeur_n_appelle_get_provider_directement() -> None:
    # Un point d'appel oublié resterait sur le provider global, et le rôle
    # déclaré dans le manifeste serait ignoré sans que rien ne le dise.
    fautifs = [
        f.name for f in (_SRC / "routers").glob("*.py")
        if re.search(r"\bget_provider\(", f.read_text(encoding="utf-8"))
    ]
    assert fautifs == []


def test_le_chat_passe_par_la_fabrique_pour_son_role(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tessera.routers import chat as routeur_chat

    roles: list[str] = []

    def fausse(project_path: Path, role: str, **kwargs: Any) -> FakeProvider:
        roles.append(role)
        return FakeProvider()

    monkeypatch.setattr(routeur_chat, "provider_pour_role", fausse)
    ws = tmp_path / "ws"
    projet = ws / "p"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# p\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)

    import asyncio
    asyncio.run(routeur_chat._build_service("p"))
    assert roles == ["chat"]
