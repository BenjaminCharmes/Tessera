import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from claude_agent_sdk.types import SystemPromptFile


@contextmanager
def prompt_systeme_pour_sdk(
    system: str, cwd: Path | None, seuil_octets: int
) -> Iterator[str | SystemPromptFile]:
    """Yields the system prompt in the form the SDK should receive.

    A prompt of at most ``seuil_octets`` UTF-8 bytes stays a string. A longer
    one is written to a temporary file outside the project, passed as a
    ``file`` prompt, and removed when the call ends, even on error.
    """
    if len(system.encode("utf-8")) <= seuil_octets:
        yield system
        return
    dossier = Path(tempfile.gettempdir()).resolve()
    if cwd is not None and dossier.is_relative_to(cwd.resolve()):
        raise RuntimeError(
            f"temporary directory {dossier} lies inside the project {cwd}"
        )
    descripteur, chemin = tempfile.mkstemp(
        prefix="tessera-system-", suffix=".md", dir=dossier
    )
    try:
        # Fermé avant que le CLI le lise : Windows refuse sinon l'ouverture.
        with os.fdopen(descripteur, "w", encoding="utf-8", newline="") as fichier:
            fichier.write(system)
        yield {"type": "file", "path": chemin}
    finally:
        Path(chemin).unlink(missing_ok=True)
