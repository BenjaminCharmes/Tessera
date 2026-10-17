"""Ce qu'un run ne pourra pas faire, lu avant son premier ticket — ticket-477.

Curio, souhaito : un ticket entier (codeur, revues, PR, de 2 à 7 $) avant de
découvrir un `github_remote` absent, une CI inexistante ou un `pnpm` introuvable.
Chacune de ces conditions se lit dès le lancement. On les rassemble ici, pour
que le refus liste tous les manques d'un coup plutôt qu'un par tentative.
"""
import shutil
from pathlib import Path

from tessera.services.autonomie import NiveauAutonomie
from tessera.services.commande_chainee import decouper
from tessera.services.livraison_possible import raison_de_refus_livraison
from tessera.services.politique_run import PolitiqueRun
from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd
from tessera.services.project_loader import load_pipeline_config


def manques_avant_depart(project_path: Path, github_token: str) -> list[str]:
    """Return every reason the run could not deliver or test, empty when fine.

    Reads the project's declared policy only: no network call, no process. A
    folder that does not exist yields nothing, the run reports it itself.
    """
    if not project_path.is_dir():
        return []
    politique = PolitiqueRun.lire(project_path)
    manques: list[str] = []
    livraison = raison_de_refus_livraison(project_path, github_token)
    if livraison:
        manques.append(livraison)
    manques.extend(_manque_de_ci(project_path, politique))
    manques.extend(_commandes_introuvables(project_path, politique))
    return manques


def _manque_de_ci(project_path: Path, politique: PolitiqueRun) -> list[str]:
    """Un projet en `merge` sans CI ne mergerait jamais : « CI none »."""
    if politique.autonomy is not NiveauAutonomie.merge or politique.merge_without_ci:
        return []
    racine = politique.racine_ecriture(project_path)
    if _a_un_workflow(racine):
        return []
    return [
        "autonomy `merge` sans aucun workflow `.github/workflows/*.yml` : "
        "ajouter une CI ou déclarer `merge_without_ci`"
    ]


def _a_un_workflow(racine: Path) -> bool:
    dossier = racine / ".github" / "workflows"
    if not dossier.is_dir():
        return False
    return any(dossier.glob("*.yml")) or any(dossier.glob("*.yaml"))


def _commandes_introuvables(project_path: Path, politique: PolitiqueRun) -> list[str]:
    """Le premier mot de chaque segment `&&` du `test_command` doit se résoudre."""
    if not politique.test_command:
        return []
    try:
        etapes = decouper(politique.test_command)
    except ValueError as exc:
        return [f"`test_command` illisible : {exc}"]
    dossier = _dossier_de_test(project_path)
    manques: list[str] = []
    for etape in etapes:
        programme = etape[0]
        if not _se_resout(programme, dossier) and programme not in manques:
            manques.append(programme)
    return [f"commande de test introuvable : `{nom}`" for nom in manques]


def _dossier_de_test(project_path: Path) -> Path:
    """Le dossier où le testeur lance sa commande, repli sur le projet."""
    cwd = load_pipeline_config(project_path).test_cwd
    if not cwd:
        return project_path
    try:
        return resoudre_le_cwd(project_path, cwd)
    except CommandeInvalide:
        return project_path


def _se_resout(programme: str, dossier: Path) -> bool:
    """Trouvable sur le PATH (PATHEXT inclus sous Windows) ou chemin existant."""
    if shutil.which(programme) is not None:
        return True
    return (dossier / programme).exists()
