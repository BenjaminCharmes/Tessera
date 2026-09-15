"""Shared loading of agent system prompts — ticket-051.

Every service used to carry its own `_load_system_prompt`, each falling back
to a one-line generic prompt when the file was missing. An agent deprived of
its system prompt does not stop: it produces work that is off-topic but
plausible — the coder ignores the project's conventions, the reviewer reviews
without criteria, the validator validates at a guess. That costs more than a
clean refusal, and the only signal was a WARNING in logs nobody reads.
"""
from pathlib import Path


class MissingPromptError(Exception):
    """An agent's system prompt is missing, empty, or unreadable.

    Carries what is needed to fix it without reading the code: the file that
    was expected, the directory searched, and the setting that overrides it.
    """

    def __init__(self, prompts_dir: Path, filename: str, reason: str) -> None:
        self.prompts_dir = prompts_dir
        self.filename = filename
        self.reason = reason
        super().__init__(
            f"System prompt introuvable ou inexploitable : '{filename}' "
            f"({reason}). Dossier cherché : '{prompts_dir}'. "
            "Vérifie que le fichier existe dans agents/prompts/, ou pointe "
            "IDE_PROMPTS_DIR sur le bon dossier."
        )


def load_system_prompt(prompts_dir: Path, filename: str) -> str:
    """Return the system prompt in `prompts_dir/filename`.

    Raises `MissingPromptError` rather than falling back to a generic prompt:
    running an agent without its instructions is worse than not running it.
    """
    prompt_file = prompts_dir / filename

    if not prompt_file.is_file():
        raise MissingPromptError(prompts_dir, filename, "fichier absent")

    try:
        content = prompt_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissingPromptError(prompts_dir, filename, f"lecture impossible : {exc}") from exc

    # Un fichier vide est aussi inexploitable qu'un fichier absent, et plus
    # trompeur : il existe, donc un simple test d'existence le laissait passer.
    if not content.strip():
        raise MissingPromptError(prompts_dir, filename, "fichier vide")

    return content
