"""La livraison d'une intervention du superviseur — ticket-854, ADR-080.

Une intervention n'est pas un run approuvé : aucune approbation n'est fabriquée
pour passer la garde de `livrer_phase_1`, qui reste intacte (ADR-030). Ce chemin
a sa propre porte, plus étroite : il relit **lui-même** le diff de la branche
depuis la base et le soumet au contrôle que l'appelant lui donne, ouvre la PR,
et s'arrête là — jamais de merge, jamais de remise à `CIWatcher`, quel que soit
le niveau d'autonomie du projet.

Le contrôle (`refus_de_chemin` du superviseur) est passé en paramètre : le
domaine `supervision` est au-dessus de `livraison` et ne s'y importe pas
(ADR-076). Le contrôle se rejoue après le rebase, sur ce qui part vraiment.
"""
from collections.abc import Callable

from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.livraison.livraison_apres import sha_pousse
from tessera.services.livraison.livraison_arrets import arret_conflit
from tessera.services.livraison.livraison_ports import GitLivraison, WorkflowLivraison
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

PREFIXE_BRANCHE = "supervision-"

#: Chemins du diff (relatifs au projet) -> raison du refus, ou `None` si tout passe.
ControleDuDiff = Callable[[list[str]], str | None]


async def _arret_de_tete(git: GitLivraison, branche: str, sha: str) -> Livraison | None:
    """The stop when the checked-out head is not `sha` on `branche`; fails closed."""
    try:
        courante, tete = await git.branche_courante(), await git.head_sha()
    except GitWorkspaceError as exc:
        return Livraison(branche_modifiee=True, arret=f"la tête de {branche} n'a pas pu être lue : {type(exc).__name__}")
    if courante != branche or tete != sha:
        return Livraison(
            branche_modifiee=True,
            arret=f"la tête de {branche} n'est pas le commit de l'intervention ({sha[:7]}) : rien n'est poussé",
        )
    return None


async def _arret_de_diff(
    git: GitLivraison, base: str, branche: str, controle: ControleDuDiff
) -> Livraison | None:
    """The stop when a path of the branch's diff is refused, or cannot be read."""
    try:
        chemins = await git.fichiers_de_branche(f"origin/{base}", branche)
    except GitWorkspaceError as exc:
        return Livraison(arret=f"le diff de {branche} n'a pas pu être lu : {type(exc).__name__}")
    refus = controle(chemins)
    if refus is not None:
        return Livraison(arret=f"Intervention refusée, rien n'est poussé : {refus}")
    return None


async def _rebaser(git: GitLivraison, base: str, etapes: list[str]) -> Livraison | None:
    """Replay the branch on the base, without resolver; the stop on refusal or conflict."""
    try:
        await git.sync_base_depuis_distant(base)
        conflits = await git.rejouer_sur(base)
    except GitWorkspaceError as exc:
        return Livraison(arret=f"Rebase refusé : {exc}")
    if conflits:
        return Livraison(conflits=conflits, arret=arret_conflit(base, conflits, [], False, None))
    etapes.append(f"rebase sur {base}")
    return None


async def livrer_intervention(
    git: GitLivraison,
    workflow: WorkflowLivraison,
    base: str,
    arret_de_niveau: Livraison | None,
    branche: str,
    sha: str,
    *,
    controle: ControleDuDiff,
    titre: str,
) -> Livraison:
    """Rebase, push and open the PR of an intervention branch; never merge it.

    Nothing is pushed unless `branche` starts with `supervision-`, its head is
    `sha`, and every path of its diff from `origin/<base>` passes `controle`,
    before and after the rebase. A project that declares the `commit` level
    keeps the work local (`arret_de_niveau`).
    """
    if not branche.startswith(PREFIXE_BRANCHE) or not sha:
        return Livraison(arret=f"« {branche} » n'est pas une branche d'intervention : rien n'est poussé")
    if arret_de_niveau is not None:
        return arret_de_niveau
    etapes: list[str] = []
    arret = await _arret_de_tete(git, branche, sha) or await _arret_de_diff(git, base, branche, controle)
    arret = arret or await _rebaser(git, base, etapes) or await _arret_de_diff(git, base, branche, controle)
    if arret is not None:
        return arret
    try:
        pr = await workflow.open_pull_request(
            branch=branche, ticket_id=branche, ticket_title=titre, ticket_body="", ticket_type="chore"
        )
    except Exception as exc:  # noqa: BLE001 — la livraison ne fait pas échouer l'intervention
        _logger.warning("livraison_intervention_echouee", extra={"branche": branche, "erreur": decrire_exception(exc)})
        return Livraison(etapes=tuple(etapes), arret=f"Livraison interrompue : {decrire_exception(exc)}")
    etapes.append(f"PR #{pr.pr_number} ouverte")
    return Livraison(
        etapes=tuple(etapes), durees_ms=(0.0,) * len(etapes), pr_number=pr.pr_number,
        pushed_sha=await sha_pousse(git, branche),
    )
