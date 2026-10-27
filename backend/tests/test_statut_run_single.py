"""The status of a single-ticket run says how its ticket ended — ticket-577."""
from datetime import datetime, timedelta, timezone

from tessera.config import settings
from tessera.services.database import create_run, finish_run
from tessera.services.run_registry import RunActif
from tessera.services.run_status import (
    en_utc,
    statut_d_un_run_vivant,
    statut_en_base,
)


async def test_approved_single_run_lists_its_ticket_as_approved_and_done() -> None:
    db = settings.ide_db_path
    run_id = await create_run(db, "projet-single", "ticket-112")
    await finish_run(db, run_id, rounds=1, approved=True, final_status="done")

    statut = await statut_en_base(db, run_id)

    assert statut is not None
    assert statut.mode == "single"
    assert statut.statut == "terminé"
    assert statut.approuves == ["ticket-112"]
    assert statut.faits == ["ticket-112"]
    assert statut.arretes == []
    assert statut.restants == []


async def test_unapproved_single_run_lists_its_ticket_as_stopped() -> None:
    db = settings.ide_db_path
    run_id = await create_run(db, "projet-single", "ticket-113")
    await finish_run(
        db, run_id, rounds=2, approved=False, final_status="blocked",
        arret="reviewer asked for changes\nsecond line",
    )

    statut = await statut_en_base(db, run_id)

    assert statut is not None
    assert statut.statut == "interrompu"
    assert statut.approuves == []
    assert [(a.ticket_id, a.motif) for a in statut.arretes] == [
        ("ticket-113", "reviewer asked for changes")
    ]
    assert statut.faits == ["ticket-113"]


async def test_single_run_without_end_shows_its_ticket_as_current() -> None:
    db = settings.ide_db_path
    run_id = await create_run(db, "projet-single", "ticket-114")

    statut = await statut_en_base(db, run_id)

    assert statut is not None
    assert statut.statut == "en cours"
    assert statut.ticket_courant == "ticket-114"
    assert statut.approuves == []
    assert statut.arretes == []


async def test_start_is_rendered_in_the_same_timezone_live_and_in_database() -> None:
    db = settings.ide_db_path
    run_id = await create_run(db, "projet-single", "ticket-115")
    await finish_run(db, run_id, rounds=1, approved=True, final_status="done")
    local = timezone(timedelta(hours=1))
    vivant = RunActif(
        run_id="vivant", project_id="projet-single",
        demarre_a=datetime(2026, 10, 26, 9, 30, tzinfo=local),
    )

    en_base = await statut_en_base(db, run_id)

    assert en_base is not None
    assert statut_d_un_run_vivant(vivant).debut == "2026-10-26T08:30:00+00:00"
    assert en_base.debut.endswith("+00:00")
    assert datetime.fromisoformat(en_base.debut).utcoffset() == timedelta(0)


def test_en_utc_converts_offsets_and_takes_naive_instants_as_utc() -> None:
    assert en_utc("2026-10-26T10:00:00+01:00") == "2026-10-26T09:00:00+00:00"
    assert en_utc("2026-10-26T10:00:00") == "2026-10-26T10:00:00+00:00"
