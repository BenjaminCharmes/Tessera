"""The `signaler` tool — how an agent reports a defect of Tessera (ticket-863, ADR-080).

An agent that hits a defect of Tessera itself (a guard too strict, a broken
tool, contradictory instructions) reports it to the ide-core backlog instead of
writing into that repository (ADR-031). The report goes through the pure checks
of ``signal_agent`` and the duplicate ledger, then waits in the queue of
``signalements_en_attente``: the backend writes the ticket, never the agent.

The project, the role and the ticket come from the run's context, never from the
arguments: an ``args["projet"]`` is ignored. No refusal fails the turn: the
agent reads the reason and carries on.

The queue lives in the ``pipeline`` domain, above this one (ADR-076): the
context receives the function that deposits a report, it does not import it.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool

from tessera.services.providers.ask_user import ASK_USER_SERVER_NAME, ASK_USER_TOOL_NAME, build_ask_user_tool
from tessera.services.providers.signal_agent import CATEGORIES, COMPOSANTS, MAX_PAR_RUN, Refus, SignalValide, valider_signal
from tessera.services.providers.signal_agent_registre import emis_du_jour, enregistrer_signal
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Nom qualifié tel que le SDK le résout. Doit figurer dans `allowed_tools`.
SIGNALER_TOOL_NAME = f"mcp__{ASK_USER_SERVER_NAME}__signaler"

#: Les rôles qui ne reçoivent jamais l'outil : aucun d'eux ne signale un défaut
#: d'outil, et le superviseur trie les signalements — pas de boucle (ADR-080).
ROLES_SANS_SIGNALER: frozenset[str] = frozenset({"lecons", "validateur", "superviseur"})

#: Un signalement d'agent est un défaut : il devient un ticket `fix`.
TYPE_TICKET = "fix"
NATURE = "bug"
LIGNE_CRITERES = "- [ ] À écrire au triage"

RECU = "Signalement reçu : il sera trié au backlog de Tessera. Poursuis ton travail."
ERREUR_INTERNE = (
    "Signalement non enregistré : erreur interne du backend. "
    "Poursuis ton travail, ce n'est pas bloquant."
)

#: (titre, type de ticket, corps) → position dans la file d'attente.
Deposer = Callable[[str, str, str], int]

_DESCRIPTION = (
    "Signale au backlog de Tessera un défaut de Tessera lui-même, rencontré après "
    "avoir tenté de le contourner : une garde trop stricte, un outil cassé, une "
    "consigne contradictoire. Ne l'utilise pas pour demander une fonctionnalité du "
    "projet, ni pour une difficulté propre au ticket. Trois signalements par run au "
    "plus, un texte court (titre 120 caractères, description 1 500). Ne recopie "
    "aucun secret. La réponse dit « reçu » ou la raison du refus ; un refus ne "
    "bloque pas ton travail."
)

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "titre": {"type": "string"},
        "description": {"type": "string"},
        "categorie": {"type": "string", "enum": sorted(CATEGORIES)},
        "composant": {"type": "string", "enum": sorted(COMPOSANTS)},
    },
    "required": ["titre", "description", "categorie", "composant"],
}


@dataclass
class CompteurRun:
    """How many reports the run emitted, shared by every role of the run."""

    emis: int = 0


@dataclass(frozen=True)
class ContexteSignal:
    """What the run knows: read from the run, never from the tool arguments."""

    projet: str
    ticket: str
    role: str
    confidentialite: str
    deposer: Deposer
    compteur: CompteurRun
    #: Combien de signalements ce run peut émettre ; une revue de projet en
    #: reçoit plus qu'un run de ticket (ticket-864).
    max_par_run: int = MAX_PAR_RUN


def role_recoit_signaler(role: str) -> bool:
    """True unless the role is one that never reports (no loop, ADR-080)."""
    return role not in ROLES_SANS_SIGNALER


def _corps(signal: SignalValide) -> str:
    lignes = [
        "## Signalement",
        "",
        f"- Source : {signal.source}",
        f"- Nature : {NATURE}",
        f"- Projet source : {signal.projet}",
        f"- Catégorie : {signal.categorie}",
        f"- Composant : {signal.composant}",
    ]
    if signal.description:
        lignes += ["", "## Description", "", signal.description]
    lignes += ["", "## Critères d'acceptation", "", LIGNE_CRITERES]
    return "\n".join(lignes) + "\n"


def _raison(contexte: ContexteSignal, args: Mapping[str, object]) -> str:
    """Check, deduplicate and queue one report; return what the agent reads."""
    verdict = valider_signal(
        args,
        projet=contexte.projet,
        confidentialite=contexte.confidentialite,
        role=contexte.role,
        ticket=contexte.ticket,
        deja_emis_run=contexte.compteur.emis,
        deja_emis_jour=emis_du_jour(contexte.projet),
        max_par_run=contexte.max_par_run,
    )
    if isinstance(verdict, Refus):
        return verdict.raison
    doublon = enregistrer_signal(verdict, projet=contexte.projet)
    if doublon is not None:
        return doublon.raison
    contexte.deposer(verdict.titre, TYPE_TICKET, _corps(verdict))
    contexte.compteur.emis += 1
    return RECU


async def traiter_signal(contexte: ContexteSignal, args: Mapping[str, object]) -> str:
    """Handle one call; never raises, so a refusal or a fault never fails the turn."""
    try:
        return _raison(contexte, args)
    except Exception as exc:  # noqa: BLE001 — un signalement ne coûte jamais le tour
        _logger.warning("signaler_failed", extra={"role": contexte.role, "error": str(exc)})
        return ERREUR_INTERNE


def build_signaler_tool(contexte: ContexteSignal) -> SdkMcpTool[Any]:
    """Build the tool over the run's context; the arguments never name the project."""

    @tool("signaler", _DESCRIPTION, _SCHEMA)
    async def signaler(args: dict[str, Any]) -> dict[str, Any]:
        texte = await traiter_signal(contexte, args)
        return {"content": [{"type": "text", "text": texte}]}

    return signaler


def serveur_tessera(
    ask_user: Callable[[str], Awaitable[str]] | None,
    signaler: ContexteSignal | None,
    *,
    outille: bool,
) -> tuple[dict[str, Any], list[str]]:
    """The in-process ``tessera`` server and the qualified names to allow.

    ``ask_user`` n'existe que si un canal de dialogue est branché (ticket-066).
    ``signaler`` n'est donné qu'à un rôle outillé (``outille``) : un rôle sans
    outil ne reçoit rien (ADR-080).
    """
    outils: list[SdkMcpTool[Any]] = []
    noms: list[str] = []
    if ask_user is not None:
        outils.append(build_ask_user_tool(ask_user))
        noms.append(ASK_USER_TOOL_NAME)
    if signaler is not None and outille and role_recoit_signaler(signaler.role):
        outils.append(build_signaler_tool(signaler))
        noms.append(SIGNALER_TOOL_NAME)
    if not outils:
        return {}, []
    return {ASK_USER_SERVER_NAME: create_sdk_mcp_server(name=ASK_USER_SERVER_NAME, tools=outils)}, noms
