"""Reading and rewriting a raw ticket in place — ticket-855, ADR-080.

A raw ticket is a `todo` ticket whose only criterion is the line a report leaves
(`LIGNE_CRITERES`). Rewriting keeps the file, hence the number and the folder,
and every section of the body but the criteria: the `## Signalement` block is
never touched. Nothing here launches a ticket.
"""
import re
from pathlib import Path

import frontmatter

from tessera.services.providers.signaler import LIGNE_CRITERES
from tessera.services.supervision.superviseur_tri_gardes import PlanTri

TITRE_CRITERES = "critères d'acceptation"
TITRE_HORS_PORTEE = "ce que ça ne fait pas"
TITRE_SIGNALEMENT = "signalement"
_TEXTE_PLACEHOLDER = LIGNE_CRITERES.removeprefix("- [ ]").strip()
_CASE = re.compile(r"^\s*- \[[ xX]\]\s*(.*?)\s*$")
_TITRE = re.compile(r"^##\s+(.*?)\s*$")


def decouper(corps: str) -> list[tuple[str, str]]:
    """The body as `(title, text)` sections, title casefolded; the preamble has title `""`."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for ligne in corps.splitlines():
        trouve = _TITRE.match(ligne)
        if trouve is not None:
            titre = trouve.group(1).replace("’", "'").casefold()
            sections.append((titre, [ligne]))
        else:
            sections[-1][1].append(ligne)
    return [(titre, "\n".join(lignes).strip()) for titre, lignes in sections]


def section(corps: str, titre: str) -> str | None:
    """The text of the section called `titre` (casefolded), heading included, or `None`."""
    return next((texte for t, texte in decouper(corps) if t == titre), None)


def est_brut(corps: str) -> bool:
    """Whether the criteria of `corps` are the single placeholder line of a raw report."""
    criteres = section(corps, TITRE_CRITERES)
    if criteres is None:
        return False
    cases = [m.group(1) for ligne in criteres.splitlines() if (m := _CASE.match(ligne))]
    return cases == [_TEXTE_PLACEHOLDER]


def _bloc_criteres(plan: PlanTri) -> str:
    lignes = [f"- [ ] {critere}" for critere in plan.criteres]
    return "\n".join(["## Critères d'acceptation", "", *lignes])


def nouveau_corps(corps: str, plan: PlanTri) -> str:
    """`corps` with its criteria replaced by the plan's, and the limits appended if given."""
    blocs: list[str] = []
    for titre, texte in decouper(corps):
        blocs.append(_bloc_criteres(plan) if titre == TITRE_CRITERES else texte)
    if plan.hors_portee and section(corps, TITRE_HORS_PORTEE) is None:
        blocs.append(f"## Ce que ça ne fait pas\n\n{plan.hors_portee}")
    return "\n\n".join(bloc for bloc in blocs if bloc) + "\n"


def reecrire_si_brut(fichier: Path, plan: PlanTri) -> bool:
    """Rewrite the ticket file in place; `False`, untouched, when it is missing or not raw."""
    if not fichier.is_file():
        return False
    post = frontmatter.loads(fichier.read_text(encoding="utf-8"))
    if not est_brut(str(post.content)):
        return False
    post.metadata.update(
        title=plan.titre, type=plan.type.value, priority=plan.priorite.value,
        depends_on=list(plan.depends_on), status="todo",
    )
    post.content = nouveau_corps(str(post.content), plan)
    fichier.write_text(frontmatter.dumps(post), encoding="utf-8", newline="\n")
    return True
