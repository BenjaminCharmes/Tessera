"""Les fichiers qui portent la politique du run se refusent — ticket-119.

`perimetre.py` acceptait toute écriture sous la racine du projet. Or c'est là
que vivent `agents.json` (la politique), `.git/hooks/` (du code exécuté par
`git commit` dans le process de l'orchestrateur, avec l'identité de
l'utilisateur), `.claude/settings*.json` (des hooks que le CLI exécute au run
suivant) et `.github/workflows/` (ce qui rend la CI « verte » en mode `merge`).
"""
import json
from pathlib import Path

import pytest

from tessera.models.worktree_config import ConfigWorktree
from tessera.services.commande_effective import commande_effective
from tessera.services.politique_run import PolitiqueRun
from tessera.services.providers.chemins_proteges import (
    PROTECTION_REFUS,
    motif_de_protection,
)
from tessera.services.providers.perimetre import (
    ECRITURE_REFUS,
    hook_refus_hors_perimetre,
)


def _projet(tmp_path: Path, nom: str = "client") -> Path:
    racine = tmp_path / "projects" / nom
    racine.mkdir(parents=True, exist_ok=True)
    return racine


@pytest.mark.parametrize(
    "relatif",
    [
        "agents.json",
        ".git/hooks/pre-commit",
        ".git/config",
        ".claude/settings.local.json",
        ".github/workflows/ci.yml",
    ],
)
async def test_le_hook_refuse_les_chemins_qui_portent_la_politique(
    tmp_path: Path, relatif: str
) -> None:
    # Un critère du ticket par chemin : chacun est une façon distincte de
    # changer, depuis l'intérieur du run, les règles qui bornent ce run.
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(projet / relatif)}},
        None,
        None,
    )

    decision = sortie["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"].startswith(PROTECTION_REFUS[:20])


async def test_le_refus_dit_pourquoi_et_ne_parle_pas_de_hors_perimetre(
    tmp_path: Path,
) -> None:
    # Le fichier **est** dans le projet : lui dire qu'il est hors périmètre
    # enverrait l'agent chercher un autre endroit où l'écrire.
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Edit", "tool_input": {"file_path": str(projet / "agents.json")}},
        None,
        None,
    )

    raison = sortie["hookSpecificOutput"]["permissionDecisionReason"]
    assert ECRITURE_REFUS[:30] not in raison
    assert "agents.json" in raison


async def test_une_redirection_bash_vers_un_hook_git_est_refusee(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'rm -rf ~' > .git/hooks/pre-commit"},
        },
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_un_chemin_relatif_est_protege_comme_un_absolu(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json"}},
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_le_depot_parent_d_un_projet_ancestor_est_protege_aussi(
    tmp_path: Path,
) -> None:
    # Le projet bootstrap écrit dans le dépôt qui le contient (ADR-028) : ses
    # `.git/` et `.github/workflows/` sont à la racine du dépôt, pas du projet.
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path)
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor"}), encoding="utf-8"
    )
    hook = hook_refus_hors_perimetre(projet)

    for relatif in (".git/hooks/pre-commit", ".github/workflows/ci.yml"):
        sortie = await hook(
            {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / relatif)}},
            None,
            None,
        )
        assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny", relatif


@pytest.mark.parametrize(
    "relatif",
    [
        "src/app.py",
        ".gitignore",
        ".github/CODEOWNERS",
        "docs/workflows/onboarding.md",
        "frontend/.claude/notes.md",
        "tests/fixtures/agents.json",
        "config/settings.json",
    ],
)
async def test_les_voisins_legitimes_passent(tmp_path: Path, relatif: str) -> None:
    # `.gitignore` n'est pas `.git`, `docs/workflows/` n'est pas
    # `.github/workflows/`, et un `agents.json` de fixture n'est pas celui du
    # projet : un faux refus priverait l'agent d'un fichier légitime.
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(projet / relatif)}},
        None,
        None,
    )

    assert sortie == {}, relatif


@pytest.mark.parametrize(
    "relatif",
    [
        "CLAUDE.md",
        "sous/dossier/CLAUDE.md",
        "CLAUDE.local.md",
        ".claude/skills/verifier/SKILL.md",
        ".claude/commands/ship.md",
        ".claude/agents/relecteur.md",
    ],
)
async def test_les_fichiers_de_consignes_sont_proteges(
    tmp_path: Path, relatif: str
) -> None:
    # Ticket-240 : le CLI charge ces fichiers dans chaque session. Les réécrire
    # pendant un run change la consigne de tous les agents suivants.
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(projet / relatif)}},
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny", relatif


@pytest.mark.parametrize("relatif", ["docs/CLAUDE-notes.md", "frontend/.claude/notes.md"])
async def test_les_voisins_des_consignes_passent(tmp_path: Path, relatif: str) -> None:
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(projet / relatif)}},
        None,
        None,
    )

    assert sortie == {}, relatif


def test_le_motif_de_claude_md_dit_qu_il_est_charge_partout(tmp_path: Path) -> None:
    projet = _projet(tmp_path)

    motif = motif_de_protection(str(projet / "CLAUDE.md"), projet, projet)

    assert motif is not None
    assert "CLAUDE.md" in motif
    assert "chaque session" in motif


def test_le_motif_nomme_ce_qui_est_protege(tmp_path: Path) -> None:
    projet = _projet(tmp_path)

    assert motif_de_protection(str(projet / "agents.json"), projet, projet) is not None
    assert motif_de_protection(str(projet / "src" / "x.py"), projet, projet) is None


def _worktree_de_verification(tmp_path: Path) -> Path:
    """A worktree shaped like ide-core; the manifest command lists no script."""
    racine = tmp_path / "wt"
    projet = racine / "projects" / "ide-core"
    projet.mkdir(parents=True)
    (racine / "scripts").mkdir()
    (racine / "scripts" / "verifier.py").write_text("print('ok')\n", encoding="utf-8")
    manifeste = {
        "git_root": "ancestor",
        "pipeline": {"test_command": "npm test", "test_cwd": "../../backend"},
    }
    (projet / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return racine


async def _ecrire_dans(racine: Path, relatif: str, commande: str | None) -> dict[str, object]:
    projet = racine / "projects" / "ide-core"
    hook = hook_refus_hors_perimetre(
        projet, racine=racine.resolve(), commande_effective=commande
    )
    entree = {"tool_name": "Write", "tool_input": {"file_path": str(racine / relatif)}}
    return dict(await hook(entree, None, None))


async def test_le_script_de_la_commande_effective_se_refuse_dans_le_worktree(
    tmp_path: Path,
) -> None:
    racine = _worktree_de_verification(tmp_path)
    commande = commande_effective(
        PolitiqueRun(
            test_command="npm test",
            worktree=ConfigWorktree(test_command="python {worktree}/scripts/verifier.py"),
        ),
        racine,
        tmp_path / "depot",
    )

    sortie = await _ecrire_dans(racine, "scripts/verifier.py", commande)

    decision = sortie["hookSpecificOutput"]
    assert isinstance(decision, dict)
    assert decision["permissionDecision"] == "deny"
    assert "verifier.py" in decision["permissionDecisionReason"]


async def test_sans_commande_effective_le_script_du_worktree_nest_pas_designe(
    tmp_path: Path,
) -> None:
    racine = _worktree_de_verification(tmp_path)

    assert await _ecrire_dans(racine, "scripts/verifier.py", None) == {}


async def test_le_script_de_la_commande_effective_se_resout_depuis_test_cwd(
    tmp_path: Path,
) -> None:
    racine = _worktree_de_verification(tmp_path)

    sortie = await _ecrire_dans(racine, "scripts/verifier.py", "python ../scripts/verifier.py")

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"  # type: ignore[index]
