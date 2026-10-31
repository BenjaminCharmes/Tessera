"""Pipeline settings of a project — ticket-196, ticket-689."""

from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel

from tessera.routers.projects.shared import new_router, require_project_path
from tessera.services.politique_run import PolitiqueRun
from tessera.services.project_loader import (
    AgentAbsentDuProjet,
    load_pipeline_config,
    set_pipeline_settings,
)
from tessera.services.run_registry import RUN_REGISTRY

router = new_router()


class PipelineReglages(BaseModel):
    """La configuration effective du pipeline d'un projet (ticket-196)."""

    max_review_rounds: int
    testeur_enabled: bool
    test_command: str | None
    securite_enabled: bool
    validateur_enabled: bool
    autonomy: str
    merge_without_ci: bool


class PipelineReglagesPatch(BaseModel):
    """Les seuls champs à changer ; les autres ne bougent pas."""

    max_review_rounds: int | None = None
    testeur_enabled: bool | None = None
    test_command: str | None = None
    securite_enabled: bool | None = None
    validateur_enabled: bool | None = None
    autonomy: str | None = None
    merge_without_ci: bool | None = None
    #: Écrite à la racine du manifeste ; vide (ou `null`), elle est retirée.
    category: str | None = None


_NIVEAUX = ("commit", "pr", "merge")


def _reglages(project_path: Path) -> PipelineReglages:
    cfg = load_pipeline_config(project_path)
    politique = PolitiqueRun.lire(project_path)
    return PipelineReglages(
        max_review_rounds=cfg.max_review_rounds,
        testeur_enabled=cfg.testeur_enabled,
        test_command=cfg.test_command,
        securite_enabled=cfg.securite_enabled,
        validateur_enabled=cfg.validateur_enabled,
        autonomy=politique.autonomy.value,
        merge_without_ci=politique.merge_without_ci,
    )


@router.get("/{project_id}/pipeline", response_model=PipelineReglages)
async def get_pipeline_settings(project_id: str) -> PipelineReglages:
    """Ce que le pipeline de ce projet fait, défauts appliqués."""
    return _reglages(require_project_path(project_id))


@router.patch("/{project_id}/pipeline", response_model=PipelineReglages)
async def set_pipeline_settings_route(
    project_id: str, body: PipelineReglagesPatch
) -> PipelineReglages:
    """Change les réglages reçus, en préservant le reste du manifeste.

    Refusé pendant un run : la politique est lue une fois avant le premier
    agent (ADR-027), un changement ne vaudrait qu'au run suivant, et l'écran
    doit le dire plutôt que laisser croire à un effet immédiat.
    """
    project_path = require_project_path(project_id)
    if RUN_REGISTRY.projet_occupe(project_id):
        raise HTTPException(
            status_code=409,
            detail="Un run est en cours : les réglages s'appliqueront au run suivant, "
            "modifie-les une fois le run terminé.",
        )
    recus = body.model_dump(exclude_unset=True)
    categorie_recue = "category" in recus
    categorie = (recus.pop("category", None) or "").strip()
    actuel = _reglages(project_path)
    fusion = actuel.model_copy(update=recus)
    if fusion.autonomy not in _NIVEAUX:
        raise HTTPException(
            status_code=400,
            detail=f"autonomy inconnue : {fusion.autonomy!r}. Valeurs : {', '.join(_NIVEAUX)}.",
        )
    if fusion.testeur_enabled and not (fusion.test_command or "").strip():
        # Un flag à vrai sans commande valide est pire qu'un flag à faux : le
        # lanceur avale l'erreur et rend `True`, si bien que l'absence de
        # tests se lirait comme des tests verts.
        raise HTTPException(
            status_code=400,
            detail="testeur_enabled exige une test_command : sans elle, l'absence "
            "de tests se lirait comme des tests verts.",
        )
    pipeline = {k: v for k, v in recus.items() if k not in ("autonomy", "merge_without_ci")}
    racine = {k: v for k, v in recus.items() if k in ("autonomy", "merge_without_ci")}
    retirer: tuple[str, ...] = ()
    if categorie_recue and categorie:
        racine["category"] = categorie
    elif categorie_recue:
        retirer = ("category",)
    try:
        set_pipeline_settings(
            project_path, pipeline=pipeline, racine=racine, retirer=retirer
        )
    except AgentAbsentDuProjet as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _reglages(project_path)
