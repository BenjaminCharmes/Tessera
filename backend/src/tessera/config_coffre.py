"""Where ``Settings`` reads its secrets: environment, vault, then .env (ADR-073).

``SECRETS_SOURCE`` decides whether the vault source exists at all. It is read
before everything else, from the environment then from .env: ``env`` never
touches the vault, ``coffre`` refuses to start without it, ``auto`` (the
default, 05/11) falls back on .env with a warning, unless .env says a secret
was migrated — a migrated ``STATIC_TOKEN`` or ``FORBIDDEN_TERMS`` must never
turn empty in silence (design §3).
"""
import logging
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from tessera.coffre import NOMS_SECRETS, CoffreAbsent, CoffreEnErreur, coffre_du_systeme
from tessera.config_errors import ConfigurationError

# Pas le logger structuré : il importe `tessera.config`.
_journal = logging.getLogger("tessera.config")

# D'où viennent les secrets du dernier `Settings` construit : `coffre`, `env`
# ou `env-repli` (mode `auto` sans coffre). Lu par `/health` et `doctor`.
_source_effective = "env"

# La ligne que la migration (ticket-797) laisse à la place d'un secret rangé.
_MARQUE_MIGRE = re.compile(r"^\s*#\s*([A-Z0-9_]+)\s*:\s*dans le coffre", re.MULTILINE)


def lire_secrets_source(env_file: Path | None) -> str:
    """Return the declared mode: the environment first, then .env, else ``auto``."""
    valeur = os.environ.get("SECRETS_SOURCE")
    if not valeur and env_file is not None and env_file.is_file():
        valeur = dotenv_values(env_file).get("SECRETS_SOURCE")
    return (valeur or "auto").strip().lower()


def noms_migres(env_file: Path | None) -> list[str]:
    """Return the secrets that .env marks as moved into the vault."""
    if env_file is None or not env_file.is_file():
        return []
    texte = env_file.read_text(encoding="utf-8")
    return [nom for nom in _MARQUE_MIGRE.findall(texte) if nom in NOMS_SECRETS]


def est_placeholder(valeur: str) -> bool:
    """True for an example value such as ``sk-ant-...``: never a real secret."""
    return valeur.strip().endswith("...")


def source_effective() -> str:
    """Return where the secrets came from: ``coffre``, ``env`` or ``env-repli``."""
    return _source_effective


def noms_en_clair(env_file: Path | None) -> list[str]:
    """Return the secrets that .env still holds in clear, by name only."""
    if env_file is None or not env_file.is_file():
        return []
    lus = dotenv_values(env_file)
    return [nom for nom in NOMS_SECRETS if (v := lus.get(nom)) and not est_placeholder(v)]


class SourceCoffre(PydanticBaseSettingsSource):
    """Settings source holding the secrets read from the vault at startup."""

    def __init__(self, settings_cls: type[BaseSettings], valeurs: dict[str, str]) -> None:
        super().__init__(settings_cls)
        self._valeurs = valeurs

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Return the vault value of one field, None when the vault lacks it."""
        return self._valeurs.get(field_name.upper()), field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return the fields the vault holds, by field name."""
        return {
            nom: self._valeurs[nom.upper()]
            for nom in self.settings_cls.model_fields
            if nom.upper() in self._valeurs
        }


def _chemin_dotenv(dotenv: PydanticBaseSettingsSource) -> Path | None:
    """Return the .env file the dotenv source reads (the last one wins)."""
    fichier = getattr(dotenv, "env_file", None)
    if isinstance(fichier, Sequence) and not isinstance(fichier, str):
        fichier = fichier[-1] if fichier else None
    return Path(fichier) if fichier else None


def _lire_le_coffre(mode: str, env_file: Path | None) -> dict[str, str] | None:
    """Read the vault; None when it is unavailable and ``auto`` may fall back."""
    try:
        coffre = coffre_du_systeme()
        return {nom: valeur for nom in NOMS_SECRETS if (valeur := coffre.lire(nom))}
    except CoffreAbsent:
        cause = "absent"
    except CoffreEnErreur:
        cause = "en erreur (verrouillé ou refusé)"
    # Levées hors du bloc `except` : rien de l'erreur d'origine ne survit.
    if mode == "coffre":
        raise ConfigurationError(
            f"Coffre du système {cause} alors que SECRETS_SOURCE=coffre : "
            "déverrouille le coffre, ou déclare SECRETS_SOURCE=auto (repli sur .env) "
            "ou SECRETS_SOURCE=env."
        )
    migres = noms_migres(env_file)
    if migres:
        raise ConfigurationError(
            f"Coffre du système {cause}, mais .env indique que {', '.join(migres)} "
            "y est rangé : déverrouille le coffre, ou remets la valeur par "
            "`tessera.ps1 secrets set` sur une machine qui en a un."
        )
    _journal.warning("coffre_indisponible_repli_env", extra={"cause": cause})
    return None


def _signaler_les_secrets_en_clair(
    env_file: Path | None, coffre: dict[str, str] | None
) -> None:
    """Log, by name only, every secret still read from .env."""
    for nom in noms_en_clair(env_file):
        if nom in os.environ:
            continue
        evenement = (
            "secret_en_double_coffre_et_env"
            if coffre and nom in coffre
            else "secret_en_clair_dans_env"
        )
        _journal.warning(evenement, extra={"nom": nom})


def sources_des_secrets(
    settings_cls: type[BaseSettings],
    init: PydanticBaseSettingsSource,
    env: PydanticBaseSettingsSource,
    dotenv: PydanticBaseSettingsSource,
    file_secret: PydanticBaseSettingsSource,
) -> tuple[PydanticBaseSettingsSource, ...]:
    """Order the sources: init, environment, vault, .env, then defaults."""
    global _source_effective
    env_file = _chemin_dotenv(dotenv)
    mode = lire_secrets_source(env_file)
    if mode not in ("auto", "coffre"):
        # `env`, ou une valeur invalide que la validation du champ refusera.
        _source_effective = "env"
        return init, env, dotenv, file_secret
    valeurs = _lire_le_coffre(mode, env_file)
    _signaler_les_secrets_en_clair(env_file, valeurs)
    if valeurs is None:
        _source_effective = "env-repli"
        return init, env, dotenv, file_secret
    _source_effective = "coffre"
    return init, env, SourceCoffre(settings_cls, valeurs), dotenv, file_secret
