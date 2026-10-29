"""Le lecteur du fichier d'activité d'un produit — ticket-671, ADR-064.

Un fichier valide rend ses agents ; chaque cause de refus rend `[]`.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tessera.models.agent import ServiceDeclare
from tessera.services.activite_produit import lire_activite
from tessera.services.declarations_activite import services_avec_activite
from tessera.services.project_loader import load_services_config

MAINTENANT = datetime(2026, 10, 29, 10, 12, 10, tzinfo=timezone.utc)
CHEMIN = "data/activite.json"


def _iso(decalage_s: float) -> str:
    return (MAINTENANT + timedelta(seconds=decalage_s)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _agent(ident: str = "triage", **extra: str) -> dict[str, str]:
    return {"id": ident, "nom": "Triage des signaux", "etat": "actif", **extra}


def _contenu(**surcharge: object) -> dict[str, object]:
    base: dict[str, object] = {
        "version": 1,
        "maj": _iso(-2),
        "agents": [_agent()],
    }
    return {**base, **surcharge}


def _ecrire(racine: Path, contenu: object, chemin: str = CHEMIN) -> None:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    texte = contenu if isinstance(contenu, str) else json.dumps(contenu)
    cible.write_text(texte, encoding="utf-8")


def test_valid_file_returns_its_agents_in_file_order(tmp_path: Path) -> None:
    agents = [_agent("zeta"), _agent("alpha", etat="repos", libelle="lot 3 sur 5")]
    _ecrire(tmp_path, _contenu(agents=agents))

    resultat = lire_activite(tmp_path, CHEMIN, MAINTENANT)

    assert [a.id for a in resultat] == ["zeta", "alpha"]
    assert resultat[1].etat == "repos"
    assert resultat[1].libelle == "lot 3 sur 5"


def test_empty_agent_list_is_a_clean_stop(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(agents=[]))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_file_at_the_edges_of_the_clock_window_is_read(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(maj=_iso(-30)))
    assert len(lire_activite(tmp_path, CHEMIN, MAINTENANT)) == 1

    _ecrire(tmp_path, _contenu(maj=_iso(5)))
    assert len(lire_activite(tmp_path, CHEMIN, MAINTENANT)) == 1


def test_missing_file_returns_nothing(tmp_path: Path) -> None:
    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_invalid_json_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, "{ not json")

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_file_over_16_kib_returns_nothing(tmp_path: Path) -> None:
    gros = _contenu(agents=[_agent(libelle="x" * 80)])
    texte = json.dumps(gros) + " " * (16 * 1024)
    _ecrire(tmp_path, texte)

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_other_version_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(version=2))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_unknown_field_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(extra="x"))
    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []

    _ecrire(tmp_path, _contenu(agents=[_agent(couleur="rouge")]))
    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_more_than_12_agents_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(agents=[_agent(f"a{i}") for i in range(13)]))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_twelve_agents_are_accepted(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(agents=[_agent(f"a{i}") for i in range(12)]))

    assert len(lire_activite(tmp_path, CHEMIN, MAINTENANT)) == 12


def test_duplicate_id_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(agents=[_agent("triage"), _agent("triage")]))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_label_over_80_chars_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(agents=[_agent(libelle="x" * 81)]))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_stale_file_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(maj=_iso(-31)))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_file_dated_over_5_seconds_ahead_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(maj=_iso(6)))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


@pytest.mark.parametrize("maj", ["2026-10-29T10:12:08", 1793182328, "hier"])
def test_maj_without_timezone_or_not_a_date_returns_nothing(
    tmp_path: Path, maj: object
) -> None:
    _ecrire(tmp_path, _contenu(maj=maj))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


@pytest.mark.parametrize("ident", ["Triage", "tri age", "", "a" * 41])
def test_bad_agent_id_returns_nothing(tmp_path: Path, ident: str) -> None:
    _ecrire(tmp_path, _contenu(agents=[_agent(ident)]))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_unknown_state_returns_nothing(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu(agents=[_agent(etat="dort")]))

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_path_leaving_the_project_returns_nothing(tmp_path: Path) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    _ecrire(tmp_path, _contenu(), "voisin.json")

    assert lire_activite(projet, "../voisin.json", MAINTENANT) == []


def test_absolute_path_outside_the_project_returns_nothing(tmp_path: Path) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    _ecrire(tmp_path, _contenu(), "voisin.json")

    assert lire_activite(projet, str(tmp_path / "voisin.json"), MAINTENANT) == []


def test_link_leading_outside_the_project_returns_nothing(tmp_path: Path) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    _ecrire(tmp_path, _contenu(), "dehors/activite.json")
    try:
        (projet / "lien").symlink_to(tmp_path / "dehors", target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available on this machine")

    assert lire_activite(projet, "lien/activite.json", MAINTENANT) == []


def test_directory_instead_of_a_file_returns_nothing(tmp_path: Path) -> None:
    (tmp_path / CHEMIN).mkdir(parents=True)

    assert lire_activite(tmp_path, CHEMIN, MAINTENANT) == []


def test_naive_now_never_raises(tmp_path: Path) -> None:
    _ecrire(tmp_path, _contenu())

    assert lire_activite(tmp_path, CHEMIN, datetime(2026, 10, 29, 10, 12, 10)) == []


def test_service_declare_accepts_activite_and_defaults_to_none() -> None:
    avec = ServiceDeclare(nom="worker", commande="x", activite="data/a.json")
    sans = ServiceDeclare(nom="web", commande="x")

    assert avec.activite == "data/a.json"
    assert sans.activite is None


def test_agents_json_with_and_without_activite_loads(tmp_path: Path) -> None:
    services = [
        {"nom": "worker", "commande": "py w.py", "activite": "data/a.json"},
        {"nom": "web", "commande": "py s.py"},
    ]
    (tmp_path / "agents.json").write_text(
        json.dumps({"services": services}), encoding="utf-8"
    )

    declares = load_services_config(tmp_path)

    assert [d["nom"] for d in declares] == ["worker", "web"]
    avec = services_avec_activite(tmp_path)
    assert [(s.nom, s.activite) for s in avec] == [("worker", "data/a.json")]


def test_services_avec_activite_ignores_malformed_entries(tmp_path: Path) -> None:
    services = [
        "pas un objet",
        {"nom": "x"},
        {"nom": "a", "commande": "c", "activite": 3},
        {"nom": "ok", "commande": "c", "activite": "d/a.json"},
    ]
    (tmp_path / "agents.json").write_text(
        json.dumps({"services": services}), encoding="utf-8"
    )

    assert [s.nom for s in services_avec_activite(tmp_path)] == ["ok"]


def test_services_avec_activite_without_agents_json_is_empty(tmp_path: Path) -> None:
    assert services_avec_activite(tmp_path) == []

    (tmp_path / "agents.json").write_text("{ no", encoding="utf-8")
    assert services_avec_activite(tmp_path) == []

    (tmp_path / "agents.json").write_text('{"services": "x"}', encoding="utf-8")
    assert services_avec_activite(tmp_path) == []
