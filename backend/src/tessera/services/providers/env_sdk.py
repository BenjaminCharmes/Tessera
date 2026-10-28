"""The environment handed to the SDK's subprocess."""
from tessera.config import VARIABLES_JETONS


def env_du_sous_processus(git_bash_path: str | None) -> dict[str, str]:
    """Builds the ``env`` of the CLI subprocess.

    Une ANTHROPIC_API_KEY présente dans l'environnement est PRIORITAIRE sur
    la session Claude Code dans le CLI. En mode abonnement — le défaut — elle
    ne sert donc à rien et casse tout : le CLI tente de s'authentifier avec
    elle et remonte `401 API key is invalid`. Le placeholder `sk-ant-...`
    livré dans `.env.example` suffit à faire échouer *tous* les appels
    agent, avec un message d'erreur qui ne pointe jamais vers `.env`.
    On la neutralise explicitement pour le sous-process du SDK ; la clef
    reste disponible pour `AnthropicApiProvider`, qui est le seul à devoir
    l'utiliser.
    Même traitement pour les jetons de mise en ligne (ADR-053) : un jeton
    exporté dans le shell qui a lancé le backend serait hérité par le CLI.
    """
    env: dict[str, str] = {"ANTHROPIC_API_KEY": ""}
    env.update({variable: "" for variable in VARIABLES_JETONS})
    # Sous Windows, le SDK n'active `Bash` que si cette variable pointe vers
    # un bash.exe. Sans elle, l'outil disparaît en silence (ticket-319).
    if git_bash_path:
        env["CLAUDE_CODE_GIT_BASH_PATH"] = git_bash_path
    return env
