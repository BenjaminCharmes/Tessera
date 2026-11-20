"""What launches the agent CLI under another account (ADR-083).

Un Protocol : l'implémentation Windows est `lanceur_windows`, un conteneur
Linux pourra en fournir une autre sans toucher au reste.
"""
from collections.abc import Mapping, Sequence
from typing import Protocol

from anyio.abc import Process


class LanceurAgent(Protocol):
    """Starts a command under ``compte`` with exactly the given environment."""

    async def lancer(
        self,
        commande: Sequence[str],
        *,
        compte: str,
        mot_de_passe: str,
        env: Mapping[str, str],
        cwd: str | None,
        avec_stderr: bool,
    ) -> Process:
        """Return the running process, stdin and stdout (and stderr) piped.

        Raises ``ProviderIndisponible`` when the account or its logon is refused.
        """
