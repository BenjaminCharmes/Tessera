import os
import sys
from pathlib import Path
from typing import ClassVar

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from tessera.config_errors import ConfigurationError, describe_validation_error

# Racine du dépôt : backend/src/tessera/config.py -> remonter de 4 niveaux.
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Ancré sur la racine du dépôt, pas sur le répertoire de lancement :
# `env_file=".env"` est relatif au cwd, et `make dev` démarre depuis
# `backend/`. Un réglage pourtant présent dans `.env` était donc
# silencieusement ignoré — même classe de bug que ticket-050.
_ENV_FILE = str(_REPO_ROOT / ".env")

# Fichier réellement lu par `Settings`. `IDE_ENV_FILE` le remplace : la suite de
# tests le pointe vers un fichier absent, pour qu'une variable égarée dans le
# `.env` du développeur ne fasse pas échouer toute la collecte. `_ENV_FILE`
# reste le vrai `.env`, celui que le hook de lecture protège (ADR-053).
_SETTINGS_ENV_FILE = os.environ.get("IDE_ENV_FILE") or _ENV_FILE

# Les jetons de mise en ligne (ADR-053) : noms des champs de `Settings`. La
# variable d'environnement est le même nom en majuscules. `VERCEL_TEAM_ID`
# n'en fait pas partie : un identifiant d'équipe n'est pas un secret.
CHAMPS_JETONS: tuple[str, ...] = (
    "vercel_token",
    "neon_api_key",
    "resend_api_key",
    "stripe_api_key",
    "cloudflare_api_token",
)
VARIABLES_JETONS: tuple[str, ...] = tuple(champ.upper() for champ in CHAMPS_JETONS)


def default_state_dir() -> Path:
    """Return the per-user data folder, always outside the repository."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "Tessera"
    return Path.home() / ".local" / "state" / "tessera"


class Settings(BaseSettings):
    # `hide_input_in_errors` : pydantic recopie sinon la valeur fautive dans le
    # message (`input_value='sk_test_…'`), donc un jeton dans les logs.
    model_config = SettingsConfigDict(
        env_file=_SETTINGS_ENV_FILE, env_file_encoding="utf-8", hide_input_in_errors=True
    )

    # Le `.env` de Tessera, que le hook de lecture refuse aux agents (ADR-053).
    env_file: ClassVar[Path] = Path(_ENV_FILE)

    # Jetons de mise en ligne (ADR-053). `SecretStr` : ni `repr` ni `model_dump`
    # ne montrent la valeur. Vides : la mise en ligne reste inactive. Portée
    # minimale et expiration : voir `.env.example`.
    vercel_token: SecretStr = SecretStr("")
    neon_api_key: SecretStr = SecretStr("")
    resend_api_key: SecretStr = SecretStr("")
    stripe_api_key: SecretStr = SecretStr("")
    cloudflare_api_token: SecretStr = SecretStr("")
    # Identifiant d'équipe Vercel : pas un secret.
    vercel_team_id: str = ""

    # Optionnel : vide lorsque le provider est `agent_sdk` (auth par abonnement).
    anthropic_api_key: str = ""
    # Termes qui ne doivent jamais quitter la machine, séparés par des virgules
    # (ADR-048). Vit dans `.env`, jamais versionné. Vide : aucun contrôle.
    forbidden_terms: str = ""
    # Provider LLM par défaut : "agent_sdk" (abonnement) ou "anthropic_api" (crédits).
    # Un rôle peut en déclarer un autre dans son `agents.json` (ADR-046).
    llm_provider: str = "agent_sdk"
    # Le serveur Ollama des rôles déclarés `provider: ollama` (ticket-189).
    # Injoignable, le repli déclaré par le rôle prend le relais.
    ollama_base_url: str = "http://127.0.0.1:11434"
    # Garde-fous ClaudeAgentSDKProvider — bornent une boucle d'agent qui dérape.
    # max_turns borne le nombre d'allers-retours outil ; max_budget_usd borne
    # la dépense réelle d'un seul appel agent (le garde-fou qui protège le
    # quota de l'abonnement). Voir memory/decisions.md pour le choix de 1.0 USD.
    llm_max_turns: int = 30
    # Le reviewer a le diff dans son prompt : ses outils servent à regarder
    # autour, pas à redécouvrir le dépôt. Trente tours pour relire un diff
    # qu'on lui a collé, c'est un budget de codeur donné à un lecteur
    # (ticket-199).
    llm_max_turns_reviewer: int = 10
    # L'audit lit le projet hors du diff (ticket-485) et un gros diff y passe
    # plus de tours qu'une relecture : à dix, puis vingt, il épuisait sa limite
    # sans rendre de verdict (ticket-495). Budget propre, annoncé à l'auditeur.
    llm_max_turns_securite: int = 30
    # Le plan lit les services pour décider d'une approche : il n'a pas le
    # diff dans son prompt et doit découvrir la base de code. Dix tours
    # échouaient systématiquement sur les tickets de taille ordinaire
    # (ticket-297).
    llm_max_turns_plan: int = 25
    # Relevé de 1.0 à 2.0 (ticket-102) : le premier run réel de ce dépôt a
    # atteint le plafond au milieu du tour d'un codeur, sur un ticket de taille
    # ordinaire. Un garde-fou qu'une tâche normale déclenche ne borne pas un
    # dérapage, il empêche le travail. Le dépassement est désormais rattrapé
    # (ADR-037), donc l'atteindre coûte un run bloqué, plus un arbre sale.
    llm_max_budget_usd: float = 2.0

    # Au-delà, un agent qui a posé une question reprend seul en énonçant son
    # hypothèse (ticket-066). Le délai existe parce qu'un run suspendu tient
    # du travail non commité, et bloque la file des tickets suivants
    # (ADR-018) : attendre indéfiniment une réponse coûte plus cher qu'une
    # hypothèse explicite et relisible.
    dialogue_timeout_s: float = 300.0
    # Plafond de dépense d'une CONVERSATION du chat (ticket-048).
    # `llm_max_budget_usd` borne un appel ; sans ce second plafond, une
    # longue discussion épuiserait le quota de l'abonnement sans que
    # rien ne le fasse remonter.
    chat_max_conversation_usd: float = 2.0
    # Plafond de dépense cumulée d'un RUN autonome (issue #61).
    # `llm_max_budget_usd` borne un appel `query()` ; un clic sur « mode
    # autonome » enchaîne jusqu'à 5 tickets, chacun sur plusieurs tours et
    # plusieurs agents — le plafond effectif se chiffrait en dizaines de
    # dollars de quota sans garde-fou agrégé. 0 désactive la borne.
    run_max_budget_usd: float = 5.0
    ide_workspace_dir: Path = Path.home() / "tessera-workspace"
    ide_log_level: str = "INFO"
    # Chemin vers agents/prompts/, ancré sur la racine du dépôt et non sur le
    # répertoire de lancement : `make dev` démarre depuis `backend/`, où
    # `agents/` n'existe pas. Un défaut relatif ne résolvait donc jamais, et
    # tous les agents tournaient sans leur system prompt en se contentant d'un
    # WARNING `prompt_file_missing`. Surchargeable via IDE_PROMPTS_DIR.
    ide_prompts_dir: Path = _REPO_ROOT / "agents" / "prompts"
    github_token: str = ""
    github_repo: str = ""  # format "owner/repo"
    # Cible par défaut des PR de ticket. Le flux est
    # ticket-XXX -> develop -> main : une PR de ticket ne vise jamais
    # `main` directement, sinon rien ne teste les tickets fusionnés
    # entre eux avant qu'ils n'atteignent l'état publiable.
    github_base_branch: str = "develop"
    ide_db_path: Path = Path("tessera.db")
    # Données d'exécution qui ne doivent jamais entrer dans un commit (file des
    # signalements en attente, ticket-430). Hors du dépôt : un fichier posé dans
    # l'arbre part dans le commit du run en cours, puis disparaît au changement
    # de branche. Surchargeable via IDE_STATE_DIR.
    ide_state_dir: Path = default_state_dir()
    # Fichier de log tournant (5 × 10 Mo). Ancré sur la racine du dépôt pour
    # ne pas dépendre du répertoire de lancement (ticket-330).
    ide_log_file: Path = _REPO_ROOT / "backend" / "logs" / "tessera.log"
    static_token: str = ""  # if set, all API requests require Authorization: Bearer <token>
    # Borne le nombre de suites de tests lancées simultanément sur la machine.
    # 0 ou moins : pas de borne. Voir ticket-348.
    max_parallel_test_runs: int = 2
    # Nombre maximal de requêtes Ollama simultanées par serveur (ticket-350).
    # Ollama sert un modèle à la suite et décharge l'un pour charger l'autre
    # quand on les alterne : plusieurs requêtes concurrentes vers le même
    # serveur rallongent le délai de chacune sans améliorer le débit global.
    # 0 ou moins : pas de borne.
    ollama_max_concurrent: int = 1
    # Délai max pour obtenir un créneau Ollama (ticket-380). Au-delà, le repli
    # prend le relais sans envoyer la requête. Évite d'attendre en file pendant
    # plusieurs minutes quand le serveur est saturé.
    ollama_slot_wait_s: float = 30.0
    # Durée de refroidissement après un dépassement de délai de lecture
    # (ticket-380). Pendant ce temps, tout appel lève `ProviderIndisponible`
    # aussitôt, sans requête — le repli prend le relais.
    ollama_cooldown_s: float = 600.0
    # Chemin vers bash.exe sous Windows, pour que le SDK puisse activer l'outil
    # `Bash` des agents. Lu depuis CLAUDE_CODE_GIT_BASH_PATH ; absent, le backend
    # tente de le déduire depuis l'emplacement de `git` au démarrage (ticket-319).
    claude_code_git_bash_path: str = ""
    # Délai maximum entre deux messages consécutifs d'un agent (ticket-381).
    # Borné par intervalle, pas par durée totale : une commande longue comme
    # la suite de tests (≈ 6 min) peut rester muette sans être figée.
    # 0 désactive la borne.
    agent_silence_max_s: float = 1200.0
    # Délai maximum d'attente du calcul « fusionnable » d'une PR par GitHub
    # avant d'abandonner le merge (ticket-384).
    attente_fusionnabilite_max_s: float = 300.0
    # Sur un projet merge_without_ci, délai maximum d'attente du merge du
    # ticket précédent avant de lancer le suivant d'une file (ticket-382).
    attente_merge_max_s: float = 600.0
    # Délai de grâce avant de lire une CI « none » comme un verdict (ticket-405).
    # GitHub inscrit les checks après l'ouverture de la PR, parfois tard quand
    # son API est lente : 120 s coupaient une CI qui existait bel et bien.
    # Passé ce délai, `none` ne conclut que si le dépôt ne déclare aucun workflow.
    ci_grace_s: float = 300.0
    # Maintient le système éveillé tant qu'un run est ouvert (ticket-394).
    # Utilise SetThreadExecutionState sous Windows ; no-op ailleurs.
    # Désactivable si un outil externe gère déjà la veille.
    keep_awake_during_runs: bool = True

    def valeurs_des_jetons(self) -> list[str]:
        """Return the non-empty values of the online-service tokens (ADR-053)."""
        valeurs = (getattr(self, champ).get_secret_value() for champ in CHAMPS_JETONS)
        return [valeur for valeur in valeurs if valeur]


def load_settings(env_file: Path | None = None) -> Settings:
    """Build the settings, turning a validation error into a value-free one.

    `env_file` replaces the default `.env`; it exists for tests.
    """
    try:
        if env_file is None:
            return Settings()
        # `_env_file` est un argument d'init de pydantic-settings que le plugin
        # mypy du projet ne connaît pas.
        return Settings(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as error:
        # `from None` : l'exception d'origine ne doit pas réapparaître dans la
        # trace chaînée.
        raise ConfigurationError(describe_validation_error(error)) from None


settings = load_settings()
