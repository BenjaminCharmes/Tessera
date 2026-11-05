"""Agent report: bounds, guards, professional projects and duplicates — ticket-862."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers.signal_agent import MAX_DESCRIPTION, MAX_TITRE, SOURCE_PROFESSIONNELLE, Refus, SignalValide, normaliser_titre, valider_signal
from tessera.services.providers.signal_agent_registre import DEJA_SIGNALE, cle_doublon, emis_du_jour, enregistrer_signal, lire_registre
from tessera.utils.secrets import SECRETS

MAINTENANT = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _etat_isole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")


def _args(**remplacements: object) -> dict[str, object]:
    args: dict[str, object] = {
        "titre": "La garde d'écriture refuse un fichier du projet",
        "description": "Un Write sous tickets/ est refusé alors que le ticket le demande.",
        "categorie": "garde_trop_strict",
        "composant": "garde_ecriture",
    }
    args.update(remplacements)
    return args


def _valider(
    args: Mapping[str, object],
    *,
    confidentialite: str = "personal",
    deja_emis_run: int = 0,
    deja_emis_jour: int = 0,
) -> SignalValide | Refus:
    return valider_signal(
        args,
        projet="mon-projet",
        confidentialite=confidentialite,
        role="codeur",
        ticket="ticket-001",
        deja_emis_run=deja_emis_run,
        deja_emis_jour=deja_emis_jour,
    )


def _accepte(args: Mapping[str, object]) -> SignalValide:
    resultat = _valider(args)
    assert isinstance(resultat, SignalValide)
    return resultat


def test_valid_signal_is_accepted_with_source_from_the_run() -> None:
    resultat = _valider(_args(projet="projet-invente-par-l-agent"))
    assert isinstance(resultat, SignalValide)
    assert resultat.source == "agent:codeur@ticket-001"
    assert resultat.projet == "mon-projet"
    assert resultat.categorie == "garde_trop_strict"
    assert resultat.composant == "garde_ecriture"
    assert resultat.titre == _args()["titre"]


def test_fourth_signal_of_a_run_is_refused() -> None:
    assert isinstance(_valider(_args(), deja_emis_run=2), SignalValide)
    refus = _valider(_args(), deja_emis_run=3)
    assert isinstance(refus, Refus)
    assert "par run" in refus.raison


def test_eleventh_signal_of_a_day_is_refused() -> None:
    assert isinstance(_valider(_args(), deja_emis_jour=9), SignalValide)
    refus = _valider(_args(), deja_emis_jour=10)
    assert isinstance(refus, Refus)
    assert "par jour" in refus.raison


def test_forbidden_term_and_secret_are_refused_with_a_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "forbidden_terms", "zorglub")
    SECRETS.register("jeton-confidentiel-9f3a7c")
    terme = _valider(_args(description="Le client Zorglub est cité ici."))
    secret = _valider(_args(titre="Le jeton jeton-confidentiel-9f3a7c fuit"))
    for refus, champ in ((terme, "description"), (secret, "titre")):
        assert isinstance(refus, Refus)
        assert champ in refus.raison
        assert "interdit" in refus.raison
        assert "zorglub" not in refus.raison.lower()
        assert "9f3a7c" not in refus.raison


@pytest.mark.parametrize("prefixe", ["+", "++", "+++", "+++ b/x ", " ++ ", "\n+++\n"])
def test_text_starting_with_plus_signs_is_still_inspected(
    monkeypatch: pytest.MonkeyPatch, prefixe: str
) -> None:
    monkeypatch.setattr(settings, "forbidden_terms", "zorglub")
    SECRETS.register("jeton-confidentiel-9f3a7c")
    secret = _valider(_args(titre=f"{prefixe}jeton-confidentiel-9f3a7c"))
    terme = _valider(_args(description=f"{prefixe}le client zorglub"))
    assert isinstance(secret, Refus)
    assert isinstance(terme, Refus)


def test_professional_project_drops_free_text_and_hides_its_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "forbidden_terms", "zorglub")
    resultat = valider_signal(
        _args(titre="Titre libre", description="Texte libre sur zorglub", projet="zorglub-app"),
        projet="zorglub-app",
        confidentialite="professional",
        role="codeur",
        ticket="ticket-001",
        deja_emis_run=0,
        deja_emis_jour=0,
    )
    assert isinstance(resultat, SignalValide)
    assert resultat.titre == "[codeur] garde_trop_strict — garde_ecriture"
    assert resultat.description == ""
    assert resultat.projet == SOURCE_PROFESSIONNELLE
    assert "zorglub" not in repr(asdict(resultat)).lower()
    assert "Titre libre" not in repr(asdict(resultat))


def test_professional_project_still_checks_enumerations() -> None:
    refus = _valider(_args(composant="inconnu"), confidentialite="professional")
    assert isinstance(refus, Refus)


def test_duplicate_is_refused_and_counts_a_view() -> None:
    signal = _accepte(_args())
    assert enregistrer_signal(signal, projet="mon-projet", maintenant=MAINTENANT) is None
    autre_forme = _accepte(_args(titre="LA GARDE d'ecriture refuse un fichier du projet !"))
    refus = enregistrer_signal(autre_forme, projet="autre", maintenant=MAINTENANT)
    assert refus == Refus(DEJA_SIGNALE)
    (entree,) = lire_registre()
    assert entree.vu == 2
    assert entree.projet == "mon-projet"


def test_duplicate_outside_the_seven_day_window_is_new_again() -> None:
    signal = _accepte(_args())
    assert enregistrer_signal(signal, projet="p", maintenant=MAINTENANT) is None
    huit_jours = MAINTENANT + timedelta(days=8)
    assert enregistrer_signal(signal, projet="p", maintenant=huit_jours) is None
    assert [e.vu for e in lire_registre()] == [1]


def test_different_component_is_not_a_duplicate() -> None:
    assert enregistrer_signal(_accepte(_args()), projet="p", maintenant=MAINTENANT) is None
    autre = _accepte(_args(composant="garde_git"))
    assert enregistrer_signal(autre, projet="p", maintenant=MAINTENANT) is None
    assert len(lire_registre()) == 2


def test_oversized_description_is_refused_not_truncated() -> None:
    limite = _valider(_args(description="d" * MAX_DESCRIPTION))
    assert isinstance(limite, SignalValide)
    assert len(limite.description) == MAX_DESCRIPTION
    refus = _valider(_args(description="d" * (MAX_DESCRIPTION + 1)))
    assert isinstance(refus, Refus)
    assert str(MAX_DESCRIPTION) in refus.raison
    refus_titre = _valider(_args(titre="t" * (MAX_TITRE + 1)))
    assert isinstance(refus_titre, Refus)


@pytest.mark.parametrize("champ", ["titre", "description"])
def test_missing_or_non_text_field_is_refused(champ: str) -> None:
    assert isinstance(_valider(_args(**{champ: ""})), Refus)
    assert isinstance(_valider(_args(**{champ: 12})), Refus)


@pytest.mark.parametrize("champ", ["categorie", "composant"])
def test_value_outside_an_enumeration_is_refused(champ: str) -> None:
    refus = _valider(_args(**{champ: "nimporte-quoi"}))
    assert isinstance(refus, Refus)
    assert champ in refus.raison


def test_normalised_title_ignores_case_accents_and_punctuation() -> None:
    assert normaliser_titre("  Élan,  CASSÉ !! ") == "elan casse"
    assert cle_doublon(_accepte(_args())).startswith("garde_trop_strict|garde_ecriture|")


def test_emitted_today_counts_the_projects_reports_of_the_last_day() -> None:
    enregistrer_signal(_accepte(_args()), projet="p", maintenant=MAINTENANT - timedelta(hours=30))
    enregistrer_signal(
        _accepte(_args(composant="garde_git")), projet="p", maintenant=MAINTENANT - timedelta(hours=2)
    )
    enregistrer_signal(
        _accepte(_args(composant="provider")), projet="autre", maintenant=MAINTENANT
    )
    assert emis_du_jour("p", maintenant=MAINTENANT) == 1
    assert emis_du_jour("inconnu", maintenant=MAINTENANT) == 0


def test_unreadable_ledger_is_set_aside_not_overwritten() -> None:
    chemin = settings.ide_state_dir / "signaux_agents.json"
    chemin.parent.mkdir(parents=True)
    chemin.write_text("{pas du json", encoding="utf-8")
    assert lire_registre() == []
    assert chemin.with_suffix(".corrompu").is_file()
    assert enregistrer_signal(_accepte(_args()), projet="p", maintenant=MAINTENANT) is None
