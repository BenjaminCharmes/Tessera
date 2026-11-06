"""The environment handed to the SDK's subprocess."""
from pathlib import Path

from tessera.coffre import NOMS_SECRETS
from tessera.config import settings

# Le garde git de `Bash` est lexical (ADR-067, ADR-031) : il attrape une
# erreur, pas une évasion. Un agent qui le contourne agirait avec les
# identifiants de l'utilisateur. On les retire donc de son environnement :
# jetons vidés, session `gh` introuvable, aide d'identifiants de git coupée.
# Le push et les PR de la livraison sont faits par le backend, hors de cet
# environnement. Un agent perd ainsi la lecture `gh` d'un dépôt privé.
_JETONS_GITHUB: tuple[str, ...] = ("GITHUB_TOKEN", "GH_TOKEN")

_NOM_CONFIG_GH = "gh-vide"


def _dossier_config_gh_vide() -> str:
    """Returns an existing, empty directory where ``gh`` finds no session."""
    dossier: Path = settings.ide_state_dir / _NOM_CONFIG_GH
    dossier.mkdir(parents=True, exist_ok=True)
    return str(dossier)


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
    Même traitement pour les autres secrets du coffre (ADR-053, ADR-073) : un
    jeton exporté dans le shell qui a lancé le backend serait hérité par le CLI.
    GitHub est traité de même (ticket-873) : jetons vidés, `GH_CONFIG_DIR` vers
    un dossier vide, aide d'identifiants de git neutralisée.
    """
    env: dict[str, str] = {nom: "" for nom in (*NOMS_SECRETS, *_JETONS_GITHUB)}
    env["GH_CONFIG_DIR"] = _dossier_config_gh_vide()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "credential.helper"
    env["GIT_CONFIG_VALUE_0"] = ""
    env["GIT_TERMINAL_PROMPT"] = "0"
    # Sous Windows, le SDK n'active `Bash` que si cette variable pointe vers
    # un bash.exe. Sans elle, l'outil disparaît en silence (ticket-319).
    if git_bash_path:
        env["CLAUDE_CODE_GIT_BASH_PATH"] = git_bash_path
    return env
