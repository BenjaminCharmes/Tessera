"""Les apps de projet qui tournent sur la machine — ticket-416.

Deux origines. `tessera` : un service que le registre a lancé, en mémoire du
backend. `externe` : un processus lancé à la main qui écoute un port qu'un
projet **déclare** (commande de service, `vite.config.ts`), ou un service
déclaré sans port que sa ligne de commande désigne (ticket-438). Un processus
n'est compté qu'une fois, même quand il écoute deux ports ou qu'il est le
descendant d'un service `tessera`.

Une app `externe` n'est attribuée à un projet que si son processus lui
appartient (`attribution_processus`, ticket-435) ; un port déclaré occupé par
un étranger ressort en avertissement, sans pid.
"""
import asyncio
from pathlib import Path

from tessera.models.inventaire import AppEnCours, Inventaire, PortOccupe
from tessera.services.arbre_de_processus import Enfants
from tessera.services.arbre_de_processus import arbre as _arbre
from tessera.services.arbre_de_processus import enfants_par_parent as _enfants
from tessera.services.arbre_de_processus import memoire_mo as _memoire_mo
from tessera.services.attribution_processus import appartient_au_projet
from tessera.services.ports_declares import ports_du_projet
from tessera.services.process_registry import PROCESS_REGISTRY, Service
from tessera.services.project_loader import fait_tourner_l_ide, list_projects
from tessera.services.services_sans_port import processus_sans_port
from tessera.services.sonde_systeme import InfoProcessus, SondeSysteme

#: Le backend de Tessera et son frontend : l'IDE ne s'inventorie pas lui-même.
#: Les mêmes numéros existent dans `doctor.py` ; les centraliser dépasse
#: ce ticket.
PORTS_DE_TESSERA = frozenset({8100, 5173})


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


def _apps_sans_port(
    projets: dict[str, str],
    workspace: Path,
    procs: dict[int, InfoProcessus],
    enfants: Enfants,
    deja: set[int],
) -> list[AppEnCours]:
    """Les services déclarés sans port, trouvés par leur ligne de commande."""
    trouvees: list[AppEnCours] = []
    for project_id, nom_du_projet in projets.items():
        racine = workspace / project_id
        if fait_tourner_l_ide(racine):
            continue
        for nom, pid in processus_sans_port(racine, procs, deja):
            deja.add(pid)
            trouvees.append(
                _app_externe(project_id, nom_du_projet, nom, pid, procs, enfants)
            )
    return trouvees


def _apps_externes(
    projets: dict[str, str],
    workspace: Path,
    ecouteurs: dict[int, int],
    procs: dict[int, InfoProcessus],
    enfants: Enfants,
    pris: set[int],
) -> tuple[list[AppEnCours], list[PortOccupe]]:
    """Les apps lancées à la main, et les ports déclarés pris par un étranger."""
    par_pid, etrangers = _apps_par_port(
        projets, workspace, ecouteurs, procs, enfants, pris
    )
    # Ce qui est déjà compté, avec sa descendance, ne l'est pas une seconde fois.
    deja = set(pris)
    for pid in par_pid:
        deja |= _arbre(pid, enfants)
    sans_port = _apps_sans_port(projets, workspace, procs, enfants, deja)
    return [*par_pid.values(), *sans_port], etrangers


def _apps_par_port(
    projets: dict[str, str],
    workspace: Path,
    ecouteurs: dict[int, int],
    procs: dict[int, InfoProcessus],
    enfants: Enfants,
    pris: set[int],
) -> tuple[dict[int, AppEnCours], list[PortOccupe]]:
    par_pid: dict[int, AppEnCours] = {}
    etrangers: list[PortOccupe] = []
    for project_id, nom_du_projet in projets.items():
        racine = workspace / project_id
        # Le projet qui fait tourner l'IDE : ses ports sont ceux de Tessera.
        if fait_tourner_l_ide(racine):
            continue
        for port, nom in ports_du_projet(racine).items():
            pid = ecouteurs.get(port)
            if port in PORTS_DE_TESSERA or pid is None or pid in pris:
                continue
            if not appartient_au_projet(pid, racine, procs):
                etrangers.append(PortOccupe.de(project_id, nom_du_projet, nom, port))
                continue
            if pid not in par_pid:
                par_pid[pid] = _app_externe(
                    project_id, nom_du_projet, nom, pid, procs, enfants
                )
            par_pid[pid].ports.append(port)
    for app in par_pid.values():
        app.ports.sort()
    return par_pid, etrangers


async def inventaire(sonde: SondeSysteme, workspace: Path) -> list[AppEnCours]:
    """Every app of every project that is alive right now, each counted once."""
    return (await inventaire_complet(sonde, workspace)).apps


async def inventaire_complet(sonde: SondeSysteme, workspace: Path) -> Inventaire:
    """The apps, plus the declared ports that a foreign program occupies."""
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
    externes, etrangers = _apps_externes(
        noms, workspace, ecouteurs, procs, enfants, pris
    )
    apps.extend(externes)
    return Inventaire(
        apps=sorted(apps, key=lambda a: (a.project_id, a.nom)),
        ports_occupes=sorted(etrangers, key=lambda o: (o.project_id, o.port)),
    )
