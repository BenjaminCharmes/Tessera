"""Les apps de projet qui tournent sur la machine — ticket-416.

Deux origines. `tessera` : un service que le registre a lancé, en mémoire du
backend. `externe` : un processus lancé à la main qui écoute un port qu'un
projet **déclare** (commande de service, `vite.config.ts`). Un processus
n'est compté qu'une fois, même quand il écoute deux ports ou qu'il est le
descendant d'un service `tessera`.
"""
import asyncio
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from tessera.services.ports_declares import ports_du_projet
from tessera.services.process_registry import PROCESS_REGISTRY, Service
from tessera.services.project_loader import list_projects
from tessera.services.sonde_systeme import InfoProcessus, SondeSysteme

#: Le backend de Tessera et son frontend : l'IDE ne s'inventorie pas lui-même.
#: Les mêmes numéros existent dans `doctor.py` ; les centraliser dépasse
#: ce ticket.
PORTS_DE_TESSERA = frozenset({8100, 5173})

Enfants = dict[int, list[int]]


class AppEnCours(BaseModel):
    """One running app of a project."""

    project_id: str
    project_name: str
    nom: str
    origine: Literal["tessera", "externe"]
    pid: int
    ports: list[int]
    demarre_a: str | None
    memoire_mo: float


def _enfants(procs: dict[int, InfoProcessus]) -> Enfants:
    enfants: Enfants = {}
    for pid, info in procs.items():
        enfants.setdefault(info.ppid, []).append(pid)
    return enfants


def _arbre(pid: int, enfants: Enfants) -> set[int]:
    """Le pid et toute sa descendance."""
    vus: set[int] = set()
    a_voir = [pid]
    while a_voir:
        courant = a_voir.pop()
        if courant in vus:
            continue
        vus.add(courant)
        a_voir.extend(enfants.get(courant, []))
    return vus


def _memoire_mo(arbre: set[int], procs: dict[int, InfoProcessus]) -> float:
    total = sum(procs[p].memoire_mo for p in arbre if p in procs)
    return round(total, 1)


def _app_tessera(
    service: Service,
    pid: int,
    racine: Path,
    nom_du_projet: str,
    procs: dict[int, InfoProcessus],
    arbre: set[int],
    ecouteurs: dict[int, int],
) -> AppEnCours | None:
    """Une entrée `tessera`, ou `None` si c'est l'IDE lui-même."""
    declares = ports_du_projet(racine)
    siens = {p for p, nom in declares.items() if nom == service.nom}
    ecoutes = {p for p, pid in ecouteurs.items() if pid in arbre} & declares.keys()
    bruts = siens | ecoutes
    ports = sorted(bruts - PORTS_DE_TESSERA)
    if bruts and not ports:
        return None
    return AppEnCours(
        project_id=service.project_id,
        project_name=nom_du_projet,
        nom=service.nom,
        origine="tessera",
        pid=pid,
        ports=ports,
        demarre_a=service.demarre_a.isoformat(),
        memoire_mo=_memoire_mo(arbre, procs),
    )


def _app_externe(
    project_id: str,
    nom_du_projet: str,
    nom: str,
    pid: int,
    procs: dict[int, InfoProcessus],
    enfants: Enfants,
) -> AppEnCours:
    info = procs.get(pid)
    return AppEnCours(
        project_id=project_id,
        project_name=nom_du_projet,
        nom=nom,
        origine="externe",
        pid=pid,
        ports=[],
        demarre_a=info.demarre_a.isoformat() if info and info.demarre_a else None,
        memoire_mo=_memoire_mo(_arbre(pid, enfants), procs),
    )


def _apps_externes(
    projets: dict[str, str],
    workspace: Path,
    ecouteurs: dict[int, int],
    procs: dict[int, InfoProcessus],
    enfants: Enfants,
    pris: set[int],
) -> list[AppEnCours]:
    par_pid: dict[int, AppEnCours] = {}
    for project_id, nom_du_projet in projets.items():
        for port, nom in ports_du_projet(workspace / project_id).items():
            pid = ecouteurs.get(port)
            if port in PORTS_DE_TESSERA or pid is None or pid in pris:
                continue
            if pid not in par_pid:
                par_pid[pid] = _app_externe(
                    project_id, nom_du_projet, nom, pid, procs, enfants
                )
            par_pid[pid].ports.append(port)
    for app in par_pid.values():
        app.ports.sort()
    return list(par_pid.values())


async def inventaire(sonde: SondeSysteme, workspace: Path) -> list[AppEnCours]:
    """Every app of every project that is alive right now, each counted once."""
    ecouteurs, procs = await asyncio.gather(sonde.ecouteurs(), sonde.processus())
    projets = await asyncio.to_thread(list_projects, workspace)
    noms = {p.id: p.name for p in projets}
    enfants = _enfants(procs)

    apps: list[AppEnCours] = []
    pris: set[int] = set()
    for service in PROCESS_REGISTRY.vivants():
        if service.pid is None:
            continue
        arbre = _arbre(service.pid, enfants)
        pris |= arbre
        app = _app_tessera(
            service,
            service.pid,
            workspace / service.project_id,
            noms.get(service.project_id, service.project_id),
            procs,
            arbre,
            ecouteurs,
        )
        if app is not None:
            apps.append(app)
    apps.extend(_apps_externes(noms, workspace, ecouteurs, procs, enfants, pris))
    return sorted(apps, key=lambda a: (a.project_id, a.nom))
