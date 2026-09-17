"""Le git qui modifie l'historique est refusé aux agents — ticket-068.

Premier usage réel, 2026-09-17 : pendant deux runs, les agents ont commité avec
leurs propres messages, mergé la branche de ticket dans `main` et poussé sur
GitHub. L'utilisateur n'avait cliqué que sur « lancer ».

ADR-018 et ADR-022 posent les règles — un commit par run, jamais de merge,
jamais de push forcé — mais elles ne contraignent que `GitWorkspaceService`.
Or le codeur a `Bash` : il peut lancer `git` directement, et court-circuiter
tout l'édifice. Une règle qu'on peut contourner en tapant une autre commande
n'est pas une règle.

Le refus est donc posé **au niveau du SDK**, via `can_use_tool`, et pas dans le
prompt : une consigne décrit une intention, un refus produit un fait.

Le git en lecture reste permis. Lire le dépôt fait partie du travail — c'est ce
qui permet de comprendre ce qui existe avant d'écrire.
"""
from typing import Any

from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

#: Sous-commandes qui écrivent dans l'historique, l'index ou les références.
_SOUS_COMMANDES_INTERDITES = frozenset({
    "commit", "merge", "push", "checkout", "switch", "branch", "reset",
    "rebase", "cherry-pick", "revert", "tag", "stash", "add", "rm", "mv",
    "clean", "restore", "am", "apply", "filter-branch", "update-ref",
    "remote", "fetch", "pull", "submodule", "worktree", "config",
})

#: Ce que l'agent lit quand on lui refuse la commande. Il doit comprendre que
#: le commit est fait *pour* lui, sinon il réessaie ou abandonne le ticket.
GIT_REFUS = (
    "Commande refusée : les agents ne modifient pas l'historique git. "
    "Le pipeline crée la branche et commite ton travail lui-même, à la fin du "
    "run, avec un message dérivé du ticket. Contente-toi d'écrire les "
    "fichiers. Le git en lecture (status, diff, log, show) reste disponible."
)

#: Options globales de git qui précèdent la sous-commande.
_OPTIONS_GLOBALES_AVEC_VALEUR = frozenset({"-C", "-c", "--git-dir", "--work-tree"})

#: Ce qui sépare deux commandes dans une ligne de shell.
_SEPARATEURS = (";", "&&", "||", "|", "&")


def _segments(commande: str) -> list[str]:
    """Découpe la ligne en commandes élémentaires.

    `cd frontend && git push` est la forme la plus naturelle pour contourner un
    contrôle qui ne regarderait que le début de la ligne.
    """
    morceaux = [commande]
    for separateur in _SEPARATEURS:
        suivants: list[str] = []
        for morceau in morceaux:
            suivants.extend(morceau.split(separateur))
        morceaux = suivants
    return morceaux


def _sous_commande(segment: str) -> str | None:
    """La sous-commande git d'un segment, ou None si ce n'est pas un git."""
    jetons = segment.split()
    if not jetons or jetons[0] != "git":
        return None

    i = 1
    while i < len(jetons):
        jeton = jetons[i]
        if jeton.startswith("--") and "=" in jeton:
            i += 1  # --git-dir=.git : la valeur est collée
            continue
        if jeton in _OPTIONS_GLOBALES_AVEC_VALEUR:
            i += 2  # -C /chemin : la valeur est le jeton suivant
            continue
        if jeton.startswith("-"):
            i += 1
            continue
        return jeton.lower()
    return None


def commande_git_interdite(commande: str) -> bool:
    """True si `commande` contient un git qui modifie l'historique.

    Tokenise plutôt que de chercher un motif : une expression régulière sur une
    ligne de shell rate toujours une forme, et ici rater une forme veut dire
    laisser un agent pousser sur le dépôt d'un client.
    """
    for segment in _segments(commande):
        sous_commande = _sous_commande(segment.strip())
        if sous_commande is not None and sous_commande in _SOUS_COMMANDES_INTERDITES:
            return True
    return False


async def hook_refus_git(
    entree: HookInput,
    tool_use_id: str | None,
    contexte: HookContext,
) -> HookJSONOutput:
    """Hook `PreToolUse` : refuse tout `Bash` qui modifie l'historique git.

    **Un hook, et pas `can_use_tool`.** Le SDK avertit lui-même qu'une entrée
    d'`allowed_tools` couvrant un outil entier — ce qui est le cas de `Bash`
    ici — l'auto-approuve *avant* que le callback de permission ne soit
    consulté. Un garde posé là ne serait jamais appelé : il donnerait
    l'apparence d'une protection sans en être une.

    Renvoyer `{}` laisse passer : le hook ne décide que ce qu'il refuse.
    """
    donnees: dict[str, Any] = dict(entree)
    if donnees.get("tool_name") != "Bash":
        return {}

    commande = str(donnees.get("tool_input", {}).get("command", ""))
    if not commande_git_interdite(commande):
        return {}

    _logger.warning("git_agent_refuse", extra={"command": commande[:200]})
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": GIT_REFUS,
        }
    }
