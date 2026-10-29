"""What an `agents.json` entry may say about an OpenAI-compatible endpoint — ticket-669.

La clé d'un point d'accès ne s'écrit jamais dans le manifeste, qui se
versionne : il en porte le nom de variable (`api_key_env`), et la valeur vit
dans l'environnement. Ce module refuse tout ce qui ressemble à une clé en
clair, et ne recopie jamais la valeur fautive dans son message.
"""
import os
import re
from collections.abc import Mapping

from tessera.models.agent import AgentConfig
from tessera.services.providers.noms import DeclarationRefusee, ProviderInconnu
from tessera.utils.logger import get_logger
from tessera.utils.secrets import SECRETS

_logger = get_logger(__name__)

PROVIDER_OPENAI = "openai_compatible"

#: Les noms de champ qui annoncent un secret, une fois mis en minuscules et
#: privés de `_` et `-` : `api_key`, `apiKey` et `api-key` donnent `apikey`.
_CHAMPS_SECRETS = frozenset({"apikey", "token", "secret", "authorization", "bearer"})

#: Un nom de variable d'environnement : majuscules, chiffres, `_`. Une clé
#: réelle porte presque toujours des minuscules ou un tiret.
_NOM_DE_VARIABLE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
#: Le préfixe des clés usuelles, même écrit en majuscules.
_PREFIXE_DE_CLE = re.compile(r"^(SK|PK|RK)_", re.IGNORECASE)


def _forme(champ: str) -> str:
    return champ.lower().replace("_", "").replace("-", "")


def _verifier_champs(role: str, entree: Mapping[str, object]) -> None:
    for champ in entree:
        if _forme(str(champ)) in _CHAMPS_SECRETS:
            raise DeclarationRefusee(
                f"Rôle '{role}' : le champ {champ!r} porte une clé en clair. "
                "Déclarez `api_key_env`, le nom de la variable d'environnement."
            )


def _verifier_variable(role: str, nom: object) -> None:
    if nom is None:
        return
    if (
        not isinstance(nom, str)
        or not _NOM_DE_VARIABLE.match(nom)
        or _PREFIXE_DE_CLE.match(nom)
    ):
        raise DeclarationRefusee(
            f"Rôle '{role}' : `api_key_env` doit être un nom de variable "
            "d'environnement en majuscules (OPENROUTER_API_KEY), pas une clé."
        )


def _verifier_url(role: str, url: object) -> None:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise DeclarationRefusee(
            f"Rôle '{role}' : le provider '{PROVIDER_OPENAI}' exige une "
            "`base_url` en http:// ou https://."
        )


def verifier_entree(role: str, entree: Mapping[str, object]) -> None:
    """Raises `DeclarationRefusee` when the raw entry mishandles a key or an URL."""
    _verifier_champs(role, entree)
    repli = entree.get("fallback")
    if isinstance(repli, Mapping):
        _verifier_champs(role, repli)
    _verifier_variable(role, entree.get("api_key_env"))
    if entree.get("provider") == PROVIDER_OPENAI:
        _verifier_url(role, entree.get("base_url"))


def verifier_provider(
    role: str, provider: str, connus: tuple[str, ...], repli: bool = False
) -> None:
    """Raises when `provider` is not one of `connus`, or is `openai_compatible`
    used as a fallback."""
    if repli and provider == PROVIDER_OPENAI:
        # `FallbackConfig` n'a ni `base_url` ni `api_key_env` : le repli
        # échouerait à l'exécution, au moment où on en a besoin.
        raise DeclarationRefusee(
            f"Rôle '{role}' : '{PROVIDER_OPENAI}' ne peut pas servir de repli, "
            "il se déclare comme provider principal."
        )
    if provider in connus:
        return
    quoi = "repli" if repli else "provider"
    raise ProviderInconnu(
        f"Rôle '{role}' : {quoi} inconnu {provider!r}. "
        f"Valeurs acceptées : {', '.join(connus)}."
    )


def verifier_entrees(entrees: list[object]) -> None:
    """Checks every raw manifest entry. Run before `AgentConfig`, which ignores
    the fields it does not know — a key written in clear would vanish."""
    for entree in entrees:
        if isinstance(entree, dict):
            verifier_entree(str(entree.get("role", "?")), entree)


def verifier_configs(configs: list[AgentConfig], connus: tuple[str, ...]) -> None:
    """Checks the provider and the fallback of every loaded role."""
    for config in configs:
        verifier_provider(config.role, config.provider, connus)
        if config.fallback is not None:
            verifier_provider(config.role, config.fallback.provider, connus, repli=True)


def resoudre_cle(nom: str | None) -> str:
    """The key held by the environment variable `nom`; empty when none.

    Un endpoint local (LM Studio) n'en demande pas : la clé absente n'est pas
    une erreur ici, c'est un 401 du serveur qui le dira, et le repli joue.
    La valeur rejoint `SECRETS` : les logs la masquent, le push la refuse.
    """
    if not nom:
        return ""
    valeur = os.environ.get(nom, "")
    if not valeur.strip():
        _logger.warning("api_key_env_vide", extra={"variable": nom})
        return ""
    SECRETS.register(valeur)
    return valeur
