"""Les arbres de processus que la sonde décrit — ticket-416.

Un service lance souvent des enfants (rechargeur, `npm` puis `node`) : sa
mémoire est celle de tout l'arbre, et un processus déjà compté dans un arbre
ne l'est pas une seconde fois.
"""
from tessera.services.sonde_systeme import InfoProcessus

Enfants = dict[int, list[int]]


def enfants_par_parent(procs: dict[int, InfoProcessus]) -> Enfants:
    enfants: Enfants = {}
    for pid, info in procs.items():
        enfants.setdefault(info.ppid, []).append(pid)
    return enfants


def arbre(pid: int, enfants: Enfants) -> set[int]:
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


def memoire_mo(membres: set[int], procs: dict[int, InfoProcessus]) -> float:
    total = sum(procs[p].memoire_mo for p in membres if p in procs)
    return round(total, 1)
