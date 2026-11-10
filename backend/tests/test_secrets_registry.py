"""Every vault secret but the forbidden terms is a masked secret (ticket-796, ADR-073)."""
from tessera.coffre import NOMS_SECRETS
from tessera.config import Settings
from tessera.utils.logger import inscrire_les_secrets
from tessera.utils.secrets import SECRETS

# Des valeurs inventées, une par secret.
_FACTICES = {nom: f"factice-{nom.lower()}-0042" for nom in NOMS_SECRETS}


def _reglages() -> Settings:
    champs = {nom.lower(): valeur for nom, valeur in _FACTICES.items()}
    return Settings(_env_file=None, **champs)  # type: ignore[arg-type]


def test_all_ten_secrets_are_registered_at_startup() -> None:
    inscrire_les_secrets(_reglages())

    attendus = {v for nom, v in _FACTICES.items() if nom != "FORBIDDEN_TERMS"}
    assert len(attendus) == 10
    assert attendus <= SECRETS.valeurs()


def test_forbidden_terms_is_not_registered_as_a_secret() -> None:
    reglages = _reglages()
    inscrire_les_secrets(reglages)

    assert _FACTICES["FORBIDDEN_TERMS"] not in reglages.valeurs_des_secrets()
    assert _FACTICES["FORBIDDEN_TERMS"] not in SECRETS.valeurs()
