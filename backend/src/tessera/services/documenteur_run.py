"""The documentation step of a run, built from the project's declarations."""

from collections.abc import Awaitable, Callable

from tessera.config import settings
from tessera.services.documentation import DocumentationService, ResultatDocumentation
from tessera.services.journal_pipeline import journal_vers
from tessera.services.politique_run import PolitiqueRun
from tessera.services.project_loader import load_pipeline_config
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.enregistrant import ProviderEnregistrant
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.roles_documentation import roles_de_documentation
from tessera.services.run_worktree import RunWorktree
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def documenteur(
    project_id: str,
    politique: PolitiqueRun | None = None,
    wt: RunWorktree | None = None,
    rapide: bool = False,
) -> Callable[[], Awaitable[ResultatDocumentation]]:
    """Build the documentation update of a project (ticket-092).

    Appelée après chaque run approuvé, sur sa branche (ticket-198), pour le
    lot des tickets livrés depuis le marqueur. Sans outils — elle lit des
    tickets et rend du JSON, elle n'a aucune raison d'écrire elle-même sur le
    disque. `README.md` et `docs/` sont cherchés à la racine d'écriture : le
    projet bootstrap documente l'IDE à la racine du dépôt (ADR-028).

    Avec un worktree (ADR-056), tout ce que le run lit et écrit — tickets,
    marqueur, journal, documentation — est celui du worktree : le checkout
    n'est jamais écrit. La configuration (`agents.json`, `CLAUDE.md`) reste
    lue sur le dossier réel, comme pour les autres services du run.
    """
    project_path = settings.ide_workspace_dir / project_id
    dossier_run = wt.projet if wt is not None else project_path
    politique = politique or PolitiqueRun.lire(project_path)
    racine_doc = politique.racine_ecriture(project_path, wt)

    def _fournisseur(role: str) -> tuple[LLMProvider, str | None]:
        # Deux rôles, chacun son provider et son modèle (ticket-188).
        # Enveloppé pour que les appels de documentation entrent dans
        # `agent_calls` comme les autres (ticket-211).
        inner = provider_pour_role(
            project_path, role, allow_tools=False, project_id=project_id,
            journal_repli=journal_vers(dossier_run / "memory" / "pipeline-log.md"),
            rapide=rapide,
        )
        return (
            ProviderEnregistrant(inner, role=role, db_path=settings.ide_db_path),
            modele_du_role(project_path, role),
        )

    # Le CLAUDE.md du projet, pas celui de la racine d'écriture : pour le
    # projet bootstrap, ce serait celui de Tessera (ticket-244).
    claude_md = (
        project_path / "CLAUDE.md"
        if load_pipeline_config(project_path).doc_claude_md
        else None
    )
    service = DocumentationService(
        _fournisseur("doc-technique")[0], settings.ide_prompts_dir,
        fournisseur=_fournisseur, claude_md=claude_md,
        roles=roles_de_documentation(project_path),
        base=politique.base_branch,
    )

    async def documenter() -> ResultatDocumentation:
        resultat = await service.mettre_a_jour(dossier_run, racine_doc=racine_doc)
        if resultat.fichiers_modifies:
            _logger.info(
                "documentation_mise_a_jour",
                extra={"fichiers": resultat.fichiers_modifies},
            )
        for refus in resultat.refus:
            _logger.warning("documentation_refusee", extra={"motif": refus})
        return resultat

    return documenter
