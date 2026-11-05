"""Services domains: their order and the flat modules still to move (ADR-076).

Data only, without any `tessera` import: read by
`backend/tests/test_domaines_services.py` (ticket-826) and by
`scripts/deplacer_domaine.py` (ticket-827), which removes a domain's lines
from `A_DEPLACER` once its modules live in `services/<domaine>/`.
"""

# Les dix-huit domaines, du rang le plus bas au plus haut : un module n'importe
# que son domaine ou un domaine de rang plus bas (ADR-076).
ORDRE: tuple[str, ...] = (
    "noyau",
    "projets",
    "usage",
    "provisioning",
    "gardes",
    "git_workspace",
    "worktrees",
    "github",
    "providers",
    "verification",
    "verdicts",
    "agents",
    "documentation",
    "creation_projet",
    "livraison",
    "pipeline",
    "file",
    "supervision",
)

# Module encore à plat dans `services/` -> son domaine. Photo de départ :
# `projects/ide-core/memory/services-domaines.md`, plus les trois modules des
# leçons (tickets 801 à 804), nés depuis, et vingt-six modules reclassés au
# ticket-826 là où un seul déplacement supprimait un import montant. Une ligne
# par module : le script de déplacement retire les lignes d'un domaine en le
# déplaçant.
A_DEPLACER: dict[str, str] = {
}
