"""Mechanical answers to the two Prisma collisions a delivery rebase meets.

Two tickets that each add a model to ``schema.prisma``, or each add a
migration of the same number, are not a real conflict: nothing is edited on
both sides. Everything here is a pure function over text and paths; the git
plumbing stays in ``GitWorkspaceService``.
"""
import re
from collections.abc import Collection
from dataclasses import dataclass, field

_DEBUT_BLOC = re.compile(r"^\s*(\w+)\s+(\w+)\s*\{")
_CHAINE = re.compile(r'"(?:[^"\\]|\\.)*"')
_TYPES_AJOUTABLES = frozenset({"model", "enum", "type", "view"})
_DOSSIER_MIGRATION = re.compile(r"^(?:.*/)?prisma/migrations/[^/]+$")
_PREFIXE = re.compile(r"^(\d+)_(.*)$")
# A timestamp prefix (20261015093000_x) is a point in time, not a counter.
_LARGEUR_HORODATAGE = 12

_CleBloc = tuple[str, str]


@dataclass
class _Schema:
    """A schema cut into its top-level blocks, in file order."""

    blocs: dict[_CleBloc, str] = field(default_factory=dict)
    orphelins: list[str] = field(default_factory=list)


def _profondeur(ligne: str) -> int:
    """Net braces opened on a line, ignoring strings and ``//`` comments."""
    nu = _CHAINE.sub('""', ligne).split("//", 1)[0]
    return nu.count("{") - nu.count("}")


def _fin_du_bloc(lignes: list[str], debut: int) -> int | None:
    """Index of the line closing the block opened at ``debut``, if it closes."""
    profondeur = 0
    for i in range(debut, len(lignes)):
        profondeur += _profondeur(lignes[i])
        if profondeur < 0:
            return None
        if profondeur == 0:
            return i
    return None


def _decouper(texte: str) -> _Schema | None:
    """Cut a schema into blocks; None when it cannot be read unambiguously."""
    schema = _Schema()
    lignes = texte.splitlines()
    commentaires: list[str] = []
    i = 0
    while i < len(lignes):
        ligne = lignes[i]
        debut = _DEBUT_BLOC.match(ligne)
        if debut is None:
            i += 1
            if ligne.strip().startswith("//"):
                # Un commentaire collé à un bloc le suit : il part avec lui.
                commentaires.append(ligne)
                continue
            schema.orphelins.extend(commentaires)
            commentaires = []
            if ligne.strip():
                schema.orphelins.append(ligne)
            continue
        fin = _fin_du_bloc(lignes, i)
        cle = (debut.group(1), debut.group(2))
        if fin is None or cle in schema.blocs:
            return None
        schema.blocs[cle] = "\n".join(commentaires + lignes[i : fin + 1])
        commentaires = []
        i = fin + 1
    schema.orphelins.extend(commentaires)
    return schema


def _blocs_ajoutes(
    base: _Schema, ticket: _Schema, ancetre: _Schema
) -> list[str] | None:
    """Blocks the ticket adds, or None when either side touched an old one."""
    for cle, texte in ancetre.blocs.items():
        if base.blocs.get(cle) != texte or ticket.blocs.get(cle) != texte:
            return None
    ajoutes: list[str] = []
    for cle, texte in ticket.blocs.items():
        if cle in ancetre.blocs:
            continue
        if cle in base.blocs:
            if base.blocs[cle] != texte:
                return None
            continue
        if cle[0] not in _TYPES_AJOUTABLES:
            return None
        ajoutes.append(texte)
    return ajoutes


def fusionner_ajouts(base: str, ticket: str, ancetre: str) -> str | None:
    """Keep both sides of a schema conflict that only adds whole blocks.

    ``base`` is the side being rebased onto, ``ticket`` the branch, ``ancetre``
    their common ancestor. The result is the base followed by the blocks the
    ticket adds, each one cut out whole so that its closing brace is its own:
    the brace two adjacent additions would otherwise share is never at stake.

    Returns None — the caller hands the file to the resolver — as soon as one
    side edits or removes a block that existed, both sides add a block of the
    same name with different content, or anything outside a block differs.
    """
    s_base, s_ticket, s_ancetre = _decouper(base), _decouper(ticket), _decouper(ancetre)
    if s_base is None or s_ticket is None or s_ancetre is None:
        return None
    if not s_base.orphelins == s_ticket.orphelins == s_ancetre.orphelins:
        return None
    ajoutes = _blocs_ajoutes(s_base, s_ticket, s_ancetre)
    if ajoutes is None:
        return None
    fin_de_ligne = "\r\n" if "\r\n" in base else "\n"
    corps = base.rstrip("\r\n") + "".join("\n\n" + bloc for bloc in ajoutes)
    return corps.replace("\r\n", "\n").replace("\n", fin_de_ligne) + fin_de_ligne


def _numero(nom: str) -> int | None:
    """Counter prefix of a migration folder; None for a timestamp or no prefix."""
    trouve = _PREFIXE.match(nom)
    if trouve is None or len(trouve.group(1)) >= _LARGEUR_HORODATAGE:
        return None
    return int(trouve.group(1))


def _renumeroter(nom: str, numero: int) -> str:
    """``0005_x`` → ``0006_x``, keeping the width of the zero padding."""
    trouve = _PREFIXE.match(nom)
    if trouve is None:
        return nom
    return f"{numero:0{len(trouve.group(1))}d}_{trouve.group(2)}"


def _plan_d_un_dossier(
    parent: str, deja_en_base: set[str], presents: set[str]
) -> list[tuple[str, str]]:
    """Renames for one ``prisma/migrations`` folder.

    The first ticket migration whose number the base already uses is moved to
    the next free one — and so is every later ticket migration, so that the
    order the ticket wrote them in survives.
    """
    numeros_base = {_numero(nom) for nom in deja_en_base}
    du_ticket = sorted(
        (nom for nom in presents - deja_en_base if _numero(nom) is not None),
        key=lambda nom: (_numero(nom) or 0, nom),
    )
    premier = next(
        (i for i, nom in enumerate(du_ticket) if _numero(nom) in numeros_base), None
    )
    if premier is None:
        return []
    libre = max(n for n in map(_numero, presents) if n is not None) + 1
    plan: list[tuple[str, str]] = []
    for offset, nom in enumerate(du_ticket[premier:]):
        plan.append((f"{parent}/{nom}", f"{parent}/{_renumeroter(nom, libre + offset)}"))
    return plan


def planifier_renumerotation(
    base: Collection[str], presents: Collection[str]
) -> list[tuple[str, str]]:
    """Which ticket migration folders to rename, as ``(old path, new path)``.

    ``base`` and ``presents`` are the directories of the base and of the
    rebased branch (which holds the base's too); the ticket's own are the
    difference. A collision is a number carried by a ticket folder and by a
    base folder of another name. A timestamp prefix (12 digits or more) is
    never renamed: two migrations written independently do not share one.
    """
    par_parent: dict[str, tuple[set[str], set[str]]] = {}
    for indice, dossiers in enumerate((base, presents)):
        for chemin in dossiers:
            if _DOSSIER_MIGRATION.match(chemin):
                parent, _, nom = chemin.rpartition("/")
                par_parent.setdefault(parent, (set(), set()))[indice].add(nom)
    plan: list[tuple[str, str]] = []
    for parent in sorted(par_parent):
        deja, presents_ici = par_parent[parent]
        plan.extend(_plan_d_un_dossier(parent, deja, presents_ici))
    return plan
