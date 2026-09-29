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

#: Le nom sous lequel l'agent désigne le CLAUDE.md du projet.
NOM = "CLAUDE.md"

#: Au-delà, le fichier ne grandit plus. ~1 500 tokens, payés à chaque session.
BUDGET_CLAUDE_MD = 6_000

#: Le seul rôle qui le reçoit.
ROLE = "doc-technique"


def depasse_le_budget(avant: str, apres: str) -> str | None:
    """Pourquoi `apres` est refusé, ou None s'il tient.

    Un fichier sous le budget peut grandir jusqu'à lui ; un fichier déjà
    au-delà ne peut que raccourcir. Refuser tout fichier trop long bloquerait
    justement la modification qui le ferait maigrir.
    """
    plafond = max(len(avant), BUDGET_CLAUDE_MD)
    if len(apres) <= plafond:
        return None
    return (
        f"CLAUDE.md dépasserait son budget ({len(apres)} caractères pour "
        f"{plafond} permis) : remplace une phrase fausse, n'en ajoute pas."
    )


def section_du_brief(claude_md: Path | None) -> str:
    """Le CLAUDE.md actuel, à recopier mot pour mot dans les `ancien`."""
    if claude_md is None or not claude_md.is_file():
        return ""
    contenu = claude_md.read_text(encoding="utf-8")
    return (
        "\n---\nCLAUDE.md du projet (fichier `CLAUDE.md`, "
        f"{len(contenu)} caractères, budget {BUDGET_CLAUDE_MD}) :\n\n{contenu}"
    )
