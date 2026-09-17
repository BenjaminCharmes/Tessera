"""Interdiction du git qui modifie l'historique, cote agent — ticket-068."""
import pytest

from vibe_ide.services.providers.git_guard import (
    GIT_REFUS,
    commande_git_interdite,
)


@pytest.mark.parametrize(
    "commande",
    [
        "git commit -m 'feat: truc'",
        "git merge ticket-001",
        "git push origin main",
        "git push",
        "git checkout main",
        "git switch main",
        "git branch -d vieux",
        "git reset --hard HEAD~1",
        "git rebase main",
        "git cherry-pick abc123",
        "git tag v1.0",
        "git stash",
        "git add -A",
        "git rm --cached CLAUDE.md",
    ],
)
def test_les_commandes_qui_modifient_l_historique_sont_refusees(commande: str) -> None:
    # Panne vecue le 2026-09-17 : les agents ont commite, merge dans `main` et
    # pousse sur GitHub pendant deux runs, avec leurs propres messages et du
    # travail hors perimetre. ADR-022 dit « l'agent ne merge jamais » — rien ne
    # l'en empechait, parce que la regle ne contraignait que
    # `GitWorkspaceService`, et que l'agent a `Bash`.
    assert commande_git_interdite(commande) is True


@pytest.mark.parametrize(
    "commande",
    [
        "git status",
        "git status --short",
        "git diff",
        "git diff --stat main..HEAD",
        "git log --oneline -5",
        "git show HEAD",
        "git rev-parse --show-toplevel",
        "git ls-files",
    ],
)
def test_le_git_en_lecture_reste_permis(commande: str) -> None:
    # Lire le depot fait partie du travail : c'est ce qui permet a un agent de
    # comprendre ce qui existe avant d'ecrire.
    assert commande_git_interdite(commande) is False


@pytest.mark.parametrize(
    "commande",
    [
        "cd frontend && git push",
        "cd /tmp/x ; git commit -m x",
        "git   commit -m 'espaces multiples'",
        "git -C /autre/depot commit -m x",
        "git --git-dir=.git commit -m x",
        "ls && git merge main && echo ok",
    ],
)
def test_les_formes_detournees_sont_couvertes(commande: str) -> None:
    # Un refus qui ne tient qu'au prefixe de la chaine ne protege de rien.
    assert commande_git_interdite(commande) is True


@pytest.mark.parametrize(
    "commande",
    ["npm test", "pytest -q", "ls -la", "echo 'git commit'", "cat git_notes.md"],
)
def test_ce_qui_n_est_pas_du_git_passe(commande: str) -> None:
    assert commande_git_interdite(commande) is False


def test_le_refus_explique_a_qui_revient_le_commit() -> None:
    # Un agent a qui l'on refuse sans expliquer reessaie, ou abandonne le
    # ticket. Le message doit lui dire que le commit est fait pour lui.
    assert "pipeline" in GIT_REFUS.lower()


# ------------------------------------------------------------------
# Branchement sur le SDK — hook PreToolUse
# ------------------------------------------------------------------


async def test_le_hook_refuse_un_git_qui_ecrit() -> None:
    # Le refus passe par un hook PreToolUse et non par `can_use_tool` : le SDK
    # avertit qu'une entree de `allowed_tools` couvrant un outil entier
    # l'auto-approuve *avant* que le callback ne soit consulte. Un garde pose
    # la serait inerte — exactement le genre de panne silencieuse qu'on corrige.
    from vibe_ide.services.providers.git_guard import hook_refus_git

    sortie = await hook_refus_git(
        {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
        None,
        None,
    )

    decision = sortie["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "pipeline" in decision["permissionDecisionReason"].lower()


async def test_le_hook_laisse_passer_le_reste() -> None:
    from vibe_ide.services.providers.git_guard import hook_refus_git

    for commande in ["git status", "npm test", "pytest -q"]:
        sortie = await hook_refus_git(
            {"tool_name": "Bash", "tool_input": {"command": commande}}, None, None
        )
        assert sortie == {}, commande


async def test_le_hook_ignore_les_autres_outils() -> None:
    from vibe_ide.services.providers.git_guard import hook_refus_git

    sortie = await hook_refus_git(
        {"tool_name": "Write", "tool_input": {"file_path": "git_notes.md"}}, None, None
    )

    assert sortie == {}


def test_le_hook_est_installe_sur_chaque_appel_d_agent() -> None:
    # Le garde ne vaut que s'il est branche : un hook ecrit mais jamais pose
    # est pire que pas de hook, parce qu'il donne l'apparence d'une protection.
    from vibe_ide.services.providers.agent_sdk import _build_options

    options = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=["Read", "Bash"],
    )

    matchers = (options.hooks or {}).get("PreToolUse", [])
    assert matchers, "aucun hook PreToolUse installe"
    callbacks = [cb for m in matchers for cb in m.hooks]
    assert any(cb.__name__ == "hook_refus_git" for cb in callbacks), callbacks
