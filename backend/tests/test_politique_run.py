"""La politique d'un run se lit une fois, avant le premier agent — ticket-119.

`lire_niveau` et `racine_autorisee` relisaient `agents.json` **après** le
passage du codeur : un ticket pouvait passer un projet en `merge` +
`ancestor` dans le même run, et la livraison obéissait au fichier réécrit.
"""
import json
from pathlib import Path

import pytest

from tessera.services.autonomie import NiveauAutonomie
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_workflow import GitHubWorkflowService, WorkflowError
from tessera.services.livraison import LivraisonService
from tessera.services.politique_run import PolitiqueRun
from tessera.services.providers.perimetre import hook_refus_hors_perimetre


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


def test_les_options_du_sdk_recoivent_la_racine_figee(tmp_path: Path) -> None:
    # Le provider reconstruit ses options à chaque appel d'agent : sans racine
    # figée, chaque agent du pipeline relirait `agents.json` à son tour.
    from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider

    provider = ClaudeAgentSDKProvider(racine_ecriture=tmp_path / "depot")

    assert provider.racine_ecriture == tmp_path / "depot"
