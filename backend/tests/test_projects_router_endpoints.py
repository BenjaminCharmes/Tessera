"""Endpoints du router projects — ticket-053.

Trois des pannes rencontrées le 2026-09-15 passaient par ce router : l'import
avec un chemin entre guillemets, le planificateur sans son prompt, et les
agents sans clef valide. Chacune a ici son test de non-régression **au niveau
du router**, là où l'utilisateur les rencontrait.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db

from .conftest import requires_symlinks


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Fixture *synchrone* : `init_db` tourne dans sa propre boucle, close et
    # drainée avant que celle du test n'existe. Avec une fixture `async`, le
    # thread interne d'aiosqlite survit parfois à la fermeture de la boucle du
    # test précédent, et la suite complète se termine sur un
    # « RuntimeError: Event loop is closed ».
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text(
        "# mon-projet\n\nUn projet de test.\n", encoding="utf-8"
    )
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)

    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))

    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


def _client() -> TestClient:
    return TestClient(app)


# ------------------------------------------------------------------
# Lecture
# ------------------------------------------------------------------


def test_liste_les_projets_du_workspace() -> None:
    body = _client().get("/api/v1/projects").json()
    assert [p["id"] for p in body] == ["mon-projet"]


def test_projet_inexistant_renvoie_404() -> None:
    assert _client().get("/api/v1/projects/jamais-vu").status_code == 404


def test_contexte_projet_expose_claude_md_et_tickets() -> None:
    body = _client().get("/api/v1/projects/mon-projet/context").json()

    assert body["project_id"] == "mon-projet"
    assert "Un projet de test" in body["claude_md"]
    assert body["open_tickets"] == []


def test_contexte_d_un_projet_inexistant_renvoie_404() -> None:
    assert _client().get("/api/v1/projects/jamais-vu/context").status_code == 404


def test_usage_d_un_projet_sans_historique_vaut_zero() -> None:
    body = _client().get("/api/v1/projects/mon-projet/usage").json()
    assert body["total_cost_usd"] == 0.0


def test_runs_vides_pour_un_projet_neuf() -> None:
    assert _client().get("/api/v1/projects/mon-projet/runs").json() == []


def test_limite_de_runs_hors_bornes_est_refusee() -> None:
    # `limit` est borné entre 1 et 100 : hors bornes, FastAPI doit refuser
    # plutôt que laisser passer une requête non bornée.
    assert _client().get("/api/v1/projects/mon-projet/runs?limit=0").status_code == 422
    assert _client().get("/api/v1/projects/mon-projet/runs?limit=999").status_code == 422


# ------------------------------------------------------------------
# Import — non-régression des pannes du 2026-09-15
# ------------------------------------------------------------------


def test_import_d_un_chemin_relatif_est_refuse_avec_un_message_exploitable(
    workspace: Path,
) -> None:
    # Panne vécue : un chemin relatif était résolu depuis le cwd du backend,
    # d'où « Le dossier source n'existe pas : .../backend/... » (ticket-050).
    resp = _client().post(
        "/api/v1/projects/import", json={"source_path": "mon-projet", "mode": "copy"}
    )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert "absolu" in detail.lower()


def test_import_retire_les_guillemets_du_chemin(tmp_path: Path, workspace: Path) -> None:
    # Panne vécue : « Copier en tant que chemin d'accès » sous Windows entoure
    # le chemin de guillemets, ce qui le faisait passer pour relatif.
    source = tmp_path / "source-projet"
    source.mkdir()
    (source / "main.py").write_text("print('hello')\n", encoding="utf-8")

    resp = _client().post(
        "/api/v1/projects/import",
        json={"source_path": f'"{source}"', "mode": "copy"},
    )

    assert resp.status_code == 201
    assert resp.json()["project"]["id"] == "source-projet"


@requires_symlinks
def test_un_projet_importe_en_symlink_exclut_ses_artefacts_du_depot(
    tmp_path: Path, workspace: Path
) -> None:
    # Panne latente : `default_mode_for` existait depuis ticket-062 mais
    # n'etait cable que sur le clone. Un depot pro lie en symlink repartait
    # donc en `tracked`, et le premier commit de ticket y poussait
    # `tickets/` et `memory/` — sans que rien ne le signale.
    source = tmp_path / "depot-client"
    (source / ".git" / "info").mkdir(parents=True)
    (source / "main.py").write_text("x = 1", encoding="utf-8")

    resp = _client().post(
        "/api/v1/projects/import",
        json={"source_path": str(source), "mode": "symlink"},
    )
    assert resp.status_code == 201

    assert _client().get("/api/v1/projects/depot-client/artifacts").json()["mode"] == "local"

    exclude = source / ".git" / "info" / "exclude"
    assert exclude.is_file(), "l'exclusion doit etre ecrite a l'import"
    assert "tickets/" in exclude.read_text(encoding="utf-8")


def test_un_projet_importe_en_copie_consigne_le_mode_local(
    tmp_path: Path, workspace: Path
) -> None:
    # En mode copie, `.git` n'est deliberement pas copie : il n'y a rien a
    # exclure, mais le mode doit quand meme etre consigne pour que le depot
    # cree plus tard herite du bon choix.
    source = tmp_path / "projet-copie"
    source.mkdir()
    (source / "main.py").write_text("x = 1", encoding="utf-8")

    resp = _client().post(
        "/api/v1/projects/import",
        json={"source_path": str(source), "mode": "copy"},
    )
    assert resp.status_code == 201
    assert _client().get("/api/v1/projects/projet-copie/artifacts").json()["mode"] == "local"


def test_import_d_un_projet_deja_present_renvoie_409(
    tmp_path: Path, workspace: Path
) -> None:
    source = tmp_path / "mon-projet"
    source.mkdir()

    resp = _client().post(
        "/api/v1/projects/import", json={"source_path": str(source), "mode": "copy"}
    )

    assert resp.status_code == 409
    assert "existe déjà" in resp.json()["detail"]


def test_import_avec_un_mode_inconnu_est_refuse(tmp_path: Path) -> None:
    resp = _client().post(
        "/api/v1/projects/import",
        json={"source_path": str(tmp_path), "mode": "telepathie"},
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------
# Planificateur — non-régression de la panne « rien ne se passe »
# ------------------------------------------------------------------


def test_plan_sans_prompt_renvoie_un_message_exploitable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Panne vécue : « Planifier une évolution » tournait puis s'arrêtait, avec
    # un 500 opaque. Depuis ticket-051 le prompt manquant se dit ; le message
    # doit atteindre l'UI, pas finir en « Internal Server Error ».
    monkeypatch.setattr(settings, "ide_prompts_dir", tmp_path / "prompts-vides")

    resp = _client().post(
        "/api/v1/projects/mon-projet/plan",
        json={"description": "Ajouter un endpoint de santé"},
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "planificateur.md" in detail
    assert "IDE_PROMPTS_DIR" in detail


def test_plan_sans_description_est_refuse() -> None:
    assert (
        _client().post("/api/v1/projects/mon-projet/plan", json={}).status_code == 422
    )


# ------------------------------------------------------------------
# Création et clone
# ------------------------------------------------------------------


def test_creation_d_un_projet_deja_existant_renvoie_409() -> None:
    resp = _client().post(
        "/api/v1/projects",
        json={"project_id": "mon-projet", "name": "Mon projet", "active_agents": []},
    )

    assert resp.status_code == 409


def test_clone_d_une_url_invalide_est_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    from tessera.services.git_clone import CloneError

    async def _refuse(self: object, **kwargs: object) -> None:
        raise CloneError("URL de dépôt invalide : pas-une-url")

    monkeypatch.setattr("tessera.services.git_clone.GitCloneService.clone", _refuse)

    resp = _client().post("/api/v1/projects/clone", json={"repo_url": "pas-une-url"})

    assert resp.status_code == 422
    assert "invalide" in resp.json()["detail"]


def test_creation_sans_project_id_est_refusee() -> None:
    resp = _client().post("/api/v1/projects", json={"name": "Sans identifiant"})
    assert resp.status_code == 422


# ------------------------------------------------------------------
# Synchronisation GitHub
# ------------------------------------------------------------------


def test_github_sync_sur_un_projet_inexistant_renvoie_404() -> None:
    resp = _client().post(
        "/api/v1/projects/jamais-vu/github/sync", json={"direction": "pull"}
    )
    assert resp.status_code == 404


def test_github_sync_sans_remote_explique_ce_qui_manque() -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/github/sync", json={"direction": "pull"}
    )

    assert resp.status_code == 422
    assert "github_remote" in resp.json()["detail"]


def test_github_sync_sans_token_explique_ce_qui_manque(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    (workspace / "mon-projet" / "agents.json").write_text(
        json.dumps({"github_remote": "owner/repo"}), encoding="utf-8"
    )
    monkeypatch.setattr(settings, "github_token", "")

    resp = _client().post(
        "/api/v1/projects/mon-projet/github/sync", json={"direction": "pull"}
    )

    assert resp.status_code == 422
    assert "GITHUB_TOKEN" in resp.json()["detail"]


def test_github_sync_avec_une_direction_inconnue_est_refuse() -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/github/sync", json={"direction": "de-cote"}
    )
    assert resp.status_code == 422


def test_analyse_d_un_projet_inexistant_renvoie_404() -> None:
    resp = _client().post(
        "/api/v1/projects/jamais-vu/analyze", json={"project_id": "jamais-vu"}
    )
    assert resp.status_code == 404


# ------------------------------------------------------------------
# Liaison git — ticket-061
# ------------------------------------------------------------------


def test_statut_git_d_un_projet_sans_depot(workspace: Path) -> None:
    body = _client().get("/api/v1/projects/mon-projet/git/status").json()

    assert body["is_repository"] is False
    assert body["remote_url"] is None


def test_init_puis_statut_montre_un_depot_avec_commit(workspace: Path) -> None:
    # Du contenu de projet, pas seulement des artefacts Tessera : ces derniers
    # sont exclus dès l'init, et un dépôt qui ne contient qu'eux n'a rien à
    # committer.
    (workspace / "mon-projet" / "main.py").write_text("x = 1", encoding="utf-8")

    resp = _client().post("/api/v1/projects/mon-projet/git/init")

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_repository"] is True
    assert body["has_commits"] is True


def test_lier_sans_depot_est_refuse(workspace: Path) -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/git/link",
        json={"repo_url": "https://github.com/moi/repo.git", "confirmed": True},
    )

    assert resp.status_code == 422
    assert "dépôt" in resp.json()["detail"].lower()


def test_lier_un_remote_apres_init(workspace: Path) -> None:
    _client().post("/api/v1/projects/mon-projet/git/init")

    resp = _client().post(
        "/api/v1/projects/mon-projet/git/link",
        json={"repo_url": "https://github.com/moi/repo.git", "confirmed": True},
    )

    assert resp.status_code == 200
    assert resp.json()["remote_url"] == "https://github.com/moi/repo.git"


def test_lier_une_url_invalide_est_refuse(workspace: Path) -> None:
    _client().post("/api/v1/projects/mon-projet/git/init")

    resp = _client().post(
        "/api/v1/projects/mon-projet/git/link",
        json={"repo_url": "pas-une-url", "confirmed": True},
    )

    assert resp.status_code == 422
    assert "URL" in resp.json()["detail"]


def test_lier_un_depot_distant_inaccessible_est_refuse(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Dépôt inexistant ou token sans droits : l'utilisateur doit savoir que le
    # problème est côté GitHub, pas côté projet.
    from tessera.services.github_service import RepositoryInfo

    monkeypatch.setattr(settings, "github_token", "ghp_test")

    async def _absent(self: object) -> RepositoryInfo:
        return RepositoryInfo(exists=False)

    monkeypatch.setattr(
        "tessera.services.github_service.GitHubService.get_repository_info", _absent
    )
    _client().post("/api/v1/projects/mon-projet/git/init")

    resp = _client().post(
        "/api/v1/projects/mon-projet/git/link",
        json={"repo_url": "https://github.com/moi/repo.git"},
    )

    assert resp.status_code == 422
    assert "introuvable" in resp.json()["detail"]


def test_un_depot_distant_non_vide_demande_confirmation(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tessera.services.github_service import RepositoryInfo

    monkeypatch.setattr(settings, "github_token", "ghp_test")

    async def _non_vide(self: object) -> RepositoryInfo:
        return RepositoryInfo(exists=True, is_empty=False)

    monkeypatch.setattr(
        "tessera.services.github_service.GitHubService.get_repository_info", _non_vide
    )
    _client().post("/api/v1/projects/mon-projet/git/init")

    resp = _client().post(
        "/api/v1/projects/mon-projet/git/link",
        json={"repo_url": "https://github.com/moi/repo.git"},
    )

    assert resp.status_code == 409
    assert "n'est pas vide" in resp.json()["detail"]


# ------------------------------------------------------------------
# Artefacts Tessera — ticket-062
# ------------------------------------------------------------------


def test_mode_des_artefacts_par_defaut(workspace: Path) -> None:
    # Fallback ferme : un projet qui ne declare rien garde ses artefacts chez
    # lui. Le defaut inverse poussait tickets/ et memory/ dans le depot.
    body = _client().get("/api/v1/projects/mon-projet/artifacts").json()

    assert body["mode"] == "local"
    assert body["already_tracked"] == []


def test_passer_les_artefacts_en_local(workspace: Path) -> None:
    _client().post("/api/v1/projects/mon-projet/git/init")

    resp = _client().put(
        "/api/v1/projects/mon-projet/artifacts", json={"mode": "local"}
    )

    assert resp.status_code == 200
    assert resp.json()["mode"] == "local"

    exclude = (workspace / "mon-projet" / ".git" / "info" / "exclude").read_text(
        encoding="utf-8"
    )
    assert "tickets/" in exclude


def test_le_gitignore_du_projet_n_est_jamais_touche(workspace: Path) -> None:
    # Le point central : `.gitignore` est versionné, donc le modifier
    # annoncerait dans un diff ce qu'on voulait garder hors du dépôt.
    project = workspace / "mon-projet"
    (project / ".gitignore").write_text("dist/\n", encoding="utf-8")
    _client().post("/api/v1/projects/mon-projet/git/init")

    _client().put("/api/v1/projects/mon-projet/artifacts", json={"mode": "local"})

    assert (project / ".gitignore").read_text(encoding="utf-8") == "dist/\n"


def test_les_artefacts_deja_suivis_sont_remontes(workspace: Path) -> None:
    # Ils ne sont pas retirés : les sortir de l'index est un `git rm --cached`,
    # qui se décide.
    #
    # Le projet déclare `tracked` **avant** l'init : depuis que l'init applique
    # le mode déclaré, un projet qui ne déclare rien n'a plus aucun artefact
    # suivi — et ce test n'aurait plus rien à observer.
    (workspace / "mon-projet" / "agents.json").write_text(
        '{"artifacts": "tracked"}', encoding="utf-8"
    )
    _client().post("/api/v1/projects/mon-projet/git/init")

    body = _client().put(
        "/api/v1/projects/mon-projet/artifacts", json={"mode": "local"}
    ).json()

    assert "CLAUDE.md" in body["already_tracked"]


def test_un_mode_inconnu_est_refuse(workspace: Path) -> None:
    resp = _client().put(
        "/api/v1/projects/mon-projet/artifacts", json={"mode": "n-importe-quoi"}
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------
# Retrait d'un projet — ticket-063
# ------------------------------------------------------------------


def test_le_plan_de_retrait_nomme_le_chemin_reel(workspace: Path) -> None:
    body = _client().get("/api/v1/projects/mon-projet/removal-plan").json()

    assert body["project_id"] == "mon-projet"
    assert body["real_path"].endswith("mon-projet")
    assert body["is_symlink"] is False


def test_le_plan_compte_les_commits_non_pousses(workspace: Path) -> None:
    # C'est ce que l'utilisateur perdrait : la confirmation doit le nommer.
    #
    # Il faut du contenu de projet, pas seulement des artefacts Tessera :
    # ceux-ci sont désormais exclus dès l'init, et un dépôt qui ne contient
    # qu'eux n'a aucun commit.
    (workspace / "mon-projet" / "main.py").write_text("x = 1", encoding="utf-8")
    _client().post("/api/v1/projects/mon-projet/git/init")

    body = _client().get("/api/v1/projects/mon-projet/removal-plan").json()

    assert body["unpushed_commits"] >= 1


def test_detacher_un_projet_deplace_les_fichiers_sans_les_perdre(
    workspace: Path,
) -> None:
    resp = _client().post("/api/v1/projects/mon-projet/detach")

    assert resp.status_code == 200
    moved_to = Path(resp.json()["moved_to"])
    assert moved_to.is_dir()
    assert (moved_to / "CLAUDE.md").exists()
    assert not (workspace / "mon-projet").exists()


def test_supprimer_sans_confirmation_est_refuse(workspace: Path) -> None:
    resp = _client().delete("/api/v1/projects/mon-projet")

    assert resp.status_code == 409
    assert (workspace / "mon-projet").is_dir()


def test_supprimer_avec_confirmation_efface(workspace: Path) -> None:
    resp = _client().delete("/api/v1/projects/mon-projet?confirmed=true")

    assert resp.status_code == 204
    assert not (workspace / "mon-projet").exists()


def test_supprimer_un_projet_lie_ne_touche_jamais_la_cible(
    workspace: Path, tmp_path: Path
) -> None:
    # Le garde-fou qui compte : `projects/fluentdb` EST `Desktop/fluentdb`.
    source = tmp_path / "vrai-dossier"
    source.mkdir()
    (source / "important.py").write_text("ne pas perdre\n", encoding="utf-8")
    link = workspace / "projet-lie"
    try:
        link.symlink_to(source, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks indisponibles sur cette machine")

    resp = _client().delete("/api/v1/projects/projet-lie?confirmed=true")

    assert resp.status_code == 204
    assert not link.exists()
    assert source.is_dir()
    assert (source / "important.py").read_text(encoding="utf-8") == "ne pas perdre\n"


def test_le_plan_de_nettoyage_est_lisible_avant_d_agir(workspace: Path) -> None:
    # Supprimer une branche est irreversible : l'utilisateur doit pouvoir lire
    # ce qui partira, et pourquoi le reste demeure.
    _client().post("/api/v1/projects/mon-projet/git/init")

    resp = _client().get("/api/v1/projects/mon-projet/branches/cleanup")

    assert resp.status_code == 200
    body = resp.json()
    assert "nettoyables" in body and "conservees" in body


def test_une_branche_hors_plan_n_est_pas_supprimee(workspace: Path) -> None:
    # Le plan est recalcule cote serveur : se fier a la liste envoyee par
    # l'interface reviendrait a supprimer sur la foi d'un etat perime.
    _client().post("/api/v1/projects/mon-projet/git/init")

    resp = _client().post(
        "/api/v1/projects/mon-projet/branches/cleanup",
        json={"branches": ["main", "une-branche-qui-n-existe-pas"]},
    )

    assert resp.status_code == 200
    assert resp.json() == []
