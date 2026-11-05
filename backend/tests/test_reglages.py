"""The five overridable settings: registry, bounds, storage, snapshot (ticket-805)."""
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from tessera import reglages
from tessera.config import CHAMPS_JETONS, Settings, settings
from tessera.reglages import REGISTRE, ReglageInvalide
from tessera.services.database import init_db


@pytest.fixture(autouse=True)
def _etat_propre() -> Iterator[None]:
    """Each test starts and ends without override and without pinned snapshot."""
    reglages._SURCHARGES.clear()
    reglages._SNAPSHOT.set(None)
    yield
    reglages._SURCHARGES.clear()
    reglages._SNAPSHOT.set(None)


@pytest.fixture
async def base(tmp_path: Path) -> Path:
    chemin = tmp_path / "tessera.db"
    await init_db(chemin)
    return chemin


def test_registre_lists_exactly_the_five_names() -> None:
    assert set(REGISTRE) == {
        "run_max_budget_usd",
        "llm_max_budget_usd",
        "dialogue_timeout_s",
        "max_parallel_test_runs",
        "keep_awake_during_runs",
    }


def test_registre_holds_no_secret_no_path_and_no_security_setting() -> None:
    interdits = {
        *CHAMPS_JETONS,
        "static_token",
        "forbidden_terms",
        "anthropic_api_key",
        "github_token",
        "allowed_hosts",
        "allowed_origins",
    }
    assert not interdits & set(REGISTRE)
    for nom in REGISTRE:
        annotation = Settings.model_fields[nom].annotation
        assert annotation is not Path


@pytest.mark.parametrize(
    ("nom", "valeur"),
    [
        ("run_max_budget_usd", 0.4),
        ("run_max_budget_usd", 50.5),
        ("llm_max_budget_usd", 11),
        ("dialogue_timeout_s", 29),
        ("dialogue_timeout_s", 3601),
        ("max_parallel_test_runs", 0),
        ("max_parallel_test_runs", 9),
        ("inconnu", 1),
        ("static_token", "x"),
    ],
)
def test_valider_rejects_out_of_bounds_values(nom: str, valeur: object) -> None:
    with pytest.raises(ReglageInvalide):
        reglages.valider(nom, valeur)


@pytest.mark.parametrize(
    ("nom", "valeur"),
    [
        ("run_max_budget_usd", True),
        ("run_max_budget_usd", "5"),
        ("run_max_budget_usd", None),
        ("max_parallel_test_runs", 2.5),
        ("max_parallel_test_runs", True),
        ("keep_awake_during_runs", 1),
        ("keep_awake_during_runs", "true"),
    ],
)
def test_valider_rejects_a_wrong_type(nom: str, valeur: object) -> None:
    with pytest.raises(ReglageInvalide):
        reglages.valider(nom, valeur)


@pytest.mark.parametrize("valeur", [float("nan"), float("inf"), float("-inf")])
def test_valider_rejects_nan_and_infinity(valeur: float) -> None:
    with pytest.raises(ReglageInvalide):
        reglages.valider("dialogue_timeout_s", valeur)


@pytest.mark.parametrize("nom", ["run_max_budget_usd", "llm_max_budget_usd"])
def test_valider_refuses_zero_for_a_budget(nom: str) -> None:
    with pytest.raises(ReglageInvalide):
        reglages.valider(nom, 0)


def test_valider_accepts_the_bounds_and_coerces_the_type() -> None:
    assert reglages.valider("run_max_budget_usd", 1) == 1.0
    assert isinstance(reglages.valider("run_max_budget_usd", 1), float)
    assert reglages.valider("max_parallel_test_runs", 8) == 8
    assert reglages.valider("keep_awake_during_runs", False) is False


def test_du_moment_returns_the_env_default_without_override() -> None:
    effectifs = reglages.du_moment()

    assert effectifs.run_max_budget_usd == settings.run_max_budget_usd
    assert effectifs.llm_max_budget_usd == settings.llm_max_budget_usd
    assert effectifs.dialogue_timeout_s == settings.dialogue_timeout_s
    assert effectifs.max_parallel_test_runs == settings.max_parallel_test_runs
    assert effectifs.keep_awake_during_runs == settings.keep_awake_during_runs


def test_du_moment_follows_a_settings_monkeypatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "run_max_budget_usd", 7.5)
    monkeypatch.setattr(settings, "max_parallel_test_runs", 4)

    effectifs = reglages.du_moment()

    assert effectifs.run_max_budget_usd == 7.5
    assert effectifs.max_parallel_test_runs == 4


async def test_ecrire_then_du_moment_returns_the_override(base: Path) -> None:
    rendu = await reglages.ecrire(base, "run_max_budget_usd", 12)

    assert rendu.run_max_budget_usd == 12.0
    assert reglages.du_moment().run_max_budget_usd == 12.0


async def test_ecrire_rejects_an_invalid_value_without_storing_it(base: Path) -> None:
    with pytest.raises(ReglageInvalide):
        await reglages.ecrire(base, "run_max_budget_usd", 0)

    lignes = sqlite3.connect(str(base)).execute("SELECT * FROM reglages").fetchall()
    assert lignes == []


async def test_ecrire_survives_a_new_charger_on_the_same_database(base: Path) -> None:
    await reglages.ecrire(base, "dialogue_timeout_s", 600)
    await reglages.ecrire(base, "keep_awake_during_runs", False)
    reglages._SURCHARGES.clear()

    await reglages.charger(base)

    effectifs = reglages.du_moment()
    assert effectifs.dialogue_timeout_s == 600.0
    assert effectifs.keep_awake_during_runs is False


async def test_retirer_returns_to_the_default(base: Path) -> None:
    await reglages.ecrire(base, "max_parallel_test_runs", 6)

    rendu = await reglages.retirer(base, "max_parallel_test_runs")

    assert rendu.max_parallel_test_runs == settings.max_parallel_test_runs
    lignes = sqlite3.connect(str(base)).execute("SELECT * FROM reglages").fetchall()
    assert lignes == []


async def test_retirer_refuses_an_unknown_name(base: Path) -> None:
    with pytest.raises(ReglageInvalide):
        await reglages.retirer(base, "static_token")


async def test_charger_ignores_an_unknown_name_and_an_out_of_bounds_value(
    base: Path,
) -> None:
    c = sqlite3.connect(str(base))
    c.executemany(
        "INSERT INTO reglages (nom, valeur, modifie_le) VALUES (?, ?, 'x')",
        [
            ("static_token", '"secret"'),
            ("run_max_budget_usd", "9999"),
            ("llm_max_budget_usd", "pas du json"),
            ("dialogue_timeout_s", "120"),
        ],
    )
    c.commit()
    c.close()

    await reglages.charger(base)

    assert reglages._SURCHARGES == {"dialogue_timeout_s": 120.0}
    assert reglages.du_moment().run_max_budget_usd == settings.run_max_budget_usd


async def test_ecrire_never_touches_the_env_file(
    base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dossier = tmp_path / "cwd"
    dossier.mkdir()
    env = dossier / ".env"
    env.write_bytes(b"RUN_MAX_BUDGET_USD=5.0\n")
    monkeypatch.chdir(dossier)

    await reglages.ecrire(base, "run_max_budget_usd", 9)
    await reglages.retirer(base, "run_max_budget_usd")

    assert env.read_bytes() == b"RUN_MAX_BUDGET_USD=5.0\n"
    assert [p.name for p in dossier.iterdir()] == [".env"]


async def test_figer_keeps_its_values_after_a_later_ecrire(base: Path) -> None:
    figees = reglages.figer()
    avant = figees.run_max_budget_usd

    await reglages.ecrire(base, "run_max_budget_usd", avant + 3)

    assert reglages.courants().run_max_budget_usd == avant
    assert reglages.courants() is figees


async def test_courants_outside_a_run_follows_ecrire(base: Path) -> None:
    await reglages.ecrire(base, "llm_max_budget_usd", 3)

    assert reglages.courants().llm_max_budget_usd == 3.0


async def test_du_moment_ignores_the_frozen_snapshot(base: Path) -> None:
    reglages.figer()

    await reglages.ecrire(base, "dialogue_timeout_s", 900)

    assert reglages.du_moment().dialogue_timeout_s == 900.0
    assert reglages.courants().dialogue_timeout_s != 900.0


def test_figer_accepts_explicit_values() -> None:
    voulues = reglages.du_moment()

    assert reglages.figer(voulues) is voulues
    assert reglages.courants() is voulues
