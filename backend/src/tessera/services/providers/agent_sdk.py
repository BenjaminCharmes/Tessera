import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import aclosing
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ConversationResetMessage,
    HookMatcher,
    RateLimitEvent,
    ResultMessage,
    SdkPluginConfig,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
    query,
)
from claude_agent_sdk.types import SystemPromptFile

# Union de tous les types émis par query() — utilisé pour typer le générateur.
_SdkMessage = (
    UserMessage
    | AssistantMessage
    | SystemMessage
    | ResultMessage
    | StreamEvent
    | RateLimitEvent
    | ConversationResetMessage
)


async def _sdk_gen(
    prompt: str, options: ClaudeAgentOptions
) -> AsyncGenerator[_SdkMessage, None]:
    """Wraps query() as a typed AsyncGenerator so it exposes aclose()."""
    async for msg in query(prompt=prompt, options=options):
        yield msg

from tessera.models.agent import EffortLevel
from tessera.services.providers.consignes_ancetres import claude_md_ancetres_a_exclure
from tessera.services.providers.env_sdk import env_du_sous_processus
from tessera.services.providers.garde_jetons import hook_refus_env_tessera
from tessera.services.providers.git_guard import hook_refus_git
from tessera.services.providers.perimetre import (
    hook_refus_hors_perimetre,
    racine_autorisee,
)
from tessera.services.racine_depot import depot_au_dessus
from tessera.services.providers.refus_cli import ReleveDesRefusCli
from tessera.services.providers.refus_garde import JournalDesRefus
from tessera.services.providers.ask_user import (
    ASK_USER_SERVER_NAME,
    ASK_USER_TOOL_NAME,
    build_ask_user_server,
)
from tessera.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)
from tessera.services.providers.duree_max import borner
from tessera.services.providers.messages_sdk import (
    OUTIL_SORTIE_STRUCTUREE,
    _extract_stream_delta,
    _format_de_sortie,
    _structured_from,
    _usage_from,
)
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.prompt_fichier import prompt_systeme_pour_sdk
from tessera.services.quota_tracker import QuotaTracker
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_ALLOWED_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

# Chemin absolu vers le plugin Tessera, ancré sur la racine du dépôt.
# Ne jamais le résoudre depuis le cwd d'un projet : il vit dans le dépôt
# de l'IDE, pas dans celui du projet qui déclare le skill.
# backend/src/tessera/services/providers/ → parents[5] = racine du dépôt
_REPO_ROOT: Path = Path(__file__).resolve().parents[5]
_TESSERA_PLUGIN_PATH: Path = _REPO_ROOT / "agents" / "plugin"

# Octets UTF-8 au-delà desquels le prompt système part par fichier : la ligne
# de commande Windows tient dans ~32 Ko et porte aussi réglages et outils.
SYSTEM_PROMPT_FILE_THRESHOLD_BYTES = 24_000


def _depart_des_consignes(cwd: Path, racine_ecriture: Path) -> Path:
    """The folder from which ancestor CLAUDE files are excluded.

    Le dépôt de l'IDE pour un projet qui y vit. Un worktree de run est hors de
    ce dépôt (ADR-056) : le départ est alors la racine de son propre checkout,
    le premier ancêtre qui porte un ``.git`` (un fichier, pour un worktree lié),
    et à défaut la racine d'écriture reçue, qui n'exclut rien.
    """
    projet = cwd.resolve()
    if projet.is_relative_to(_REPO_ROOT.resolve()):
        return _REPO_ROOT
    depot = depot_au_dessus(projet)
    return depot if depot is not None else racine_ecriture


def _reglages_sans_consignes_ancetres(
    cwd: Path | None, racine_ecriture: Path | None
) -> str | None:
    """The ``settings`` JSON excluding Tessera's CLAUDE files, or ``None``.

    Un projet est « ancestor » quand sa racine d'écriture n'est pas son propre
    dossier : on réutilise donc celle que le run a figée (ticket-119).
    """
    if cwd is None:
        return None
    racine = racine_ecriture if racine_ecriture is not None else racine_autorisee(cwd)
    ancestor = racine.resolve() != cwd.resolve()
    exclus = claude_md_ancetres_a_exclure(
        cwd, _depart_des_consignes(cwd, racine), ancestor
    )
    if not exclus:
        return None
    return json.dumps({"claudeMdExcludes": exclus})


def _build_options(
    *,
    system: str | SystemPromptFile,
    model: str,
    max_turns: int,
    max_budget_usd: float | None,
    cwd: Path | None,
    allowed_tools: list[str] | None = None,
    ask_user: Callable[[str], Awaitable[str]] | None = None,
    racine_ecriture: Path | None = None,
    resume: str | None = None,
    skills: list[str] | None = None,
    git_bash_path: str | None = None,
    journal_refus: JournalDesRefus | None = None,
    effort: EffortLevel | None = None,
    schema: dict[str, Any] | None = None,
) -> ClaudeAgentOptions:
    """Builds SDK options with the guardrails established by the ticket-044 spike.

    ``schema`` asks the SDK for an output validated against it (ADR-061).

    ``effort`` is the role's reasoning effort (ticket-573); left ``None``, the
    SDK keeps its own default.

    ``racine_ecriture`` is the write root the run froze before its first agent
    (ticket-119); left ``None``, the perimeter hook reads it from the project's
    ``agents.json`` as before.

    ``resume`` names a session of a previous call to pick up from (ticket-187).
    The CLI finds it on disk by ``cwd``, so both must match between the calls.
    """
    # ``allowed_tools`` only controls auto-approval — the SDK CLI's
    # subprocess transport reads ``if effective_allowed_tools:`` and omits
    # ``--allowedTools`` entirely when the list is empty, leaving the CLI's
    # full default toolset available. Only ``tools`` controls which built-in
    # tools exist at all (``[]`` disables all of them). Both fields are
    # always set to the same resolved list here, so a "no tools" request
    # (`allowed_tools=[]`) actually disables tool availability instead of
    # merely withholding auto-approval, and no configuration path can end up
    # with an implicit toolset (ticket-044 merge-gate review, finding 1).
    effective_tools = allowed_tools if allowed_tools is not None else _ALLOWED_TOOLS

    # `tools` étant explicite, l'option `skills` du SDK ne suffit pas à rendre
    # l'outil disponible : il faut l'y ajouter. La liste, elle, borne ce que le
    # CLI découvrirait seul — les skills de la racine du dépôt, ceux qu'il
    # intègre — et un skill non listé est refusé par l'outil (ticket-242).
    if skills:
        effective_tools = [*effective_tools, "Skill"]

    # Plugin local Tessera : chargé uniquement si au moins un skill déclaré
    # porte le préfixe `tessera:`. Le chemin est absolu, ancré sur la racine
    # du dépôt, jamais sur le cwd du projet (ticket-293).
    plugins: list[SdkPluginConfig] = []
    if skills and any(s.startswith("tessera:") for s in skills):
        plugins = [{"type": "local", "path": str(_TESSERA_PLUGIN_PATH)}]

    # L'outil `ask_user` n'existe que si un canal de dialogue est branché sur
    # ce run (ticket-066). Le donner sans canal reviendrait à promettre à
    # l'agent une réponse que personne ne pourrait lui apporter.
    mcp_servers: dict[str, Any] = {}
    if ask_user is not None:
        mcp_servers[ASK_USER_SERVER_NAME] = build_ask_user_server(ask_user)
        effective_tools = [*effective_tools, ASK_USER_TOOL_NAME]

    env = env_du_sous_processus(git_bash_path)

    return ClaudeAgentOptions(
        env=env,
        # Chemin long obligatoire : un chemin court Windows 8.3 fait refuser
        # les écritures.
        cwd=str(cwd.resolve()) if cwd is not None else None,
        system_prompt=system,
        model=model,
        # permission_mode seul ne suffit pas — allowed_tools doit être explicite.
        permission_mode="acceptEdits",
        tools=effective_tools,
        allowed_tools=effective_tools,
        setting_sources=["project"],
        # Un projet hébergé ne lit pas les CLAUDE.md de Tessera (ticket-414).
        settings=_reglages_sans_consignes_ancetres(cwd, racine_ecriture),
        include_partial_messages=True,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        mcp_servers=mcp_servers,
        resume=resume,
        skills=list(skills) if skills else None,
        effort=effort,
        output_format=_format_de_sortie(schema),
        plugins=plugins,
        # Les agents n'écrivent pas dans l'historique git : le pipeline crée la
        # branche et commite lui-même (ADR-018), et ne merge jamais (ADR-022).
        # Le refus est posé ici, en `PreToolUse`, parce qu'une entrée de
        # `allowed_tools` couvrant `Bash` l'auto-approuverait avant tout
        # callback de permission — le garde serait inerte (ticket-068).
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[hook_refus_git]),
                # Le `.env` de Tessera porte les jetons de mise en ligne, et
                # ADR-031 laisse lire hors du projet (ADR-053, ticket-464).
                HookMatcher(
                    matcher="Read|Glob|Grep|Bash",
                    hooks=[hook_refus_env_tessera(cwd)],
                ),
                # `cwd` place l'agent dans le projet, il ne l'y enferme pas :
                # rien n'empêchait un `Write` vers le dépôt du client d'à côté
                # (ticket-085).
                HookMatcher(
                    matcher="Write|Edit|NotebookEdit|Bash",
                    hooks=[hook_refus_hors_perimetre(
                            cwd, racine=racine_ecriture, journal=journal_refus
                        )],
                ),
            ]
        },
    )


class ClaudeAgentSDKProvider:
    """Claude Agent SDK backend: real file tools, billed against the subscription."""

    name = "agent_sdk"
    ALLOWED_TOOLS = _ALLOWED_TOOLS

    def __init__(
        self,
        max_turns: int = 30,
        max_budget_usd: float | None = None,
        allowed_tools: list[str] | None = None,
        racine_ecriture: Path | None = None,
        skills: list[str] | None = None,
        git_bash_path: str | None = None,
        silence_max_s: float | None = None,
        journal_refus: JournalDesRefus | None = None,
        duree_max_s: float | None = None,
        effort: EffortLevel | None = None,
    ) -> None:
        # L'effort de raisonnement du rôle (ticket-573) ; None : défaut du SDK.
        self._effort = effort
        # Durée totale d'un appel (ticket-518) ; None : pas de borne, comme
        # pour le codeur, dont un tour légitime dure longtemps.
        self._duree_max_s = duree_max_s
        # Là où les refus du garde-fou s'accumulent pour le reviewer et le
        # validateur (ticket-476). None : personne ne les lira.
        self._journal_refus = journal_refus
        self._max_turns = max_turns
        self._skills = list(skills) if skills else []
        self._max_budget_usd = max_budget_usd
        # La racine d'écriture figée pour tout le run (ticket-119). Les options
        # sont reconstruites à chaque appel d'agent : sans elle, chaque agent
        # du pipeline relirait `agents.json` — donc ce que le codeur y a écrit.
        self.racine_ecriture = racine_ecriture
        # Le provider est le seul endroit qui voit les messages du SDK : c'est
        # donc ici que le quota se capte, et sa forme s'arrête ici (ticket-054).
        self.quota = QuotaTracker()
        self._allowed_tools = list(allowed_tools) if allowed_tools is not None else list(_ALLOWED_TOOLS)
        # Chemin vers bash.exe sous Windows, transmis au sous-processus du SDK
        # pour activer l'outil `Bash` (ticket-319).
        self._git_bash_path = git_bash_path
        # Délai maximum entre deux messages consécutifs (ticket-381).
        # None à la construction → lu depuis les réglages.
        if silence_max_s is not None:
            self._silence_max_s = silence_max_s
        else:
            from tessera.config import settings
            self._silence_max_s = settings.agent_silence_max_s

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        session: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        # NB : max_tokens est reçu pour satisfaire le protocole LLMProvider mais
        # ClaudeAgentOptions n'expose aucun champ équivalent — il est ignoré ici.
        # Voir LLMProvider.complete pour la portée exacte de cette limitation.
        return await self._run_ou_reprendre(
            system=system, user=user, model=model, cwd=cwd, ask_user=ask_user,
            session=session, schema=schema,
        )

    async def stream(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        on_token: StreamCallback | None = None,
        on_tool_use: ToolEventCallback | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        session: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        # NB : max_tokens est ignoré — voir la note dans complete() ci-dessus.
        return await self._run_ou_reprendre(
            system=system, user=user, model=model, cwd=cwd,
            on_token=on_token, on_tool_use=on_tool_use, ask_user=ask_user,
            session=session, schema=schema,
        )

    async def _run_ou_reprendre(
        self, *, session: str | None, **kwargs: Any
    ) -> ProviderResult:
        """Resumes ``session`` when given, and falls back to a fresh call if
        that resume fails (ticket-187).

        Le CLI retrouve une session sur le disque, par `cwd` : une session
        introuvable ne doit coûter que l'économie espérée, jamais le run. Un
        appel neuf qui échoue, lui, remonte tel quel — le rejouer aurait le
        même résultat et coûterait deux fois.
        """
        if session is None:
            return await self._run(**kwargs)
        try:
            return await self._run(resume=session, **kwargs)
        except Exception as exc:  # noqa: BLE001 — le repli est le comportement d'avant
            _logger.warning(
                "session_resume_failed", extra={"session": session, "error": str(exc)}
            )
            return await self._run(**kwargs)

    async def _run(self, **kwargs: Any) -> ProviderResult:
        """One SDK call, within the total duration the provider was given.

        La borne enveloppe aussi la fermeture du générateur : `wait_for`
        attend l'annulation de `__anext__`, et sur un CLI figé rien d'autre
        ne la limitait (ticket-518).
        """
        system = kwargs.pop("system")
        seuil = SYSTEM_PROMPT_FILE_THRESHOLD_BYTES
        # Un fichier par tentative : il vit le temps de l'appel, erreur comprise.
        with prompt_systeme_pour_sdk(system, kwargs["cwd"], seuil) as prompt:
            async with borner(self._duree_max_s):
                return await self._executer(system=prompt, **kwargs)

    async def _executer(
        self,
        *,
        system: str | SystemPromptFile,
        user: str,
        model: str,
        cwd: Path | None,
        on_token: StreamCallback | None = None,
        on_tool_use: ToolEventCallback | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        resume: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        options = _build_options(
            system=system, model=model, max_turns=self._max_turns,
            max_budget_usd=self._max_budget_usd, cwd=cwd,
            allowed_tools=self._allowed_tools, ask_user=ask_user,
            racine_ecriture=self.racine_ecriture, resume=resume,
            skills=self._skills, git_bash_path=self._git_bash_path,
            journal_refus=self._journal_refus, effort=self._effort,
            schema=schema,
        )
        chunks: list[str] = []
        result: ResultMessage | None = None
        refus_cli = ReleveDesRefusCli()
        # None → pas de borne (0 ou négatif désactive également).
        silence_timeout: float | None = self._silence_max_s if self._silence_max_s > 0 else None

        async with aclosing(_sdk_gen(prompt=user, options=options)) as gen:
            while True:
                try:
                    # `asyncio.timeout` plutôt que `wait_for` : sous Python 3.11,
                    # `wait_for` rend le résultat et avale l'annulation quand
                    # son tâche interne vient de finir. Avec un flux qui émet
                    # sans cesse, la durée maximale était alors perdue et
                    # l'appel ne finissait jamais (ticket-518).
                    async with asyncio.timeout(silence_timeout):
                        message = await gen.__anext__()
                except TimeoutError:
                    _logger.warning(
                        "agent_silencieux_arrete",
                        extra={"model": model, "silence_s": self._silence_max_s},
                    )
                    raise ProviderIndisponible(
                        f"agent silencieux depuis {self._silence_max_s:.0f} s"
                    )
                except StopAsyncIteration:
                    break

                refus_cli.observer(message)
                if isinstance(message, RateLimitEvent):
                    # L'état du quota d'abonnement : la seule mesure de la
                    # ressource réellement finie en mode abonnement. Un provider
                    # qui n'en émet pas laisse le tracker vide, et rien ne casse.
                    self.quota.observe(getattr(message, "rate_limit_info", None))
                elif isinstance(message, ResultMessage):
                    result = message
                elif isinstance(message, StreamEvent):
                    # Forwarded live for display only — the authoritative record
                    # of content is the buffered TextBlock below, so this must
                    # never also be appended to `chunks` (would double the text).
                    if on_token is not None:
                        delta = _extract_stream_delta(message.event)
                        if delta:
                            await on_token(delta)
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        # isinstance plutôt que comparaison de type().__name__ :
                        # robuste et vérifiable statiquement (finding 2, revue ticket-044).
                        if isinstance(block, TextBlock):
                            chunks.append(block.text)
                        # La sortie structurée n'est pas une action de l'agent.
                        elif (isinstance(block, ToolUseBlock) and on_tool_use is not None
                              and block.name != OUTIL_SORTIE_STRUCTUREE):
                            await on_tool_use(block.name, dict(block.input))

        if result is None:
            raise RuntimeError("Agent SDK: aucun ResultMessage reçu")

        inp, out, cache_read, cache_creation = _usage_from(result)
        return ProviderResult(
            content="".join(chunks),
            input_tokens=inp,
            output_tokens=out,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            cost_usd=result.total_cost_usd,
            provider_name=self.name,
            session_id=getattr(result, "session_id", None) or None,
            outils_refuses=refus_cli.outils_refuses,
            structured=_structured_from(result),
        )
