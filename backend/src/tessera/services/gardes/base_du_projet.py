"""La branche de base d'un run, partagée par le pipeline et la documentation."""
from tessera.config import settings
from tessera.services.gardes.politique_run import PolitiqueRun


def base_du_projet(politique: PolitiqueRun) -> str:
    """The base branch a run starts from: the declared one, else the global default."""
    return politique.base_branch or settings.github_base_branch
