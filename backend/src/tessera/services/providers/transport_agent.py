"""The SDK transport that starts the CLI under the dedicated account (ADR-083).

Sous-classe de `SubprocessCLITransport` : elle garde `_build_command`, donc
les drapeaux, les hooks et le MCP restent ceux du SDK ; elle remplace
seulement le démarrage du processus. `query(transport=…)` laisse hooks, MCP
et `ask_user` au protocole de contrôle, branché sur ce transport.
"""
import sys

from anyio.abc import Process
from anyio.streams.text import TextReceiveStream, TextSendStream
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk._internal._task_compat import spawn_detached
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from claude_agent_sdk._version import __version__

from tessera.config import settings
from tessera.services.providers.lanceur_agent import LanceurAgent
from tessera.services.providers.noms import ProviderIndisponible
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def fabriquer_lanceur() -> LanceurAgent:
    """Returns the launcher of this platform; refuses where there is none."""
    if sys.platform != "win32":
        raise ProviderIndisponible("AGENT_USER n'a pas de lanceur sur cette plateforme")
    from tessera.services.providers.lanceur_windows import LanceurWindows
    return LanceurWindows()


class TransportCompteAgent(SubprocessCLITransport):
    """Starts the CLI through a ``LanceurAgent`` instead of ``open_process``."""

    def __init__(
        self, prompt: str, options: ClaudeAgentOptions, *,
        lanceur: LanceurAgent, compte: str, mot_de_passe: str,
    ) -> None:
        super().__init__(prompt=prompt, options=options)
        self._lanceur = lanceur
        self._compte = compte
        self._mot_de_passe = mot_de_passe

    async def connect(self) -> None:
        if self._process:
            return
        if self._cli_path is None:
            raise ProviderIndisponible("cli_path absent : pas de CLI partagé pour le compte agent")
        # L'environnement est celui des options, rien d'autre : le SDK, lui,
        # y mêlerait `os.environ` (celui du backend).
        env = {
            "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
            "CLAUDE_CODE_SDK_READS_SESSION_STATE": "1",
            **self._options.env,
            "CLAUDE_AGENT_SDK_VERSION": __version__,
        }
        if self._cwd:
            env["PWD"] = self._cwd
        commande = self._build_command()
        _logger.info("agent_lance_sous_compte", extra={"compte": self._compte})
        process: Process = await self._lanceur.lancer(
            commande, compte=self._compte, mot_de_passe=self._mot_de_passe,
            env=env, cwd=self._cwd, avec_stderr=self._options.stderr is not None,
        )
        self._brancher(process)

    def _brancher(self, process: Process) -> None:
        """Wires the streams as the parent class does after its own spawn."""
        self._process = process
        if process.stdout:
            self._stdout_stream = TextReceiveStream(process.stdout)
        if self._options.stderr is not None and process.stderr:
            self._stderr_stream = TextReceiveStream(process.stderr)
            self._stderr_task = spawn_detached(self._handle_stderr())
        if process.stdin:
            self._stdin_stream = TextSendStream(process.stdin)
        self._ready = True


def transport_du_compte(
    prompt: str, options: ClaudeAgentOptions, lanceur: LanceurAgent | None = None
) -> TransportCompteAgent | None:
    """Returns the transport for ``AGENT_USER``, or ``None`` when it is empty.

    Mot de passe absent : ``ProviderIndisponible``, jamais de repli sous le
    compte du backend (ADR-037).
    """
    compte = settings.agent_user
    if not compte:
        return None
    mot_de_passe = settings.agent_logon_password.get_secret_value()
    if not mot_de_passe:
        raise ProviderIndisponible("AGENT_LOGON_PASSWORD absent : l'agent ne peut pas démarrer")
    return TransportCompteAgent(
        prompt, options, lanceur=lanceur or fabriquer_lanceur(),
        compte=compte, mot_de_passe=mot_de_passe,
    )
