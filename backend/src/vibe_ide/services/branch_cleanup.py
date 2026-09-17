"""Nettoyage des branches créées par vibe-ide — ticket-070.

Chaque run crée `ticket-XXX-…`, chaque session de chat `chat/<horodatage>`, et
rien ne les retirait jamais. Après une seule session d'usage réel, `tmp` en
portait déjà deux, mortes, identiques à `main`. Sur un dépôt client, cette
accumulation devient visible.

Supprimer une branche est irréversible, et sur le dépôt de quelqu'un d'autre
c'est le genre d'automatisme qu'on regrette. D'où quatre garde-fous, et un plan
qu'on peut lire avant d'agir :

1. **Seulement ce que vibe-ide a créé** — `ticket-*` et `chat/*`. Le reste
   appartient à l'utilisateur.
2. **Jamais la branche courante.**
3. **Jamais une branche poussée** : elle existe ailleurs, et la retirer ici
   laisserait un état incohérent entre le local et le distant.
4. **Jamais une branche qui porte du travail absent de la base.** Un run rejeté
   commite quand même (ADR-018) : sa branche est le seul exemplaire de ce
   travail.

Le quatrième est le plus important. Une branche dont tous les commits sont déjà
dans la base ne contient rien qui puisse être perdu — c'est la seule condition
sous laquelle une suppression est sans conséquence.
"""
import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

#: Ce que vibe-ide crée, et donc ce qu'il peut retirer.
_PREFIXES = ("ticket-", "chat/")


class PlanDeNettoyage(BaseModel):
    """Ce qui peut partir, et pourquoi le reste demeure."""

    nettoyables: list[str] = Field(default_factory=list)
    #: (branche, raison) — la raison est destinée à être lue par l'utilisateur.
    conservees: list[tuple[str, str]] = Field(default_factory=list)


async def _git(project_path: Path, *args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", errors="replace")


async def _branche_courante(project_path: Path) -> str:
    code, sortie = await _git(project_path, "symbolic-ref", "--short", "HEAD")
    return sortie.strip() if code == 0 else ""


async def _base(project_path: Path, courante: str) -> str:
    """La branche de référence : `main` si elle existe, sinon la courante."""
    code, _ = await _git(project_path, "rev-parse", "--verify", "--quiet", "main")
    return "main" if code == 0 else courante


async def plan_de_nettoyage(project_path: Path) -> PlanDeNettoyage:
    """Ce qu'on peut supprimer sans rien perdre, et ce qu'on garde, avec la raison."""
    code, sortie = await _git(
        project_path, "branch", "--format=%(refname:short)%09%(upstream)"
    )
    if code != 0:
        return PlanDeNettoyage()

    courante = await _branche_courante(project_path)
    base = await _base(project_path, courante)
    plan = PlanDeNettoyage()

    for ligne in sortie.splitlines():
        if not ligne.strip():
            continue
        nom, _, upstream = ligne.partition("\t")
        nom = nom.strip()

        if not nom.startswith(_PREFIXES):
            continue
        if nom == courante:
            plan.conservees.append((nom, "c'est la branche courante"))
            continue
        if upstream.strip():
            plan.conservees.append((nom, "elle a été poussée sur un dépôt distant"))
            continue

        fusionnee, _ = await _git(
            project_path, "merge-base", "--is-ancestor", nom, base
        )
        if fusionnee != 0:
            plan.conservees.append((nom, "porte du travail absent de la base"))
            continue

        plan.nettoyables.append(nom)

    return plan


async def supprimer_branches(project_path: Path, demandees: list[str]) -> list[str]:
    """Supprime les branches demandées **qui figurent au plan**, et rend la liste.

    Le plan est recalculé ici plutôt que reçu du client : entre l'affichage et
    le clic, un run a pu commiter sur l'une de ces branches. Se fier à une liste
    envoyée par l'interface reviendrait à supprimer sur la foi d'un état périmé.
    """
    autorisees = set((await plan_de_nettoyage(project_path)).nettoyables)
    supprimees: list[str] = []

    for nom in demandees:
        if nom not in autorisees:
            _logger.info("branche_hors_plan", extra={"branch": nom})
            continue
        code, _ = await _git(project_path, "branch", "-D", nom)
        if code == 0:
            supprimees.append(nom)

    return supprimees
