"""Tests for scripts/arreter_tessera.py (ticket-423).

The selection is pure: processes and listening ports in, Tessera's own
processes out. Nothing here touches a real process.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from arreter_tessera import (  # noqa: E402
    Processus,
    formater_sortie,
    lire_entree,
    main,
    select_processus_tessera,
)

RACINE = r"C:\Users\Dev\tessera"
AUCUN_PORT: dict[int, list[int]] = {}


def _python(pid: int, commande: str) -> Processus:
    return Processus(pid=pid, nom="python.exe", commande=commande)


def _node(pid: int, commande: str) -> Processus:
    return Processus(pid=pid, nom="node.exe", commande=commande)


def _pids(selection: list[Processus]) -> list[int]:
    return [p.pid for p in selection]


def test_other_app_uvicorn_is_not_selected() -> None:
    autre = _python(10, r"python.exe -m uvicorn app.main:app --port 8025")
    assert select_processus_tessera([autre], RACINE, AUCUN_PORT) == []


def test_tessera_backend_is_selected() -> None:
    backend = _python(11, r"python.exe -m uvicorn tessera.main:app --port 8100")
    assert _pids(select_processus_tessera([backend], RACINE, AUCUN_PORT)) == [11]


def test_spawn_main_worker_with_tessera_marker_is_selected() -> None:
    worker = _python(12, "python.exe -c from multiprocessing.spawn import spawn_main; tessera.main:app")
    assert _pids(select_processus_tessera([worker], RACINE, AUCUN_PORT)) == [12]


def test_vite_of_another_folder_is_not_selected() -> None:
    autre = _node(20, r"node.exe C:\Users\Dev\vigie\frontend\node_modules\vite\bin\vite.js")
    assert select_processus_tessera([autre], RACINE, AUCUN_PORT) == []


def test_vite_of_a_sibling_folder_prefix_is_not_selected() -> None:
    voisin = _node(21, r"node.exe C:\Users\Dev\tessera\frontend-old\node_modules\vite\bin\vite.js")
    assert select_processus_tessera([voisin], RACINE, AUCUN_PORT) == []


def test_vite_of_tessera_frontend_is_selected() -> None:
    mien = _node(22, r"node.exe C:\Users\Dev\tessera\frontend\node_modules\vite\bin\vite.js")
    assert _pids(select_processus_tessera([mien], RACINE, AUCUN_PORT)) == [22]


def test_path_match_ignores_case_and_trailing_separator() -> None:
    mien = _node(23, r"node.exe c:\users\dev\TESSERA\frontend\node_modules\vite\bin\vite.js")
    assert _pids(select_processus_tessera([mien], RACINE + "\\", AUCUN_PORT)) == [23]


def test_vite_listening_on_frontend_port_is_selected_without_path() -> None:
    muet = _node(24, "node.exe vite")
    assert _pids(select_processus_tessera([muet], RACINE, {5173: [24]})) == [24]


def test_node_without_vite_is_never_selected() -> None:
    serveur = _node(25, r"node.exe C:\Users\Dev\tessera\frontend\server.js")
    assert select_processus_tessera([serveur], RACINE, {5173: [25]}) == []


def test_listener_on_backend_port_is_selected_whatever_its_command_line() -> None:
    orphelin = _python(30, "python.exe -c from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=1)")
    autre = _python(31, "python.exe -m uvicorn app.main:app --port 8025")
    selection = select_processus_tessera([orphelin, autre], RACINE, {8100: [30]})
    assert _pids(selection) == [30]


def test_listener_on_backend_port_is_selected_whatever_its_name() -> None:
    inconnu = Processus(pid=32, nom="uvicorn.exe", commande="")
    assert _pids(select_processus_tessera([inconnu], RACINE, {8100: [32]})) == [32]


def test_selection_keeps_input_order_and_skips_the_rest() -> None:
    processus = [
        _python(1, "python.exe -m uvicorn app.main:app --port 8025"),
        _python(2, "python.exe -m uvicorn tessera.main:app"),
        _node(3, r"node.exe C:\Users\Dev\vigie\frontend\node_modules\vite\bin\vite.js"),
        _node(4, r"node.exe C:\Users\Dev\tessera\frontend\node_modules\vite\bin\vite.js"),
    ]
    assert _pids(select_processus_tessera(processus, RACINE, AUCUN_PORT)) == [2, 4]


def test_lire_entree_parses_launcher_json() -> None:
    brut = json.dumps(
        {
            "processus": [{"pid": 7, "nom": "python.exe", "commande": None}],
            "ecoutes": {"8100": [7], "5173": []},
        }
    )
    processus, ecoutes = lire_entree(brut)
    assert processus == [Processus(pid=7, nom="python.exe", commande="")]
    assert ecoutes == {8100: [7], 5173: []}


def test_formater_sortie_truncates_the_command_line() -> None:
    long = _python(5, "x" * 300)
    sortie = json.loads(formater_sortie([long]))
    assert sortie == [{"pid": 5, "nom": "python.exe", "debut": "x" * 100}]


def test_main_reads_stdin_and_prints_selection() -> None:
    entree = json.dumps(
        {
            "processus": [
                {"pid": 1, "nom": "python.exe", "commande": "uvicorn tessera.main:app"},
                {"pid": 2, "nom": "python.exe", "commande": "uvicorn app.main:app"},
            ],
            "ecoutes": {},
        }
    )
    sortie = io.StringIO()
    code = main([RACINE], io.BytesIO(entree.encode("utf-8")), sortie)
    assert code == 0
    assert [p["pid"] for p in json.loads(sortie.getvalue())] == [1]


def test_main_without_root_argument_fails() -> None:
    sortie = io.StringIO()
    assert main([], io.BytesIO(b"{}"), sortie) == 2
    assert sortie.getvalue() == ""
