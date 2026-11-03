"""Ce que le lot de documentation peut faire du CLAUDE.md d'un projet — t.244.

Le CLAUDE.md décrit ce que le produit fait et ne fait pas, pour les agents. Un
ticket qui rend une phrase fausse laisse une consigne fausse, chargée dans
chaque session, jusqu'à ce que quelqu'un la relise. Mais chaque ligne ajoutée
concurrence toutes les autres pour l'attention du modèle : un agent qui y
ajoute à chaque lot produit un fichier qu'on finit par ignorer.

Trois bornes, donc. Le projet le déclare (`pipeline.doc_claude_md`). Seul
`doc-technique` le reçoit : c'est une consigne pour agents, pas un guide. Et le
fichier ne franchit pas son budget — déjà au-delà, il ne peut que raccourcir.

« CLAUDE.md » désigne toujours celui **du projet**. Le projet bootstrap
documente à la racine du dépôt (ADR-028), où vit un autre CLAUDE.md que la
règle 5 réserve à un ticket explicite.
"""
from pathlib import Path

from tessera.services.documentation_base import EditionRefusee

#: Le nom sous lequel l'agent désigne le CLAUDE.md du projet.
NOM = "CLAUDE.md"

#: AGENTS.md suit le même chemin que CLAUDE.md : même déclaration, même rôle,
#: même budget (ticket-724). Il vit à la racine de la documentation.
NOM_AGENTS = "AGENTS.md"

#: Au-delà, le fichier ne grandit plus. ~1 500 tokens, payés à chaque session.
BUDGET_CLAUDE_MD = 6_000

#: Le seul rôle qui le reçoit.
ROLE = "doc-technique"


def depasse_le_budget(avant: str, apres: str, nom: str = NOM) -> str | None:
    """Pourquoi `apres` est refusé, ou None s'il tient.

    Un fichier sous le budget peut grandir jusqu'à lui ; un fichier déjà
    au-delà ne peut que raccourcir. Refuser tout fichier trop long bloquerait
    justement la modification qui le ferait maigrir.
    """
    plafond = max(len(avant), BUDGET_CLAUDE_MD)
    if len(apres) <= plafond:
        return None
    return (
        f"{nom} dépasserait son budget ({len(apres)} caractères pour "
        f"{plafond} permis) : remplace une phrase fausse, n'en ajoute pas."
    )


def section_du_brief(fichier: Path | None, nom: str = NOM) -> str:
    """Le CLAUDE.md (ou l'AGENTS.md) actuel, à recopier mot pour mot dans les `ancien`."""
    if fichier is None or not fichier.is_file():
        return ""
    contenu = fichier.read_text(encoding="utf-8")
    return (
        f"\n---\n{nom} du projet (fichier `{nom}`, "
        f"{len(contenu)} caractères, budget {BUDGET_CLAUDE_MD}) :\n\n{contenu}"
    )


def sections_du_brief(claude_md: Path | None, agents_md: Path | None) -> str:
    """Les sections du brief pour CLAUDE.md puis AGENTS.md, vides si non fournis."""
    return section_du_brief(claude_md) + section_du_brief(agents_md, NOM_AGENTS)


def agents_md_de(racine: Path, claude_md: Path | None) -> Path | None:
    """L'AGENTS.md de la racine de documentation, aux conditions du CLAUDE.md.

    Fourni seulement si le projet déclare `doc_claude_md` (donc `claude_md`) et
    que le fichier existe : doc-technique ne crée pas un AGENTS.md (ticket-724).
    """
    if claude_md is None:
        return None
    agents_md = racine / NOM_AGENTS
    return agents_md if agents_md.is_file() else None


def verifier_budgets(
    resultat: dict[Path, str], claude_md: Path | None, agents_md: Path | None
) -> None:
    """Refuse (`EditionRefusee`) un CLAUDE.md ou un AGENTS.md qui franchirait son budget."""
    for fichier, nom in ((claude_md, NOM), (agents_md, NOM_AGENTS)):
        if fichier is not None and fichier in resultat:
            refus = depasse_le_budget(fichier.read_text(encoding="utf-8"), resultat[fichier], nom)
            if refus is not None:
                raise EditionRefusee(refus)
