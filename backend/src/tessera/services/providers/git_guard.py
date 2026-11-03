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
qui permet de comprendre ce qui existe avant d'écrire. Depuis ticket-705
(ADR-067), « en lecture » veut dire « nommé dans une liste blanche » : voir
`git_guard_lectures.py`.
"""
from typing import Any

from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from tessera.services.providers import git_guard_lexique as lexique
from tessera.services.providers.git_guard_lectures import gh_interdit, git_interdit
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Ce que l'agent lit quand on lui refuse la commande. Il doit comprendre que
#: le commit est fait *pour* lui, sinon il réessaie ou abandonne le ticket.
GIT_REFUS = (
    "Commande refusée : les agents ne modifient pas l'historique git. "
    "Le pipeline crée la branche et commite ton travail lui-même, à la fin du "
    "run, avec un message dérivé du ticket. Contente-toi d'écrire les "
    "fichiers. Le git en lecture (status, diff, log, show) reste disponible."
)

def _segment_interdit(jetons_: list[str]) -> bool:
    """True si ce segment, une fois déballé, est un git ou un gh qui écrit."""
    while True:
        jetons_ = lexique.sans_prefixe(jetons_)
        if not jetons_:
            return False
        nom = lexique.nom_de_commande(jetons_[0])
        if nom in lexique.SHELLS:
            ligne = lexique.ligne_derriere_c(jetons_)
            return ligne is not None and commande_git_interdite(ligne)
        if nom == "eval":
            return commande_git_interdite(" ".join(jetons_[1:]))
        if nom in lexique.ENVELOPPES:
            jetons_ = lexique.sans_enveloppe(jetons_)
            continue
        if nom == "git":
            return git_interdit(jetons_[1:])
        if nom == "gh":
            return gh_interdit(jetons_[1:])
        return False


def commande_git_interdite(commande: str) -> bool:
    """True si `commande` contient un git — ou un gh — qui écrit.

    Tokenise plutôt que de chercher un motif : une expression régulière sur une
    ligne de shell rate toujours une forme, et ici rater une forme veut dire
    laisser un agent pousser sur le dépôt d'un client. Chaque segment est
    déballé de ses enveloppes (`env`, `sudo`, `sh -c`…) avant d'être lu ; les
    formes qui passaient avant ticket-119 sont dans `test_git_guard.py`.
    """
    return any(_segment_interdit(lexique.jetons(s)) for s in lexique.segments(commande))


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
