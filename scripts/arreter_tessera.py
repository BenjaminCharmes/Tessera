"""Select the processes `tessera.ps1 stop` may kill — ticket-423.

The old filter killed every `python.exe` mentioning uvicorn and every `node.exe`
mentioning vite, which also took down other applications served on the machine.
Only Tessera's own processes are selected here:

- a `python.exe` whose command line carries `tessera.main:app` (the backend, or
  the `spawn_main` worker that descends from it);
- a `node.exe` running vite from this repository's `frontend/` folder, or
  listening on the frontend port;
- whatever process listens on the backend port, whatever its name, so the
  orphan `--reload` worker (ticket-056) is caught even without `tessera.main`.

The PowerShell launcher lists the processes and the listening ports, pipes them
as JSON on stdin, and kills what this script prints back as JSON.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import IO, Mapping, Sequence

BACKEND_PORT = 8100
FRONTEND_PORT = 5173
BACKEND_MARKER = "tessera.main:app"
EXCERPT_LENGTH = 100


@dataclass(frozen=True)
class Processus:
    """A running process as seen by the launcher."""

    pid: int
    nom: str
    commande: str


def _normaliser(texte: str) -> str:
    """Lower-case a path or command line and unify the separators."""
    return texte.replace("\\", "/").lower()


def _est_python(processus: Processus) -> bool:
    return processus.nom.lower() == "python.exe"


def _est_node(processus: Processus) -> bool:
    return processus.nom.lower() == "node.exe"


def _vise_dossier(commande: str, dossier: str) -> bool:
    """Tell whether a command line names `dossier` itself or a path under it."""
    cible = _normaliser(dossier).rstrip("/") + "/"
    return cible in _normaliser(commande) + "/"


def _est_backend(processus: Processus) -> bool:
    return _est_python(processus) and BACKEND_MARKER in processus.commande


def _est_frontend(
    processus: Processus, dossier_frontend: str, ecoute_frontend: frozenset[int]
) -> bool:
    if not _est_node(processus) or "vite" not in processus.commande.lower():
        return False
    if processus.pid in ecoute_frontend:
        return True
    return _vise_dossier(processus.commande, dossier_frontend)


def select_processus_tessera(
    processus: Sequence[Processus],
    racine: str,
    ecoutes: Mapping[int, Sequence[int]],
) -> list[Processus]:
    """Return the processes belonging to Tessera, in input order.

    `ecoutes` maps a port to the PIDs listening on it.
    """
    dossier_frontend = racine.rstrip("\\/") + "/frontend"
    ecoute_backend = frozenset(ecoutes.get(BACKEND_PORT, ()))
    ecoute_frontend = frozenset(ecoutes.get(FRONTEND_PORT, ()))
    return [
        p
        for p in processus
        if p.pid in ecoute_backend
        or _est_backend(p)
        or _est_frontend(p, dossier_frontend, ecoute_frontend)
    ]


def lire_entree(brut: str) -> tuple[list[Processus], dict[int, list[int]]]:
    """Parse the launcher's JSON: `{"processus": [...], "ecoutes": {"8100": [...]}}`."""
    donnees = json.loads(brut)
    processus = [
        Processus(
            pid=int(p["pid"]),
            nom=str(p.get("nom") or ""),
            commande=str(p.get("commande") or ""),
        )
        for p in donnees.get("processus", [])
    ]
    ecoutes = {
        int(port): [int(pid) for pid in pids]
        for port, pids in donnees.get("ecoutes", {}).items()
    }
    return processus, ecoutes


def formater_sortie(selection: Sequence[Processus]) -> str:
    """Serialize the selection with a short command-line excerpt per process."""
    return json.dumps(
        [
            {"pid": p.pid, "nom": p.nom, "debut": p.commande[:EXCERPT_LENGTH]}
            for p in selection
        ]
    )


def main(argv: Sequence[str], entree: IO[bytes], sortie: IO[str]) -> int:
    """Read the launcher's JSON from `entree`, print the selection to `sortie`."""
    if len(argv) != 1:
        sys.stderr.write("usage: arreter_tessera.py <racine du depot>\n")
        return 2
    processus, ecoutes = lire_entree(entree.read().decode("utf-8"))
    sortie.write(formater_sortie(select_processus_tessera(processus, argv[0], ecoutes)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdin.buffer, sys.stdout))
