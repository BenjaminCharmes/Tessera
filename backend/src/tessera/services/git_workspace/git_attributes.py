"""Déclaration locale du pilote de fusion `union` — ticket-418.

Le journal du pipeline ne fait qu'ajouter des lignes : deux branches qui y
écrivent chacune la leur doivent fusionner sans conflit. Git sait le faire
nativement (`merge=union`), à condition de le déclarer.

La déclaration va dans `.git/info/attributes`, pas dans `.gitattributes` : même
raison que pour `.git/info/exclude` (ADR-021). `.gitattributes` est versionné,
et l'écrire dans le dépôt d'un client y laisserait une trace de Tessera.
"""
from pathlib import Path

_DRIVER = "merge=union"


def union_attribute_line(journal: str) -> str:
    """The attributes line that makes git merge ``journal`` as a union."""
    return f"{journal} {_DRIVER}"


def declare_union_merge(attributes: Path, journal: str) -> bool:
    """Ensure ``attributes`` declares ``journal`` with the union merge driver.

    Idempotent: a line already present (whatever the spacing) is never added
    twice, and whatever else the user wrote in the file is left untouched.
    Returns True when the file was modified.
    """
    ligne = union_attribute_line(journal)
    existant = attributes.read_text(encoding="utf-8") if attributes.is_file() else ""
    for presente in existant.splitlines():
        if presente.split() == ligne.split():
            return False
    attributes.parent.mkdir(parents=True, exist_ok=True)
    separateur = "" if not existant or existant.endswith("\n") else "\n"
    attributes.write_text(f"{existant}{separateur}{ligne}\n", encoding="utf-8")
    return True
