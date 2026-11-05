"""Direct anomaly rules — ticket-835 (ADR-078): repeated tool, silence, review rounds."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tessera.services.anomalies.lecture_evenements import (
    AppelOutil,
    derniers_appels_d_outils,
    hacher_input,
)
from tessera.services.anomalies.regles_directes import outil_repete, silence, tours_de_revue
from tests.anomalies_base import base_neuve, evenement, ligne_de_run

T0 = datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc)


def _appel(i: int, tool: str = "Bash", h: str = "a", agent: str = "codeur") -> AppelOutil:
    return AppelOutil(id=i, agent=agent, tool=tool, input_hash=h, ticket_id="ticket-001")


def test_outil_repete_three_identical_calls_is_none() -> None:
    assert outil_repete([_appel(i) for i in range(3)]) is None


def test_outil_repete_four_identical_calls_reports() -> None:
    a = outil_repete([_appel(i) for i in range(1, 5)])
    assert a is not None
    assert (a.regle, a.mesure, a.seuil, a.unite) == ("outil_repete", 4.0, 4.0, "appels")
    assert a.ticket_id == "ticket-001" and a.agent == "codeur"


def test_outil_repete_five_calls_keeps_the_key_of_the_series_start() -> None:
    a = outil_repete([_appel(i) for i in range(10, 15)])
    assert a is not None
    assert a.cle == "outil_repete:10"
    assert a.mesure == 5.0


def test_outil_repete_a_different_input_or_tool_in_between_breaks_the_series() -> None:
    par_input = [_appel(1), _appel(2), _appel(3, h="b"), _appel(4), _appel(5), _appel(6)]
    assert outil_repete(par_input) is None
    par_outil = [_appel(1), _appel(2), _appel(3, tool="Read"), _appel(4), _appel(5), _appel(6)]
    assert outil_repete(par_outil) is None
    par_agent = [_appel(1), _appel(2), _appel(3, agent="reviewer"), _appel(4), _appel(5)]
    assert outil_repete(par_agent) is None


def test_outil_repete_message_never_contains_the_tool_input() -> None:
    secret = "ghp_FAKE_TOKEN_0123456789"
    h = hacher_input({"command": f"curl -H {secret}"})
    a = outil_repete([_appel(i, h=h) for i in range(4)])
    assert a is not None
    assert secret not in a.message and h not in a.message
    assert "Bash" in a.message


def test_silence_899s_is_none() -> None:
    assert silence(T0, T0 + timedelta(seconds=899), ticket_id="t") is None


def test_silence_900s_reports() -> None:
    a = silence(T0, T0 + timedelta(seconds=900), ticket_id="t")
    assert a is not None
    assert (a.regle, a.mesure, a.seuil, a.unite) == ("silence", 900.0, 900.0, "s")
    assert a.cle == f"silence:{T0.isoformat()}"


def test_silence_is_none_when_exempt_or_when_no_event_was_seen() -> None:
    later = T0 + timedelta(hours=2)
    assert silence(T0, later, exempte=True, ticket_id="t") is None
    assert silence(None, later, ticket_id="t") is None


def test_tours_de_revue_round_2_is_none() -> None:
    assert tours_de_revue(2, "ticket-001") is None


def test_tours_de_revue_round_3_reports() -> None:
    a = tours_de_revue(3, "ticket-001")
    assert a is not None
    assert (a.regle, a.cle, a.mesure, a.unite) == ("tours_de_revue", "tours:ticket-001", 3.0, "tours")


async def test_derniers_appels_d_outils_ignores_calls_before_the_last_agent_started(
    tmp_path: Path,
) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r")
    ts = "2026-11-05T10:00:00+00:00"
    await evenement(db, "r", "agent_started", ts=ts, agent="codeur")
    await evenement(db, "r", "agent_tool_use", ts=ts, agent="codeur", data={"tool": "Old", "input": {}})
    await evenement(db, "r", "agent_started", ts=ts, agent="codeur")
    await evenement(db, "r", "agent_tool_use", ts=ts, agent="codeur", data={"tool": "New", "input": {"a": 1}})
    await evenement(db, "r", "agent_tool_use", ts=ts, agent="codeur", ticket_id="autre",
                    data={"tool": "Other", "input": {}})
    appels = await derniers_appels_d_outils(db, "r", "ticket-001")
    assert [a.tool for a in appels] == ["New"]
    assert appels[0].agent == "codeur" and appels[0].ticket_id == "ticket-001"


async def test_derniers_appels_d_outils_keeps_the_n_most_recent_in_order(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r")
    ts = "2026-11-05T10:00:00+00:00"
    for i in range(10):
        await evenement(db, "r", "agent_tool_use", ts=ts, agent="codeur", data={"tool": f"T{i}"})
    appels = await derniers_appels_d_outils(db, "r", "ticket-001", n=3)
    assert [a.tool for a in appels] == ["T7", "T8", "T9"]


async def test_derniers_appels_d_outils_never_writes(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r")
    await evenement(db, "r", "agent_tool_use", ts="2026-11-05T10:00:00+00:00",
                    agent="codeur", data={"tool": "Bash", "input": {}})
    avant = db.read_bytes()
    await derniers_appels_d_outils(db, "r", "ticket-001")
    assert db.read_bytes() == avant


def test_input_hash_is_stable_across_key_order() -> None:
    assert hacher_input({"a": 1, "b": {"x": 1, "y": 2}}) == hacher_input({"b": {"y": 2, "x": 1}, "a": 1})
    assert hacher_input({"a": 1}) != hacher_input({"a": 2})


async def test_ouvrir_en_lecture_refuses_any_write(tmp_path: Path) -> None:
    import aiosqlite
    import pytest

    from tessera.services.anomalies.lecture_base import ouvrir_en_lecture

    db = await base_neuve(tmp_path / "t.db")
    async with ouvrir_en_lecture(db) as c:
        with pytest.raises(aiosqlite.OperationalError):
            await c.execute("INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at)"
                            " VALUES ('x','p','t','2026-01-01')")
