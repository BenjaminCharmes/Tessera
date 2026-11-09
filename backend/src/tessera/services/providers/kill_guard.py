"""Un agent ne tue pas les processus de la machine — ticket-899.

Le 2026-11-09, un codeur a lancé `pkill -f "python"` : tous les processus Python
de la machine, backend Tessera compris. Ce garde attrape une erreur, pas une
évasion (ADR-031) : `python -c "import os; ..."` passe. La frontière, c'est
l'isolation par compte dédié.

Il réutilise le découpage de `git_guard_lexique` (segments, enveloppes, shells).
Reste permis : `kill %1` (job du shell), `kill $!` (dernier processus lancé par
la même ligne), `kill $VARIABLE`.
"""
import re
from typing import Any

from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from tessera.services.providers import git_guard_lexique as lexique
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

KILL_REFUS = (
    "Commande refusée : un agent ne tue pas les processus par leur nom ni par "
    "un PID qu'il n'a pas lancé. Les processus lancés par les tests sont arrêtés "
    "par le pipeline. Lance ton serveur en arrière-plan (`commande &`) et arrête-le "
    "avec `kill $!` (ou `kill %1`)."
)

#: Des commandes qui tuent par leur nom, quelle que soit leur cible.
_PAR_NOM = frozenset({"pkill", "killall", "taskkill", "tskill", "stop-process", "spps"})

#: Découpage grossier : `$(…)` et les accents graves restent dans le segment,
#: pour que `kill $(pgrep x)` se lise en entier.
_SEPARATEURS_GROSSIERS = re.compile(r"\|\||&&|[;|&\n\r]")

_VARIABLE = re.compile(r"^\$(\{[A-Za-z_]\w*\}|[A-Za-z_]\w*)$")
_JOB_OU_DERNIER = re.compile(r"^(%.*|\$!|\$\{!\})$")
_SIGNAL_NUMERIQUE = re.compile(r"^-\d+$")
_RESTE_DE_KILL = re.compile(r"^kill\s+-\d+$")
_OPTIONS_A_VALEUR =frozenset({"-s", "-n", "--signal"})


def _cibles_de_kill(args: list[str]) -> list[str]:
    """Les arguments de `kill` qui désignent des processus, signal écarté."""
    cibles: list[str] = []
    saute = False
    for index, arg in enumerate(args):
        if saute:
            saute = False
        elif arg in _OPTIONS_A_VALEUR:
            saute = True
        elif index == 0 and len(args) > 1 and _SIGNAL_NUMERIQUE.match(arg):
            continue
        elif arg.startswith("-") and arg[1:2].isalpha():
            continue
        else:
            cibles.append(arg)
    return cibles


def _cible_admise(cible: str) -> bool:
    if "`" in cible or cible.startswith("$("):
        return False
    return bool(_JOB_OU_DERNIER.match(cible) or _VARIABLE.match(cible))


def _wmic_tue(jetons_: list[str]) -> bool:
    mots = [j.lower() for j in jetons_[1:]]
    return "process" in mots and ("delete" in mots or "terminate" in mots)


def _enveloppe_interdite(nom: str, jetons_: list[str]) -> bool:
    """Déballe `env`, `sudo`, `xargs`… ; `xargs kill` reçoit ses PID sur l'entrée."""
    reste = lexique.sans_enveloppe(jetons_)
    if nom == "xargs" and reste:
        cible = lexique.nom_de_commande(reste[0])
        if cible == "kill" and not _cibles_de_kill(reste[1:]):
            return True
    return _segment_interdit(reste)


def _shell_interdit(nom: str, jetons_: list[str]) -> bool:
    if nom == "eval":
        return commande_kill_interdite(" ".join(jetons_[1:]))
    if lexique.commande_opaque(jetons_):
        return True
    ligne = lexique.ligne_derriere_c(jetons_)
    return ligne is not None and commande_kill_interdite(ligne)


def _segment_interdit(jetons_: list[str]) -> bool:
    """True si ce segment, une fois déballé, tue des processus hors de portée."""
    jetons_ = lexique.sans_prefixe(jetons_)
    if not jetons_:
        return False
    nom = lexique.nom_de_commande(jetons_[0])
    if nom in lexique.SHELLS or nom == "eval":
        return _shell_interdit(nom, jetons_)
    if nom in lexique.ENVELOPPES:
        return _enveloppe_interdite(nom, jetons_)
    if nom in _PAR_NOM:
        return True
    if nom == "wmic":
        return _wmic_tue(jetons_)
    if nom == "kill":
        return not all(_cible_admise(c) for c in _cibles_de_kill(jetons_[1:]))
    return False


def commande_kill_interdite(commande: str) -> bool:
    """True si `commande` tue des processus par leur nom ou par un PID étranger.

    Deux lectures : le découpage fin de `git_guard_lexique` trouve une commande
    nichée dans `$(…)`, le découpage grossier lit les arguments de `kill` en
    entier.
    """
    # Le découpage fin coupe `kill -9 $!` avant son `$` : un `kill -N` sans
    # cible n'y est qu'un reste, le découpage grossier juge la ligne entière.
    fins = [s for s in lexique.segments(commande) if not _RESTE_DE_KILL.match(s)]
    grossiers = [s.strip() for s in _SEPARATEURS_GROSSIERS.split(commande) if s.strip()]
    return any(_segment_interdit(lexique.jetons(s)) for s in [*fins, *grossiers])


async def hook_refus_kill(
    entree: HookInput,
    tool_use_id: str | None,
    contexte: HookContext,
) -> HookJSONOutput:
    """Hook `PreToolUse` : refuse tout `Bash` qui tue des processus étrangers."""
    donnees: dict[str, Any] = dict(entree)
    if donnees.get("tool_name") != "Bash":
        return {}

    commande = str(donnees.get("tool_input", {}).get("command", ""))
    if not commande_kill_interdite(commande):
        return {}

    _logger.warning("kill_agent_refuse", extra={"command": commande[:200]})
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": KILL_REFUS,
        }
    }
