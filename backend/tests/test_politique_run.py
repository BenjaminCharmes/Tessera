"""La politique d'un run se lit une fois, avant le premier agent — ticket-119.

`lire_niveau` et `racine_autorisee` relisaient `agents.json` **après** le
passage du codeur : un ticket pouvait passer un projet en `merge` +
`ancestor` dans le même run, et la livraison obéissait au fichier réécrit.
"""
import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from tessera.config import Settings, settings
from tessera.models.worktree_config import ConfigWorktree, EntreePopulate
from tessera.services.autonomie import NiveauAutonomie
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_workflow import GitHubWorkflowService, WorkflowError
from tessera.services.livraison import LivraisonService
from tessera.services.politique_run import PolitiqueRun
from tessera.services.providers.perimetre import hook_refus_hors_perimetre
from tessera.services.run_worktree import RunWorktree


def _projet(tmp_path: Path, manifeste: dict[str, object] | None) -> Path:
    racine = tmp_path / "projects" / "client"
    racine.mkdir(parents=True, exist_ok=True)
    if manifeste is not None:
        (racine / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return racine


def _reecrire(projet: Path, manifeste: dict[str, object]) -> None:
    """Ce qu'un agent ferait par `Edit agents.json` au milieu du run."""
    (projet / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")


# ------------------------------------------------------------------
# Lecture
# ------------------------------------------------------------------


def test_la_politique_reprend_les_quatre_reglages_du_manifeste(tmp_path: Path) -> None:
    projet = _projet(
        tmp_path,
        {
            "autonomy": "pr",
            "git_root": "ancestor",
            "artifacts": "tracked",
            "pipeline": {"test_command": "uv run pytest -q"},
        },
    )

    politique = PolitiqueRun.lire(projet)

    assert politique.autonomy is NiveauAutonomie.pr
    assert politique.dans_le_depot_parent is True
    assert politique.artifacts == "tracked"
    assert politique.test_command == "uv run pytest -q"


def test_sans_manifeste_la_politique_est_fermee(tmp_path: Path) -> None:
    # ADR-023, ADR-028, ADR-029 : le défaut protège, l'exception s'énonce.
    politique = PolitiqueRun.lire(_projet(tmp_path, None))

    assert politique.autonomy is NiveauAutonomie.commit
    assert politique.dans_le_depot_parent is False
    assert politique.artifacts == "local"
    assert politique.test_command is None


def test_une_valeur_inconnue_de_git_root_ne_desarme_rien(tmp_path: Path) -> None:
    politique = PolitiqueRun.lire(_projet(tmp_path, {"git_root": "parent"}))

    assert politique.dans_le_depot_parent is False


def test_la_racine_d_ecriture_suit_la_politique_et_non_le_fichier(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, {"git_root": "ancestor"})

    figee = PolitiqueRun(autonomy=NiveauAutonomie.commit)

    assert figee.racine_ecriture(projet) == projet.resolve()
    assert PolitiqueRun.lire(projet).racine_ecriture(projet) == tmp_path.resolve()


# ------------------------------------------------------------------
# Ce que les services voient, une fois la politique figée
# ------------------------------------------------------------------


class _FauxGit:
    async def rejouer_sur(self, base: str, resolveur: object = None) -> tuple[str, ...]:
        return ()


class _FauxWorkflow:
    def __init__(self) -> None:
        self.ouvertures = 0

    async def open_pull_request(self, **kwargs: object) -> object:
        self.ouvertures += 1

        class _R:
            pr_number = 1

        return _R()

    async def etat_ci(self, pr_number: int) -> str:
        return "passing"

    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool:
        return True


async def test_editer_agents_json_pendant_le_run_ne_change_pas_la_livraison(
    tmp_path: Path,
) -> None:
    # Le cas du ticket : le codeur écrit `{"autonomy": "merge"}` dans
    # agents.json, et la livraison, qui relisait le fichier, mergeait.
    projet = _projet(tmp_path, {"autonomy": "commit"})
    politique = PolitiqueRun.lire(projet)
    workflow = _FauxWorkflow()
    service = LivraisonService(
        git_workspace=_FauxGit(),
        workflow=workflow,
        project_path=projet,
        base_branch="develop",
        politique=politique,
    )

    _reecrire(projet, {"autonomy": "merge"})
    livraison = await service.livrer(
        ticket_id="ticket-001",
        ticket_title="T",
        ticket_body="",
        branch="ticket-001-x",
        approuve=True,
    )

    assert livraison.merged is False
    assert workflow.ouvertures == 0
    assert livraison.arret is not None
    assert "commité sur ticket-001-x" in livraison.arret


async def test_le_workflow_github_tient_le_niveau_fige(tmp_path: Path) -> None:
    projet = _projet(tmp_path, {"autonomy": "commit"})
    service = GitHubWorkflowService(
        git_workspace=None,
        github=None,
        base_branch="develop",
        project_path=projet,
        politique=PolitiqueRun.lire(projet),
    )

    _reecrire(projet, {"autonomy": "pr"})

    with pytest.raises(WorkflowError, match="ne laisse pas l'IDE pousser"):
        await service.open_pull_request(
            branch="b", ticket_id="t", ticket_title="T", ticket_body=""
        )


def test_le_workspace_git_tient_la_racine_figee(tmp_path: Path) -> None:
    # `git_root: ancestor` déplace le `git add` à la racine du dépôt (`:/`) :
    # un agent qui l'écrit en cours de run ferait committer au-dessus du projet.
    projet = _projet(tmp_path, {})
    service = GitWorkspaceService(projet, politique=PolitiqueRun.lire(projet))

    _reecrire(projet, {"git_root": "ancestor"})

    assert service._travaille_dans_le_parent() is False


async def test_le_hook_de_perimetre_tient_la_racine_figee(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, {})
    hook = hook_refus_hors_perimetre(projet, racine=PolitiqueRun.lire(projet).racine_ecriture(projet))

    _reecrire(projet, {"git_root": "ancestor"})
    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "backend" / "x.py")}},
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"


# ------------------------------------------------------------------
# merge_method — ticket-265
# ------------------------------------------------------------------


def test_merge_method_vaut_squash_par_defaut(tmp_path: Path) -> None:
    # Absent de agents.json : le défaut protège (convention ticket → develop).
    politique = PolitiqueRun.lire(_projet(tmp_path, {}))

    assert politique.merge_method == "squash"


def test_merge_method_sans_manifeste_vaut_squash(tmp_path: Path) -> None:
    politique = PolitiqueRun.lire(_projet(tmp_path, None))

    assert politique.merge_method == "squash"


def test_merge_method_merge_est_respecte(tmp_path: Path) -> None:
    politique = PolitiqueRun.lire(_projet(tmp_path, {"merge_method": "merge"}))

    assert politique.merge_method == "merge"


def test_merge_method_rebase_est_respecte(tmp_path: Path) -> None:
    politique = PolitiqueRun.lire(_projet(tmp_path, {"merge_method": "rebase"}))

    assert politique.merge_method == "rebase"


def test_merge_method_valeur_inconnue_retombe_sur_squash(tmp_path: Path) -> None:
    # Une valeur non reconnue ne désarme pas le défaut (ADR-023 pattern).
    politique = PolitiqueRun.lire(_projet(tmp_path, {"merge_method": "fast-forward"}))

    assert politique.merge_method == "squash"


# ------------------------------------------------------------------
# Worktree déclaré (ticket-521, ADR-056)
# ------------------------------------------------------------------


def _avec_worktree(tmp_path: Path, worktree: object, **reste: object) -> Path:
    """Un projet `tracked` : sans cela le worktree est refusé (artifacts local)."""
    return _projet(tmp_path, {"artifacts": "tracked", "worktree": worktree, **reste})


def test_sans_cle_worktree_la_politique_n_en_porte_pas(tmp_path: Path) -> None:
    politique = PolitiqueRun.lire(_projet(tmp_path, {"artifacts": "tracked"}))

    assert politique.worktree is None


def test_une_declaration_valide_devient_une_config_worktree(tmp_path: Path) -> None:
    projet = _avec_worktree(
        tmp_path,
        {
            "populate": [
                {"path": "CLAUDE.md", "mode": "copy"},
                {"path": "backend/.venv", "mode": "link"},
            ],
            "env": {"PYTHONPATH": "{worktree}/backend/src"},
            "test_command": "{repo}/backend/.venv/Scripts/python.exe scripts/verifier.py",
        },
    )

    config = PolitiqueRun.lire(projet).worktree

    assert config is not None
    assert [(e.path, e.mode) for e in config.populate] == [
        ("CLAUDE.md", "copy"),
        ("backend/.venv", "link"),
    ]
    assert dict(config.env) == {"PYTHONPATH": "{worktree}/backend/src"}
    assert config.test_command == "{repo}/backend/.venv/Scripts/python.exe scripts/verifier.py"


def test_une_declaration_vide_donne_une_config_sans_entree(tmp_path: Path) -> None:
    config = PolitiqueRun.lire(_avec_worktree(tmp_path, {})).worktree

    assert config is not None
    assert config.populate == ()
    assert dict(config.env) == {}
    assert config.test_command is None


@pytest.mark.parametrize(
    "refusee",
    [
        {"path": "a", "mode": "symlink"},
        {"path": "a", "mode": "LINK"},
        {"path": "a"},
        {"mode": "copy"},
        {"path": "/etc/passwd", "mode": "copy"},
        {"path": "\\\\serveur\\partage", "mode": "copy"},
        {"path": "C:/Users/x", "mode": "copy"},
        {"path": "../dehors", "mode": "copy"},
        {"path": "a/../../dehors", "mode": "link"},
        {"path": "a\\..\\b", "mode": "copy"},
        {"path": "", "mode": "copy"},
        "backend/.venv",
    ],
)
def test_une_entree_douteuse_est_retiree_et_les_autres_gardees(
    tmp_path: Path, refusee: object
) -> None:
    valide = {"path": "CLAUDE.md", "mode": "copy"}
    projet = _avec_worktree(tmp_path, {"populate": [refusee, valide]})

    config = PolitiqueRun.lire(projet).worktree

    assert config is not None
    assert [e.path for e in config.populate] == ["CLAUDE.md"]


def test_le_env_de_tessera_est_retire_sous_toutes_ses_graphies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ADR-053 : le copier dans un dossier où le codeur écrit le lui rendrait lisible.
    depot = tmp_path / "depot"
    (depot / ".git").mkdir(parents=True)
    projet = depot / "projects" / "client"
    projet.mkdir(parents=True)
    monkeypatch.setattr(Settings, "env_file", depot / ".env")
    entrees = [{"path": p, "mode": "copy"} for p in (".env", "./.env", "sous/../.env", "ok.txt")]
    _reecrire(
        projet,
        {"artifacts": "tracked", "git_root": "ancestor", "worktree": {"populate": entrees}},
    )

    config = PolitiqueRun.lire(projet).worktree

    assert config is not None
    assert [e.path for e in config.populate] == ["ok.txt"]


def test_le_env_d_un_projet_se_copie(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Le `.env` du projet est le sien : seul celui de Tessera est protégé.
    monkeypatch.setattr(Settings, "env_file", tmp_path / "ailleurs" / ".env")
    projet = _avec_worktree(tmp_path, {"populate": [{"path": ".env", "mode": "copy"}]})

    config = PolitiqueRun.lire(projet).worktree

    assert config is not None
    assert [e.path for e in config.populate] == [".env"]


@pytest.mark.parametrize(
    "declaration",
    [
        "oui",
        ["CLAUDE.md"],
        {"populate": "CLAUDE.md"},
        {"env": ["PYTHONPATH"]},
        {"env": {"PYTHONPATH": 1}},
        {"test_command": 3},
    ],
)
def test_une_declaration_mal_typee_donne_none(tmp_path: Path, declaration: object) -> None:
    assert PolitiqueRun.lire(_avec_worktree(tmp_path, declaration)).worktree is None


def test_un_agents_json_illisible_donne_none(tmp_path: Path) -> None:
    projet = _projet(tmp_path, None)
    (projet / "agents.json").write_text('{"worktree": {"populate": [', encoding="utf-8")

    assert PolitiqueRun.lire(projet).worktree is None


def test_un_projet_local_qui_declare_un_worktree_n_en_a_pas(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    projet = _projet(tmp_path, {"artifacts": "local", "worktree": {"populate": []}})

    with caplog.at_level(logging.WARNING, logger="tessera.services.worktree_politique"):
        politique = PolitiqueRun.lire(projet)

    assert politique.worktree is None
    assert any(r.getMessage() == "worktree_ignore" for r in caplog.records)
    assert any(getattr(r, "raison", "") == "artifacts_local" for r in caplog.records)


def test_un_manifeste_sans_artifacts_est_local_donc_sans_worktree(tmp_path: Path) -> None:
    # Le défaut d'`artifacts` est `local` (ADR-023) : il ne laisse rien passer.
    projet = _projet(tmp_path, {"worktree": {}})

    assert PolitiqueRun.lire(projet).worktree is None


def test_une_entree_retiree_est_journalisee(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    projet = _avec_worktree(tmp_path, {"populate": [{"path": "a", "mode": "symlink"}]})

    with caplog.at_level(logging.WARNING, logger="tessera.services.worktree_politique"):
        PolitiqueRun.lire(projet)

    assert any(r.getMessage() == "worktree_populate_retire" for r in caplog.records)


def test_config_worktree_est_immuable() -> None:
    config = ConfigWorktree(populate=(EntreePopulate(path="a", mode="copy"),))

    with pytest.raises(ValidationError):
        config.test_command = "autre"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        config.populate[0].path = "b"  # type: ignore[misc]


def test_la_politique_lit_le_worktree_une_seule_fois(tmp_path: Path) -> None:
    # Ce qu'un agent réécrit dans `agents.json` ne vaut qu'au run suivant.
    projet = _avec_worktree(tmp_path, {"populate": [{"path": "a", "mode": "copy"}]})
    politique = PolitiqueRun.lire(projet)

    _reecrire(projet, {"artifacts": "tracked", "worktree": {"test_command": "rm -rf /"}})

    assert politique.worktree is not None
    assert politique.worktree.test_command is None


def test_ide_worktrees_dir_vaut_tessera_worktrees_dans_le_dossier_personnel() -> None:
    assert settings.ide_worktrees_dir == Path.home() / ".tessera" / "worktrees"


def test_les_options_du_sdk_recoivent_la_racine_figee(tmp_path: Path) -> None:
    # Le provider reconstruit ses options à chaque appel d'agent : sans racine
    # figée, chaque agent du pipeline relirait `agents.json` à son tour.
    from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider

    provider = ClaudeAgentSDKProvider(racine_ecriture=tmp_path / "depot")

    assert provider.racine_ecriture == tmp_path / "depot"


# ------------------------------------------------------------------
# racine_ecriture et worktree — ticket-525
# ------------------------------------------------------------------


def _worktree(tmp_path: Path) -> RunWorktree:
    racine = tmp_path / "worktrees" / "client" / "ticket-1"
    projet = racine / "projects" / "client"
    projet.mkdir(parents=True)
    return RunWorktree(racine=racine, projet=projet, branche="ticket-1-demo")


def test_racine_ecriture_sans_worktree_est_inchangee(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, {})

    assert PolitiqueRun().racine_ecriture(projet, None) == projet.resolve()
    assert PolitiqueRun(git_root="ancestor").racine_ecriture(projet, None) == tmp_path.resolve()


def test_racine_ecriture_d_un_projet_ancestor_est_la_racine_du_worktree(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, {})
    wt = _worktree(tmp_path)

    racine = PolitiqueRun(git_root="ancestor").racine_ecriture(projet, wt)

    assert racine == wt.racine.resolve()


def test_racine_ecriture_d_un_projet_simple_est_son_dossier_dans_le_worktree(tmp_path: Path) -> None:
    projet = _projet(tmp_path, {})
    wt = _worktree(tmp_path)

    assert PolitiqueRun().racine_ecriture(projet, wt) == wt.projet.resolve()
