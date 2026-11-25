"""The repository's rituels.md falls on weekday working hours — ticket-1045."""
from datetime import time

from tessera.services.projets import rituels as service
from tessera.services.projets.rituels_echeances import Hebdo, Quotidien


def _par_id() -> dict[str, service.RituelDefini]:
    definitions, erreur = service.lire_definitions()
    assert erreur is None
    return {d.id: d for d in definitions}


def test_weekly_and_daily_rituals_stay_in_weekday_working_hours() -> None:
    definitions, _ = service.lire_definitions()
    controles = 0
    for d in definitions:
        if isinstance(d.rythme, (Hebdo, Quotidien)):
            controles += 1
            assert time(8, 0) <= d.rythme.heure <= time(17, 59), d.id
        if isinstance(d.rythme, Hebdo):
            assert d.rythme.jour not in ("samedi", "dimanche"), d.id
    assert controles > 0


def test_moved_rituals_have_their_new_hours() -> None:
    par_id = _par_id()
    attendu = {
        "lecture-veille": ("lundi", time(10, 30)),
        "radar-hebdo": ("lundi", time(11, 0)),
        "point-revenus": ("lundi", time(14, 0)),
        "portfolio-hebdo": ("vendredi", time(14, 0)),
    }
    for id_, (jour, heure) in attendu.items():
        rythme = par_id[id_].rythme
        assert isinstance(rythme, Hebdo)
        assert (rythme.jour, rythme.heure) == (jour, heure)


def test_journal_du_jour_is_gone_and_point_hebdo_stays() -> None:
    par_id = _par_id()
    assert "journal-du-jour" not in par_id
    assert par_id["point-hebdo-travail"].detail == "Noter la semaine de travail."
