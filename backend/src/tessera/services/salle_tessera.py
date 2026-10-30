"""Assemble la salle des serveurs de Tessera — ticket-726.

La salle ne lit que ce que le backend sait déjà : la sonde système de
l'inventaire (ticket-416) pour ses propres processus, le disjoncteur d'Ollama
(ticket-380), le registre des runs (ADR-041), le CIWatcher (ADR-051), la fin de
`tessera.log`, la taille de la base et le dossier des worktrees (ADR-056).

Le journal est réduit à son événement : un message de log peut porter un chemin
ou une commande, et la salle n'en a pas besoin pour dire « ça tourne ».
"""
import json
import os
from datetime import datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any

from tessera.models.salle_tessera import (
    EtatOllama,
    LigneDeJournal,
    ProcessusDeTessera,
    RunVivant,
    SalleTessera,
)
from tessera.services.arbre_de_processus import arbre, enfants_par_parent, memoire_mo
from tessera.services.sonde_systeme import InfoProcessus, SondeSysteme

#: Le port du Vite qui sert le frontend (`frontend/vite.config.ts`, `devUrl` de Tauri).
PORT_DU_FRONTEND = 5173
#: Lignes de journal montrées, et octets relus en fin de fichier pour les trouver.
LIGNES_DU_JOURNAL = 6
_FIN_LUE = 32_000
_SUIVANTS = 3


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment is not None else None


def _processus(
    nom: str, port: int, pid: int | None, procs: dict[int, InfoProcessus], avec_enfants: bool
) -> ProcessusDeTessera:
    info = procs.get(pid) if pid is not None else None
    if pid is None or info is None:
        return ProcessusDeTessera(nom=nom, port=port, pid=pid, memoire_mo=0.0, demarre_a=None)
    # Le backend ne compte que lui-même : ses enfants sont les agents des runs.
    membres = arbre(pid, enfants_par_parent(procs)) if avec_enfants else {pid}
    return ProcessusDeTessera(
        nom=nom, port=port, pid=pid, memoire_mo=memoire_mo(membres, procs), demarre_a=_iso(info.demarre_a)
    )


async def processus_de_tessera(sonde: SondeSysteme) -> list[ProcessusDeTessera]:
    """The backend (this process) and the Vite that serves the frontend."""
    ecouteurs = await sonde.ecouteurs()
    procs = await sonde.processus()
    moi = os.getpid()
    port_backend = next((port for port, pid in ecouteurs.items() if pid == moi), 0)
    return [
        _processus("backend", port_backend, moi, procs, avec_enfants=False),
        _processus("frontend", PORT_DU_FRONTEND, ecouteurs.get(PORT_DU_FRONTEND), procs, avec_enfants=True),
    ]


def runs_vivants(instantane: list[dict[str, Any]]) -> list[RunVivant]:
    """The registry's open runs, with the next tickets of their queue."""
    return [
        RunVivant(
            project_id=str(run.get("project_id", "")),
            ticket_id=run.get("ticket_id"),
            agent=run.get("agent"),
            etape=run.get("etape"),
            file_index=int(run.get("file_index") or 0),
            file_total=int(run.get("file_total") or 0),
            suivants=[str(t) for t in (run.get("file_restants") or [])][:_SUIVANTS],
        )
        for run in instantane
    ]


def _ligne(brute: str) -> LigneDeJournal | None:
    try:
        donnees = json.loads(brute)
    except ValueError:
        return None
    if not isinstance(donnees, dict) or not isinstance(donnees.get("message"), str):
        return None
    def texte(cle: str) -> str | None:
        valeur = donnees.get(cle)
        return valeur if isinstance(valeur, str) else None

    return LigneDeJournal(
        ts=texte("ts"),
        niveau=texte("level") or "INFO",
        evenement=donnees["message"],
        ticket_id=texte("ticket_id"),
        role=texte("role"),
    )


def fin_du_journal(chemin: Path, nombre: int = LIGNES_DU_JOURNAL) -> list[LigneDeJournal]:
    """The last `nombre` readable lines of the log ; none when the file is missing."""
    try:
        with chemin.open("rb") as fichier:
            fichier.seek(0, os.SEEK_END)
            debut = max(0, fichier.tell() - _FIN_LUE)
            fichier.seek(debut)
            fin = fichier.read().decode("utf-8", "replace")
    except OSError:
        return []
    brutes = fin.splitlines()
    # Lu depuis le milieu du fichier, la première ligne est coupée : on l'écarte.
    lignes = [_ligne(brute) for brute in (brutes[1:] if debut > 0 else brutes)]
    return [l for l in lignes if l is not None][-nombre:]


def taille_mo(chemin: Path) -> float:
    try:
        return round(chemin.stat().st_size / 1_048_576, 1)
    except OSError:
        return 0.0


def ci_en_attente(projets: list[str], en_attente: Callable[[str], tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    """Each project's tickets the CIWatcher waits on, projects with none left out."""
    return {p: tuple(sorted(t)) for p in projets if (t := en_attente(p))}


def nombre_de_worktrees(racine: Path) -> int:
    """Run worktrees live at `<racine>/<projet>/<ticket>` (ADR-056)."""
    if not racine.is_dir():
        return 0
    return sum(1 for projet in racine.iterdir() if projet.is_dir() for wt in projet.iterdir() if wt.is_dir())


async def salle_tessera(
    sonde: SondeSysteme,
    *,
    instantane: list[dict[str, Any]],
    ci_en_attente: dict[str, tuple[str, ...]],
    ollama_url: str,
    refroidissement_s: float | None,
    journal: Path,
    base: Path,
    worktrees: Path,
) -> SalleTessera:
    """The room, assembled from facts read now."""
    return SalleTessera(
        processus=await processus_de_tessera(sonde),
        ollama=EtatOllama(url=ollama_url, refroidissement_s=refroidissement_s),
        runs=runs_vivants(instantane),
        ci_en_attente={p: list(t) for p, t in ci_en_attente.items()},
        journal=fin_du_journal(journal),
        base_mo=taille_mo(base),
        worktrees=nombre_de_worktrees(worktrees),
    )
